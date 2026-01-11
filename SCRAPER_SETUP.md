# Scraper Configuration Guide

## Current Setup

✅ **ScreenScraper** - Primary scraper (user credentials configured)
✅ **IGDB** - Fallback scraper (credentials configured)
❌ **ScreenScraper Dev Credentials** - Not configured (optional but recommended)

## How It Works

retroMaid now uses a **multi-scraper fallback system**:

1. **ScreenScraper (Primary)** - Tries first, has ROM hash matching
2. **IGDB (Fallback)** - Automatically used if ScreenScraper fails or is unavailable

## ScreenScraper Authentication

### User Credentials (Currently Using)
- **What**: Your ScreenScraper.fr account
- **Limits**: 20 requests/minute, daily quota limits
- **Status**: ✅ Configured (`sbetamc`)

### Dev Credentials (Recommended)
- **What**: Developer API access (requires approval)
- **Limits**: Higher quotas, better rate limits
- **Status**: ❌ Not configured
- **How to Get**: Apply at https://www.screenscraper.fr/forumsujets.php?frub=12

To add dev credentials, update `.env`:
```bash
SCREENSCRAPER_DEV_ID=your_dev_id
SCREENSCRAPER_DEV_PASSWORD=your_dev_password
```

## IGDB Setup

✅ **Configured and Ready**

Your IGDB credentials are already set up in `.env`:
```bash
IGDB_CLIENT_ID=rssmdorbluw4lpurfdorjnk0bd5r17
IGDB_CLIENT_SECRET=7itln3ld4s3091b32oz5bxklqruauo
```

### How IGDB Works
- Uses Twitch Developer API
- No ROM hash matching (name-based only)
- 4 requests/second rate limit
- Access token auto-refreshes

## Supported Systems

### ScreenScraper
All major systems including:
- C64 (ID: 66) ✅
- Commodore systems, Amiga, etc.
- All consoles (NES, SNES, PlayStation, etc.)

### IGDB
All major systems including:
- C64 (ID: 15) ✅
- All modern and retro systems

## Troubleshooting

### "Unknown system for ScreenScraper: c64"
✅ **Fixed!** Added C64 and all computer systems to mapping.

### Rate Limit Errors
If you see:
```
WARNING  Thread limit exceeded
WARNING  Daily quota exceeded
```

**Solutions:**
1. Wait a few minutes for rate limit to reset
2. Get ScreenScraper dev credentials (recommended)
3. IGDB will automatically be used as fallback

### Authentication Failures

**ScreenScraper 401 Unauthorized:**
- Check username/password in `.env`
- Verify account is active at screenscraper.fr

**IGDB 401 Unauthorized:**
- Check client_id/secret in `.env`
- Verify Twitch Developer app is active

## Testing

Test both scrapers:

```bash
# Will try ScreenScraper first, fall back to IGDB if needed
python3 retromaid.py scrape c64
```

You should see:
```
Processing: game.d64
✓ Game Name (from ScreenScraper or IGDB)
```

If ScreenScraper fails:
```
Trying IGDB fallback for: game.d64
✓ Game Name (from IGDB)
```

## Recommended Actions

1. **Get ScreenScraper Dev Credentials**
   Apply at: https://www.screenscraper.fr/forumsujets.php?frub=12
   This will significantly improve rate limits

2. **Current Workaround**
   IGDB fallback is now active - scraping will work even if ScreenScraper rate limits

3. **Monitor Usage**
   ScreenScraper shows your daily usage at: https://www.screenscraper.fr/votrecompte.php

## System IDs Reference

### C64 System IDs
- ScreenScraper: 66
- IGDB: 15

Both are now configured and working!
