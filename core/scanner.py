"""
ROM scanner to identify files and missing metadata
"""
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import re

from core.xml_manager import GameListXML, GameMetadata
from core.hasher import ROMHasher
from utils.filename import sanitize_filename, extract_region_from_filename
from utils.logger import get_logger

logger = get_logger()


# Fallback extensions if _info.txt is not found
# Batocera system IDs and their ROM extensions (with .7z added)
SYSTEM_EXTENSIONS = {
    'nes': ['.7z', '.nes', '.zip'],
    'snes': ['.7z', '.sfc', '.smc', '.zip'],
    'n64': ['.7z', '.n64', '.z64', '.v64', '.zip'],
    'gb': ['.7z', '.gb', '.zip'],
    'gbc': ['.7z', '.gbc', '.zip'],
    'gba': ['.7z', '.gba', '.zip'],
    'md': ['.7z', '.md', '.smd', '.gen', '.bin', '.zip'],  # Sega Genesis/Mega Drive
    'sms': ['.7z', '.sms', '.zip'],  # Sega Master System
    'gg': ['.7z', '.gg', '.zip'],  # Game Gear
    'pce': ['.7z', '.pce', '.zip'],  # PC Engine
    'psx': ['.7z', '.cue', '.pbp', '.chd'],  # PlayStation (multi-file games)
    'ps2': ['.7z', '.iso', '.chd'],
    'psp': ['.7z', '.iso', '.cso'],
    'dreamcast': ['.7z', '.cdi', '.gdi', '.chd'],
    'saturn': ['.7z', '.cue', '.chd'],
    'arcade': ['.7z', '.zip'],
    'mame': ['.7z', '.zip'],
    'fba': ['.7z', '.zip'],
    'atari2600': ['.7z', '.a26', '.bin', '.zip'],
    'atari7800': ['.7z', '.a78', '.bin', '.zip'],
    'lynx': ['.7z', '.lnx', '.zip'],
    'jaguar': ['.7z', '.j64', '.jag', '.zip'],
    'ngp': ['.7z', '.ngp', '.zip'],  # Neo Geo Pocket
    'ngpc': ['.7z', '.ngc', '.zip'],  # Neo Geo Pocket Color
    'wonderswan': ['.7z', '.ws', '.zip'],
    'wonderswancolor': ['.7z', '.wsc', '.zip'],
    # Commodore systems
    'c64': ['.7z', '.d64', '.t64', '.prg', '.crt', '.tap', '.g64', '.zip'],  # Commodore 64
    'vic20': ['.7z', '.prg', '.crt', '.tap', '.a0', '.20', '.zip'],  # VIC-20
    'amiga': ['.7z', '.adf', '.ipf', '.dms', '.adz', '.lha', '.zip'],  # Amiga
    'amigacd32': ['.7z', '.cue', '.iso', '.chd'],  # Amiga CD32
    # Other computer systems
    'zxspectrum': ['.7z', '.z80', '.sna', '.tap', '.tzx', '.dsk', '.trd', '.zip'],  # ZX Spectrum
    'amstradcpc': ['.7z', '.dsk', '.sna', '.cdt', '.zip'],  # Amstrad CPC
    'msx': ['.7z', '.rom', '.dsk', '.cas', '.mx1', '.mx2', '.zip'],  # MSX
    'msx1': ['.7z', '.rom', '.dsk', '.cas', '.mx1', '.zip'],  # MSX1
    'msx2': ['.7z', '.rom', '.dsk', '.cas', '.mx2', '.zip'],  # MSX2
    'sq1000': ['.7z', '.rom', '.zip'],  # Sega SQ-1000
    'dos': ['.exe', '.com', '.bat'],  # DOS (inside .pc folders)
}


def read_system_extensions_from_info(system_path: Path) -> Optional[List[str]]:
    """
    Read supported ROM extensions from _info.txt file in system directory

    Args:
        system_path: Path to system ROM directory

    Returns:
        List of extensions (with leading dots) or None if not found
    """
    info_file = system_path / "_info.txt"

    if not info_file.exists():
        return None

    try:
        content = info_file.read_text()

        # Look for extension pattern like: .7z .nes .zip
        # Usually appears as a space-separated list
        match = re.search(r'(?:extensions?|formats?)[:\s]+([.\w\s]+)', content, re.IGNORECASE)

        if match:
            ext_string = match.group(1).strip()
            # Extract all .ext patterns
            extensions = re.findall(r'\.\w+', ext_string)
            if extensions:
                logger.debug(f"Read extensions from _info.txt: {extensions}")
                return extensions

        # Alternative: just find all .ext in the file
        extensions = re.findall(r'\.\w+', content)
        if extensions:
            # Filter out common non-extension patterns
            valid_exts = [ext for ext in extensions if len(ext) <= 6 and ext not in ['.txt', '.xml']]
            if valid_exts:
                logger.debug(f"Extracted extensions from _info.txt: {valid_exts}")
                return valid_exts

    except Exception as e:
        logger.warning(f"Error reading _info.txt: {e}")

    return None


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
        # Try reading from _info.txt first, then fall back to hardcoded
        extensions = read_system_extensions_from_info(system_path)
        if extensions:
            logger.info(f"Using extensions from _info.txt for {system}: {extensions}")
        else:
            extensions = SYSTEM_EXTENSIONS.get(system, ['.7z', '.zip'])
            logger.debug(f"Using fallback extensions for {system}: {extensions}")

        # Directories to exclude from ROM scanning
        excluded_dirs = {'images', 'videos', 'manuals', 'music', 'wheels', 'marquees'}

        # Find ROM files
        rom_files = []
        seen_paths = set()  # Deduplicate in case both .ext and .EXT match the same file

        for ext in extensions:
            # Check both lowercase and uppercase versions (for case-insensitive matching)
            # This handles .t64 vs .T64, .zip vs .ZIP, etc.
            extensions_to_check = [ext.lower(), ext.upper()]
            if ext != ext.lower() and ext != ext.upper():
                # Also check the original case if it's mixed case
                extensions_to_check.append(ext)

            for ext_variant in extensions_to_check:
                # For .cue files, look in subdirectories (PSX multi-disc games)
                if ext.lower() == '.cue':
                    for cue_file in system_path.rglob(f'*{ext_variant}'):
                        # Skip if in excluded directories
                        if any(excluded_dir in cue_file.parts for excluded_dir in excluded_dirs):
                            continue

                        # Skip if we've already seen this file
                        if str(cue_file) in seen_paths:
                            continue
                        seen_paths.add(str(cue_file))

                        rom_files.append(self._create_rom_file(
                            cue_file, system_path, system, gamelist, compute_hashes
                        ))
                else:
                    # For other files, search in root and subdirectories
                    for rom_file in system_path.rglob(f'*{ext_variant}'):
                        # Skip if in excluded directories
                        if any(excluded_dir in rom_file.parts for excluded_dir in excluded_dirs):
                            continue

                        # Skip if we've already seen this file
                        if str(rom_file) in seen_paths:
                            continue
                        seen_paths.add(str(rom_file))

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

        # DEDUPLICATE: Ensure each unique file path only appears once
        # (fixes issue with symlinks/hardlinks being scanned multiple times)
        seen_paths = {}
        unique_roms = []

        for rom in all_roms:
            rom_path = str(rom.path)
            if rom_path not in seen_paths:
                seen_paths[rom_path] = rom
                unique_roms.append(rom)
            else:
                logger.debug(f"Skipping duplicate scan of: {rom_path}")

        # Group by sanitized name
        name_groups: Dict[str, List[ROMFile]] = {}

        for rom in unique_roms:
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
