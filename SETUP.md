# retroMaid Setup Guide

## Initial Setup

### 1. Install Dependencies

```bash
cd /Users/shayan/Documents/GitHub/retroMaid
python3 -m pip install -r requirements.txt
```

### 2. Configure Credentials

Create a `.env` file with your ScreenScraper credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
SCREENSCRAPER_USERNAME=your_username_here
SCREENSCRAPER_PASSWORD=your_password_here
```

### 3. Update Configuration

Edit `config.yaml` and set your ROMs path:

**For Local Testing (Mac):**
```yaml
roms_path: "/Users/shayan/Documents/GitHub/retroMaid/roms"
```

**For Network Share (Batocera SMB):**
```yaml
roms_path: "/Volumes/BATOCERA/roms"
```

or when mounted differently:
```yaml
roms_path: "/Volumes/share/roms"
```

### 4. Test the Installation

```bash
python3 retromaid.py list-systems
```

You should see a list of available systems.

## Usage Examples

### Basic Workflow

1. **Check what systems are available:**
   ```bash
   python3 retromaid.py list-systems
   ```

2. **Scan a specific system to see statistics:**
   ```bash
   python3 retromaid.py list-systems --system psx
   ```

3. **Scrape metadata for a system:**
   ```bash
   python3 retromaid.py scrape psx
   ```

4. **Check processing status:**
   ```bash
   python3 retromaid.py status --system psx
   ```

### Advanced Usage

**Scrape with videos (uses more quota):**
```bash
python3 retromaid.py scrape psx --videos
```

**Skip image downloads (metadata only):**
```bash
python3 retromaid.py scrape psx --no-images
```

**Force reprocessing (ignore checkpoint):**
```bash
python3 retromaid.py scrape psx --force
```

**Find and resolve duplicates:**
```bash
python3 retromaid.py duplicates psx --resolve
```

**Clear checkpoint to start fresh:**
```bash
python3 retromaid.py clear --system psx
```

## Network Share Setup (Mac)

### Mount Batocera Share

1. **Via Finder:**
   - Press `Cmd+K`
   - Enter: `smb://BATOCERA/share`
   - Connect

2. **Via Command Line:**
   ```bash
   mkdir -p /Volumes/BATOCERA
   mount_smbfs //guest@BATOCERA/share /Volumes/BATOCERA
   ```

3. **Auto-mount on login:**
   - Go to System Preferences > Users & Groups
   - Select your user
   - Go to Login Items
   - Add the share: `smb://BATOCERA/share`

### Update Config

Once mounted, update `config.yaml`:
```yaml
roms_path: "/Volumes/BATOCERA/roms"
```

## Running on Raspberry Pi (Batocera)

### SSH into Batocera

```bash
ssh root@batocera
# Default password: linux
```

### Install retroMaid

```bash
cd /userdata
git clone https://github.com/yourusername/retroMaid.git
cd retroMaid
```

### Install Dependencies

Batocera has Python pre-installed, but you may need to install pip packages:

```bash
python -m pip install -r requirements.txt
```

### Configure for Local Use

Update `config.yaml`:
```yaml
roms_path: "/userdata/roms"
```

### Run retroMaid

```bash
python retromaid.py list-systems
python retromaid.py scrape psx
```

## Tips

### Save API Quota

- **Test with a small system first** (like Game Boy with fewer games)
- **Use hash-based matching** (automatic, most accurate, uses 1 request per game)
- **Disable videos** unless you really want them (they're large)
- **Check rate limits** in your ScreenScraper account

### Best Practices

1. **Always backup first**: retroMaid creates backups automatically, but you can also:
   ```bash
   cp roms/psx/gamelist.xml roms/psx/gamelist.xml.manual_backup
   ```

2. **Process in batches**: If you have 1000+ ROMs, consider breaking into chunks
   - Process, wait for rate limit reset, continue
   - retroMaid's checkpoint system handles this automatically

3. **Region preferences**: Edit `config.yaml` to set your preferred region order:
   ```yaml
   matching:
     region_priority:
       - "us"
       - "eu"
       - "jp"
   ```

4. **Check results in Batocera**: After scraping, reload gamelist in EmulationStation:
   - Press `Start` > `Game Settings` > `Update Gamelists`

## Troubleshooting

### "Configuration file not found"
```bash
# Make sure you're in the retroMaid directory
cd /Users/shayan/Documents/GitHub/retroMaid
```

### "ROMs path does not exist"
- Check that the path in `config.yaml` is correct
- For network shares, ensure it's mounted
- For local testing, verify the roms directory exists

### "ScreenScraper credentials not configured"
- Make sure `.env` file exists
- Check that credentials are correct
- Try logging into ScreenScraper website to verify

### "Rate limit exceeded"
- Wait a few minutes
- Lower `rate_limit` in config.yaml
- Check your ScreenScraper account quota

### Import errors
```bash
# Reinstall dependencies
python3 -m pip install -r requirements.txt --force-reinstall
```

## Next Steps

1. **Test with sample data**: Use the included `roms/psx` sample
2. **Configure for your setup**: Update paths for your environment
3. **Start small**: Process one small system first
4. **Expand**: Once comfortable, process larger collections
5. **Schedule**: Consider setting up a cron job for periodic updates

## Getting Help

- Check the main [README.md](README.md)
- Review [idea.md](idea.md) for project goals
- Open an issue on GitHub
- Check ScreenScraper API documentation

Happy scraping! 🎮
