"""
ROM file hashing utilities for API lookups
"""
import hashlib
import zipfile
from pathlib import Path
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger()


class ROMHasher:
    """Compute hashes for ROM files"""

    # Read files in chunks to handle large files
    CHUNK_SIZE = 8192 * 1024  # 8MB chunks

    @staticmethod
    def hash_file(file_path: Path, hash_type: str = 'md5') -> Optional[str]:
        """
        Compute hash of a file

        Args:
            file_path: Path to file
            hash_type: Hash algorithm ('md5', 'sha1', 'crc32')

        Returns:
            Hash string or None on error
        """
        try:
            if hash_type == 'crc32':
                return ROMHasher._crc32_file(file_path)

            # Get hash function
            if hash_type == 'md5':
                hasher = hashlib.md5()
            elif hash_type == 'sha1':
                hasher = hashlib.sha1()
            else:
                raise ValueError(f"Unsupported hash type: {hash_type}")

            # Read and hash file in chunks
            with open(file_path, 'rb') as f:
                while chunk := f.read(ROMHasher.CHUNK_SIZE):
                    hasher.update(chunk)

            return hasher.hexdigest()

        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return None

    @staticmethod
    def _crc32_file(file_path: Path) -> Optional[str]:
        """
        Compute CRC32 hash

        Args:
            file_path: Path to file

        Returns:
            CRC32 hash as hex string
        """
        try:
            import zlib
            crc = 0

            with open(file_path, 'rb') as f:
                while chunk := f.read(ROMHasher.CHUNK_SIZE):
                    crc = zlib.crc32(chunk, crc)

            # Convert to unsigned and format as hex (uppercase, 8 chars)
            return f"{crc & 0xFFFFFFFF:08X}"

        except Exception as e:
            logger.error(f"Error computing CRC32 for {file_path}: {e}")
            return None

    @staticmethod
    def get_rom_hash_info(rom_path: Path) -> Optional[dict]:
        """
        Get hash information for a ROM file

        For ZIP files, hashes the first ROM file inside
        For other files, hashes the file directly

        Args:
            rom_path: Path to ROM file

        Returns:
            Dictionary with hash info or None on error
        """
        try:
            if rom_path.suffix.lower() == '.zip':
                return ROMHasher._hash_zip_rom(rom_path)
            else:
                return ROMHasher._hash_regular_rom(rom_path)

        except Exception as e:
            logger.error(f"Error getting hash info for {rom_path}: {e}")
            return None

    @staticmethod
    def _hash_regular_rom(rom_path: Path) -> Optional[dict]:
        """
        Hash a regular (non-ZIP) ROM file

        Args:
            rom_path: Path to ROM file

        Returns:
            Dictionary with hash info
        """
        if not rom_path.exists():
            return None

        file_size = rom_path.stat().st_size

        return {
            'filename': rom_path.name,
            'size': file_size,
            'md5': ROMHasher.hash_file(rom_path, 'md5'),
            'sha1': ROMHasher.hash_file(rom_path, 'sha1'),
            'crc32': ROMHasher.hash_file(rom_path, 'crc32'),
        }

    @staticmethod
    def _hash_zip_rom(zip_path: Path) -> Optional[dict]:
        """
        Hash the first ROM file inside a ZIP archive

        Args:
            zip_path: Path to ZIP file

        Returns:
            Dictionary with hash info
        """
        if not zip_path.exists():
            return None

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Get list of files in ZIP
                file_list = zf.namelist()

                # Filter for ROM files (exclude directories and metadata)
                rom_extensions = [
                    '.nes', '.sfc', '.smc', '.gb', '.gbc', '.gba',
                    '.n64', '.z64', '.v64', '.md', '.smd', '.gen',
                    '.gg', '.sms', '.pce', '.bin', '.iso', '.cue'
                ]

                rom_files = [
                    f for f in file_list
                    if not f.endswith('/') and Path(f).suffix.lower() in rom_extensions
                ]

                if not rom_files:
                    # If no known ROM extension, take the largest file
                    rom_files = [
                        f for f in file_list
                        if not f.endswith('/') and not f.startswith('__MACOSX')
                    ]

                    if not rom_files:
                        return None

                    # Sort by file size (descending) and take largest
                    rom_files.sort(key=lambda f: zf.getinfo(f).file_size, reverse=True)

                # Use the first ROM file
                rom_file = rom_files[0]
                file_info = zf.getinfo(rom_file)

                # Extract to temporary location and hash
                temp_data = zf.read(rom_file)

                md5_hash = hashlib.md5(temp_data).hexdigest()
                sha1_hash = hashlib.sha1(temp_data).hexdigest()

                import zlib
                crc32_hash = f"{zlib.crc32(temp_data) & 0xFFFFFFFF:08X}"

                return {
                    'filename': Path(rom_file).name,
                    'size': file_info.file_size,
                    'md5': md5_hash,
                    'sha1': sha1_hash,
                    'crc32': crc32_hash,
                    'is_zipped': True,
                    'zip_path': str(zip_path),
                }

        except zipfile.BadZipFile:
            logger.error(f"Bad ZIP file: {zip_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading ZIP file {zip_path}: {e}")
            return None
