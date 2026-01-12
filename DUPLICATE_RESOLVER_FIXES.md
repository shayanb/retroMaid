# Duplicate Resolver Fixes - Complete

## Issues Fixed ✅

### 1. Error: `DuplicateGroup.__init__() got an unexpected keyword argument 'canonical_name'`

**Root Cause:** The `run_duplicate_finder()` function in `retromaid.py` (line 846) was using an outdated API for creating `DuplicateGroup` objects.

**Old code (broken):**
```python
resolver = DuplicateResolver(retromaid.config)  # Wrong signature

groups = [
    DuplicateGroup(canonical_name=name, files=roms)  # Wrong parameters
    for name, roms in duplicates.items()
]

resolver.resolve_duplicates(groups, delete_from_disk=True)  # Method doesn't exist
```

**New code (fixed):**
```python
resolver = DuplicateResolver(strategy="ask", delete_files=delete_files)

for name, roms in duplicates.items():
    group = DuplicateGroup(roms)  # Correct: just pass roms list
    keep = resolver.resolve(group)  # Correct: call resolve() for each group
    # ... handle results
```

**Files Modified:**
- `retromaid.py` lines 838-883

---

### 2. Enhanced Interactive Menu

**Added improvements:**

#### Better Visual Layout
```
Options:
  [1-N] - Keep specific ROM(s) (comma-separated, e.g. '1,3')

  Single group actions:
    a - Keep all
    m - Keep most complete (based on metadata)
    f - Keep first
    s - Skip (keep all)

  Default for all remaining groups:
    da - Default: keep all for remaining
    dm - Default: keep most complete for remaining
    df - Default: keep first for remaining
```

#### Recommended ROM Highlighting
The table now includes a "Recommended" column with a ⭐ star marking the ROM with the most complete metadata. This row is also highlighted in green.

```
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ #  ┃ Filename             ┃   Size ┃ Has Metadata ┃ Completeness┃ Recommended ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 1  │ Sonic (USA).zip      │ 1.2 MB │      ✓       │       85%   │             │
│ 2  │ Sonic (Europe).zip   │ 1.3 MB │      ✓       │       100%  │     ⭐      │  ← Green
│ 3  │ Sonic (Japan).zip    │ 1.1 MB │      ✓       │       60%   │             │
└────┴──────────────────────┴────────┴──────────────┴─────────────┴─────────────┘
```

#### User Feedback
When a choice is made, the system now shows what was selected:

**Keep most complete:**
```
→ Keeping: Sonic (Europe).zip
```

**Keep specific ROMs:**
```
→ Keeping 2 ROM(s):
    Sonic (USA).zip
    Sonic (Japan).zip
```

**Default action applied:**
```
Sonic the Hedgehog (3 duplicates): keeping most complete
Mortal Kombat (2 duplicates): keeping most complete
Street Fighter (4 duplicates): keeping most complete
```

---

## How It Works Now

### Interactive Workflow

1. **Select System:**
   ```
   Select system to deduplicate: megadrive
   ```

2. **View Duplicates:**
   Shows all duplicate groups with file details in tables

3. **Choose Resolution Method:**
   ```
   Resolve duplicates interactively? [y/n]: y
   ```

4. **Choose Deletion Method:**
   ```
   Delete ROM files from disk? (not just remove from gamelist) [y/n]: n
   ```

5. **For Each Duplicate Group:**
   - Shows table with all ROMs
   - Highlights recommended ROM (most complete metadata)
   - Prompts for action
   - Shows what was selected

6. **Summary:**
   ```
   Done!
     Removed from gamelist: 15
     Deleted files: 0
   ```

---

## Available Options Explained

### Single Group Actions

| Option | Description | Example |
|--------|-------------|---------|
| `1,2,3` | Keep specific ROMs by number | Keep ROMs #1 and #3 only |
| `a` | Keep all ROMs | Multi-disc games, no deletion |
| `m` | Keep most complete | **Recommended** - keeps ROM with best metadata |
| `f` | Keep first | Keep first ROM in list |
| `s` | Skip this group | Same as "keep all" |

### Default Actions (Apply to ALL Remaining Groups)

| Option | Description | Use Case |
|--------|-------------|----------|
| `da` | Default: keep all | When you want to keep everything from this point on |
| `dm` | Default: keep most complete | **Best for bulk cleanup** - auto-select best ROM |
| `df` | Default: keep first | Quick cleanup, keep first found |

---

## Example Usage

### Scenario 1: Clean up Genesis duplicates, keep best versions

```bash
python3 retromaid.py
# Select: 2. Deduplicate ROMs
# System: megadrive
# Resolve interactively: y
# Delete files: y

# For first group, review and choose:
Your choice: m

# Happy with the results? Use default for rest:
Your choice: dm

# All remaining groups automatically keep most complete ROM
```

### Scenario 2: Manual selection for important games

```bash
# For Sonic duplicates:
Your choice: 1,3  # Keep USA and Japan versions, remove Europe

# For generic games:
Your choice: dm   # Use default "most complete" for all remaining
```

### Scenario 3: Multi-disc games

The system automatically detects multi-disc games and keeps all discs:
```
Multi-disc game detected: Final Fantasy VII (3 discs)
→ Keeping all 3 ROMs
```

---

## Files Modified

### retromaid.py (lines 838-883)
- Fixed `run_duplicate_finder()` function
- Proper DuplicateGroup instantiation
- Correct DuplicateResolver API usage
- Added gamelist update and file deletion logic
- Added summary statistics

### core/duplicate_detector.py (multiple sections)

**Enhanced `_ask_user()` method (lines 180-227):**
- Added "Recommended" column to table
- Highlighted recommended ROM in green
- Improved menu layout with color coding
- Better option descriptions

**Enhanced `_apply_choice()` method (lines 260-301):**
- Added feedback showing which ROMs were kept
- Better error messages for invalid choices
- Clear confirmation of selections

**Enhanced `_apply_default_action()` method (lines 237-258):**
- Added feedback showing what action was applied
- Clear indication when default is being used

---

## Testing

### Test 1: Basic Interactive Resolution
```bash
python3 retromaid.py
# Select: 2. Deduplicate ROMs
# Choose a system with duplicates
# Resolve interactively: y
# Try different options: m, f, a, 1,2, etc.
```

**Expected:**
- ✓ No errors about `canonical_name`
- ✓ Table shows with star on recommended ROM
- ✓ Feedback shows what was kept
- ✓ Summary shows results

### Test 2: Default Actions
```bash
# When prompted for a duplicate group:
Your choice: dm

# All remaining groups should auto-resolve
```

**Expected:**
- ✓ Each group shows brief message: "Game Name: keeping most complete"
- ✓ No more prompts for remaining groups
- ✓ Summary at end

### Test 3: Multi-disc Detection
```bash
# If you have multi-disc games in your collection
```

**Expected:**
- ✓ Multi-disc games automatically kept (all discs)
- ✓ Message: "Multi-disc game detected"
- ✓ No prompt for these groups

---

## Summary

**Before:**
- ❌ Error on interactive resolution
- ❌ No visual indication of recommended ROM
- ❌ No feedback on selections
- ❌ Limited menu clarity

**After:**
- ✅ Interactive resolution works perfectly
- ✅ Star marks recommended ROM (also highlighted green)
- ✅ Clear feedback on all actions
- ✅ Organized, color-coded menu
- ✅ Default actions show progress
- ✅ Summary statistics at end

All duplicate resolution features now work as expected! 🎮
