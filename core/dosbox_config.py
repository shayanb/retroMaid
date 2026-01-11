"""
DOSBox configuration generator for Batocera
"""
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class DOSBoxConfigGenerator:
    """Generates dosbox.cfg files with Batocera-optimized settings"""

    @staticmethod
    def create_basic_config(
        game_dir: Path,
        enable_joystick: bool = True,
        cpu_cycles: str = "auto",
        enable_mapper: bool = True
    ) -> Path:
        """
        Create a basic dosbox.cfg file

        Args:
            game_dir: Game directory (.pc folder)
            enable_joystick: Enable joystick support
            cpu_cycles: CPU cycles (auto, max, or number)
            enable_mapper: Enable mapper file support

        Returns:
            Path to created config file
        """
        config_path = game_dir / "dosbox.cfg"

        config_content = f"""[cpu]
core=auto
cputype=auto
cycles={cpu_cycles}

[joystick]
joysticktype={'auto' if enable_joystick else 'none'}
timed=true
autofire=false
swap34=false
buttonwrap=false

[sdl]
{'mapperfile=mapper.map' if enable_mapper else ''}
output=opengl
autolock=false

[render]
aspect=true
scaler=normal2x

[dosbox]
memsize=16
"""

        with open(config_path, 'w', newline='\n') as f:
            f.write(config_content.strip() + '\n')

        logger.info(f"Created dosbox.cfg for {game_dir.name}")
        return config_path

    @staticmethod
    def add_setup_option(game_dir: Path, setup_exe: str = "setup.exe") -> bool:
        """
        Modify dosbox.bat to offer setup option

        Creates a dosbox_setup.bat for running game setup

        Args:
            game_dir: Game directory
            setup_exe: Name of setup executable

        Returns:
            True if setup file found and created
        """
        setup_path = game_dir / setup_exe

        if not setup_path.exists():
            logger.warning(f"Setup file not found: {setup_exe}")
            return False

        # Create setup batch file
        setup_bat = game_dir / "dosbox_setup.bat"

        content = f"""c:
{setup_exe}
"""

        with open(setup_bat, 'w', newline='\r\n') as f:
            f.write(content)

        logger.info(f"Created dosbox_setup.bat for {game_dir.name}")
        logger.info(f"  To run setup: rename dosbox_setup.bat to dosbox.bat")
        logger.info(f"  After setup: rename back to use the game")

        return True

    @staticmethod
    def create_controller_readme(game_dir: Path) -> None:
        """
        Create a README for controller configuration

        Args:
            game_dir: Game directory
        """
        readme_path = game_dir / "CONTROLLER_SETUP.txt"

        content = """CONTROLLER SETUP FOR BATOCERA
================================

Default Batocera Controller Layout (Gravis PC Gamepad style):
- Button 1 (A/Green): East button
- Button 2 (B/Yellow): South button
- Button 3 (X/Blue): North button
- Button 4 (Y/Red): West button

CUSTOM BUTTON MAPPING:
1. Start the game in Batocera
2. Press CTRL+F1 to open the mapper
3. Click on a DOSBox action
4. Press the controller button you want to assign
5. Exit mapper (ESC)
6. Your settings are saved to mapper.map

JOYSTICK CALIBRATION:
Some games need joystick calibration:
1. Run the game's SETUP.EXE (see dosbox_setup.bat)
2. Configure joystick/gamepad
3. Save and exit setup
4. Run the game normally

COMMON FIXES:
- Joystick moving by itself: Edit dosbox.cfg, set timed=true
- Buttons not working: Edit dosbox.cfg, set buttonwrap=false
- Need deadzone: Use DOSBox Pure core (has deadzone settings)

FILES:
- dosbox.bat: Main game launcher
- dosbox_setup.bat: Run game setup (if available)
- dosbox.cfg: DOSBox configuration
- mapper.map: Controller button mapping (created when you use mapper)
"""

        with open(readme_path, 'w') as f:
            f.write(content)

        logger.info(f"Created CONTROLLER_SETUP.txt for {game_dir.name}")
