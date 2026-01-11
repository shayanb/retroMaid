# Changelog

All notable changes to retroMaid will be documented in this file.

## [1.0.0] - 2026-01-11

### Initial Release

#### Features
- ✨ Full Batocera gamelist.xml support
- 🔍 ScreenScraper.fr integration with rate limiting
- 🎨 Media downloads (box art, screenshots, marquees, videos)
- 🎯 Hash-based and name-based game matching
- 📊 Duplicate ROM detection and resolution
- 💾 Checkpoint/resume system for interruption recovery
- 🖥️ Rich CLI with progress tracking
- 🔧 Comprehensive configuration system
- 📝 Detailed logging
- 🔄 Automatic gamelist.xml backups

#### Core Components
- **Scanner**: Multi-system ROM scanning with metadata detection
- **XML Manager**: Parse and write gamelist.xml files
- **Hasher**: MD5/SHA1/CRC32 ROM hashing for accurate matching
- **Scraper**: ScreenScraper API client with authentication
- **Media Downloader**: Multi-threaded image and video downloads
- **Duplicate Detector**: Interactive duplicate resolution
- **State Manager**: Progress tracking and checkpoint system

#### Supported Systems
- PlayStation (PSX)
- Nintendo: NES, SNES, N64, Game Boy, GBC, GBA
- Sega: Genesis/Mega Drive, Master System, Game Gear, Saturn, Dreamcast
- And many more (see SYSTEM_EXTENSIONS in core/scanner.py)

#### CLI Commands
- `list-systems`: Show available systems and statistics
- `scrape`: Scrape metadata for a system
- `duplicates`: Find and resolve duplicate ROMs
- `status`: Show processing status and progress
- `clear`: Clear checkpoint data

#### Configuration
- YAML-based configuration with .env support
- Scraper preferences and API credentials
- Region and language preferences
- Duplicate resolution strategies
- Media download options
- Rate limiting controls

#### Documentation
- Comprehensive README with examples
- Detailed SETUP guide
- Inline code documentation
- Example configurations

### Known Limitations
- ScreenScraper only (TheGamesDB and IGDB planned)
- CLI only (web UI planned)
- No Batocera script integration yet

### TODO for Future Releases
- [ ] Web-based UI
- [ ] TheGamesDB integration
- [ ] IGDB integration
- [ ] Batocera script integration
- [ ] Docker container
- [ ] Automated testing suite
- [ ] Multi-language support
- [ ] Scheduling/cron support
- [ ] Bulk operations
- [ ] Statistics dashboard

## Contributing

See [README.md](README.md) for contribution guidelines.
