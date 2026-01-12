"""
Duplicate ROM detection and resolution
"""
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from core.scanner import ROMFile
from core.xml_manager import GameMetadata
from utils.filename import get_base_name_and_disc
from utils.logger import get_logger

logger = get_logger()


class DuplicateGroup:
    """Represents a group of duplicate ROMs"""

    def __init__(self, roms: List[ROMFile]):
        """
        Initialize duplicate group

        Args:
            roms: List of duplicate ROM files
        """
        self.roms = roms
        self.base_name, self.is_multi_disc = self._analyze_group()

    def _analyze_group(self):
        """Analyze the group to determine if it's a multi-disc game"""
        if not self.roms:
            return "", False

        # Check if all ROMs have disc numbers
        disc_info = []
        for rom in self.roms:
            base_name, disc_num = get_base_name_and_disc(rom.filename)
            disc_info.append((base_name, disc_num))

        # If all have disc numbers and same base name, it's multi-disc
        base_names = set(info[0] for info in disc_info)
        disc_numbers = [info[1] for info in disc_info]

        if len(base_names) == 1 and all(disc is not None for disc in disc_numbers):
            return list(base_names)[0], True

        # Otherwise, regular duplicates
        return disc_info[0][0] if disc_info else "", False

    def get_most_complete(self) -> Optional[ROMFile]:
        """
        Get the ROM with the most complete metadata

        Returns:
            ROM file with best metadata or None
        """
        roms_with_metadata = [rom for rom in self.roms if rom.metadata]

        if not roms_with_metadata:
            # No metadata, return first one
            return self.roms[0] if self.roms else None

        # Sort by metadata completeness
        roms_with_metadata.sort(
            key=lambda r: r.metadata.calculate_completeness() if r.metadata else 0,
            reverse=True
        )

        return roms_with_metadata[0]

    def get_summary(self) -> str:
        """Get a summary description of this duplicate group"""
        if self.is_multi_disc:
            return f"{self.base_name} (Multi-disc: {len(self.roms)} discs)"
        else:
            return f"{self.base_name} ({len(self.roms)} duplicates)"


class DuplicateResolver:
    """Interactive duplicate resolution"""

    def __init__(self, strategy: str = "ask", delete_files: bool = False):
        """
        Initialize resolver

        Args:
            strategy: Resolution strategy ('ask', 'keep_first', 'keep_most_complete', 'keep_all')
            delete_files: Whether to physically delete ROM files (not just remove from gamelist)
        """
        self.strategy = strategy
        self.delete_files = delete_files
        self.default_action: Optional[str] = None

    def resolve(self, group: DuplicateGroup) -> List[ROMFile]:
        """
        Resolve a duplicate group

        Args:
            group: Duplicate group

        Returns:
            List of ROMs to keep
        """
        # Multi-disc games should always be kept
        if group.is_multi_disc:
            logger.info(f"Multi-disc game detected: {group.get_summary()}")
            return group.roms

        # Handle based on strategy
        if self.strategy == "keep_all":
            return group.roms

        elif self.strategy == "keep_first":
            return [group.roms[0]]

        elif self.strategy == "keep_most_complete":
            most_complete = group.get_most_complete()
            return [most_complete] if most_complete else []

        elif self.strategy == "ask":
            return self._ask_user(group)

        else:
            logger.warning(f"Unknown strategy: {self.strategy}, keeping all")
            return group.roms

    def delete_rom_files(self, roms_to_delete: List[ROMFile]) -> Tuple[int, int]:
        """
        Physically delete ROM files from disk

        Args:
            roms_to_delete: List of ROM files to delete

        Returns:
            Tuple of (successful_deletes, failed_deletes)
        """
        import shutil

        successful = 0
        failed = 0

        for rom in roms_to_delete:
            try:
                if rom.path.is_file():
                    rom.path.unlink()
                    logger.info(f"Deleted file: {rom.path.name}")
                    successful += 1
                elif rom.path.is_dir():
                    shutil.rmtree(rom.path)
                    logger.info(f"Deleted directory: {rom.path.name}")
                    successful += 1
                else:
                    logger.warning(f"Path does not exist: {rom.path}")
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to delete {rom.path}: {e}")
                failed += 1

        return successful, failed

    def _ask_user(self, group: DuplicateGroup) -> List[ROMFile]:
        """
        Ask user which ROM(s) to keep

        Args:
            group: Duplicate group

        Returns:
            List of ROMs to keep
        """
        from rich.console import Console
        from rich.table import Table
        from rich.prompt import Prompt, Confirm

        console = Console()

        # Check if we have a default action
        if self.default_action:
            console.print(f"[dim]Applying default action '{self.default_action}' to {group.get_summary()}[/dim]")
            return self._apply_default_action(group, self.default_action)

        console.print(f"\n[bold yellow]Duplicate ROMs found:[/bold yellow] {group.get_summary()}")

        # Ask about deletion if not already decided
        if self.delete_files is None:
            self.delete_files = Confirm.ask(
                "\n[bold]Delete ROM files from disk?[/bold] (not just remove from gamelist)",
                default=False
            )

        # Find most complete ROM for highlighting
        most_complete = group.get_most_complete()

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Filename", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Has Metadata", justify="center")
        table.add_column("Completeness", justify="right")
        table.add_column("Recommended", justify="center")

        for idx, rom in enumerate(group.roms, 1):
            has_metadata = "✓" if rom.has_metadata else "✗"
            completeness = f"{rom.metadata.calculate_completeness():.0f}%" if rom.metadata else "0%"
            size_mb = rom.size / (1024 * 1024)
            is_recommended = "⭐" if rom == most_complete else ""

            # Highlight the recommended row
            style = "bold green" if rom == most_complete else None

            table.add_row(
                str(idx),
                rom.filename,
                f"{size_mb:.1f} MB",
                has_metadata,
                completeness,
                is_recommended,
                style=style
            )

        console.print(table)

        # Prompt user
        console.print("\n[bold cyan]Options:[/bold cyan]")
        console.print("  [bold yellow][1-N][/bold yellow] - Keep specific ROM(s) (comma-separated, e.g. '1,3')")
        console.print("")
        console.print("  [bold green]Single group actions:[/bold green]")
        console.print("    [bold]a[/bold] - Keep all")
        console.print("    [bold]m[/bold] - Keep most complete (based on metadata)")
        console.print("    [bold]f[/bold] - Keep first")
        console.print("    [bold]s[/bold] - Skip (keep all)")
        console.print("")
        console.print("  [bold magenta]Default for all remaining groups:[/bold magenta]")
        console.print("    [bold]da[/bold] - Default: keep all for remaining")
        console.print("    [bold]dm[/bold] - Default: keep most complete for remaining")
        console.print("    [bold]df[/bold] - Default: keep first for remaining")

        choice = Prompt.ask("\n[bold]Your choice[/bold]", default="m")

        # Handle default actions
        if choice.startswith('d'):
            self.default_action = choice[1:]  # Remove 'd' prefix
            console.print(f"[bold green]✓ Default action set to '{self.default_action}' for all remaining groups[/bold green]")
            return self._apply_default_action(group, self.default_action)

        # Handle regular choices
        return self._apply_choice(group, choice)

    def _apply_default_action(self, group: DuplicateGroup, action: str) -> List[ROMFile]:
        """Apply default action to a group"""
        # Don't print here - let the caller handle output for consistency

        if action == 'a':
            return group.roms
        elif action == 'm':
            most_complete = group.get_most_complete()
            return [most_complete] if most_complete else []
        elif action == 'f':
            return [group.roms[0]]
        else:
            return group.roms

    def _apply_choice(self, group: DuplicateGroup, choice: str) -> List[ROMFile]:
        """Apply user choice to a group"""
        from rich.console import Console
        console = Console()

        choice = choice.lower().strip()

        if choice == 'a' or choice == 's':
            console.print(f"[green]→ Keeping all {len(group.roms)} ROMs[/green]")
            return group.roms

        elif choice == 'm':
            most_complete = group.get_most_complete()
            if most_complete:
                console.print(f"[green]→ Keeping:[/green] {most_complete.filename}")
            return [most_complete] if most_complete else []

        elif choice == 'f':
            console.print(f"[green]→ Keeping:[/green] {group.roms[0].filename}")
            return [group.roms[0]]

        else:
            # Try to parse as number(s)
            try:
                indices = [int(x.strip()) for x in choice.split(',')]
                selected = []
                for idx in indices:
                    if 1 <= idx <= len(group.roms):
                        selected.append(group.roms[idx - 1])

                if selected:
                    console.print(f"[green]→ Keeping {len(selected)} ROM(s):[/green]")
                    for rom in selected:
                        console.print(f"    {rom.filename}")
                    return selected
                else:
                    console.print("[yellow]→ No valid selections, keeping all[/yellow]")
                    return group.roms
            except ValueError:
                logger.warning(f"Invalid choice: {choice}, keeping all")
                console.print(f"[yellow]→ Invalid choice, keeping all[/yellow]")
                return group.roms
