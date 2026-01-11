# DOS ROM Conversion Guide

retroMaid now includes a **DOS ROM converter** that transforms DOS games into Batocera-compatible format automatically!

## What It Does

Converts DOS games to Batocera's required structure:
- Renames folders to add `.pc` or `.dos` extension
- Creates `dosbox.bat` with the correct launch command
- Handles ZIP file extraction
- Updates `gamelist.xml` paths automatically
- Preserves user stats (playcounts, favorites, etc.)

## Batocera DOS Structure

Batocera requires DOS games in this format:

```
gamename.pc/
├── dosbox.bat    # Launch command file
├── game.exe      # The actual game executable
└── ...           # Other game files
```

The `dosbox.bat` file must contain the command to launch the game (e.g., `game.exe`).

## Usage

### Basic Conversion (Interactive)

```bash
python3 retromaid.py convert-dos
```

This will:
1. Scan your `dos` directory
2. Show games that need conversion
3. Ask for confirmation for each game
4. Let you choose the correct executable if multiple found
5. Create `.pc` folders with `dosbox.bat`
6. Update `gamelist.xml`

### Automatic Conversion

```bash
python3 retromaid.py convert-dos --no-interactive
```

Converts all games automatically using auto-detected launch commands.

### Delete Original ZIPs

```bash
python3 retromaid.py convert-dos --delete-zips
```

Extracts ZIP files and deletes the original archives after successful conversion.

## Examples

### Example 1: Simple Game

**Before:**
```
dos/
└── Arkanoid (1988)/
    ├── arkanoid.exe
    └── arkanoid.dat
```

**After:**
```
dos/
└── Arkanoid (1988).pc/
    ├── dosbox.bat       # Contains: arkanoid.exe
    ├── arkanoid.exe
    └── arkanoid.dat
```

### Example 2: ZIP File

**Before:**
```
dos/
└── Doom (1993).zip
```

**After:**
```
dos/
└── Doom (1993).pc/
    ├── dosbox.bat       # Contains: doom.exe
    ├── doom.exe
    ├── doom.wad
    └── ...
```

### Example 3: Multiple Executables (Interactive)

**Before:**
```
dos/
└── Prince of Persia (1989)/
    ├── setup.exe
    ├── prince.exe
    └── data files...
```

**Interactive prompt:**
```
Found executables:
  → [1] prince.exe
    [2] setup.exe

Suggested: prince.exe

Launch command (number or custom): 1
```

## How It Works

### Launch Command Detection

The converter automatically detects the correct executable using this logic:

1. **Common launchers first**: Looks for `start.bat`, `run.bat`, `game.exe`, etc.
2. **Single executable**: If only one `.exe`/`.com`/`.bat` found, uses it
3. **Name matching**: Matches executable name with folder name
4. **Largest file**: Uses the biggest executable as fallback
5. **Manual override**: In interactive mode, you can choose or type custom command

### ZIP File Handling

When converting ZIP files:
1. Extracts to temporary location
2. Analyzes for executables
3. Creates `.pc` folder
4. Moves extracted files
5. Creates `dosbox.bat`
6. Optionally deletes original ZIP

### gamelist.xml Updates

After conversion, the tool:
- Updates paths from `./game.zip` → `./game.pc`
- Updates paths from `./game/` → `./game.pc`
- Preserves all metadata (descriptions, images, etc.)
- Preserves user stats (playcounts, favorites, playtime)
- Creates automatic backup

## Troubleshooting

### "Could not detect launch command"

**Problem:** Multiple executables found and auto-detection failed.

**Solution:** Run in interactive mode and select manually:
```bash
python3 retromaid.py convert-dos --interactive
```

### "Target directory already exists"

**Problem:** A `.pc` folder already exists with the same name.

**Solution:** Either:
1. Delete or rename the existing `.pc` folder
2. The game is already converted (check if it has `dosbox.bat`)

### Wrong Executable Selected

**Problem:** Auto-detection picked the wrong `.exe` file.

**Solution:**
1. Navigate to the `.pc` folder
2. Edit `dosbox.bat`
3. Change to correct executable name

Or reconvert with interactive mode.

### Game Won't Launch in Batocera

**Common issues:**

1. **Wrong command in dosbox.bat**
   - Open the `.pc` folder
   - Edit `dosbox.bat` to use correct executable
   - Make sure file name matches exactly (case-sensitive on some systems)

2. **Missing files**
   - Some games need all files from the original ZIP
   - Check if extraction was complete
   - Compare with original ZIP contents

3. **Needs special DOSBox config**
   - Some games need specific CPU cycles, memory, etc.
   - You can add these to `dosbox.bat`:
     ```bat
     @echo off
     config -set "cpu cycles=10000"
     game.exe
     ```

## Advanced Usage

### Custom Launch Command

In interactive mode, you can type any command:
```
Launch command: cd game && start.bat
```

### Batch Processing

Process all games automatically:
```bash
# Convert everything without asking
python3 retromaid.py convert-dos --no-interactive

# Convert and clean up ZIPs
python3 retromaid.py convert-dos --no-interactive --delete-zips
```

### Selective Conversion

The tool only converts games that need it:
- Already converted games (with `dosbox.bat`) are skipped
- Duplicate folder/ZIP pairs: only one is converted
- You can run the command multiple times safely

## Integration with Scraping

After converting DOS games, you can scrape metadata:

```bash
# Convert DOS games first
python3 retromaid.py convert-dos

# Then scrape metadata
python3 retromaid.py scrape dos
```

The scraper will:
- Use the new `.pc` paths
- Download cover art and media
- Fill in game descriptions
- Add release dates and developers

## Comparison with ExoDOSConverter

**ExoDOSConverter:**
- Python-based
- Requires specific ExoDOS format
- Complex dependencies
- ~500+ lines for conversion alone

**retroMaid DOS Converter:**
- Integrated into retroMaid
- Works with any DOS game folder or ZIP
- Minimal dependencies (uses built-in zipfile)
- ~350 lines with full CLI integration
- Automatic gamelist.xml updates
- Interactive and batch modes
- Better error handling and recovery

## Tips

1. **Test First**: Convert one or two games first to verify they work in Batocera
2. **Backup**: The tool creates backups, but make your own copy of important games
3. **Interactive Mode**: Use interactive mode for games you're unsure about
4. **Check Launch**: After conversion, verify `dosbox.bat` has the right command
5. **Original ZIPs**: Keep original ZIPs until you verify games work in Batocera

## Supported Formats

**Input formats:**
- Regular folders (no extension)
- ZIP archives (.zip)
- Already extracted game folders

**Output format:**
- `.pc` folders with `dosbox.bat`
- Compatible with Batocera DOS system
- Works with DOSBox and pure-DOSBox cores

## Next Steps

After converting your DOS games:

1. **Test in Batocera**:
   - Copy converted games to Batocera
   - Launch from EmulationStation
   - Verify they work correctly

2. **Scrape Metadata**:
   ```bash
   python3 retromaid.py scrape dos
   ```

3. **Find Duplicates**:
   ```bash
   python3 retromaid.py duplicates dos --resolve
   ```

4. **Clean Up**: Remove any original ZIPs or unconverted folders

## Support

If you encounter issues:
- Check the main [README.md](README.md)
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Open an issue on GitHub

Happy DOS gaming! 🎮💾
