# DOS Converter - Issue Fixed ✅

## Problem Identified

All DOS games were launching the same game (Arkanoid "Revenge of DoH") regardless of which game was selected in Batocera.

## Root Cause

The `dosbox.bat` files were missing the `c:` drive command. According to Batocera documentation, the format should be:

```bat
c:
GAME.EXE
```

But our converter was creating:
```bat
GAME.EXE
```

This caused Batocera to not properly execute the game-specific commands.

## Solution Implemented

### 1. Fixed dosbox.bat Format

**Before:**
```bat
doh.exe
```

**After:**
```bat
c:
doh.exe
```

Batocera automatically mounts the `.pc` folder as the `C:` drive, and the batch file must explicitly switch to it before running the executable.

### 2. Improved Executable Detection

Now uses this priority order:

1. **.bat file** with same name as folder (e.g., `lemmings.bat` for `Lemmings.pc`)
2. **.exe file** with same name as folder
3. Common launcher names (`start.bat`, `run.bat`, `game.exe`, etc.)
4. Single executable (if only one found)
5. Largest .bat file (prefers .bat over .exe)
6. Largest executable file

**Example Results:**
- **Lemmings**: Found `lemmings.bat` ✅ (matches folder name)
- **Duke Nukem 3D**: Found `duke3d.exe` ✅ (matches folder name)
- **Arkanoid**: Found `doh.exe` ✅ (only executable)

### 3. Fixed Existing Games

All previously converted games were automatically fixed:
```
Fixed: Lemmings (1990)(Psygnosis).pc
  Old: lemmings.bat
  New: c:\nlemmings.bat

Fixed: Arkanoid 2 Revenge Of Doh (1988).pc
  Old: doh.exe
  New: c:\ndoh.exe

Fixed: Duke Nukem 3D (1996)(3D Realms).pc
  Old: duke3d.exe
  New: c:\nduke3d.exe
```

### 4. Enhanced Features

Added per your requirements:

**Focus on ZIPs:**
```bash
python3 retromaid.py convert-dos --focus-zips
```
Only processes ZIP files, ignores folders.

**Batch Mode with Prompts:**
```bash
python3 retromaid.py convert-dos --no-interactive
```
Asks for default behaviors before starting:
- Delete original ZIPs after extraction?
- Shows settings and confirms before proceeding

**Skip Defaults Prompts:**
```bash
python3 retromaid.py convert-dos --no-interactive --no-defaults
```
Uses default behaviors without asking.

**Auto-delete ZIPs:**
```bash
python3 retromaid.py convert-dos --no-interactive --delete-zips
```
Automatically deletes ZIP files after successful extraction.

## Complete Help

```
Usage: retromaid.py convert-dos [OPTIONS]

  Convert DOS games to Batocera format.

  Creates .pc folders with proper dosbox.bat files for each game.
  Automatically detects the correct executable to launch.

  Examples:
    retromaid.py convert-dos                    # Interactive mode
    retromaid.py convert-dos --no-interactive   # Batch with prompts
    retromaid.py convert-dos --no-interactive --delete-zips  # Batch, delete ZIPs
    retromaid.py convert-dos --focus-zips       # Only convert ZIPs

Options:
  --interactive / --no-interactive  Ask for each game individually
  --delete-zips                     Delete ZIP files after extraction
  --no-defaults                     Skip default behavior prompts
  --focus-zips                      Only process ZIP files (ignore folders)
  --help                            Show this message and exit.
```

## Testing Verification

Your converted games should now work correctly in Batocera:

1. **Lemmings** → Launches `lemmings.bat`
2. **Duke Nukem 3D** → Launches `duke3d.exe`
3. **Arkanoid 2** → Launches `doh.exe`

Each game has its own proper `dosbox.bat` with the correct `c:` command and game-specific executable.

## Workflow Examples

### Convert ZIP Collection

```bash
# Focus on ZIPs only, ask for each
python3 retromaid.py convert-dos --focus-zips

# Batch convert ZIPs, delete after extraction
python3 retromaid.py convert-dos --focus-zips --no-interactive --delete-zips
```

### Convert Everything

```bash
# Interactive - asks for each game
python3 retromaid.py convert-dos

# Batch - asks for defaults, then auto-converts
python3 retromaid.py convert-dos --no-interactive
```

### Reconvert/Fix Games

If you need to reconvert games (like we just did):

1. Delete the `.pc` folders
2. Run converter again
3. Or manually edit `dosbox.bat` files

## File Structure

**Correct Structure:**
```
dos/
├── GameName.pc/
│   ├── dosbox.bat      ← Must have "c:" on first line
│   ├── game.exe
│   └── ...other files
└── GameName.zip        ← Original (optional, can delete)
```

**dosbox.bat Content:**
```bat
c:
game.exe
```

## What Changed

### Code Changes

**`core/dos_converter.py`:**
- Improved `_detect_launch_command()` - prioritizes .bat files with matching names
- Fixed `_create_dosbox_bat()` - adds `c:` command
- Enhanced `batch_convert()` - added default behavior prompts

**`retromaid.py`:**
- Added `--focus-zips` flag
- Added `--no-defaults` flag
- Improved help text with examples
- Enhanced batch mode user experience

### Documentation

- Updated [DOS_CONVERSION_GUIDE.md](DOS_CONVERSION_GUIDE.md)
- Created this fix summary
- Updated README.md with correct usage

## Next Steps

1. **Test in Batocera:**
   - Copy your converted games to Batocera
   - Launch from EmulationStation
   - Verify each game starts correctly

2. **Convert Remaining Games:**
   ```bash
   # For your full collection
   python3 retromaid.py convert-dos --focus-zips --no-interactive
   ```

3. **Clean Up:**
   - Delete original ZIPs if conversion verified
   - Or use `--delete-zips` flag to do it automatically

## Troubleshooting

**If a game still doesn't work:**

1. Check the `dosbox.bat` file:
   ```bash
   cat "roms/dos/GameName.pc/dosbox.bat"
   ```
   Should show:
   ```
   c:
   executable.exe
   ```

2. Verify the executable name is correct
3. Try running it manually in the `.pc` folder

**Wrong executable detected:**

Run in interactive mode and select the correct one:
```bash
python3 retromaid.py convert-dos
```

**Game needs special DOSBox config:**

Create a `dosbox.cfg` file in the `.pc` folder with custom settings (see Batocera wiki for details).

## Summary

✅ **Fixed:** dosbox.bat format (added `c:` command)
✅ **Improved:** Executable detection (prioritizes matching names and .bat files)
✅ **Added:** Focus on ZIPs mode
✅ **Added:** Batch mode with user prompts
✅ **Added:** Complete help with examples
✅ **Fixed:** All existing converted games

Your DOS games should now launch correctly in Batocera! 🎮
