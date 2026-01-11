# retroMaid Quick Start Guide

Get up and running with retroMaid in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- Batocera OS ROMs (or compatible EmulationStation setup)
- ScreenScraper.fr account (free registration at https://www.screenscraper.fr/)

## Quick Setup (5 steps)

### 1. Install Dependencies (1 min)

```bash
cd /Users/shayan/Documents/GitHub/retroMaid
python3 -m pip install -r requirements.txt
```

### 2. Configure Credentials (2 min)

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env
```

Add your ScreenScraper credentials:
```env
SCREENSCRAPER_USERNAME=your_username
SCREENSCRAPER_PASSWORD=your_password
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter` in nano)

### 3. Set ROMs Path (1 min)

```bash
# Edit config
nano config.yaml
```

Update the `roms_path`:
```yaml
# For local testing (Mac):
roms_path: "/Users/shayan/Documents/GitHub/retroMaid/roms"

# For network share (Batocera):
roms_path: "/Volumes/share/roms"
```

### 4. Test Installation (30 sec)

```bash
python3 retromaid.py list-systems
```

You should see:
```
Available systems:
  - psx
```

### 5. Try Your First Scrape (30 sec)

```bash
# Scan the psx system
python3 retromaid.py list-systems --system psx

# Scrape metadata (dry run with current sample data)
python3 retromaid.py scrape psx
```

## Next Steps

Now that retroMaid is working, here are common tasks:

### Add More ROMs

1. Copy your ROM files to the appropriate system folder:
   ```bash
   # Example for PSX
   cp /path/to/your/games/*.cue roms/psx/
   cp /path/to/your/games/*.bin roms/psx/
   ```

2. Rescan to see the new ROMs:
   ```bash
   python3 retromaid.py list-systems --system psx
   ```

### Scrape a Full System

```bash
# Scrape all missing metadata for PlayStation
python3 retromaid.py scrape psx

# Include video previews (uses more quota)
python3 retromaid.py scrape psx --videos

# Force reprocess everything
python3 retromaid.py scrape psx --force
```

### Check Progress

```bash
# See processing status
python3 retromaid.py status --system psx
```

### Find Duplicates

```bash
# List duplicate ROMs
python3 retromaid.py duplicates psx

# Interactively resolve duplicates
python3 retromaid.py duplicates psx --resolve
```

### Start Fresh

```bash
# Clear checkpoint to start over
python3 retromaid.py clear --system psx
```

## Common Configurations

### For Mac with Network Share

1. Mount Batocera share:
   ```bash
   # Open Finder, press Cmd+K, enter:
   smb://BATOCERA/share
   ```

2. Update config.yaml:
   ```yaml
   roms_path: "/Volumes/BATOCERA/roms"
   ```

### For Raspberry Pi (Running on Batocera)

1. SSH into Batocera:
   ```bash
   ssh root@batocera
   # Password: linux
   ```

2. Clone retroMaid:
   ```bash
   cd /userdata
   git clone https://github.com/yourusername/retroMaid.git
   cd retroMaid
   ```

3. Update config:
   ```yaml
   roms_path: "/userdata/roms"
   ```

4. Run:
   ```bash
   python retromaid.py scrape psx
   ```

## Tips for Success

### 1. Start Small
Test with a small system first (like Game Boy) to understand the workflow.

### 2. Monitor API Usage
ScreenScraper free accounts have limits:
- ~20 requests/minute
- 50,000 requests/day

retroMaid respects these limits automatically.

### 3. Use Hash Matching
Hash-based matching is most accurate and uses the same quota as name matching. retroMaid uses hashes automatically when available.

### 4. Backup First
retroMaid creates automatic backups, but you can also:
```bash
cp roms/psx/gamelist.xml roms/psx/gamelist.xml.backup
```

### 5. Check Results in Batocera
After scraping:
1. Open EmulationStation
2. Press `Start`
3. Go to `Game Settings` > `Update Gamelists`

## Troubleshooting

### "Module not found" errors
```bash
python3 -m pip install -r requirements.txt --upgrade
```

### "ROMs path does not exist"
Check that your path in `config.yaml` is correct and accessible.

### "No matches found"
Some ROMs may not be in ScreenScraper database. Try:
- Renaming to standard format: "Game Name (Region).ext"
- Checking if the ROM is actually the file you think it is
- Trying a different ROM dump

### "Rate limit exceeded"
Wait a few minutes, then continue. retroMaid will resume from where it left off.

## Getting More Help

- **Detailed Setup**: See [SETUP.md](SETUP.md)
- **Full Documentation**: See [README.md](README.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: Open an issue on GitHub

## Example Session

Here's what a typical session looks like:

```bash
# 1. Check what systems you have
$ python3 retromaid.py list-systems
Available systems:
  - psx
  - nes
  - snes

# 2. See what needs scraping
$ python3 retromaid.py list-systems --system psx
PSX Statistics
┌─────────────────────┬───────┐
│ Metric              │ Count │
├─────────────────────┼───────┤
│ Total ROMs          │   150 │
│ With Metadata       │    50 │
│ Without Metadata    │   100 │
│ Complete Metadata   │    45 │
│ Incomplete Metadata │     5 │
└─────────────────────┴───────┘

# 3. Scrape the missing ones
$ python3 retromaid.py scrape psx
Processing system: psx
Found 100 ROMs missing metadata
Proceed with scraping? [Y/n]: y

Processing psx... ━━━━━━━━━━━━━━━━━━━━━ 100/100
✓ Crash Bandicoot
✓ Spyro the Dragon
✓ Final Fantasy VII
...

Processing complete!
Successful: 95
Failed: 3
Skipped: 2

# 4. Check what failed
$ python3 retromaid.py status --system psx
PSX Processing Status
┌───────────────┬───────┐
│ Metric        │ Value │
├───────────────┼───────┤
│ Total         │   100 │
│ Processed     │   100 │
│ Successful    │    95 │
│ Failed        │     3 │
│ Skipped       │     2 │
│ Remaining     │     0 │
└───────────────┴───────┘

Errors:
  ./unknown_game.cue: No match found
  ...
```

That's it! You're ready to use retroMaid. Happy scraping! 🎮
