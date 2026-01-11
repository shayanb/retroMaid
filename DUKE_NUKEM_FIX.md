# Duke Nukem 3D - Quick Fix Guide

## Why Duke Nukem Doesn't Work

Duke Nukem 3D (and many BUILD engine games) need to run **SETUP.EXE** first to configure:
- Video mode
- Sound card
- Controller/joystick settings

## Solution

I've created helper files in your Duke Nukem folder:

### Files Created

1. **dosbox.cfg** - DOSBox configuration with joystick enabled
2. **dosbox_setup.bat** - Launcher for SETUP.EXE
3. **CONTROLLER_SETUP.txt** - Controller mapping guide

### How to Fix in Batocera

**On your Raspberry Pi (via SSH or File Manager):**

```bash
cd "/userdata/roms/dos/Duke Nukem 3D (1996)(3D Realms).pc"

# Temporarily swap files
mv dosbox.bat dosbox_game.bat
mv dosbox_setup.bat dosbox.bat
```

**Launch the game in EmulationStation** - it will run SETUP instead:

1. Select **Video Mode**: VESA 2.0 (recommended)
2. Select **Sound Setup**:
   - Sound Blaster 16
   - IRQ: 5
   - DMA: 1
   - Port: 220 (hex)
3. Configure **Controller** (optional, can do later)
4. **Save** and exit

**Swap files back:**

```bash
mv dosbox.bat dosbox_setup.bat
mv dosbox_game.bat dosbox.bat
```

**Launch game again** - should now work!

## Alternative: Edit dosbox.bat

Or just try adding parameters to `dosbox.bat`:

```bat
c:
duke3d.exe /v8
```

Or:

```bat
c:
cd \
duke3d.exe
```

## Controller Issues?

See **CONTROLLER_SETUP.txt** in the game folder or [DOS_TROUBLESHOOTING.md](DOS_TROUBLESHOOTING.md)

Quick fix: While game is running, press **HOTKEY + L1** (or CTRL+F1) to open DOSBox mapper and remap buttons.
