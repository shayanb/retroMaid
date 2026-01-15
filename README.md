# retroMaid 🎮

A powerful metadata scraper for Batocera OS ROM collections. Automatically fetch and organize game metadata, cover art, screenshots, and videos from online databases.

## Features

- **Automatic Metadata Scraping**: Fetch game information from ScreenScraper.fr (with support for TheGamesDB and IGDB)
- **Media Downloads**: Download box art, screenshots, marquees, and video previews
- **Intelligent Matching**: Hash-based and name-based game matching with fuzzy matching
- **Duplicate Detection**: Find and resolve duplicate ROMs interactively with optional file deletion
- **DOS ROM Converter**: Convert DOS games to Batocera format (.pc folders with dosbox.bat)
- **Resume Capability**: Checkpoint system allows resuming after interruptions
- **Batocera Integration**: Native support for Batocera's gamelist.xml format
- **Rich CLI**: Beautiful command-line interface with progress tracking

## Installation

### Requirements

- Python 3.8+
- Batocera OS (or compatible RetroPie/EmulationStation setup)
- ScreenScraper.fr account (free)

### Setup

1. Clone the repository:
```bash
cd /userdata
git clone https://github.com/yourusername/retroMaid.git
cd retroMaid
```

2. Install dependencies:
```bash
python -m pip install -r requirements.txt
```

3. Configure credentials:
```bash
cp .env.example .env
nano .env  # Add your ScreenScraper credentials
```

4. Update configuration:
```bash
nano config.yaml  # Set your ROMs path and preferences
```

## Quick Start

### List Available Systems
```bash
python retromaid.py list-systems
```

### Scan a System
```bash
python retromaid.py list-systems --system psx
```

### Scrape Metadata
```bash
# Basic scraping (images only)
python retromaid.py scrape psx

# Include videos
python retromaid.py scrape psx --videos

# Reprocess all games (ignore checkpoint)
python retromaid.py scrape psx --force
```

### Find Duplicates
```bash
# List duplicates
python retromaid.py duplicates psx

# Interactively resolve duplicates (remove from gamelist only)
python retromaid.py duplicates psx --resolve

# Resolve and DELETE files from disk
python retromaid.py duplicates psx --resolve --delete
```

### Convert DOS Games
```bash
# Convert DOS games to Batocera format (interactive)
python retromaid.py convert-dos

# Automatic conversion
python retromaid.py convert-dos --no-interactive

# Extract ZIPs and delete originals
python retromaid.py convert-dos --delete-zips
```

### Check Status
```bash
python retromaid.py status --system psx
```

### Clear Checkpoint
```bash
python retromaid.py clear --system psx
```

## Configuration

Edit `config.yaml` to customize:

- **ROMs Path**: Path to your ROMs directory (SMB mount or local)
- **Scraper Settings**: Primary scraper, API credentials, rate limits
- **Media Preferences**: Which media types to download
- **Matching Settings**: Region preferences, fuzzy matching threshold
- **Duplicate Handling**: Resolution strategy (ask, keep_first, keep_most_complete)
- **Backup**: Automatic backup of gamelist.xml

### Environment Variables

Create a `.env` file for sensitive credentials:

```env
SCREENSCRAPER_USERNAME=your_username
SCREENSCRAPER_PASSWORD=your_password
```

## Workflow

1. **Initial Scan**: Run a scan to see what's missing
   ```bash
   python retromaid.py list-systems --system psx
   ```

2. **Scrape Metadata**: Start scraping for a system
   ```bash
   python retromaid.py scrape psx
   ```

3. **Handle Interruptions**: If interrupted, simply run the same command again. retroMaid will resume from where it left off.

4. **Find Duplicates**: Clean up duplicate ROMs
   ```bash
   python retromaid.py duplicates psx --resolve
   ```

5. **Verify**: Check the processing status
   ```bash
   python retromaid.py status --system psx
   ```

## Network Share (Mac)

If accessing Batocera over network share:

1. Mount the share:
   ```bash
   # SMB mount
   open smb://BATOCERA/share
   ```

2. Update `config.yaml`:
   ```yaml
   roms_path: "/Volumes/share/roms"
   ```

3. Run retroMaid from your Mac

## SSH Access (Raspberry Pi)

To run directly on the Pi:

1. SSH into Batocera:
   ```bash
   ssh root@batocera
   ```

2. Install Python dependencies (if not already installed)

3. Run retroMaid directly on the Pi

## Advanced Usage

### Custom System Extensions

Edit `core/scanner.py` to add support for additional systems or ROM formats.

### Multiple Scrapers

Configure fallback scrapers in `config.yaml`:

```yaml
scrapers:
  primary: "screenscraper"
  # Add IGDB or TheGamesDB as fallbacks
```

### Rate Limiting

Adjust request rates to avoid hitting API limits:

```yaml
scrapers:
  screenscraper:
    rate_limit: 20  # requests per minute
```

## Troubleshooting

### "Rate limit exceeded" errors
- Lower the `rate_limit` in config.yaml
- Wait a few minutes before retrying
- Consider upgrading your ScreenScraper account

### "No match found" for games
- Check ROM filename format
- Try renaming to standard format: "Game Name (Region).ext"
- Use `--force` to retry with updated names

### Missing media files
- Check that `scrapers.screenscraper.media.download_images` is `true`
- Ensure the images directory exists
- Check network connectivity

### Checkpoint issues
- Clear checkpoint: `python retromaid.py clear --system psx`
- Delete `.retromaid_checkpoint.json` manually if needed

## API Limits

### ScreenScraper.fr
- **Free accounts**: ~20 requests/minute, 50,000/day
- **Contributor accounts**: Higher limits
- **Developer accounts**: Special registration required

Rate limiting is built into retroMaid to stay within limits.

## Project Structure

```
retroMaid/
├── config.yaml              # Main configuration
├── .env                     # Credentials (not in git)
├── retromaid.py            # CLI entry point
├── core/
│   ├── scanner.py          # ROM scanning
│   ├── xml_manager.py      # gamelist.xml handling
│   ├── hasher.py           # ROM hashing
│   ├── duplicate_detector.py
│   └── state_manager.py    # Checkpoint system
├── scrapers/
│   ├── base.py             # Base scraper interface
│   ├── screenscraper.py    # ScreenScraper client
│   └── ...                 # Additional scrapers
├── media/
│   └── downloader.py       # Media downloads
└── utils/
    ├── config.py           # Config management
    ├── logger.py           # Logging
    └── filename.py         # Name sanitization
```

## Contributing

Contributions welcome! Areas for improvement:

- Additional scraper implementations (TheGamesDB, IGDB, MobyGames)
- Web-based UI
- Batocera script integration
- Docker container
- Automated testing

## Support

If retroMaid has helped organize your ROM collection, consider supporting development:

<a href="https://buymeacoffee.com/pangana" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50">
</a>

Your support helps keep the project maintained and improved!

## License

MIT License - see LICENSE file

## Acknowledgments

- [Batocera.linux](https://batocera.org/) - Amazing retro gaming OS
- [ScreenScraper.fr](https://screenscraper.fr/) - Comprehensive game database
- Built with love for the retro gaming community 🕹️
