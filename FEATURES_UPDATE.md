# retroMaid v1.1.0 - New Features

## 🎉 What's New

### 1. DOS ROM Converter

Transform DOS games into Batocera-compatible format automatically!

**What it does:**
- Converts folders to `.pc` format (e.g., `game/` → `game.pc/`)
- Creates `dosbox.bat` with correct launch command
- Extracts and converts ZIP files
- Auto-detects the right executable to launch
- Updates `gamelist.xml` paths automatically

**Usage:**
```bash
# Interactive mode (recommended first time)
python3 retromaid.py convert-dos

# Automatic mode
python3 retromaid.py convert-dos --no-interactive

# Clean up ZIPs after extraction
python3 retromaid.py convert-dos --delete-zips
```

**See:** [DOS_CONVERSION_GUIDE.md](DOS_CONVERSION_GUIDE.md) for complete guide

---

### 2. Physical File Deletion for Duplicates

Now you can actually **delete ROM files** when resolving duplicates, not just remove them from gamelist.xml!

**Before:**
```bash
python3 retromaid.py duplicates psx --resolve
# Only removed from gamelist.xml, files stayed on disk
```

**Now:**
```bash
# Option 1: Specify on command line
python3 retromaid.py duplicates psx --resolve --delete

# Option 2: Interactive prompt during resolution
python3 retromaid.py duplicates psx --resolve
# You'll be asked: "Delete ROM files from disk?"
```

**Features:**
- Deletes both files and directories
- Shows confirmation before deleting
- Reports successful/failed deletions
- Preserves multi-disc games automatically
- Creates backups of gamelist.xml before changes

**Example session:**
```bash
$ python3 retromaid.py duplicates psx --resolve --delete

Scanning for duplicates: psx
Found 5 groups of duplicates

Duplicate ROMs found: Final Fantasy VII (3 duplicates)

Delete ROM files from disk? (not just remove from gamelist) [y/N]: y

┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ # ┃ Filename                   ┃ Size   ┃ Has Metadata┃Completeness┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1 │ Final Fantasy VII (USA).bin│ 654 MB │      ✓      │    100%    │
│ 2 │ Final Fantasy VII.bin      │ 654 MB │      ✓      │     85%    │
│ 3 │ FF7.bin                    │ 654 MB │      ✗      │      0%    │
└───┴────────────────────────────┴────────┴─────────────┴────────────┘

Your choice [m]: 1
Removed from gamelist: Final Fantasy VII.bin
Removed from gamelist: FF7.bin
Deleted file: Final Fantasy VII.bin
Deleted file: FF7.bin

Duplicate resolution complete!
Removed from gamelist: 2
Deleted files: 2
```

---

## 📚 Updated Documentation

New documentation files:
- **[DOS_CONVERSION_GUIDE.md](DOS_CONVERSION_GUIDE.md)** - Complete DOS conversion guide
  - How it works
  - Usage examples
  - Troubleshooting
  - Comparison with ExoDOSConverter
  - Integration tips

Updated files:
- **[README.md](README.md)** - Added new features to main docs
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

## 🔧 Technical Details

### DOS Converter Implementation

**New files:**
- `core/dos_converter.py` (~350 lines)
  - `DOSConverter` class
  - Intelligent executable detection
  - ZIP extraction and conversion
  - Batch processing with progress

**Key algorithms:**
1. **Launch Command Detection:**
   - Common launcher patterns (`start.bat`, `game.exe`)
   - Single executable auto-select
   - Name-based matching (folder name ↔ exe name)
   - Size-based fallback (largest executable)
   - Interactive override in UI

2. **ZIP Handling:**
   - Extract to `.pc` folder
   - Find ROM files (skip metadata/docs)
   - Hash for verification
   - Optional cleanup

3. **gamelist.xml Updates:**
   - Path rewriting (`.zip` → `.pc`)
   - Metadata preservation
   - Backup creation

### Duplicate Deletion Enhancement

**Modified files:**
- `core/duplicate_detector.py`
  - Added `delete_files` parameter to `DuplicateResolver`
  - New `delete_rom_files()` method
  - Interactive confirmation prompt
  - File and directory deletion support

- `retromaid.py`
  - Added `--delete` flag to `duplicates` command
  - Integrated file deletion into resolution flow
  - Added deletion statistics to summary

**Safety features:**
- Always backs up gamelist.xml first
- Multi-disc games never deleted
- Confirmation required (unless automated)
- Detailed logging of all deletions
- Reports failures separately

---

## 🧪 Testing

Both features have been tested with sample ROMs:

**DOS Converter:**
- ✅ Folder conversion (no extension → `.pc`)
- ✅ ZIP extraction and conversion
- ✅ dosbox.bat creation
- ✅ Executable auto-detection
- ✅ gamelist.xml path updates
- ✅ User stats preservation

**Duplicate Deletion:**
- ✅ Interactive mode with confirmation
- ✅ Command-line flag mode
- ✅ File deletion
- ✅ Directory deletion
- ✅ Error handling
- ✅ Multi-disc preservation

---

## 💡 Usage Tips

### DOS Conversion Workflow

1. **Test First:**
   ```bash
   # Try interactive mode first
   python3 retromaid.py convert-dos
   ```

2. **Verify:**
   - Check the created `.pc` folders
   - Open `dosbox.bat` to see launch command
   - Test one game in Batocera

3. **Batch Convert:**
   ```bash
   # Once confident, batch convert
   python3 retromaid.py convert-dos --no-interactive
   ```

4. **Scrape Metadata:**
   ```bash
   # Get full metadata for DOS games
   python3 retromaid.py scrape dos
   ```

### Duplicate Management Workflow

1. **Find Duplicates:**
   ```bash
   # See what duplicates exist
   python3 retromaid.py duplicates psx
   ```

2. **Resolve Interactively:**
   ```bash
   # Interactive resolution without deletion
   python3 retromaid.py duplicates psx --resolve
   ```

3. **Review Changes:**
   - Check `gamelist.xml_backup`
   - Verify kept ROMs

4. **Delete if Confident:**
   ```bash
   # Only after verifying, delete files
   python3 retromaid.py duplicates psx --resolve --delete
   ```

---

## 🚀 Upgrade Instructions

If you already have retroMaid installed:

```bash
# Pull latest changes
git pull origin main

# No new dependencies needed!
# All new features use existing packages

# Test new features
python3 retromaid.py convert-dos --help
python3 retromaid.py duplicates --help
```

---

## 📝 Examples

### Complete DOS Setup

```bash
# 1. Convert DOS games
python3 retromaid.py convert-dos

# 2. Scrape metadata
python3 retromaid.py scrape dos

# 3. Find and resolve duplicates
python3 retromaid.py duplicates dos --resolve

# 4. Check results
python3 retromaid.py list-systems --system dos
```

### Clean Duplicate Collection

```bash
# For each system with duplicates
for system in psx nes snes; do
  echo "Processing $system..."
  python3 retromaid.py duplicates $system --resolve --delete
done
```

---

## 🐛 Known Issues

None at this time. Please report any issues on GitHub.

---

## 🎯 Future Enhancements

Potential improvements for future versions:

- **DOS Converter:**
  - DOSBox configuration file generation
  - Game-specific settings database
  - Mount point configuration
  - Soundfont management

- **Duplicate Detection:**
  - Fuzzy file matching (similar file sizes)
  - Hash-based duplicate detection
  - Regional variant handling
  - Batch operations across systems

---

## 📊 Statistics

**New Code:**
- 1 new module (dos_converter.py)
- ~350 lines of conversion logic
- ~100 lines of CLI integration
- ~50 lines of deletion enhancement

**Documentation:**
- 1 new guide (DOS_CONVERSION_GUIDE.md)
- 1 update summary (this file)
- Updated README.md
- Updated CHANGELOG.md

**Total Impact:**
- ~500 lines of new code
- ~300 lines of documentation
- 2 new CLI commands
- 0 new dependencies

---

## 🙏 Acknowledgments

- Inspired by [ExoDOSConverter](https://github.com/Voljega/ExoDOSConverter)
- Built for the [Batocera](https://batocera.org/) community
- Tested with real ExoDOS games

---

**Enjoy the new features!** 🎮

For questions or issues, see the main [README.md](README.md) or open a GitHub issue.
