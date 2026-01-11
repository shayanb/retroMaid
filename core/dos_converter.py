"""
DOS ROM converter for Batocera format

Converts DOS game folders to Batocera-compatible format:
- Renames folders to add .pc extension
- Creates dosbox.bat with launch command
- Handles ZIP extraction if needed
"""
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from utils.logger import get_logger

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

    def __init__(self, dos_path: Path):
        """
        Initialize DOS converter

        Args:
            dos_path: Path to DOS ROMs directory
        """
        self.dos_path = Path(dos_path)

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

        # Find all executables
        for ext in self.EXECUTABLE_EXTENSIONS:
            executables.extend(folder.glob(f'*{ext}'))

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
        5. Largest executable

        Args:
            folder: Game folder
            executables: List of executable files

        Returns:
            Launch command or None
        """
        if not executables:
            return None

        # Get folder base name (without .pc/.dos extension)
        folder_base = folder.stem.lower()
        if folder_base.endswith('.pc') or folder_base.endswith('.dos'):
            folder_base = folder_base[:-3]

        # Priority 1 & 2: Look for file with same name as folder
        for exe in executables:
            exe_base = exe.stem.lower()

            # Exact match or close match
            if exe_base == folder_base or folder_base in exe_base or exe_base in folder_base:
                # Prefer .bat over .exe if both exist
                if exe.suffix.lower() == '.bat':
                    return exe.name

        # Check again for .exe with matching name (if no .bat found)
        for exe in executables:
            exe_base = exe.stem.lower()
            if exe.suffix.lower() == '.exe' and (exe_base == folder_base or folder_base in exe_base):
                return exe.name

        # Priority 3: Check for common launcher names
        for launcher_name in self.COMMON_LAUNCHERS:
            launcher = folder / launcher_name
            if launcher.exists():
                return launcher.name

        # Priority 4: If only one executable, use it
        if len(executables) == 1:
            return executables[0].name

        # Priority 5: Use the largest executable as fallback
        # But prefer .bat over .exe
        bat_files = [e for e in executables if e.suffix.lower() == '.bat']
        if bat_files:
            largest = max(bat_files, key=lambda e: e.stat().st_size)
            return largest.name

        largest = max(executables, key=lambda e: e.stat().st_size)
        return largest.name

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

        # Analyze extracted folder
        game.path = target_dir
        game.executables = []
        for ext in self.EXECUTABLE_EXTENSIONS:
            game.executables.extend(target_dir.glob(f'*{ext}'))

        # Detect or use provided launch command
        if not launch_command:
            launch_command = self._detect_launch_command(target_dir, game.executables)

        if not launch_command:
            logger.error(f"Could not detect launch command for {game.name}")
            return False

        # Create dosbox.bat
        self._create_dosbox_bat(target_dir, launch_command)

        # Delete original ZIP if requested
        if delete_original:
            game.path.unlink()  # This is still the ZIP path
            logger.info(f"Deleted original ZIP: {game.path.name}")

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

        logger.info(f"✓ Converted {game.name}")
        return True

    def _create_dosbox_bat(self, game_dir: Path, launch_command: str) -> None:
        """
        Create dosbox.bat file with proper Batocera format

        Format:
            c:
            COMMAND.EXE

        Args:
            game_dir: Game directory
            launch_command: Command to launch the game
        """
        dosbox_bat = game_dir / 'dosbox.bat'

        # Proper Batocera dosbox.bat format with C: drive
        # Batocera automatically mounts the .pc folder as C:
        content = f"c:\n{launch_command}\n"

        with open(dosbox_bat, 'w', newline='\r\n') as f:  # DOS line endings
            f.write(content)

        logger.debug(f"Created dosbox.bat with: c:\\n{launch_command}")

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
                    console.print("Found executables:")
                    for i, exe in enumerate(game.executables, 1):
                        indicator = "→" if exe.name == launch_cmd else " "
                        console.print(f"  {indicator} [{i}] {exe.name}")

                    if launch_cmd:
                        console.print(f"\nSuggested: [green]{launch_cmd}[/green]")

                    choice = Prompt.ask(
                        "Launch command (number or custom)",
                        default=launch_cmd or "1"
                    )

                    # Handle numeric choice
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(game.executables):
                            launch_cmd = game.executables[idx].name
                    except ValueError:
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
