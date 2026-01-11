"""
ScreenScraper.fr API client
"""
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urlencode

from scrapers.base import BaseScraper, ScraperGame
from utils.logger import get_logger
from utils.filename import calculate_similarity

logger = get_logger()


# Batocera system ID to ScreenScraper platform ID mapping
SYSTEM_ID_MAP = {
    # Nintendo
    'nes': 3,  # Nintendo Entertainment System
    'snes': 4,  # Super Nintendo
    'n64': 14,  # Nintendo 64
    'gb': 9,  # Game Boy
    'gbc': 10,  # Game Boy Color
    'gba': 12,  # Game Boy Advance
    # Sega
    'md': 1,  # Sega Mega Drive/Genesis
    'sms': 2,  # Sega Master System
    'gg': 21,  # Game Gear
    'dreamcast': 23,  # Sega Dreamcast
    'saturn': 22,  # Sega Saturn
    # Sony
    'psx': 57,  # Sony PlayStation
    'ps2': 58,  # Sony PlayStation 2
    'psp': 61,  # Sony PSP
    # NEC
    'pce': 31,  # PC Engine/TurboGrafx-16
    # Arcade
    'arcade': 75,  # Arcade
    'mame': 75,  # MAME (same as arcade)
    'fba': 75,  # FinalBurn Alpha (same as arcade)
    # Atari
    'atari2600': 26,  # Atari 2600
    'atari7800': 43,  # Atari 7800
    'lynx': 28,  # Atari Lynx
    'jaguar': 27,  # Atari Jaguar
    # SNK
    'ngp': 25,  # Neo Geo Pocket
    'ngpc': 82,  # Neo Geo Pocket Color
    # Bandai
    'wonderswan': 45,  # WonderSwan
    'wonderswancolor': 46,  # WonderSwan Color
    # Commodore
    'c64': 66,  # Commodore 64
    'vic20': 73,  # VIC-20
    'amiga': 64,  # Amiga
    'amigacd32': 130,  # Amiga CD32
    # Other computers
    'zxspectrum': 76,  # ZX Spectrum
    'amstradcpc': 65,  # Amstrad CPC
    'msx': 113,  # MSX
    'msx1': 113,  # MSX1 (same as MSX)
    'msx2': 116,  # MSX2
}


class ScreenScraperError(Exception):
    """ScreenScraper API error"""
    pass


class RateLimitError(ScreenScraperError):
    """Rate limit exceeded"""
    pass


class ScreenScraper(BaseScraper):
    """ScreenScraper.fr API client"""

    BASE_URL = "https://www.screenscraper.fr/api2"

    def __init__(self, config: Dict):
        """
        Initialize ScreenScraper client

        Args:
            config: Configuration with credentials and settings
        """
        super().__init__(config)

        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.dev_id = config.get('dev_id', '')
        self.dev_password = config.get('dev_password', '')
        self.soft_name = config.get('soft_name', 'retroMaid')

        # Rate limiting
        self.rate_limit = config.get('rate_limit', 20)  # requests per minute
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.rate_limit  # seconds between requests

        if not self.username or not self.password:
            logger.warning("ScreenScraper credentials not configured")

    @property
    def name(self) -> str:
        return "ScreenScraper"

    @property
    def requires_auth(self) -> bool:
        return True

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits"""
        elapsed = time.time() - self.last_request_time

        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _build_auth_params(self) -> Dict[str, str]:
        """Build authentication parameters"""
        params = {
            'softname': self.soft_name,
            'output': 'json',
        }

        # Add developer credentials if available
        if self.dev_id and self.dev_password:
            params['devid'] = self.dev_id
            params['devpassword'] = self.dev_password

        # Add user credentials
        if self.username and self.password:
            params['ssid'] = self.username
            params['sspassword'] = self.password

        return params

    def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict:
        """
        Make API request with rate limiting and error handling

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            JSON response

        Raises:
            ScreenScraperError: On API error
            RateLimitError: On rate limit exceeded
        """
        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}/{endpoint}.php"
        all_params = {**self._build_auth_params(), **params}

        try:
            logger.debug(f"ScreenScraper request: {endpoint} with params: {params}")
            response = requests.get(url, params=all_params, timeout=30)

            # Check for HTTP errors
            if response.status_code == 429:
                raise RateLimitError("Thread limit exceeded")
            elif response.status_code == 430:
                raise RateLimitError("Daily quota exceeded")
            elif response.status_code == 426:
                raise ScreenScraperError("Software version blacklisted")
            elif response.status_code == 401:
                raise ScreenScraperError("Invalid credentials")
            elif response.status_code != 200:
                raise ScreenScraperError(f"HTTP {response.status_code}: {response.text}")

            data = response.json()

            # Check for API-level errors
            if 'header' in data and 'APIversion' not in data['header']:
                error = data.get('header', {}).get('error', 'Unknown error')
                raise ScreenScraperError(f"API error: {error}")

            return data

        except requests.exceptions.Timeout:
            raise ScreenScraperError("Request timeout")
        except requests.exceptions.RequestException as e:
            raise ScreenScraperError(f"Request failed: {e}")
        except ValueError as e:
            raise ScreenScraperError(f"Invalid JSON response: {e}")

    def search_by_hash(
        self,
        rom_hash: str,
        hash_type: str,
        system: str,
        file_size: Optional[int] = None
    ) -> Optional[ScraperGame]:
        """
        Search for game by ROM hash

        Args:
            rom_hash: ROM file hash
            hash_type: Type of hash ('md5', 'sha1', 'crc')
            system: System/platform name
            file_size: Optional file size

        Returns:
            Matching game or None
        """
        # Get ScreenScraper system ID
        system_id = SYSTEM_ID_MAP.get(system)
        if system_id is None:
            logger.warning(f"Unknown system for ScreenScraper: {system}")
            return None

        params = {
            'systemeid': str(system_id),
        }

        # Add hash parameter
        if hash_type.lower() == 'md5':
            params['md5'] = rom_hash.lower()
        elif hash_type.lower() == 'sha1':
            params['sha1'] = rom_hash.lower()
        elif hash_type.lower() in ['crc', 'crc32']:
            params['crc'] = rom_hash.upper()
        else:
            logger.error(f"Unsupported hash type: {hash_type}")
            return None

        # Add file size if provided
        if file_size is not None:
            params['romtaille'] = str(file_size)

        try:
            data = self._make_request('jeuInfos', params)

            # Parse game info
            if 'response' in data and 'jeu' in data['response']:
                return self._parse_game(data['response']['jeu'])

            return None

        except ScreenScraperError as e:
            logger.error(f"ScreenScraper error: {e}")
            return None

    def search_by_name(
        self,
        game_name: str,
        system: str,
        region: Optional[str] = None
    ) -> List[ScraperGame]:
        """
        Search for games by name

        Args:
            game_name: Game name to search for
            system: System/platform name
            region: Optional region filter

        Returns:
            List of matching games
        """
        # Get ScreenScraper system ID
        system_id = SYSTEM_ID_MAP.get(system)
        if system_id is None:
            logger.warning(f"Unknown system for ScreenScraper: {system}")
            return []

        params = {
            'systemeid': str(system_id),
            'recherche': game_name,
        }

        try:
            data = self._make_request('jeuRecherche', params)

            # Parse results
            if 'response' in data and 'jeux' in data['response']:
                jeux = data['response']['jeux']

                # Handle both single game and multiple games
                if isinstance(jeux, dict):
                    # Single game - check if it's a game object or a dict of games
                    if 'jeu' in jeux:
                        jeux = [jeux['jeu']]
                    else:
                        # It's a dict of games, convert to list
                        jeux = list(jeux.values())
                elif isinstance(jeux, list):
                    # Already a list
                    pass
                else:
                    return []

                games = []
                for jeu_data in jeux:
                    game = self._parse_game(jeu_data)
                    if game:
                        # Calculate match confidence based on name similarity
                        game.confidence = calculate_similarity(game_name, game.name)
                        games.append(game)

                # Sort by confidence
                games.sort(key=lambda g: g.confidence, reverse=True)

                return games

            return []

        except ScreenScraperError as e:
            logger.error(f"ScreenScraper error: {e}")
            return []

    def get_game_by_id(self, game_id: str) -> Optional[ScraperGame]:
        """
        Get game details by ScreenScraper game ID

        Args:
            game_id: Game ID

        Returns:
            Game details or None
        """
        params = {
            'gameid': game_id,
        }

        try:
            data = self._make_request('jeuInfos', params)

            if 'response' in data and 'jeu' in data['response']:
                return self._parse_game(data['response']['jeu'])

            return None

        except ScreenScraperError as e:
            logger.error(f"ScreenScraper error: {e}")
            return None

    def _parse_game(self, jeu: Dict) -> Optional[ScraperGame]:
        """
        Parse game data from API response

        Args:
            jeu: Game data dictionary

        Returns:
            ScraperGame object or None
        """
        try:
            game_id = str(jeu.get('id', ''))
            if not game_id:
                return None

            # Get game names (prefer English)
            names = jeu.get('noms', [])
            name = self._get_text_by_region(names, 'en') or self._get_text_by_region(names)

            if not name:
                return None

            # Get descriptions
            descriptions = jeu.get('synopsis', [])
            description = self._get_text_by_region(descriptions, 'en') or self._get_text_by_region(descriptions)

            # Get release date
            release_date = None
            dates = jeu.get('dates', [])
            if dates:
                # Try to find a date entry
                date_entry = dates[0] if isinstance(dates, list) else dates
                if isinstance(date_entry, dict):
                    date_text = date_entry.get('text', '')
                    if date_text:
                        try:
                            # Parse date (format: YYYY-MM-DD)
                            release_date = date_text
                        except:
                            pass

            # Get developer/publisher
            developer = None
            publisher = None

            developpeur = jeu.get('developpeur')
            if developpeur:
                developer = developpeur.get('text') if isinstance(developpeur, dict) else str(developpeur)

            editeur = jeu.get('editeur')
            if editeur:
                publisher = editeur.get('text') if isinstance(editeur, dict) else str(editeur)

            # Get genre
            genres = jeu.get('genres', [])
            genre = None
            if genres:
                genre_entry = genres[0] if isinstance(genres, list) else genres
                if isinstance(genre_entry, dict):
                    # Prefer English genre name
                    genre_names = genre_entry.get('noms', [])
                    genre = self._get_text_by_region(genre_names, 'en') or self._get_text_by_region(genre_names)

            # Get players
            players = jeu.get('joueurs', {})
            players_text = players.get('text', '1') if isinstance(players, dict) else None

            # Get region
            region = jeu.get('region', {})
            region_text = region.get('text') if isinstance(region, dict) else None

            # Get media URLs
            medias = jeu.get('medias', [])

            game = ScraperGame(
                id=game_id,
                name=name,
                description=description,
                release_date=release_date,
                developer=developer,
                publisher=publisher,
                genre=genre,
                players=players_text,
                region=region_text,
                source="ScreenScraper"
            )

            # Parse media
            for media in medias:
                if not isinstance(media, dict):
                    continue

                media_type = media.get('type', '')
                media_url = media.get('url', '')

                if not media_url:
                    continue

                # Map media types to game fields
                if media_type == 'box-2D':
                    game.box_art_url = media_url
                elif media_type == 'ss' or media_type == 'sstitle':
                    if not game.screenshot_url:  # Use first screenshot
                        game.screenshot_url = media_url
                elif media_type == 'wheel':
                    game.marquee_url = media_url
                elif media_type == 'video':
                    if not game.video_url:
                        game.video_url = media_url
                elif media_type == 'box-texture':
                    if not game.thumbnail_url:
                        game.thumbnail_url = media_url

            # Use box art as thumbnail if no thumbnail found
            if not game.thumbnail_url and game.box_art_url:
                game.thumbnail_url = game.box_art_url

            return game

        except Exception as e:
            logger.error(f"Error parsing game data: {e}")
            return None

    def _get_text_by_region(self, items: List[Dict], region: str = None) -> Optional[str]:
        """
        Get text from a list of region-specific items

        Args:
            items: List of text items with region info
            region: Preferred region code (e.g., 'en', 'us')

        Returns:
            Text string or None
        """
        if not items:
            return None

        if not isinstance(items, list):
            if isinstance(items, dict):
                return items.get('text')
            return str(items)

        # Try to find preferred region
        if region:
            for item in items:
                if isinstance(item, dict):
                    if item.get('region') == region or item.get('langue') == region:
                        return item.get('text')

        # Fall back to first item
        if items:
            first = items[0]
            if isinstance(first, dict):
                return first.get('text')
            return str(first)

        return None
