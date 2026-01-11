"""
Configuration management for retroMaid
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager that loads from YAML and environment variables"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}

        # Load environment variables from .env file
        load_dotenv()

        # Load YAML configuration
        self.load()

        # Override with environment variables
        self._load_env_overrides()

    def load(self) -> None:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f) or {}

    def _load_env_overrides(self) -> None:
        """Override configuration with environment variables"""
        # ScreenScraper credentials
        if os.getenv("SCREENSCRAPER_USERNAME"):
            self.set("scrapers.screenscraper.username", os.getenv("SCREENSCRAPER_USERNAME"))
        if os.getenv("SCREENSCRAPER_PASSWORD"):
            self.set("scrapers.screenscraper.password", os.getenv("SCREENSCRAPER_PASSWORD"))
        if os.getenv("SCREENSCRAPER_DEV_ID"):
            self.set("scrapers.screenscraper.dev_id", os.getenv("SCREENSCRAPER_DEV_ID"))
        if os.getenv("SCREENSCRAPER_DEV_PASSWORD"):
            self.set("scrapers.screenscraper.dev_password", os.getenv("SCREENSCRAPER_DEV_PASSWORD"))

        # TheGamesDB
        if os.getenv("THEGAMESDB_API_KEY"):
            self.set("scrapers.thegamesdb.api_key", os.getenv("THEGAMESDB_API_KEY"))

        # IGDB
        if os.getenv("IGDB_CLIENT_ID"):
            self.set("scrapers.igdb.client_id", os.getenv("IGDB_CLIENT_ID"))
        if os.getenv("IGDB_CLIENT_SECRET"):
            self.set("scrapers.igdb.client_secret", os.getenv("IGDB_CLIENT_SECRET"))

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., "scrapers.screenscraper.username")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation

        Args:
            key: Configuration key (e.g., "scrapers.screenscraper.username")
            value: Value to set
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: Optional[str] = None) -> None:
        """
        Save configuration to YAML file

        Args:
            path: Path to save to (defaults to original config_path)
        """
        save_path = Path(path) if path else self.config_path

        with open(save_path, 'w') as f:
            yaml.safe_dump(self._config, f, default_flow_style=False, sort_keys=False)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access"""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like setting"""
        self.set(key, value)
