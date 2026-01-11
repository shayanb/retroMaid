"""
XML Manager for Batocera gamelist.xml files
"""
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from lxml import etree
from dataclasses import dataclass, field


@dataclass
class GameMetadata:
    """Represents metadata for a single game"""
    path: str  # Relative path to ROM file
    name: Optional[str] = None
    desc: Optional[str] = None
    image: Optional[str] = None  # Path to box art
    marquee: Optional[str] = None  # Path to marquee/logo
    thumbnail: Optional[str] = None  # Path to thumbnail
    video: Optional[str] = None  # Path to video preview
    releasedate: Optional[str] = None  # Format: YYYYMMDDTHHMMSS
    developer: Optional[str] = None
    publisher: Optional[str] = None
    genre: Optional[str] = None
    players: Optional[str] = None
    rating: Optional[str] = None
    lang: Optional[str] = None
    region: Optional[str] = None

    # User stats (preserve existing values)
    favorite: Optional[bool] = None
    playcount: Optional[int] = None
    lastplayed: Optional[str] = None
    gametime: Optional[int] = None

    # Scrape metadata
    scrap_name: Optional[str] = None
    scrap_date: Optional[str] = None

    # Internal flags
    is_complete: bool = False  # Whether metadata is complete
    missing_fields: List[str] = field(default_factory=list)

    def has_minimal_metadata(self) -> bool:
        """Check if game has minimal required metadata"""
        return self.name is not None

    def calculate_completeness(self) -> float:
        """
        Calculate metadata completeness percentage

        Returns:
            Percentage of filled metadata fields (0-100)
        """
        important_fields = [
            'name', 'desc', 'image', 'thumbnail',
            'releasedate', 'developer', 'publisher', 'genre'
        ]

        filled = sum(1 for field in important_fields if getattr(self, field) is not None)
        return (filled / len(important_fields)) * 100

    def update_missing_fields(self) -> None:
        """Update the list of missing important fields"""
        important_fields = [
            'name', 'desc', 'image', 'thumbnail',
            'releasedate', 'developer', 'publisher', 'genre'
        ]

        self.missing_fields = [
            field for field in important_fields
            if getattr(self, field) is None
        ]

        self.is_complete = len(self.missing_fields) == 0


class GameListXML:
    """Manager for Batocera gamelist.xml files"""

    def __init__(self, xml_path: Path):
        """
        Initialize XML manager

        Args:
            xml_path: Path to gamelist.xml file
        """
        self.xml_path = Path(xml_path)
        self.system_path = self.xml_path.parent
        self.tree: Optional[etree._ElementTree] = None
        self.root: Optional[etree._Element] = None
        self.games: Dict[str, GameMetadata] = {}

        if self.xml_path.exists():
            self.load()
        else:
            self.create_new()

    def load(self) -> None:
        """Load and parse the gamelist.xml file"""
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            self.tree = etree.parse(str(self.xml_path), parser)
            self.root = self.tree.getroot()

            # Parse all games
            self.games = {}
            for game_elem in self.root.findall('game'):
                game = self._parse_game_element(game_elem)
                if game:
                    self.games[game.path] = game

        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid XML in {self.xml_path}: {e}")

    def create_new(self) -> None:
        """Create a new empty gamelist.xml structure"""
        self.root = etree.Element("gameList")
        self.tree = etree.ElementTree(self.root)
        self.games = {}

    def _parse_game_element(self, elem: etree._Element) -> Optional[GameMetadata]:
        """
        Parse a <game> element into GameMetadata

        Args:
            elem: XML element

        Returns:
            GameMetadata object or None
        """
        path_elem = elem.find('path')
        if path_elem is None or not path_elem.text:
            return None

        game = GameMetadata(path=path_elem.text)

        # Parse all fields
        game.name = self._get_text(elem, 'name')
        game.desc = self._get_text(elem, 'desc')
        game.image = self._get_text(elem, 'image')
        game.marquee = self._get_text(elem, 'marquee')
        game.thumbnail = self._get_text(elem, 'thumbnail')
        game.video = self._get_text(elem, 'video')
        game.releasedate = self._get_text(elem, 'releasedate')
        game.developer = self._get_text(elem, 'developer')
        game.publisher = self._get_text(elem, 'publisher')
        game.genre = self._get_text(elem, 'genre')
        game.players = self._get_text(elem, 'players')
        game.rating = self._get_text(elem, 'rating')
        game.lang = self._get_text(elem, 'lang')
        game.region = self._get_text(elem, 'region')

        # User stats
        favorite_text = self._get_text(elem, 'favorite')
        game.favorite = favorite_text == 'true' if favorite_text else None

        playcount_text = self._get_text(elem, 'playcount')
        game.playcount = int(playcount_text) if playcount_text else None

        game.lastplayed = self._get_text(elem, 'lastplayed')

        gametime_text = self._get_text(elem, 'gametime')
        game.gametime = int(gametime_text) if gametime_text else None

        # Scrape info
        scrap_elem = elem.find('scrap')
        if scrap_elem is not None:
            game.scrap_name = scrap_elem.get('name')
            game.scrap_date = scrap_elem.get('date')

        # Calculate completeness
        game.update_missing_fields()

        return game

    def _get_text(self, elem: etree._Element, tag: str) -> Optional[str]:
        """Safely get text content from a child element"""
        child = elem.find(tag)
        return child.text if child is not None and child.text else None

    def add_or_update_game(self, game: GameMetadata) -> None:
        """
        Add a new game or update existing game metadata

        Args:
            game: GameMetadata object
        """
        # Update scrap date
        game.scrap_date = datetime.now().strftime("%Y%m%dT%H%M%S")
        game.scrap_name = "retroMaid"

        # Update completeness
        game.update_missing_fields()

        # Add to games dict
        self.games[game.path] = game

    def remove_game(self, path: str) -> bool:
        """
        Remove a game from the list

        Args:
            path: Game path

        Returns:
            True if removed, False if not found
        """
        if path in self.games:
            del self.games[path]
            return True
        return False

    def save(self, backup: bool = True) -> None:
        """
        Save the gamelist.xml file

        Args:
            backup: Whether to create a backup before saving
        """
        if backup and self.xml_path.exists():
            backup_path = self.xml_path.with_suffix('.xml_backup')
            shutil.copy2(self.xml_path, backup_path)

        # Rebuild XML tree
        self.root.clear()

        # Sort games by path for consistent output
        sorted_games = sorted(self.games.values(), key=lambda g: g.path)

        for game in sorted_games:
            game_elem = etree.SubElement(self.root, "game")
            self._add_element(game_elem, 'path', game.path)

            # Add all metadata fields
            if game.name:
                self._add_element(game_elem, 'name', game.name)
            if game.desc:
                self._add_element(game_elem, 'desc', game.desc)
            if game.image:
                self._add_element(game_elem, 'image', game.image)
            if game.marquee:
                self._add_element(game_elem, 'marquee', game.marquee)
            if game.thumbnail:
                self._add_element(game_elem, 'thumbnail', game.thumbnail)
            if game.video:
                self._add_element(game_elem, 'video', game.video)
            if game.releasedate:
                self._add_element(game_elem, 'releasedate', game.releasedate)
            if game.developer:
                self._add_element(game_elem, 'developer', game.developer)
            if game.publisher:
                self._add_element(game_elem, 'publisher', game.publisher)
            if game.genre:
                self._add_element(game_elem, 'genre', game.genre)
            if game.players:
                self._add_element(game_elem, 'players', game.players)
            if game.rating:
                self._add_element(game_elem, 'rating', game.rating)

            # User stats (preserve if they exist)
            if game.favorite is not None:
                self._add_element(game_elem, 'favorite', 'true' if game.favorite else 'false')
            if game.playcount is not None:
                self._add_element(game_elem, 'playcount', str(game.playcount))
            if game.lastplayed:
                self._add_element(game_elem, 'lastplayed', game.lastplayed)
            if game.gametime is not None:
                self._add_element(game_elem, 'gametime', str(game.gametime))

            if game.lang:
                self._add_element(game_elem, 'lang', game.lang)
            if game.region:
                self._add_element(game_elem, 'region', game.region)

            # Scrape metadata
            if game.scrap_name and game.scrap_date:
                scrap_elem = etree.SubElement(game_elem, "scrap")
                scrap_elem.set('name', game.scrap_name)
                scrap_elem.set('date', game.scrap_date)

        # Write to file with proper formatting
        self.xml_path.parent.mkdir(parents=True, exist_ok=True)
        self.tree.write(
            str(self.xml_path),
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )

    def _add_element(self, parent: etree._Element, tag: str, text: str) -> None:
        """Helper to add a child element with text"""
        elem = etree.SubElement(parent, tag)
        elem.text = text

    def get_games_missing_metadata(self, fields: Optional[List[str]] = None) -> List[GameMetadata]:
        """
        Get games that are missing specified metadata fields

        Args:
            fields: List of field names to check, or None for any missing field

        Returns:
            List of games with missing metadata
        """
        missing = []

        for game in self.games.values():
            if fields:
                # Check specific fields
                if any(getattr(game, field) is None for field in fields):
                    missing.append(game)
            else:
                # Check if any important field is missing
                if not game.is_complete:
                    missing.append(game)

        return missing

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about the gamelist

        Returns:
            Dictionary with statistics
        """
        total = len(self.games)
        complete = sum(1 for g in self.games.values() if g.is_complete)
        missing_name = sum(1 for g in self.games.values() if not g.name)
        missing_desc = sum(1 for g in self.games.values() if not g.desc)
        missing_image = sum(1 for g in self.games.values() if not g.image)

        return {
            'total': total,
            'complete': complete,
            'incomplete': total - complete,
            'missing_name': missing_name,
            'missing_desc': missing_desc,
            'missing_image': missing_image,
        }
