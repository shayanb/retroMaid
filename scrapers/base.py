"""
Base scraper interface
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ScraperGame:
    """Represents a game result from a scraper"""
    id: str  # Scraper-specific game ID
    name: str
    description: Optional[str] = None
    release_date: Optional[str] = None  # ISO format YYYY-MM-DD
    developer: Optional[str] = None
    publisher: Optional[str] = None
    genre: Optional[str] = None
    players: Optional[str] = None
    rating: Optional[float] = None
    region: Optional[str] = None
    language: Optional[str] = None

    # Media URLs
    box_art_url: Optional[str] = None
    screenshot_url: Optional[str] = None
    marquee_url: Optional[str] = None
    logo_url: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    # Match confidence (0-100)
    confidence: float = 0.0

    # Source scraper name
    source: str = ""


class BaseScraper(ABC):
    """Base class for game metadata scrapers"""

    def __init__(self, config: Dict):
        """
        Initialize scraper

        Args:
            config: Configuration dictionary
        """
        self.config = config

    @abstractmethod
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
        pass

    @abstractmethod
    def search_by_hash(
        self,
        rom_hash: str,
        hash_type: str,
        system: str,
        file_size: Optional[int] = None
    ) -> Optional[ScraperGame]:
        """
        Search for game by ROM hash (most accurate)

        Args:
            rom_hash: ROM file hash
            hash_type: Type of hash ('md5', 'sha1', 'crc32')
            system: System/platform name
            file_size: Optional file size for additional verification

        Returns:
            Matching game or None
        """
        pass

    @abstractmethod
    def get_game_by_id(self, game_id: str) -> Optional[ScraperGame]:
        """
        Get game details by scraper-specific ID

        Args:
            game_id: Game ID

        Returns:
            Game details or None
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Scraper name"""
        pass

    @property
    @abstractmethod
    def requires_auth(self) -> bool:
        """Whether this scraper requires authentication"""
        pass
