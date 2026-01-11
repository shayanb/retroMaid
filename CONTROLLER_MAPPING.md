# Controller Mapping for DOS Games in Batocera

## Your Controller Layout

You have a standard layout with:
- **4 Face Buttons**: A (East), B (South), X (North), Y (West)
- **Shoulder Buttons**: L, L2, R, R2

## Default Batocera/DOSBox Mapping

Batocera uses the **Gravis PC Gamepad** layout from the 90s:

| Your Controller | → | DOS Button | Color |
|----------------|---|-----------|-------|
| **A (East)** | → | Button 1 | Green |
| **B (South)** | → | Button 2 | Yellow |
| **X (North)** | → | Button 3 | Blue |
| **Y (West)** | → | Button 4 | Red |
| **L/L2** | → | Additional |  |
| **R/R2** | → | Additional |  |

This might feel "backwards" because:
- Modern games: A = confirm, B = cancel
- DOS games: Button 1 (your A) = fire, Button 2 (your B) = jump

## Why It Feels Off

DOS games were designed for keyboards or the Gravis PC Gamepad. The button order was different from modern controllers, so what feels natural now (A=action, B=back) doesn't match DOS games.

## Solutions

### Option 1: Use DOSBox Mapper (Recommended)

**Remap buttons per-game in Batocera:**

1. Launch the game
2. Press **HOTKEY + L1** (or **Ctrl+F1** on keyboard)
3. The DOSBox mapper opens
4. Click a DOS action (like "Joy 1 Button 1")
5. Press the controller button you want (e.g., press B for fire)
6. Repeat for all buttons
7. Press ESC to save and exit

Your mapping is saved to `mapper.map` in the game's folder.

**Example Mapping:**
- DOS Button 1 (Fire) → Your B button
- DOS Button 2 (Jump) → Your A button
- DOS Button 3 (Action) → Your X button
- DOS Button 4 (Special) → Your Y button

### Option 2: Edit dosbox.cfg

For all games, edit `dosbox.cfg`:

```ini
[joystick]
joysticktype=auto
timed=true          # Fixes drift
buttonwrap=false    # Prevents button issues
swap34=false        # Try true to swap buttons 3&4
```

### Option 3: Use DOSBox Pure Core

DOSBox Pure has better gamepad defaults:

1. In EmulationStation, highlight the game
2. Press SELECT
3. Go to "Advanced System Options"
4. Change "Emulator" to **dosbox-pure**
5. Launch game

DOSBox Pure has:
- Better button defaults
- Deadzone settings
- Automatic gamepad detection

## Game-Specific Setup

Some games need controller setup in their own menus:

1. Run `dosbox_setup.bat` (see [DOS_TROUBLESHOOTING.md](DOS_TROUBLESHOOTING.md))
2. Configure joystick in game setup
3. Enable/calibrate gamepad
4. Save and exit
5. Run game normally

## Common Issues & Fixes

### Joystick Moving By Itself

**Fix:** Edit `dosbox.cfg`:
```ini
[joystick]
timed=true
```

Or switch to DOSBox Pure (has deadzone settings).

### Buttons Don't Work

**Causes:**
1. Game doesn't support gamepad
2. Needs joystick enabled in game setup
3. Button wrapping issue

**Fix:**
```ini
[joystick]
buttonwrap=false
```

Or run game SETUP and enable joystick.

### Wrong Buttons Trigger Actions

Use the DOSBox mapper (HOTKEY+L1) to remap per-game.

## Controller Types in Batocera

Batocera supports:
- **4-axis, 2-button joystick** (default, Gravis-style)
- **4-axis, 4-button gamepad** (better for modern controllers)

To change in `dosbox.cfg`:
```ini
[joystick]
joysticktype=4axis    # Default 2-button
# OR
joysticktype=fcs      # 4-button gamepad
```

## Per-Game Customization

Each game can have its own:

1. **dosbox.cfg** - DOSBox settings
2. **mapper.map** - Button mapping (created when you use mapper)

Files go in the game's `.pc` folder.

## Example: Perfect Duke Nukem 3D Setup

1. Run `dosbox_setup.bat` first (configure video/sound)
2. Launch game normally
3. Press HOTKEY+L1 for mapper
4. Map buttons:
   - Fire → B
   - Jump → A
   - Use → X
   - Inventory → Y
   - Previous Weapon → L
   - Next Weapon → R
5. Save and play!

## Quick Reference

| Issue | Solution |
|-------|----------|
| Buttons feel wrong | Use DOSBox mapper (HOTKEY+L1) |
| Joystick drifts | Set `timed=true` in dosbox.cfg |
| No gamepad detected | Enable in game setup |
| Buttons don't work | Set `buttonwrap=false` |
| Need modern layout | Use DOSBox Pure core |

## Getting Help

- Check `CONTROLLER_SETUP.txt` in each game folder
- See [DOS_TROUBLESHOOTING.md](DOS_TROUBLESHOOTING.md) for more solutions
- Try DOSBox Pure core for better defaults

## Summary

The controller mapping feels "off" because DOS games use a different button order than modern games. Use the DOSBox mapper (HOTKEY+L1) to customize buttons per-game, or switch to DOSBox Pure for better defaults.

Your mapped settings are saved and will work every time you launch that game!
