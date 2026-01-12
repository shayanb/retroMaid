"""
IGDB (Internet Game Database) API client
"""
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from scrapers.base import BaseScraper, ScraperGame
from utils.logger import get_logger
from utils.filename import calculate_similarity

logger = get_logger()


# Batocera system ID to IGDB platform ID mapping
SYSTEM_ID_MAP = {
    # Nintendo
    'nes': 18,  # Nintendo Entertainment System
    'snes': 19,  # Super Nintendo Entertainment System
    'n64': 4,  # Nintendo 64
    'gb': 33,  # Game Boy
    'gbc': 22,  # Game Boy Color
    'gba': 24,  # Game Boy Advance
    'nds': 20,  # Nintendo DS
    '3ds': 37,  # Nintendo 3DS
    'switch': 130,  # Nintendo Switch
    'wii': 5,  # Wii
    'wiiu': 41,  # Wii U
    'gamecube': 21,  # GameCube
    # Sega
    'md': 29,  # Sega Mega Drive/Genesis
    'sms': 64,  # Sega Master System
    'gg': 35,  # Game Gear
    'sg1000': 84,  # Sega SG-1000
    'sega32x': 30,  # Sega 32X
    '32x': 30,  # Sega 32X (alias)
    'dreamcast': 23,  # Sega Dreamcast
    'saturn': 32,  # Sega Saturn
    'megadrive': 29,  # Mega Drive (alias)
    'genesis': 29,  # Genesis (alias)
    # Sony
    'psx': 7,  # Sony PlayStation
    'ps2': 8,  # Sony PlayStation 2
    'ps3': 9,  # Sony PlayStation 3
    'ps4': 48,  # Sony PlayStation 4
    'ps5': 167,  # Sony PlayStation 5
    'psp': 38,  # Sony PSP
    'psvita': 46,  # PlayStation Vita
    # Microsoft
    'xbox': 11,  # Xbox
    'xbox360': 12,  # Xbox 360
    'xboxone': 49,  # Xbox One
    'xboxseries': 169,  # Xbox Series X/S
    # NEC
    'pce': 86,  # PC Engine/TurboGrafx-16
    'pcengine': 86,  # PC Engine (alias)
    'pcenginecd': 150,  # PC Engine CD
    # Arcade
    'arcade': 52,  # Arcade
    'mame': 52,  # MAME (same as arcade)
    'fba': 52,  # FinalBurn Alpha (same as arcade)
    'neogeo': 80,  # Neo Geo
    # Atari
    'atari2600': 59,  # Atari 2600
    'atari7800': 60,  # Atari 7800
    'atarist': 63,  # Atari ST
    'lynx': 46,  # Atari Lynx
    'jaguar': 62,  # Atari Jaguar
    # SNK
    'ngp': 119,  # Neo Geo Pocket
    'ngpc': 120,  # Neo Geo Pocket Color
    # Bandai
    'wonderswan': 57,  # WonderSwan
    'wonderswancolor': 56,  # WonderSwan Color
    # Commodore
    'c64': 15,  # Commodore 64
    'vic20': 71,  # VIC-20
    'amiga': 16,  # Amiga
    'amigacd32': 117,  # Amiga CD32
    # Other computers
    'zxspectrum': 26,  # ZX Spectrum
    'amstradcpc': 25,  # Amstrad CPC
    'msx': 27,  # MSX
    'msx1': 27,  # MSX1 (same as MSX)
    'msx2': 27,  # MSX2 (same as MSX)
    'dos': 13,  # PC (DOS)
}


class IGDBError(Exception):
    """IGDB API error"""
    pass


class RateLimitError(IGDBError):
    """Rate limit exceeded"""
    pass


class IGDB(BaseScraper):
    """IGDB API client"""

    BASE_URL = "https://api.igdb.com/v4"
    AUTH_URL = "https://id.twitch.tv/oauth2/token"

    def __init__(self, config: Dict):
        """
        Initialize IGDB client

        Args:
            config: Configuration with credentials
        """
        super().__init__(config)

        self.client_id = config.get('client_id', '')
        self.client_secret = config.get('client_secret', '')

        # Access token management
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        # Rate limiting
        self.rate_limit = config.get('rate_limit', 4)  # 4 requests per second
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.rate_limit

        if not self.client_id or not self.client_secret:
            logger.warning("IGDB credentials not configured")

    @property
    def name(self) -> str:
        return "IGDB"

    @property
    def requires_auth(self) -> bool:
        return True

    def _get_access_token(self) -> str:
        """
        Get or refresh access token

        Returns:
            Access token

        Raises:
            IGDBError: On authentication failure
        """
        # Check if token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token

        # Request new token
        logger.info("Requesting new IGDB access token")

        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(self.AUTH_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            self.access_token = data['access_token']
            expires_in = data.get('expires_in', 3600)

            # Set expiration time (subtract 60 seconds for buffer)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

            logger.info("IGDB access token obtained")
            return self.access_token

        except requests.exceptions.RequestException as e:
            raise IGDBError(f"Failed to get access token: {e}")

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits"""
        elapsed = time.time() - self.last_request_time

        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, query: str) -> List[Dict]:
        """
        Make IGDB API request

        Args:
            endpoint: API endpoint (e.g., 'games')
            query: Apicalypse query string

        Returns:
            List of results

        Raises:
            IGDBError: On API error
        """
        self._wait_for_rate_limit()

        token = self._get_access_token()
        url = f"{self.BASE_URL}/{endpoint}"

        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }

        try:
            logger.debug(f"IGDB request to {endpoint}: {query}")
            response = requests.post(url, headers=headers, data=query, timeout=30)

            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status_code == 401:
                # Token expired, clear it and retry once
                self.access_token = None
                self.token_expires_at = None
                raise IGDBError("Token expired, retry needed")
            elif response.status_code != 200:
                raise IGDBError(f"HTTP {response.status_code}: {response.text}")

            return response.json()

        except requests.exceptions.Timeout:
            raise IGDBError("Request timeout")
        except requests.exceptions.RequestException as e:
            raise IGDBError(f"Request failed: {e}")

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
        # Get IGDB platform ID
        platform_id = SYSTEM_ID_MAP.get(system)
        if platform_id is None:
            logger.warning(f"Unknown system for IGDB: {system}")
            return []

        # Build query
        # Use flexible search without strict quoting for better matching
        # Remove special characters that might cause issues
        search_term = game_name.replace('"', '').replace("'", "")

        query = f"""
        search "{search_term}";
        fields name, summary, first_release_date, genres.name,
               involved_companies.company.name, involved_companies.developer,
               cover.url, screenshots.url, artworks.url, videos.video_id;
        where platforms = ({platform_id});
        limit 25;
        """

        logger.debug(f"IGDB query for '{game_name}' on platform {platform_id}")
        logger.debug(f"IGDB full query:\n{query}")

        try:
            results = self._make_request('games', query)
            logger.debug(f"IGDB returned {len(results)} results for '{game_name}'")

            games = []
            for game_data in results:
                game = self._parse_game(game_data)
                if game:
                    # Calculate match confidence
                    game.confidence = calculate_similarity(game_name, game.name)
                    games.append(game)

            # Sort by confidence
            games.sort(key=lambda g: g.confidence, reverse=True)

            return games

        except IGDBError as e:
            # Re-raise authentication and JSON errors so verification can detect them
            error_str = str(e).lower()
            if any(err in error_str for err in ['403', '401', 'unauthorized', 'credentials', 'token', 'json', 'expecting value', 'decode']):
                raise
            # Log and return empty list for other errors
            logger.error(f"IGDB error: {e}")
            return []

    def get_game_by_id(self, game_id: str) -> Optional[ScraperGame]:
        """
        Get game details by IGDB game ID

        Args:
            game_id: Game ID

        Returns:
            Game details or None
        """
        query = f"""
        fields name, summary, first_release_date, genres.name,
               involved_companies.company.name, involved_companies.developer,
               cover.url, screenshots.url, artworks.url, videos.video_id;
        where id = {game_id};
        """

        try:
            results = self._make_request('games', query)

            if results:
                return self._parse_game(results[0])

            return None

        except IGDBError as e:
            logger.error(f"IGDB error: {e}")
            return None

    def _parse_game(self, game_data: Dict) -> Optional[ScraperGame]:
        """
        Parse game data from API response

        Args:
            game_data: Game data dictionary

        Returns:
            ScraperGame object or None
        """
        try:
            game_id = str(game_data.get('id', ''))
            name = game_data.get('name', '')

            if not game_id or not name:
                return None

            # Description
            description = game_data.get('summary')

            # Release date
            release_date = None
            timestamp = game_data.get('first_release_date')
            if timestamp:
                try:
                    dt = datetime.fromtimestamp(timestamp)
                    release_date = dt.strftime('%Y-%m-%d')
                except:
                    pass

            # Genres
            genre = None
            genres = game_data.get('genres', [])
            if genres:
                genre = genres[0].get('name') if isinstance(genres[0], dict) else None

            # Developer/Publisher
            developer = None
            publisher = None
            companies = game_data.get('involved_companies', [])
            for company_entry in companies:
                if isinstance(company_entry, dict):
                    company = company_entry.get('company', {})
                    company_name = company.get('name') if isinstance(company, dict) else None

                    if company_name:
                        if company_entry.get('developer'):
                            developer = company_name
                        else:
                            publisher = company_name

            # Cover art
            box_art_url = None
            cover = game_data.get('cover')
            if cover and isinstance(cover, dict):
                url = cover.get('url', '')
                if url:
                    # Convert to HTTPS and larger size
                    box_art_url = url.replace('t_thumb', 't_cover_big').replace('//', 'https://')

            # Screenshots
            screenshot_url = None
            screenshots = game_data.get('screenshots', [])
            if screenshots and isinstance(screenshots, list) and len(screenshots) > 0:
                url = screenshots[0].get('url', '')
                if url:
                    screenshot_url = url.replace('t_thumb', 't_screenshot_big').replace('//', 'https://')

            # Artworks
            artwork_url = None
            artworks = game_data.get('artworks', [])
            if artworks and isinstance(artworks, list) and len(artworks) > 0:
                url = artworks[0].get('url', '')
                if url:
                    artwork_url = url.replace('t_thumb', 't_1080p').replace('//', 'https://')

            # Videos
            video_url = None
            videos = game_data.get('videos', [])
            if videos and isinstance(videos, list) and len(videos) > 0:
                video_id = videos[0].get('video_id')
                if video_id:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

            game = ScraperGame(
                id=game_id,
                name=name,
                description=description,
                release_date=release_date,
                developer=developer,
                publisher=publisher,
                genre=genre,
                source="IGDB"
            )

            game.box_art_url = box_art_url
            game.screenshot_url = screenshot_url
            game.thumbnail_url = box_art_url  # Use cover as thumbnail
            game.marquee_url = artwork_url
            game.video_url = video_url

            return game

        except Exception as e:
            logger.error(f"Error parsing IGDB game data: {e}")
            return None

    def search_by_hash(
        self,
        rom_hash: str,
        hash_type: str,
        system: str,
        file_size: Optional[int] = None
    ) -> Optional[ScraperGame]:
        """
        IGDB doesn't support hash-based search
        """
        return None
