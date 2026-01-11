"""
TheGamesDB API client
"""
import time
import requests
from typing import Dict, List, Optional

from scrapers.base import BaseScraper, ScraperGame
from utils.logger import get_logger
from utils.filename import calculate_similarity

logger = get_logger()


# Batocera system ID to TheGamesDB platform ID mapping
SYSTEM_ID_MAP = {
    # Nintendo
    'nes': 7,  # Nintendo Entertainment System (NES)
    'snes': 6,  # Super Nintendo (SNES)
    'n64': 3,  # Nintendo 64
    'gb': 4,  # Nintendo Game Boy
    'gbc': 41,  # Nintendo Game Boy Color
    'gba': 5,  # Nintendo Game Boy Advance
    'nds': 8,  # Nintendo DS
    '3ds': 4912,  # Nintendo 3DS
    'switch': 4971,  # Nintendo Switch
    'wii': 9,  # Nintendo Wii
    'wiiu': 38,  # Nintendo Wii U
    'gamecube': 2,  # Nintendo GameCube
    # Sega
    'md': 18,  # Sega Genesis
    'genesis': 18,  # Sega Genesis (alias)
    'megadrive': 18,  # Sega Mega Drive (alias)
    'sms': 35,  # Sega Master System
    'gg': 20,  # Sega Game Gear
    'dreamcast': 16,  # Sega Dreamcast
    'saturn': 17,  # Sega Saturn
    '32x': 33,  # Sega 32X
    'segacd': 21,  # Sega CD
    # Sony
    'psx': 10,  # Sony Playstation
    'ps2': 11,  # Sony Playstation 2
    'ps3': 12,  # Sony Playstation 3
    'ps4': 4919,  # Sony Playstation 4
    'ps5': 4920,  # Sony Playstation 5
    'psp': 13,  # Sony PSP
    'psvita': 39,  # Sony Playstation Vita
    # Microsoft
    'xbox': 14,  # Microsoft Xbox
    'xbox360': 15,  # Microsoft Xbox 360
    'xboxone': 4920,  # Microsoft Xbox One
    # NEC
    'pce': 34,  # TurboGrafx 16
    'pcengine': 34,  # PC Engine (alias)
    'pcenginecd': 40,  # TurboGrafx CD
    # Arcade
    'arcade': 23,  # Arcade
    'mame': 23,  # MAME (same as arcade)
    'neogeo': 24,  # Neo Geo
    # Atari
    'atari2600': 22,  # Atari 2600
    'atari5200': 26,  # Atari 5200
    'atari7800': 27,  # Atari 7800
    'atarist': 4937,  # Atari ST
    'lynx': 28,  # Atari Lynx
    'jaguar': 29,  # Atari Jaguar
    # SNK
    'ngp': 4922,  # Neo Geo Pocket
    'ngpc': 4923,  # Neo Geo Pocket Color
    # Commodore
    'c64': 40,  # Commodore 64
    'amiga': 4911,  # Amiga
    # Other computers
    'dos': 1,  # PC
    'msx': 4929,  # MSX
}


class TheGamesDBError(Exception):
    """TheGamesDB API error"""
    pass


class TheGamesDB(BaseScraper):
    """TheGamesDB API client"""

    BASE_URL = "https://api.thegamesdb.net/v1"

    def __init__(self, config: Dict):
        """
        Initialize TheGamesDB client

        Args:
            config: Configuration with API key
        """
        super().__init__(config)

        self.api_key = config.get('api_key', '')

        # Rate limiting (no API key = 1 request/sec, with key = 3000/day)
        self.rate_limit = config.get('rate_limit', 1)  # requests per second
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.rate_limit

        # Image base URLs (cached from API)
        self.image_base_url = "https://cdn.thegamesdb.net/images/"

    @property
    def name(self) -> str:
        return "TheGamesDB"

    @property
    def requires_auth(self) -> bool:
        return False  # API key is optional

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits"""
        elapsed = time.time() - self.last_request_time

        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict:
        """
        Make API request

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            JSON response

        Raises:
            TheGamesDBError: On API error
        """
        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"

        # Add API key if available
        if self.api_key:
            params['apikey'] = self.api_key

        try:
            logger.debug(f"TheGamesDB request: {endpoint} with params: {params}")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                raise TheGamesDBError("Rate limit exceeded")
            elif response.status_code != 200:
                raise TheGamesDBError(f"HTTP {response.status_code}: {response.text}")

            data = response.json()

            # Check for API errors
            if data.get('code') != 200:
                error = data.get('status', 'Unknown error')
                raise TheGamesDBError(f"API error: {error}")

            return data

        except requests.exceptions.Timeout:
            raise TheGamesDBError("Request timeout")
        except requests.exceptions.RequestException as e:
            raise TheGamesDBError(f"Request failed: {e}")

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
        # Get TheGamesDB platform ID
        platform_id = SYSTEM_ID_MAP.get(system)
        if platform_id is None:
            logger.warning(f"Unknown system for TheGamesDB: {system}")
            return []

        params = {
            'name': game_name,
            'filter[platform]': str(platform_id),
        }

        try:
            data = self._make_request('Games/ByGameName', params)

            games = []

            if 'data' in data and 'games' in data['data']:
                game_list = data['data']['games']

                for game_data in game_list:
                    game = self._parse_game(game_data, data.get('include', {}))
                    if game:
                        # Calculate match confidence
                        game.confidence = calculate_similarity(game_name, game.name)
                        games.append(game)

            # Sort by confidence
            games.sort(key=lambda g: g.confidence, reverse=True)

            return games

        except TheGamesDBError as e:
            logger.error(f"TheGamesDB error: {e}")
            return []

    def get_game_by_id(self, game_id: str) -> Optional[ScraperGame]:
        """
        Get game details by TheGamesDB game ID

        Args:
            game_id: Game ID

        Returns:
            Game details or None
        """
        params = {
            'id': game_id,
        }

        try:
            data = self._make_request('Games/ByGameID', params)

            if 'data' in data and 'games' in data['data']:
                games = data['data']['games']
                if games:
                    return self._parse_game(games[0], data.get('include', {}))

            return None

        except TheGamesDBError as e:
            logger.error(f"TheGamesDB error: {e}")
            return None

    def _parse_game(self, game_data: Dict, includes: Dict) -> Optional[ScraperGame]:
        """
        Parse game data from API response

        Args:
            game_data: Game data dictionary
            includes: Additional data (boxart, platform info)

        Returns:
            ScraperGame object or None
        """
        try:
            game_id = str(game_data.get('id', ''))
            name = game_data.get('game_title', '')

            if not game_id or not name:
                return None

            # Description
            description = game_data.get('overview')

            # Release date
            release_date = game_data.get('release_date')

            # Developer/Publisher
            developers = game_data.get('developers', [])
            developer = developers[0] if developers else None

            publishers = game_data.get('publishers', [])
            publisher = publishers[0] if publishers else None

            # Genre
            genres = game_data.get('genres', [])
            genre = None
            if genres:
                # Look up genre name from includes
                genre_id = genres[0]
                if 'genres' in includes:
                    genre_data = includes['genres'].get('data', {})
                    if str(genre_id) in genre_data:
                        genre = genre_data[str(genre_id)].get('name')

            # Players
            players = game_data.get('players')

            # Get images
            box_art_url = None
            screenshot_url = None

            # Images are referenced in the game data
            images = game_data.get('images', {})

            # Box art
            if 'boxart' in includes:
                boxart_data = includes['boxart'].get('data', {})
                game_boxart = boxart_data.get(game_id, [])

                # Find front boxart
                for img in game_boxart:
                    if img.get('side') == 'front':
                        filename = img.get('filename')
                        if filename:
                            box_art_url = f"{self.image_base_url}original/{filename}"
                            break

            # Screenshots
            if 'screenshots' in images:
                screenshots = images['screenshots']
                if screenshots:
                    filename = screenshots[0].get('filename')
                    if filename:
                        screenshot_url = f"{self.image_base_url}original/{filename}"

            game = ScraperGame(
                id=game_id,
                name=name,
                description=description,
                release_date=release_date,
                developer=developer,
                publisher=publisher,
                genre=genre,
                players=str(players) if players else None,
                source="TheGamesDB"
            )

            game.box_art_url = box_art_url
            game.screenshot_url = screenshot_url
            game.thumbnail_url = box_art_url  # Use boxart as thumbnail

            return game

        except Exception as e:
            logger.error(f"Error parsing TheGamesDB game data: {e}")
            return None

    def search_by_hash(
        self,
        rom_hash: str,
        hash_type: str,
        system: str,
        file_size: Optional[int] = None
    ) -> Optional[ScraperGame]:
        """
        TheGamesDB doesn't support hash-based search
        """
        return None
