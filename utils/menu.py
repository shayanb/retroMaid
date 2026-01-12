"""
Interactive menu system for retroMaid
"""
from typing import Optional, Callable, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

console = Console()


ASCII_ART = """
[cyan]
 ██████╗ ███████╗████████╗██████╗  ██████╗ ███╗   ███╗ █████╗ ██╗██████╗
 ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗████╗ ████║██╔══██╗██║██╔══██╗
 ██████╔╝█████╗     ██║   ██████╔╝██║   ██║██╔████╔██║███████║██║██║  ██║
 ██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║██║╚██╔╝██║██╔══██║██║██║  ██║
 ██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║  ██║██║██████╔╝
 ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚═════╝
[/cyan]
[dim]           Batocera ROM Metadata Scraper & Manager[/dim]
"""


class MenuItem:
    """Represents a menu item"""

    def __init__(
        self,
        key: str,
        label: str,
        description: str,
        action: Optional[Callable] = None,
        submenu: Optional['Menu'] = None
    ):
        self.key = key
        self.label = label
        self.description = description
        self.action = action
        self.submenu = submenu


class Menu:
    """Interactive menu system"""

    def __init__(self, title: str, items: List[MenuItem]):
        self.title = title
        self.items = items

    def display(self) -> None:
        """Display the menu"""
        console.clear()

        # Show ASCII art for main menu only
        if self.title == "Main Menu":
            console.print(ASCII_ART)

        # Create menu table
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Action", style="bold")
        table.add_column("Description", style="dim")

        for item in self.items:
            table.add_row(f"[{item.key}]", item.label, item.description)

        panel = Panel(
            table,
            title=f"[bold cyan]{self.title}[/bold cyan]",
            border_style="cyan"
        )

        console.print(panel)

    def run(self, is_main_menu: bool = False) -> bool:
        """
        Run the menu loop

        Args:
            is_main_menu: If True, loops until exit. If False (submenu), returns after action.

        Returns:
            True to continue, False to exit
        """
        while True:
            self.display()

            # Get valid choices
            choices = [item.key for item in self.items]

            choice = Prompt.ask(
                "\n[cyan]Select an option[/cyan]",
                choices=choices,
                default="0" if "0" in choices else choices[0]
            )

            # Find the selected item
            selected = next((item for item in self.items if item.key == choice), None)

            if not selected:
                continue

            # Handle exit or back
            if selected.key == "0":
                # If main menu and option is "Exit", exit completely
                if is_main_menu and selected.label.lower() == "exit":
                    return False
                # If submenu and option is "Back", return to parent
                elif not is_main_menu and selected.label.lower() == "back":
                    return True
                # Fallback
                return False

            # Handle submenu
            if selected.submenu:
                should_continue = selected.submenu.run(is_main_menu=False)
                if not should_continue:
                    return False
                # Continue to show this menu again

            # Handle action
            elif selected.action:
                console.print()  # Blank line
                try:
                    selected.action()
                except KeyboardInterrupt:
                    console.print("\n[yellow]Operation cancelled[/yellow]")
                except Exception as e:
                    console.print(f"\n[red]Error: {e}[/red]")

                # Wait for user to continue
                console.print()
                try:
                    Prompt.ask("\n[dim]Press Enter to return to menu (or Ctrl+C to exit)[/dim]", default="")
                except KeyboardInterrupt:
                    console.print("\n[cyan]Exiting retroMaid...[/cyan]")
                    return False  # Exit completely

                # For submenus, return to parent after action
                if not is_main_menu:
                    return True
                # For main menu, loop back to show menu again

        return True


def create_main_menu(retromaid) -> Menu:
    """
    Create the main menu

    Args:
        retromaid: RetroMaid instance

    Returns:
        Menu object
    """
    items = [
        MenuItem(
            "1",
            "Scrape Metadata",
            "Download game metadata and media from online databases",
            action=lambda: scrape_system_interactive(retromaid)
        ),
        MenuItem(
            "2",
            "Find Duplicates",
            "Find and optionally delete duplicate ROM files",
            action=lambda: find_duplicates_interactive(retromaid)
        ),
        MenuItem(
            "3",
            "Convert DOS Games",
            "Convert DOS games to Batocera .pc format",
            action=lambda: dos_converter_interactive(retromaid)
        ),
        MenuItem(
            "4",
            "View System Status",
            "Show ROM collection statistics and scraping progress",
            action=lambda: show_status_interactive(retromaid)
        ),
        MenuItem(
            "5",
            "List Systems",
            "Show all available ROM systems",
            action=lambda: list_systems(retromaid)
        ),
        MenuItem(
            "6",
            "Clear Checkpoint",
            "Clear scraping checkpoint and start fresh",
            action=lambda: clear_checkpoint(retromaid)
        ),
        MenuItem(
            "0",
            "Exit",
            "Exit retroMaid",
            action=None
        )
    ]

    return Menu("Main Menu", items)


def scrape_system_interactive(retromaid):
    """Interactive scrape system function (called directly from main menu)"""
    systems = retromaid.scanner.get_available_systems()

    if not systems:
        console.print("\n[yellow]No systems found[/yellow]")
        return

    # Show available systems WITHOUT stats (too slow for 195+ systems)
    console.print(f"\n[bold]Available systems ({len(systems)} total):[/bold]")
    console.print("[dim]Type system name to scrape (e.g., 'c64', 'megadrive', 'nes')[/dim]\n")

    # Show systems in columns
    sorted_systems = sorted(systems)
    num_columns = 4
    systems_per_column = (len(sorted_systems) + num_columns - 1) // num_columns

    for row in range(systems_per_column):
        line_parts = []
        for col in range(num_columns):
            idx = col * systems_per_column + row
            if idx < len(sorted_systems):
                line_parts.append(f"[cyan]{sorted_systems[idx]:20}[/cyan]")
        console.print("  " + "  ".join(line_parts))

    # Ask which system
    console.print()
    choice = Prompt.ask("[cyan]Select system[/cyan]")

    # Validate system name
    if choice in systems:
        system = choice
    else:
        console.print(f"[red]Unknown system: {choice}[/red]")
        console.print(f"[dim]Hint: System names are case-sensitive. Try one from the list above.[/dim]")
        return

    # Import and run scraper
    import sys
    # Access run_scraper from __main__ module (retromaid.py when running)
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, 'run_scraper'):
        main_module.run_scraper(retromaid, system)
    else:
        console.print("[red]Error: run_scraper function not found[/red]")


def find_duplicates_interactive(retromaid):
    """Interactive find duplicates function (called directly from main menu)"""
    systems = retromaid.scanner.get_available_systems()

    if not systems:
        console.print("\n[yellow]No systems found[/yellow]")
        return

    system = Prompt.ask(
        "\n[cyan]Enter system name[/cyan]",
        choices=systems
    )

    # Import and run duplicate finder
    import sys
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, 'run_duplicate_finder'):
        main_module.run_duplicate_finder(retromaid, system)
    else:
        console.print("[red]Error: run_duplicate_finder function not found[/red]")


def dos_converter_interactive(retromaid):
    """Interactive DOS converter function (called directly from main menu)"""
    import sys
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, 'run_dos_converter'):
        main_module.run_dos_converter(retromaid)
    else:
        console.print("[red]Error: run_dos_converter function not found[/red]")


def show_status_interactive(retromaid):
    """Interactive status viewer function (called directly from main menu)"""
    systems = retromaid.scanner.get_available_systems()

    if not systems:
        console.print("\n[yellow]No systems found[/yellow]")
        return

    system = Prompt.ask(
        "\n[cyan]Enter system name (or 'all')[/cyan]",
        default="all"
    )

    if system == "all":
        # Show all systems
        table = Table(title="ROM Collection Status", show_header=True, header_style="bold cyan")
        table.add_column("System", style="cyan")
        table.add_column("Total ROMs", justify="right")
        table.add_column("With Metadata", justify="right", style="green")
        table.add_column("Missing", justify="right", style="yellow")
        table.add_column("Complete", justify="right", style="blue")

        for sys in sorted(systems):
            stats = retromaid.scanner.get_statistics(sys)
            table.add_row(
                sys,
                str(stats['total_roms']),
                str(stats['with_metadata']),
                str(stats['without_metadata']),
                str(stats['complete_metadata'])
            )

        console.print("\n")
        console.print(table)
    else:
        # Show specific system
        stats = retromaid.scanner.get_statistics(system)

        table = Table(title=f"Status: {system}", show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        table.add_row("Total ROMs", str(stats['total_roms']))
        table.add_row("With Metadata", f"[green]{stats['with_metadata']}[/green]")
        table.add_row("Missing Metadata", f"[yellow]{stats['without_metadata']}[/yellow]")
        table.add_row("Complete", f"[blue]{stats['complete_metadata']}[/blue]")
        table.add_row("Incomplete", str(stats['incomplete_metadata']))

        console.print("\n")
        console.print(table)


def list_systems(retromaid) -> None:
    """List all available systems"""
    systems = retromaid.scanner.get_available_systems()

    if not systems:
        console.print("\n[yellow]No systems found[/yellow]")
        return

    table = Table(title="Available Systems", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("System", style="cyan")
    table.add_column("ROMs", justify="right")

    for i, system in enumerate(sorted(systems), 1):
        stats = retromaid.scanner.get_statistics(system)
        table.add_row(str(i), system, str(stats['total_roms']))

    console.print("\n")
    console.print(table)


def clear_checkpoint(retromaid) -> None:
    """Clear scraping checkpoint"""
    from rich.prompt import Confirm

    if Confirm.ask("\n[yellow]Clear all scraping checkpoints?[/yellow]"):
        retromaid.state_manager.clear_all()
        console.print("[green]Checkpoint cleared[/green]")
    else:
        console.print("[dim]Cancelled[/dim]")
