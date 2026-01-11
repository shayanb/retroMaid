"""
ROM scanner to identify files and missing metadata
"""
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from core.xml_manager import GameListXML, GameMetadata
from core.hasher import ROMHasher
from utils.filename import sanitize_filename, extract_region_from_filename
from utils.logger import get_logger

logger = get_logger()


# Batocera system IDs and their ROM extensions
SYSTEM_EXTENSIONS = {
    'nes': ['.nes', '.zip'],
    'snes': ['.sfc', '.smc', '.zip'],
    'n64': ['.n64', '.z64', '.v64', '.zip'],
    'gb': ['.gb', '.zip'],
    'gbc': ['.gbc', '.zip'],
    'gba': ['.gba', '.zip'],
    'md': ['.md', '.smd', '.gen', '.bin', '.zip'],  # Sega Genesis/Mega Drive
    'sms': ['.sms', '.zip'],  # Sega Master System
    'gg': ['.gg', '.zip'],  # Game Gear
    'pce': ['.pce', '.zip'],  # PC Engine
    'psx': ['.cue', '.pbp', '.chd'],  # PlayStation (multi-file games)
    'ps2': ['.iso', '.chd'],
    'psp': ['.iso', '.cso'],
    'dreamcast': ['.cdi', '.gdi', '.chd'],
    'saturn': ['.cue', '.chd'],
    'arcade': ['.zip'],
    'mame': ['.zip'],
    'fba': ['.zip'],
    'atari2600': ['.a26', '.bin', '.zip'],
    'atari7800': ['.a78', '.bin', '.zip'],
    'lynx': ['.lnx', '.zip'],
    'jaguar': ['.j64', '.jag', '.zip'],
    'ngp': ['.ngp', '.zip'],  # Neo Geo Pocket
    'ngpc': ['.ngc', '.zip'],  # Neo Geo Pocket Color
    'wonderswan': ['.ws', '.zip'],
    'wonderswancolor': ['.wsc', '.zip'],
}


@dataclass
class ROMFile:
    """Represents a ROM file found on disk"""
    path: Path  # Absolute path to ROM
    relative_path: str  # Relative path from system directory
    filename: str
    system: str
    size: int
    has_metadata: bool = False
    metadata: Optional[GameMetadata] = None
    hash_info: Optional[dict] = None


class ROMScanner:
    """Scans ROM directories and identifies missing metadata"""

    def __init__(self, roms_base_path: Path):
        """
        Initialize ROM scanner

        Args:
            roms_base_path: Base path to ROMs directory (e.g., /userdata/roms)
        """
        self.roms_base_path = Path(roms_base_path)

        if not self.roms_base_path.exists():
            raise FileNotFoundError(f"ROMs path does not exist: {self.roms_base_path}")

    def get_available_systems(self) -> List[str]:
        """
        Get list of available systems in the ROMs directory

        Returns:
            List of system names (directory names)
        """
        systems = []

        for item in self.roms_base_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                systems.append(item.name)

        return sorted(systems)

    def scan_system(self, system: str, compute_hashes: bool = False) -> List[ROMFile]:
        """
        Scan a specific system directory for ROM files

        Args:
            system: System name (e.g., 'psx', 'nes')
            compute_hashes: Whether to compute file hashes (slower but needed for API)

        Returns:
            List of found ROM files
        """
        system_path = self.roms_base_path / system

        if not system_path.exists():
            logger.warning(f"System directory not found: {system_path}")
            return []

        logger.info(f"Scanning system: {system}")

        # Load gamelist.xml if it exists
        gamelist_path = system_path / "gamelist.xml"
        gamelist = GameListXML(gamelist_path) if gamelist_path.exists() else None

        # Get valid extensions for this system
        extensions = SYSTEM_EXTENSIONS.get(system, ['.zip'])

        # Find ROM files
        rom_files = []

        for ext in extensions:
            # For .cue files, look in subdirectories (PSX multi-disc games)
            if ext == '.cue':
                for cue_file in system_path.rglob(f'*{ext}'):
                    # Skip if in images directory
                    if 'images' in cue_file.parts:
                        continue

                    rom_files.append(self._create_rom_file(
                        cue_file, system_path, system, gamelist, compute_hashes
                    ))
            else:
                # For other files, search in root and subdirectories
                for rom_file in system_path.rglob(f'*{ext}'):
                    # Skip if in images directory
                    if 'images' in rom_file.parts:
                        continue

                    rom_files.append(self._create_rom_file(
                        rom_file, system_path, system, gamelist, compute_hashes
                    ))

        logger.info(f"Found {len(rom_files)} ROM files for {system}")

        return rom_files

    def _create_rom_file(
        self,
        file_path: Path,
        system_path: Path,
        system: str,
        gamelist: Optional[GameListXML],
        compute_hashes: bool
    ) -> ROMFile:
        """
        Create ROMFile object from a file path

        Args:
            file_path: Absolute path to ROM file
            system_path: Path to system directory
            system: System name
            gamelist: GameListXML object (if exists)
            compute_hashes: Whether to compute file hashes

        Returns:
            ROMFile object
        """
        # Calculate relative path from system directory
        try:
            relative = file_path.relative_to(system_path)
            relative_path = f"./{relative}"
        except ValueError:
            relative_path = file_path.name

        rom = ROMFile(
            path=file_path,
            relative_path=relative_path,
            filename=file_path.name,
            system=system,
            size=file_path.stat().st_size if file_path.exists() else 0,
        )

        # Check if metadata exists in gamelist
        if gamelist and relative_path in gamelist.games:
            rom.has_metadata = True
            rom.metadata = gamelist.games[relative_path]

        # Compute hashes if requested
        if compute_hashes:
            rom.hash_info = ROMHasher.get_rom_hash_info(file_path)

        return rom

    def get_missing_metadata_games(
        self,
        system: str,
        fields: Optional[List[str]] = None
    ) -> List[ROMFile]:
        """
        Get ROM files that are missing metadata

        Args:
            system: System name
            fields: Specific fields to check (None = check if complete)

        Returns:
            List of ROM files with missing metadata
        """
        all_roms = self.scan_system(system, compute_hashes=False)

        missing = []

        for rom in all_roms:
            if not rom.has_metadata:
                # No metadata at all
                missing.append(rom)
            elif rom.metadata and fields:
                # Check specific fields
                if any(getattr(rom.metadata, field) is None for field in fields):
                    missing.append(rom)
            elif rom.metadata and not rom.metadata.is_complete:
                # Check if incomplete
                missing.append(rom)

        return missing

    def find_duplicates(self, system: str) -> Dict[str, List[ROMFile]]:
        """
        Find duplicate ROM files based on sanitized names

        Args:
            system: System name

        Returns:
            Dictionary mapping sanitized names to lists of duplicate ROMs
        """
        all_roms = self.scan_system(system, compute_hashes=False)

        # Group by sanitized name
        name_groups: Dict[str, List[ROMFile]] = {}

        for rom in all_roms:
            sanitized = sanitize_filename(rom.filename, for_matching=True).lower()

            if sanitized not in name_groups:
                name_groups[sanitized] = []

            name_groups[sanitized].append(rom)

        # Filter to only groups with multiple items
        duplicates = {
            name: roms for name, roms in name_groups.items()
            if len(roms) > 1
        }

        return duplicates

    def get_unmatched_metadata(self, system: str) -> List[GameMetadata]:
        """
        Find metadata entries that don't have corresponding ROM files

        Args:
            system: System name

        Returns:
            List of orphaned metadata entries
        """
        system_path = self.roms_base_path / system
        gamelist_path = system_path / "gamelist.xml"

        if not gamelist_path.exists():
            return []

        gamelist = GameListXML(gamelist_path)
        all_roms = self.scan_system(system, compute_hashes=False)

        # Get set of existing ROM paths
        existing_paths = {rom.relative_path for rom in all_roms}

        # Find metadata without corresponding files
        orphaned = []

        for path, metadata in gamelist.games.items():
            if path not in existing_paths:
                orphaned.append(metadata)

        return orphaned

    def get_statistics(self, system: str) -> Dict[str, int]:
        """
        Get statistics about a system's ROM collection

        Args:
            system: System name

        Returns:
            Dictionary with statistics
        """
        all_roms = self.scan_system(system, compute_hashes=False)

        total = len(all_roms)
        with_metadata = sum(1 for rom in all_roms if rom.has_metadata)
        complete = sum(
            1 for rom in all_roms
            if rom.metadata and rom.metadata.is_complete
        )

        return {
            'total_roms': total,
            'with_metadata': with_metadata,
            'without_metadata': total - with_metadata,
            'complete_metadata': complete,
            'incomplete_metadata': with_metadata - complete,
        }
