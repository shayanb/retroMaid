# DOS Games Troubleshooting Guide

## Duke Nukem 3D Not Working

Duke Nukem 3D (and many BUILD engine games) may need initial setup before they work properly.

### Solution 1: Run Setup First

1. **In your Duke Nukem 3D.pc folder**, you'll find:
   - `dosbox.bat` - Regular game launcher
   - `dosbox_setup.bat` - Setup launcher
   - `dosbox.cfg` - Configuration file
   - `CONTROLLER_SETUP.txt` - Controller help

2. **On Batocera**, temporarily rename files:
   ```bash
   cd "Duke Nukem 3D (1996)(3D Realms).pc"
   mv dosbox.bat dosbox_game.bat
   mv dosbox_setup.bat dosbox.bat
   ```

3. **Launch the game** - it will run SETUP.EXE instead

4. **Configure in setup:**
   - Set video mode (VESA 2.0 recommended)
   - Configure sound card
   - Set up controls/joystick if needed
   - Save and exit

5. **Rename back:**
   ```bash
   mv dosbox.bat dosbox_setup.bat
   mv dosbox_game.bat dosbox.bat
   ```

6. **Launch game normally** - should now work!

### Solution 2: Try Different Executable

Duke Nukem might need parameters or different launcher:

Edit `dosbox.bat`:
```bat
c:
duke3d.exe /v8
```

Or try:
```bat
c:
cd \
duke3d.exe
```

## Controller Mapping Issues

### Understanding Default Layout

Batocera uses the **Gravis PC Gamepad** layout by default:

**Your Controller → DOS Mapping:**
- **A (East)** → Button 1 (Green)
- **B (South)** → Button 2 (Yellow)
- **X (North)** → Button 3 (Blue)
- **Y (West)** → Button 4 (Red)
- **L/L2** → Additional buttons
- **R/R2** → Additional buttons

This might feel "off" because DOS games from the 90s used different button layouts.

### Fix 1: Use DOSBox Mapper (Per-Game)

**In Batocera while game is running:**

1. Press `HOTKEY + L1` (or `CTRL+F1` on keyboard)
2. The DOSBox mapper interface opens
3. Click a DOS action (like "Fire" or "Jump")
4. Press the controller button you want (like A or B)
5. Repeat for all actions
6. Press ESC to exit and save

Your settings are saved to `mapper.map` in the game's `.pc` folder.

### Fix 2: Edit dosbox.cfg (Global Settings)

Edit `dosbox.cfg` in your game folder:

```ini
[joystick]
joysticktype=auto        # Enables gamepad
timed=true              # Fixes self-moving joystick
buttonwrap=false        # Prevents button wrapping issues
swap34=false            # Try true if buttons 3&4 are swapped
```

### Fix 3: Use DOSBox Pure Core

DOSBox Pure has better controller support:

1. In EmulationStation, go to game options
2. Select "Advanced System Options"
3. Choose "Emulator: dosbox-pure" (instead of dosbox)
4. DOSBox Pure has deadzone settings and better gamepad defaults

## Common Issues

### Game Launches But Immediately Exits

**Cause:** Missing `c:` command in dosbox.bat

**Fix:** Edit `dosbox.bat`:
```bat
c:
game.exe
```

### Wrong Game Launches

**Cause:** All games using same dosbox.bat

**Fix:** Reconvert with fixed retroMaid:
```bash
python3 retromaid.py convert-dos --focus-zips --no-interactive
```

### Joystick Moving By Itself

**Cause:** DOSBox timed setting

**Fix:** Edit `dosbox.cfg`:
```ini
[joystick]
timed=true
```

Or add deadzone in DOSBox Pure core options.

### Buttons Don't Work in Game

**Causes:**
1. Game needs joystick enabled in its setup
2. Button wrapping issue
3. Game uses keyboard only

**Fix:**
```ini
[joystick]
buttonwrap=false
```

Or run the game's SETUP.EXE and configure joystick/gamepad.

### Sound Doesn't Work

**Cause:** Sound card not configured

**Fix:** Run SETUP.EXE and select:
- **Sound Blaster** or **Sound Blaster 16**
- IRQ: 5 or 7
- DMA: 1
- Port: 220 (hex)

### Game Runs Too Fast/Slow

**Fix:** Edit `dosbox.cfg`:
```ini
[cpu]
cycles=10000    # Try different values: 5000, 10000, 15000
```

Or use `max` or `auto`:
```ini
cycles=auto
```

## Game-Specific Solutions

### Duke Nukem 3D
- Run setup first (see above)
- May need `/v8` parameter
- Configure sound as Sound Blaster 16

### Lemmings
- Usually works out of the box
- Use `lemmings.bat` launcher (auto-detected)

### Doom/Doom II
- Set music to Sound Blaster
- Configure mouse if needed
- May need `-nomusic` parameter if music causes issues

### Build Engine Games (Blood, Shadow Warrior, etc.)
- Usually need setup first
- Configure video mode (VESA 2.0)
- Set up sound card

## Creating Your Own Fixes

### Custom dosbox.bat

You can customize the launch:

```bat
c:
cd GAMEDIR
game.exe /parameter
```

Or with multiple commands:
```bat
c:
mount d .\cd\game.iso -t cdrom
c:
cd GAME
game.exe
```

### Custom dosbox.cfg

Place in your game's `.pc` folder:
```ini
[autoexec]
# Custom commands run on startup
@echo off
cls
echo Starting Game...
```

## Getting Help

1. Check `CONTROLLER_SETUP.txt` in game folder
2. Review [Batocera DOS Wiki](https://wiki.batocera.org/systems:dos)
3. Try DOSBox Pure core (better defaults)
4. Check game-specific guides online

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Wrong game launches | Add `c:` to dosbox.bat |
| Setup needed | Use dosbox_setup.bat |
| Controller weird | Press HOTKEY+L1 for mapper |
| Joystick drifts | Set `timed=true` in dosbox.cfg |
| No sound | Run SETUP.EXE, choose Sound Blaster |
| Too fast/slow | Adjust `cycles` in dosbox.cfg |
| Buttons wrong | Use DOSBox mapper (CTRL+F1) |

## Automated Fixes

retroMaid can generate these files automatically:

```bash
# Generate configs for all games
python3 << 'EOF'
from pathlib import Path
from core.dosbox_config import DOSBoxConfigGenerator

dos_path = Path("roms/dos")
gen = DOSBoxConfigGenerator()

for pc_folder in dos_path.glob("*.pc"):
    # Create config with joystick enabled
    gen.create_basic_config(pc_folder, enable_joystick=True)

    # Add setup option if setup.exe exists
    gen.add_setup_option(pc_folder)

    # Create controller readme
    gen.create_controller_readme(pc_folder)

print("✓ Created configs for all games")
EOF
```

This creates:
- `dosbox.cfg` - DOSBox configuration
- `dosbox_setup.bat` - Setup launcher (if setup.exe exists)
- `CONTROLLER_SETUP.txt` - Controller help guide
