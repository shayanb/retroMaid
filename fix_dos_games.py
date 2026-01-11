#!/usr/bin/env python3
"""
Fix existing DOS game conversions

This script fixes previously converted DOS games by:
1. Re-analyzing for executables (now searches subdirectories)
2. Regenerating dosbox.bat with proper paths
3. Creating dosbox.cfg and other config files
4. Allowing interactive selection of the correct executable
"""
from pathlib import Path
from core.dos_converter import DOSConverter
from rich.console import Console
from rich.prompt import Prompt, Confirm

def main():
    """Fix existing DOS game conversions"""
    console = Console()

    # Use the roms/dos directory
    dos_path = Path("roms/dos")

    if not dos_path.exists():
        console.print(f"[red]Error:[/red] {dos_path} not found")
        return

    converter = DOSConverter(dos_path)

    # Find all .pc folders
    pc_folders = list(dos_path.glob("*.pc"))

    if not pc_folders:
        console.print("[yellow]No .pc folders found[/yellow]")
        return

    console.print(f"\n[cyan]Found {len(pc_folders)} converted DOS game(s)[/cyan]\n")

    # Ask if user wants to fix all or select specific games
    fix_all = Confirm.ask("Fix all games automatically?", default=False)

    fixed = 0
    skipped = 0

    for pc_folder in pc_folders:
        game_name = pc_folder.stem  # Remove .pc extension

        console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        console.print(f"[bold]Game:[/bold] {game_name}")
        console.print(f"[bold cyan]{'='*60}[/bold cyan]")

        # Analyze the folder
        game = converter._analyze_game_folder(pc_folder)

        if not game:
            console.print("[red]Failed to analyze game folder[/red]")
            skipped += 1
            continue

        console.print(f"Found [yellow]{len(game.executables)}[/yellow] executable(s)")

        if not game.executables:
            console.print("[yellow]No executables found, skipping[/yellow]")
            skipped += 1
            continue

        # Show all executables with paths
        def get_display_path(exe: Path) -> str:
            try:
                rel = exe.relative_to(pc_folder)
                return str(rel).replace('/', '\\')
            except ValueError:
                return exe.name

        for i, exe in enumerate(game.executables, 1):
            display_path = get_display_path(exe)
            is_suggested = (game.launch_command and
                          display_path.upper() == game.launch_command.upper())
            indicator = "[green]→[/green]" if is_suggested else " "
            console.print(f"  {indicator} [{i}] {display_path}")

        if game.launch_command:
            console.print(f"\n[bold green]Auto-detected:[/bold green] {game.launch_command}")

        # Decide on launch command
        launch_cmd = game.launch_command

        if not fix_all:
            choice = Prompt.ask(
                "\nSelect executable (number, path, Enter to use suggested, 's' to skip)",
                default=""
            )

            if choice.lower() == 's':
                console.print("[yellow]Skipped[/yellow]")
                skipped += 1
                continue

            if choice and choice != "":
                try:
                    # Handle numeric choice
                    idx = int(choice) - 1
                    if 0 <= idx < len(game.executables):
                        exe = game.executables[idx]
                        rel = exe.relative_to(pc_folder)
                        launch_cmd = str(rel).replace('/', '\\').upper()
                    else:
                        console.print(f"[red]Invalid choice[/red]")
                        skipped += 1
                        continue
                except ValueError:
                    # User entered a custom path
                    launch_cmd = choice

        if not launch_cmd:
            console.print("[red]No launch command specified[/red]")
            skipped += 1
            continue

        # Create new dosbox.bat
        try:
            converter._create_dosbox_bat(pc_folder, launch_cmd)
            console.print(f"[green]✓[/green] Created dosbox.bat: {launch_cmd}")

            # Create config files
            converter._create_config_files(pc_folder)
            console.print(f"[green]✓[/green] Created config files")

            fixed += 1

        except Exception as e:
            console.print(f"[red]Failed to fix game:[/red] {e}")
            skipped += 1

    # Summary
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  Fixed: [green]{fixed}[/green]")
    console.print(f"  Skipped: [yellow]{skipped}[/yellow]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")

    if fixed > 0:
        console.print("[bold green]Games fixed successfully![/bold green]")
        console.print("\nThe games should now:")
        console.print("  • Launch the correct executable")
        console.print("  • Have joystick support enabled")
        console.print("  • Include controller mapping guides")
        console.print("\nIf a game needs setup (like Duke Nukem 3D):")
        console.print("  1. Look for dosbox_setup.bat in the game folder")
        console.print("  2. See CONTROLLER_SETUP.txt for details")

if __name__ == '__main__':
    main()
