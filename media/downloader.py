"""
Media downloader for game images and videos
"""
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from utils.logger import get_logger

logger = get_logger()


class MediaDownloader:
    """Downloads and manages game media (images, videos)"""

    def __init__(self, timeout: int = 30):
        """
        Initialize media downloader

        Args:
            timeout: Download timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'retroMaid/1.0'
        })

    def download_image(
        self,
        url: str,
        output_path: Path,
        overwrite: bool = False
    ) -> bool:
        """
        Download an image from URL

        Args:
            url: Image URL
            output_path: Path to save image
            overwrite: Whether to overwrite existing file

        Returns:
            True if successful, False otherwise
        """
        if not overwrite and output_path.exists():
            logger.debug(f"Image already exists: {output_path}")
            return True

        try:
            logger.debug(f"Downloading image: {url}")

            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type:
                logger.warning(f"URL does not point to an image: {url} (type: {content_type})")
                return False

            # Create parent directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            total_size = int(response.headers.get('content-length', 0))

            with open(output_path, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

            logger.info(f"Downloaded image: {output_path.name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return False
        except IOError as e:
            logger.error(f"Failed to save image to {output_path}: {e}")
            return False

    def download_video(
        self,
        url: str,
        output_path: Path,
        overwrite: bool = False,
        max_size_mb: int = 50
    ) -> bool:
        """
        Download a video from URL

        Args:
            url: Video URL
            output_path: Path to save video
            overwrite: Whether to overwrite existing file
            max_size_mb: Maximum video size in MB (skip if larger)

        Returns:
            True if successful, False otherwise
        """
        if not overwrite and output_path.exists():
            logger.debug(f"Video already exists: {output_path}")
            return True

        try:
            logger.debug(f"Downloading video: {url}")

            # Make HEAD request to check size first
            head_response = self.session.head(url, timeout=10)
            content_length = int(head_response.headers.get('content-length', 0))

            # Check size limit
            if content_length > max_size_mb * 1024 * 1024:
                size_mb = content_length / (1024 * 1024)
                logger.warning(f"Video too large ({size_mb:.1f}MB > {max_size_mb}MB): {url}")
                return False

            # Download video
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Create parent directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            with open(output_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            logger.info(f"Downloaded video: {output_path.name} ({downloaded / (1024*1024):.1f}MB)")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download video from {url}: {e}")
            return False
        except IOError as e:
            logger.error(f"Failed to save video to {output_path}: {e}")
            return False

    def get_file_extension_from_url(self, url: str) -> str:
        """
        Get file extension from URL

        Args:
            url: File URL

        Returns:
            File extension (with dot) or empty string
        """
        parsed = urlparse(url)
        path = parsed.path

        if '.' in path:
            ext = Path(path).suffix.lower()
            return ext

        return ''

    def close(self) -> None:
        """Close the session"""
        self.session.close()


class GameMediaManager:
    """Manages media downloads for a game"""

    def __init__(self, system_path: Path, downloader: Optional[MediaDownloader] = None):
        """
        Initialize game media manager

        Args:
            system_path: Path to system directory (e.g., /roms/psx)
            downloader: MediaDownloader instance (creates new if None)
        """
        self.system_path = Path(system_path)
        self.images_path = self.system_path / "images"
        self.downloader = downloader or MediaDownloader()
        self._owned_downloader = downloader is None

    def download_game_media(
        self,
        game_name: str,
        box_art_url: Optional[str] = None,
        screenshot_url: Optional[str] = None,
        marquee_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        video_url: Optional[str] = None,
        overwrite: bool = False
    ) -> dict:
        """
        Download all media for a game

        Args:
            game_name: Base name for files
            box_art_url: URL to box art image
            screenshot_url: URL to screenshot
            marquee_url: URL to marquee/logo
            thumbnail_url: URL to thumbnail
            video_url: URL to video
            overwrite: Whether to overwrite existing files

        Returns:
            Dictionary with relative paths to downloaded files
        """
        # Sanitize game name for filename
        safe_name = self._sanitize_filename(game_name)

        results = {}

        # Download box art (image)
        if box_art_url:
            ext = self.downloader.get_file_extension_from_url(box_art_url) or '.png'
            filename = f"{safe_name}-image{ext}"
            output_path = self.images_path / filename

            if self.downloader.download_image(box_art_url, output_path, overwrite):
                results['image'] = f"./images/{filename}"

        # Download screenshot
        if screenshot_url:
            ext = self.downloader.get_file_extension_from_url(screenshot_url) or '.png'
            filename = f"{safe_name}-screenshot{ext}"
            output_path = self.images_path / filename

            if self.downloader.download_image(screenshot_url, output_path, overwrite):
                results['screenshot'] = f"./images/{filename}"

        # Download marquee
        if marquee_url:
            ext = self.downloader.get_file_extension_from_url(marquee_url) or '.png'
            filename = f"{safe_name}-marquee{ext}"
            output_path = self.images_path / filename

            if self.downloader.download_image(marquee_url, output_path, overwrite):
                results['marquee'] = f"./images/{filename}"

        # Download thumbnail
        if thumbnail_url:
            ext = self.downloader.get_file_extension_from_url(thumbnail_url) or '.jpg'
            filename = f"{safe_name}-thumb{ext}"
            output_path = self.images_path / filename

            if self.downloader.download_image(thumbnail_url, output_path, overwrite):
                results['thumbnail'] = f"./images/{filename}"

        # Download video
        if video_url:
            ext = self.downloader.get_file_extension_from_url(video_url) or '.mp4'
            filename = f"{safe_name}-video{ext}"
            output_path = self.images_path / filename

            if self.downloader.download_video(video_url, output_path, overwrite):
                results['video'] = f"./images/{filename}"

        return results

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string for use as filename

        Args:
            name: Original name

        Returns:
            Safe filename
        """
        # Remove/replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '')

        # Replace multiple spaces with single space
        name = ' '.join(name.split())

        # Trim
        name = name.strip()

        return name

    def cleanup(self) -> None:
        """Clean up resources"""
        if self._owned_downloader:
            self.downloader.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
