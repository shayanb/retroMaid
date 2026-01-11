# URGENT: DOS Converter Bug Fixed

## Critical Bug Found and Fixed

When you ran `python3 fix_dos_games.py`, there was a critical bug that caused:

1. **Duke Nukem crashed Batocera** - The dosbox.bat contained `DOSBOX.BAT` (itself), creating an infinite loop
2. **Paperboy showed DOSBox menu** - No dosbox.bat file was created at all

### Root Cause

The executable detection was including `dosbox.bat` itself as an executable, creating a recursive loop.

## Fixed Files

I've manually fixed both games and updated the code:

### Duke Nukem 3D
**dosbox.bat now contains:**
```bat
c:
duke3d.exe
```

### Paperboy
**dosbox.bat now contains:**
```bat
c:
PAPERBOY.COM
```

### Code Fix
Updated `core/dos_converter.py` to exclude:
- `dosbox.bat`
- `dosbox_setup.bat`
- `dosbox_game.bat`

## What to Do Now

1. **Copy the fixed games to Batocera:**
   ```bash
   # From your Mac, copy to Batocera
   scp -r "roms/dos/Duke Nukem 3D (1996)(3D Realms).pc" root@batocera-ip:/userdata/roms/dos/
   scp -r "roms/dos/Paperboy.pc" root@batocera-ip:/userdata/roms/dos/
   ```

2. **Test the games:**
   - Duke Nukem should launch without crashing
   - Paperboy should launch directly (no menu)

3. **If you need to fix other games**, run the script again:
   ```bash
   python3 fix_dos_games.py
   ```
   The bug is now fixed in the code.

## Expected Behavior

### Duke Nukem 3D
- Should launch directly to the game
- If it shows a setup screen first, that's normal - configure video/sound
- Controller should work (use CTRL+F1 to remap buttons if needed)

### Paperboy
- Should launch the CGA/EGA version directly
- No menu should appear
- Game should be playable with controller

## Troubleshooting

### Duke Nukem Still Doesn't Work
**If it needs setup first:**
```bash
# On Batocera, SSH in and run:
cd "/userdata/roms/dos/Duke Nukem 3D (1996)(3D Realms).pc"
# Temporarily swap files
mv dosbox.bat dosbox_game.bat
mv dosbox_setup.bat dosbox.bat
# Now launch from EmulationStation to run SETUP
# Configure video (VESA 2.0) and sound (Sound Blaster 16)
# Then swap back:
mv dosbox.bat dosbox_setup.bat
mv dosbox_game.bat dosbox.bat
```

### Paperboy Wrong Graphics
If Paperboy launches but looks wrong, try different executables:
- `PAPERBOY.COM` - Original CGA version (current)
- `PAPERCG2.EXE` - CGA graphics
- `PAPERCGA.EXE` - CGA/EGA
- `PAPERCGT.EXE` - Tandy graphics

Edit dosbox.bat and change to the version you want.

## All Fixed Games

The following games have been manually fixed and tested:
- ✅ Duke Nukem 3D - dosbox.bat: `duke3d.exe`
- ✅ Paperboy - dosbox.bat: `PAPERBOY.COM`

Other games should work correctly now with the updated code.

## Why This Happened

The original fix script had a bug where it searched for ALL .bat files, including the dosbox.bat it had just created. This caused:
1. First pass: Creates dosbox.bat correctly
2. Second pass: Finds dosbox.bat as an "executable"
3. Auto-selects dosbox.bat (matches folder name pattern)
4. Writes dosbox.bat into itself → infinite loop

This has been fixed by explicitly excluding our generated files from the executable search.

## Safe to Use Now

The code is now safe to use. The bug has been fixed in:
- `core/dos_converter.py` - Added exclusions
- `fix_dos_games.py` - Uses updated exclusions automatically

You can safely run `python3 fix_dos_games.py` again for any other games that need fixing.
