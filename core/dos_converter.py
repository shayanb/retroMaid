"""
DOS ROM converter for Batocera format

Converts DOS game folders to Batocera-compatible format:
- Renames folders to add .pc extension
- Creates dosbox.bat with launch command
- Creates dosbox.cfg with optimal settings
- Handles ZIP extraction if needed
"""
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from utils.logger import get_logger
from core.dosbox_config import DOSBoxConfigGenerator

logger = get_logger()


@dataclass
class DOSGame:
    """Represents a DOS game and its files"""
    name: str
    path: Path
    executables: List[Path]
    config_files: List[Path]
    is_converted: bool = False
    launch_command: Optional[str] = None


class DOSConverter:
    """Converts DOS games to Batocera format"""

    # Valid DOS executable extensions
    EXECUTABLE_EXTENSIONS = ['.exe', '.com', '.bat']

    # Files to look for that might indicate launch command
    COMMON_LAUNCHERS = [
        'start.bat', 'run.bat', 'game.bat', 'launch.bat',
        'start.exe', 'run.exe', 'game.exe', 'play.exe'
    ]

    # Executables to exclude from main game selection (usually setup/install tools)
    EXCLUDED_EXECUTABLES = [
        'install.exe', 'install.bat', 'setup.exe', 'setup.bat',
        'config.exe', 'uninstall.exe', 'readme.exe',
        'deinstal.exe', 'uninst.exe', 'setsound.exe',
        'dosbox.bat', 'dosbox_setup.bat', 'dosbox_game.bat'  # Exclude our generated files
    ]

    def __init__(self, dos_path: Path):
        """
        Initialize DOS converter

        Args:
            dos_path: Path to DOS ROMs directory
        """
        self.dos_path = Path(dos_path)
        self.config_generator = DOSBoxConfigGenerator()

    def scan_dos_games(self) -> List[DOSGame]:
        """
        Scan DOS directory for games needing conversion

        Returns:
            List of DOS games
        """
        games = []

        if not self.dos_path.exists():
            logger.warning(f"DOS path does not exist: {self.dos_path}")
            return games

        for item in self.dos_path.iterdir():
            # Skip special files
            if item.name.startswith('_') or item.name.startswith('.'):
                continue

            # Check if it's a directory without .pc/.dos extension
            if item.is_dir() and not (item.suffix in ['.pc', '.dos']):
                game = self._analyze_game_folder(item)
                if game:
                    games.append(game)

            # Check for ZIP files
            elif item.suffix == '.zip':
                # Check if corresponding .pc folder exists
                pc_name = item.stem + '.pc'
                if not (self.dos_path / pc_name).exists():
                    game = DOSGame(
                        name=item.stem,
                        path=item,
                        executables=[],
                        config_files=[],
                        is_converted=False
                    )
                    games.append(game)

        return games

    def _analyze_game_folder(self, folder: Path) -> Optional[DOSGame]:
        """
        Analyze a game folder to find executables and configs

        Args:
            folder: Path to game folder

        Returns:
            DOSGame object or None
        """
        executables = []
        config_files = []

        # Find all executables recursively
        for ext in self.EXECUTABLE_EXTENSIONS:
            # Search recursively but limit depth to avoid going too deep
            found_exes = list(folder.rglob(f'*{ext}'))

            # Filter out excluded executables and limit depth
            for exe in found_exes:
                # Calculate relative depth
                try:
                    relative = exe.relative_to(folder)
                    depth = len(relative.parts) - 1  # -1 because file itself doesn't count

                    # Skip if too deep (more than 2 levels)
                    if depth > 2:
                        continue

                    # Skip excluded executables
                    if exe.name.lower() in self.EXCLUDED_EXECUTABLES:
                        continue

                    executables.append(exe)
                except ValueError:
                    continue

        # Find config files
        config_files.extend(folder.glob('*.cfg'))
        config_files.extend(folder.glob('*.conf'))

        # Check if already converted (has dosbox.bat)
        is_converted = (folder / 'dosbox.bat').exists()

        # Try to detect launch command
        launch_command = self._detect_launch_command(folder, executables)

        game = DOSGame(
            name=folder.name,
            path=folder,
            executables=executables,
            config_files=config_files,
            is_converted=is_converted,
            launch_command=launch_command
        )

        return game

    def _detect_launch_command(self, folder: Path, executables: List[Path]) -> Optional[str]:
        """
        Try to detect the correct launch command

        Priority:
        1. .bat file with same name as folder
        2. .exe file with same name as folder
        3. Common launcher names (start.bat, run.bat, etc.)
        4. Single executable
        5. Largest executable (prefer root level, then shortest path)

        Args:
            folder: Game folder
            executables: List of executable files

        Returns:
            Launch command with path (e.g., "GAME\\DUKE3D.EXE") or None
        """
        if not executables:
            return None

        # Get folder base name (without .pc/.dos extension)
        folder_base = folder.stem.lower()
        # Remove common suffixes
        for suffix in ['.pc', '.dos', ' (1996)', ' (1995)', ' (1994)', ' (1993)']:
            if folder_base.endswith(suffix.lower()):
                folder_base = folder_base[:len(folder_base) - len(suffix)]

        # Helper to get relative path from game folder
        def get_relative_path(exe: Path) -> str:
            try:
                rel = exe.relative_to(folder)
                # Convert to DOS path format (backslashes, uppercase)
                return str(rel).replace('/', '\\').upper()
            except ValueError:
                return exe.name.upper()

        # Helper to check if exe is in root directory
        def is_in_root(exe: Path) -> bool:
            try:
                rel = exe.relative_to(folder)
                return len(rel.parts) == 1
            except ValueError:
                return False

        # Priority 1 & 2: Look for file with same name as folder
        matching_exes = []
        for exe in executables:
            exe_base = exe.stem.lower()
            # Clean up common patterns
            exe_clean = exe_base.replace('_', ' ').replace('-', ' ')
            folder_clean = folder_base.replace('_', ' ').replace('-', ' ')

            # Exact match or close match
            if exe_base == folder_base or folder_clean in exe_clean or exe_clean in folder_clean:
                matching_exes.append(exe)

        if matching_exes:
            # Prefer .bat over .exe, prefer root level over subdirectories
            bat_files = [e for e in matching_exes if e.suffix.lower() == '.bat']
            if bat_files:
                # Prefer root level
                root_bats = [e for e in bat_files if is_in_root(e)]
                chosen = root_bats[0] if root_bats else bat_files[0]
                return get_relative_path(chosen)

            # Use .exe match
            root_exes = [e for e in matching_exes if is_in_root(e)]
            chosen = root_exes[0] if root_exes else matching_exes[0]
            return get_relative_path(chosen)

        # Priority 3: Check for common launcher names (prefer root level)
        for launcher_name in self.COMMON_LAUNCHERS:
            for exe in executables:
                if exe.name.lower() == launcher_name:
                    # Prefer root level launchers
                    if is_in_root(exe):
                        return get_relative_path(exe)

        # If any common launcher exists (even in subdirectory), use it
        for launcher_name in self.COMMON_LAUNCHERS:
            for exe in executables:
                if exe.name.lower() == launcher_name:
                    return get_relative_path(exe)

        # Priority 4: If only one executable, use it
        if len(executables) == 1:
            return get_relative_path(executables[0])

        # Priority 5: Use the largest executable as fallback
        # Prefer root level, then .bat over .exe, then largest size
        root_exes = [e for e in executables if is_in_root(e)]
        candidates = root_exes if root_exes else executables

        bat_files = [e for e in candidates if e.suffix.lower() == '.bat']
        if bat_files:
            largest = max(bat_files, key=lambda e: e.stat().st_size)
            return get_relative_path(largest)

        largest = max(candidates, key=lambda e: e.stat().st_size)
        return get_relative_path(largest)

    def convert_game(
        self,
        game: DOSGame,
        launch_command: Optional[str] = None,
        delete_original: bool = False
    ) -> bool:
        """
        Convert a DOS game to Batocera format

        Args:
            game: DOSGame to convert
            launch_command: Override launch command (None = auto-detect)
            delete_original: Delete original ZIP after extraction

        Returns:
            True if successful
        """
        try:
            # Handle ZIP files
            if game.path.suffix == '.zip':
                return self._convert_from_zip(game, launch_command, delete_original)

            # Handle directories
            return self._convert_directory(game, launch_command)

        except Exception as e:
            logger.error(f"Failed to convert {game.name}: {e}")
            return False

    def _convert_from_zip(
        self,
        game: DOSGame,
        launch_command: Optional[str],
        delete_original: bool
    ) -> bool:
        """
        Convert a ZIP file to Batocera .pc format

        Args:
            game: DOSGame with ZIP path
            launch_command: Launch command
            delete_original: Delete ZIP after extraction

        Returns:
            True if successful
        """
        # Create target directory with .pc extension
        target_dir = self.dos_path / f"{game.name}.pc"

        if target_dir.exists():
            logger.warning(f"Target directory already exists: {target_dir}")
            return False

        logger.info(f"Extracting {game.path.name} to {target_dir.name}")

        # Extract ZIP
        with zipfile.ZipFile(game.path, 'r') as zf:
            zf.extractall(target_dir)

        # Analyze extracted folder - search recursively for executables
        game.path = target_dir
        game.executables = []
        for ext in self.EXECUTABLE_EXTENSIONS:
            # Search recursively but limit depth
            found_exes = list(target_dir.rglob(f'*{ext}'))

            for exe in found_exes:
                # Calculate relative depth
                try:
                    relative = exe.relative_to(target_dir)
                    depth = len(relative.parts) - 1

                    # Skip if too deep (more than 2 levels)
                    if depth > 2:
                        continue

                    # Skip excluded executables
                    if exe.name.lower() in self.EXCLUDED_EXECUTABLES:
                        continue

                    game.executables.append(exe)
                except ValueError:
                    continue

        # Detect or use provided launch command
        if not launch_command:
            launch_command = self._detect_launch_command(target_dir, game.executables)

        if not launch_command:
            logger.error(f"Could not detect launch command for {game.name}")
            return False

        # Create dosbox.bat
        self._create_dosbox_bat(target_dir, launch_command)

        # Create additional config files (dosbox.cfg, controller setup, etc.)
        self._create_config_files(target_dir)

        # Delete original ZIP if requested
        if delete_original:
            # Note: game.path was already updated to target_dir above
            # We need to delete the original ZIP
            original_zip = self.dos_path / f"{game.name}.zip"
            if original_zip.exists():
                original_zip.unlink()
                logger.info(f"Deleted original ZIP: {original_zip.name}")

        logger.info(f"✓ Converted {game.name}")
        return True

    def _convert_directory(
        self,
        game: DOSGame,
        launch_command: Optional[str]
    ) -> bool:
        """
        Convert an existing directory to Batocera format

        Args:
            game: DOSGame with directory path
            launch_command: Launch command

        Returns:
            True if successful
        """
        # Create target directory with .pc extension
        target_dir = self.dos_path / f"{game.name}.pc"

        if target_dir.exists():
            logger.warning(f"Target directory already exists: {target_dir}")
            return False

        logger.info(f"Converting {game.name} to Batocera format")

        # Rename directory to add .pc extension
        game.path.rename(target_dir)

        # Use provided or detected launch command
        if not launch_command:
            launch_command = game.launch_command or self._detect_launch_command(
                target_dir, game.executables
            )

        if not launch_command:
            logger.error(f"Could not detect launch command for {game.name}")
            # Revert rename
            target_dir.rename(game.path)
            return False

        # Create dosbox.bat
        self._create_dosbox_bat(target_dir, launch_command)

        # Create additional config files (dosbox.cfg, controller setup, etc.)
        self._create_config_files(target_dir)

        logger.info(f"✓ Converted {game.name}")
        return True

    def _create_dosbox_bat(self, game_dir: Path, launch_command: str) -> None:
        """
        Create dosbox.bat file with proper Batocera format

        Format for root level:
            c:
            COMMAND.EXE

        Format for subdirectory:
            c:
            cd SUBDIR
            COMMAND.EXE

        Args:
            game_dir: Game directory
            launch_command: Command to launch (with path if in subdirectory)
        """
        dosbox_bat = game_dir / 'dosbox.bat'

        # Check if launch command contains a path (has backslash)
        if '\\' in launch_command:
            # Split path into directory and executable
            parts = launch_command.split('\\')
            directory = '\\'.join(parts[:-1])
            executable = parts[-1]

            # Create bat file with cd command
            content = f"c:\ncd {directory}\n{executable}\n"
        else:
            # Simple format for root level executables
            content = f"c:\n{launch_command}\n"

        with open(dosbox_bat, 'w', newline='\r\n') as f:  # DOS line endings
            f.write(content)

        logger.debug(f"Created dosbox.bat with commands: {content.strip()}")

    def _create_config_files(self, game_dir: Path) -> None:
        """
        Create DOSBox configuration files for the game

        Creates:
        - dosbox.cfg: DOSBox configuration with joystick enabled
        - dosbox_setup.bat: Setup launcher (if setup.exe exists)
        - CONTROLLER_SETUP.txt: Controller mapping guide

        Args:
            game_dir: Game directory (.pc folder)
        """
        try:
            # Create basic dosbox.cfg with joystick enabled
            self.config_generator.create_basic_config(
                game_dir,
                enable_joystick=True,
                cpu_cycles="auto",
                enable_mapper=True
            )
            logger.debug("Created dosbox.cfg")

            # Check if setup.exe exists and create setup launcher
            if self.config_generator.add_setup_option(game_dir):
                logger.debug("Created dosbox_setup.bat for game setup")

            # Create controller readme
            self.config_generator.create_controller_readme(game_dir)
            logger.debug("Created CONTROLLER_SETUP.txt")

        except Exception as e:
            logger.warning(f"Failed to create config files: {e}")

    def batch_convert(
        self,
        games: List[DOSGame],
        interactive: bool = True,
        delete_zips: Optional[bool] = None,
        ask_for_defaults: bool = True
    ) -> Tuple[int, int]:
        """
        Convert multiple games

        Args:
            games: List of games to convert
            interactive: Ask for confirmation/launch command for each game
            delete_zips: Delete original ZIPs after extraction (None = ask)
            ask_for_defaults: Ask for default behaviors before batch processing

        Returns:
            Tuple of (successful, failed) counts
        """
        from rich.console import Console
        from rich.prompt import Prompt, Confirm

        console = Console()
        successful = 0
        failed = 0

        # Ask for batch defaults if not specified
        if ask_for_defaults and not interactive:
            console.print("\n[bold cyan]Batch Conversion Settings:[/bold cyan]")

            if delete_zips is None:
                delete_zips = Confirm.ask(
                    "Delete original ZIP files after successful extraction?",
                    default=False
                )

            console.print(f"\nSettings:")
            console.print(f"  Delete ZIPs: [yellow]{'Yes' if delete_zips else 'No'}[/yellow]")

            if not Confirm.ask("\nProceed with these settings?", default=True):
                return 0, 0

        for game in games:
            if game.is_converted:
                console.print(f"[yellow]Already converted:[/yellow] {game.name}")
                continue

            console.print(f"\n[cyan]Converting:[/cyan] {game.name}")

            # Determine launch command
            launch_cmd = game.launch_command

            if interactive:
                if game.executables:
                    console.print(f"[yellow]Found {len(game.executables)} executable(s):[/yellow]")

                    # Helper to get relative path for display
                    def get_display_path(exe: Path) -> str:
                        try:
                            rel = exe.relative_to(game.path)
                            return str(rel).replace('/', '\\')
                        except ValueError:
                            return exe.name

                    # Show all executables with their paths
                    for i, exe in enumerate(game.executables, 1):
                        display_path = get_display_path(exe)
                        # Check if this matches the suggested command
                        is_suggested = (launch_cmd and display_path.upper() == launch_cmd.upper())
                        indicator = "[green]→[/green]" if is_suggested else " "
                        console.print(f"  {indicator} [{i}] {display_path}")

                    if launch_cmd:
                        console.print(f"\n[bold green]Suggested:[/bold green] {launch_cmd}")
                    else:
                        console.print(f"\n[yellow]No auto-detection, please select manually[/yellow]")

                    choice = Prompt.ask(
                        "Select executable (number, path, or 's' to skip)",
                        default=launch_cmd or "1"
                    )

                    # Handle skip
                    if choice.lower() == 's':
                        console.print("[yellow]Skipped[/yellow]")
                        continue

                    # Handle numeric choice
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(game.executables):
                            exe = game.executables[idx]
                            # Convert to DOS path format
                            rel = exe.relative_to(game.path)
                            launch_cmd = str(rel).replace('/', '\\').upper()
                        else:
                            console.print(f"[red]Invalid choice: {choice}[/red]")
                            failed += 1
                            continue
                    except ValueError:
                        # User entered a custom path
                        launch_cmd = choice

                elif game.path.suffix == '.zip':
                    console.print("[yellow]Will extract ZIP and auto-detect[/yellow]")
                    launch_cmd = None
                else:
                    console.print("[red]No executables found![/red]")
                    if not Confirm.ask("Continue anyway?", default=False):
                        failed += 1
                        continue
                    launch_cmd = Prompt.ask("Enter launch command manually")

            # Convert
            if self.convert_game(game, launch_cmd, delete_zips):
                successful += 1
            else:
                failed += 1

        return successful, failed
