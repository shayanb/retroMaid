#!/usr/bin/env python3
"""
retroMaid - Batocera ROM Metadata Scraper
"""
import click
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Confirm, Prompt

from utils.config import Config
from utils.logger import Logger, get_logger
from core.scanner import ROMScanner

logger = get_logger()
from core.xml_manager import GameListXML, GameMetadata
from core.hasher import ROMHasher
from core.duplicate_detector import DuplicateResolver, DuplicateGroup
from core.state_manager import StateManager
from core.dos_converter import DOSConverter
from scrapers.screenscraper import ScreenScraper
from scrapers.igdb import IGDB
from scrapers.thegamesdb import TheGamesDB
from media.downloader import GameMediaManager

console = Console()


class RetroMaid:
    """Main retroMaid application"""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize retroMaid"""
        self.config = Config(config_path)
        self.logger = Logger.setup(
            log_file=self.config.get("logging.log_file", "retromaid.log"),
            level=self.config.get("logging.level", "INFO"),
            console_output=self.config.get("logging.console", True)
        )

        # Initialize components
        roms_path = self.config.get("roms_path")
        if not roms_path:
            raise ValueError("roms_path not configured")

        self.scanner = ROMScanner(Path(roms_path))
        self.state_manager = StateManager(
            self.config.get("resume.checkpoint_file", ".retromaid_checkpoint.json")
        )

        # Initialize all available scrapers
        scrapers = []

        # ScreenScraper (primary)
        scraper_config = self.config.get("scrapers.screenscraper", {})
        if scraper_config.get('username'):
            scrapers.append(('screenscraper', ScreenScraper(scraper_config)))

        # IGDB (fallback)
        igdb_config = self.config.get("scrapers.igdb", {})
        if igdb_config.get('client_id'):
            scrapers.append(('igdb', IGDB(igdb_config)))

        # TheGamesDB (fallback)
        tgdb_config = self.config.get("scrapers.thegamesdb", {})
        scrapers.append(('thegamesdb', TheGamesDB(tgdb_config)))  # Works without API key

        if not scrapers:
            raise ValueError("No scrapers configured")

        self.scrapers = scrapers
        self.active_scraper = None  # Will be set when first scraper succeeds
        self.failed_scrapers = set()  # Track permanently failed scrapers (auth errors, etc.)

    def _mark_scraper_failed(self, scraper_name: str, error: Exception) -> bool:
        """
        Mark a scraper as permanently failed if it has auth/credential errors

        Args:
            scraper_name: Name of the scraper
            error: Exception that occurred

        Returns:
            True if permanently failed, False if temporary
        """
        error_str = str(error).lower()

        # Permanent failures (don't retry)
        permanent_errors = ['403', '401', 'identifiants', 'credentials', 'unauthorized', 'forbidden']
        if any(err in error_str for err in permanent_errors):
            if scraper_name not in self.failed_scrapers:
                self.failed_scrapers.add(scraper_name)
                console.print(f"[red]Scraper '{scraper_name}' disabled due to auth error[/red]")
            return True

        return False  # Temporary failure

    def _try_scrapers(self, search_func, *args, **kwargs):
        """
        Try scrapers in order until one succeeds

        Once a scraper succeeds, it becomes the active scraper for the session

        Args:
            search_func: Function name to call on scraper ('search_by_hash' or 'search_by_name')
            *args, **kwargs: Arguments to pass to search function

        Returns:
            Search results or None
        """
        # If we have an active scraper, try it first (if not failed)
        if self.active_scraper:
            name, scraper = self.active_scraper

            # Skip if this scraper has permanently failed
            if name not in self.failed_scrapers:
                try:
                    func = getattr(scraper, search_func)
                    result = func(*args, **kwargs)
                    if result:
                        return result
                except Exception as e:
                    # Check if this is a permanent failure
                    if self._mark_scraper_failed(name, e):
                        # Permanently failed, will try fallbacks below
                        pass
                    else:
                        # Temporary failure
                        logger.debug(f"{name} failed: {e}")

            # If active scraper failed, try other scrapers as fallback
            for fallback_name, fallback_scraper in self.scrapers:
                # Skip failed scrapers and the one we just tried
                if fallback_name in self.failed_scrapers or fallback_name == name:
                    continue

                try:
                    func = getattr(fallback_scraper, search_func)
                    result = func(*args, **kwargs)

                    if result:
                        # Switch to this scraper
                        console.print(f"[yellow]Switched to {fallback_name} scraper[/yellow]")
                        self.active_scraper = (fallback_name, fallback_scraper)
                        return result

                except Exception as e:
                    if self._mark_scraper_failed(fallback_name, e):
                        continue  # Skip permanently failed
                    logger.debug(f"{fallback_name} failed: {e}")
                    continue

            return None

        # No active scraper yet - try all in order (skip failed ones)
        for name, scraper in self.scrapers:
            # Skip permanently failed scrapers
            if name in self.failed_scrapers:
                continue

            try:
                func = getattr(scraper, search_func)
                result = func(*args, **kwargs)

                if result:
                    # Success! Set this as active scraper
                    console.print(f"[cyan]Using {name} scraper[/cyan]")
                    self.active_scraper = (name, scraper)
                    return result

            except Exception as e:
                if self._mark_scraper_failed(name, e):
                    continue  # Skip permanently failed
                logger.debug(f"{name} failed: {e}")
                continue

        return None

    def scan_system(self, system: str) -> None:
        """Scan and display statistics for a system"""
        console.print(f"\n[bold cyan]Scanning system:[/bold cyan] {system}")

        stats = self.scanner.get_statistics(system)

        table = Table(title=f"{system.upper()} Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="magenta")

        table.add_row("Total ROMs", str(stats['total_roms']))
        table.add_row("With Metadata", str(stats['with_metadata']))
        table.add_row("Without Metadata", str(stats['without_metadata']))
        table.add_row("Complete Metadata", str(stats['complete_metadata']))
        table.add_row("Incomplete Metadata", str(stats['incomplete_metadata']))

        console.print(table)

    def process_system(
        self,
        system: str,
        scrape_images: bool = True,
        scrape_videos: bool = False,
        force: bool = False
    ) -> None:
        """Process all ROMs in a system"""
        console.print(f"\n[bold cyan]Processing system:[/bold cyan] {system}")

        # Get ROMs missing metadata
        missing = self.scanner.get_missing_metadata_games(system)

        if not missing:
            console.print("[green]All ROMs have metadata![/green]")
            return

        # Filter out already processed (unless force)
        if not force:
            missing = [
                rom for rom in missing
                if not self.state_manager.is_processed(system, rom.relative_path)
            ]

        if not missing:
            console.print("[green]No new ROMs to process (use --force to reprocess)[/green]")
            return

        console.print(f"Found [yellow]{len(missing)}[/yellow] ROMs missing metadata")

        # Confirm before proceeding
        if not Confirm.ask("Proceed with scraping?", default=True):
            return

        # Initialize state
        state = self.state_manager.get_or_create_state(system)
        state.total_games = len(missing)

        # Get system path
        system_path = self.scanner.roms_base_path / system
        gamelist = GameListXML(system_path / "gamelist.xml")

        # Initialize media manager
        media_manager = GameMediaManager(system_path)

        # Process each ROM (with interrupt handling)
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"Processing {system}...", total=len(missing))

                for rom in missing:
                    progress.update(task, description=f"Processing: {rom.filename}")

                    try:
                        # Compute hash for accurate matching
                        if not rom.hash_info:
                            rom.hash_info = ROMHasher.get_rom_hash_info(rom.path)

                        # Try hash-based search first (most accurate)
                        # Only ScreenScraper supports hash search
                        game = None
                        if rom.hash_info and rom.hash_info.get('md5'):
                            game = self._try_scrapers(
                                'search_by_hash',
                                rom.hash_info['md5'],
                                'md5',
                                system,
                                rom.hash_info.get('size')
                            )

                        # Fall back to name-based search (tries all scrapers)
                        if not game:
                            from utils.filename import sanitize_filename, extract_region_from_filename

                            clean_name = sanitize_filename(rom.filename, for_matching=True)
                            region = extract_region_from_filename(rom.filename)

                            # Try all scrapers with smart switching
                            results = self._try_scrapers('search_by_name', clean_name, system, region)

                            if results:
                                # _try_scrapers returns single game or list
                                if isinstance(results, list):
                                    game = results[0] if results else None
                                else:
                                    game = results

                                if game:
                                    # If confidence is low, ask user
                                    if game.confidence < 80:
                                        choice = self._confirm_game_match(
                                            rom.filename,
                                            game,
                                            progress=progress,
                                            task=task
                                        )

                                        if choice == "stop":
                                            console.print("\n[yellow]Stopping scraping (progress will be saved)...[/yellow]")
                                            break  # Exit the ROM loop
                                        elif choice == "no":
                                            self.state_manager.mark_skipped(system, rom.relative_path)
                                            progress.advance(task)
                                            continue
                                        # else: choice == "yes", continue processing

                        if not game:
                            console.print(f"[yellow]No match found for:[/yellow] {rom.filename}")
                            self.state_manager.mark_processed(
                                system, rom.relative_path, False, "No match found"
                            )
                            progress.advance(task)
                            continue

                        # Download media
                        media_paths = {}
                        if scrape_images or scrape_videos:
                            media_paths = media_manager.download_game_media(
                                game.name,
                                box_art_url=game.box_art_url if scrape_images else None,
                                screenshot_url=game.screenshot_url if scrape_images else None,
                                marquee_url=game.marquee_url if scrape_images else None,
                                thumbnail_url=game.thumbnail_url if scrape_images else None,
                                video_url=game.video_url if scrape_videos else None,
                            )

                        # Create metadata
                        metadata = self._create_metadata_from_game(rom, game, media_paths)

                        # Add to gamelist
                        gamelist.add_or_update_game(metadata)

                        # Mark as processed
                        self.state_manager.mark_processed(system, rom.relative_path, True)

                        # Show which scraper was used
                        scraper_name = game.source if hasattr(game, 'source') else 'Unknown'
                        console.print(f"[green]✓[/green] {game.name} [dim]({scraper_name})[/dim]")

                    except Exception as e:
                        console.print(f"[red]Error processing {rom.filename}:[/red] {e}")
                        self.state_manager.mark_processed(system, rom.relative_path, False, str(e))

                        progress.advance(task)

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Scraping interrupted by user (Ctrl+C)[/yellow]")

        finally:
            # Always save progress, even on interrupt
            console.print("\n[cyan]Saving gamelist.xml...[/cyan]")
            gamelist.save(backup=self.config.get("backup.enabled", True))

            # Save state
            self.state_manager.save()

            # Show summary
            summary = self.state_manager.get_summary(system)
            if summary:
                console.print(f"\n[bold green]Processing complete![/bold green]")
                console.print(f"Successful: {summary['successful']}")
                console.print(f"Failed: {summary['failed']}")
                console.print(f"Skipped: {summary['skipped']}")

            media_manager.cleanup()

    def _confirm_game_match(self, rom_filename: str, game, progress=None, task=None) -> str:
        """
        Ask user to confirm a game match

        Args:
            rom_filename: ROM filename
            game: Matched game
            progress: Progress context (optional, for pausing)
            task: Progress task (optional, for pausing)

        Returns:
            'yes' - Accept match
            'no' - Skip this ROM
            'stop' - Stop scraping and save
        """
        # Stop progress bar to avoid overlap
        if progress and task is not None:
            progress.stop_task(task)

        # Clear formatting and show prompt
        console.print()  # Blank line
        console.print(f"[yellow]Low confidence match for:[/yellow] {rom_filename}")
        console.print(f"[bold]Found:[/bold] {game.name} [dim](confidence: {game.confidence:.0f}%)[/dim]")

        if game.description:
            # Limit description length
            desc = game.description[:150] + "..." if len(game.description) > 150 else game.description
            console.print(f"[dim]{desc}[/dim]")

        console.print()  # Blank line
        console.print("[dim]Options: [y]es / [n]o (skip) / [s]top scraping[/dim]")

        choice = Prompt.ask(
            "Accept match?",
            choices=["y", "n", "s"],
            default="y",
            show_choices=False
        )

        console.print()  # Blank line after

        # Resume progress bar
        if progress and task is not None:
            progress.start_task(task)

        if choice == "y":
            return "yes"
        elif choice == "n":
            return "no"
        else:  # choice == "s"
            return "stop"

    def _create_metadata_from_game(self, rom, game, media_paths: dict) -> GameMetadata:
        """Create GameMetadata from scraper game result"""
        # Convert release date format
        releasedate = None
        if game.release_date:
            try:
                # Convert YYYY-MM-DD to YYYYMMDDTHHMMSS
                date_parts = game.release_date.split('-')
                if len(date_parts) == 3:
                    releasedate = f"{date_parts[0]}{date_parts[1]}{date_parts[2]}T000000"
            except:
                pass

        metadata = GameMetadata(
            path=rom.relative_path,
            name=game.name,
            desc=game.description,
            releasedate=releasedate,
            developer=game.developer,
            publisher=game.publisher,
            genre=game.genre,
            players=game.players,
            region=game.region,
            lang=game.language or self.config.get("matching.language", "en"),
        )

        # Add media paths
        if 'image' in media_paths:
            metadata.image = media_paths['image']
        if 'marquee' in media_paths:
            metadata.marquee = media_paths['marquee']
        if 'thumbnail' in media_paths:
            metadata.thumbnail = media_paths['thumbnail']
        if 'video' in media_paths:
            metadata.video = media_paths['video']

        # Preserve existing user stats if ROM already has metadata
        if rom.metadata:
            metadata.favorite = rom.metadata.favorite
            metadata.playcount = rom.metadata.playcount
            metadata.lastplayed = rom.metadata.lastplayed
            metadata.gametime = rom.metadata.gametime

        return metadata

    def find_duplicates(self, system: str, resolve: bool = True, delete_files: bool = False) -> None:
        """Find and optionally resolve duplicate ROMs"""
        console.print(f"\n[bold cyan]Scanning for duplicates:[/bold cyan] {system}")

        duplicates = self.scanner.find_duplicates(system)

        if not duplicates:
            console.print("[green]No duplicates found![/green]")
            return

        console.print(f"Found [yellow]{len(duplicates)}[/yellow] groups of duplicates")

        if not resolve:
            # Just display
            for name, roms in duplicates.items():
                group = DuplicateGroup(roms)
                console.print(f"\n{group.get_summary()}")
                for rom in roms:
                    console.print(f"  - {rom.filename}")
            return

        # Interactive resolution
        strategy = self.config.get("duplicates.strategy", "ask")
        resolver = DuplicateResolver(strategy, delete_files=delete_files)

        system_path = self.scanner.roms_base_path / system
        gamelist = GameListXML(system_path / "gamelist.xml")

        total_deleted_files = 0
        total_removed_from_xml = 0

        for name, roms in duplicates.items():
            group = DuplicateGroup(roms)
            keep = resolver.resolve(group)

            # Collect ROMs to remove
            to_remove = [rom for rom in roms if rom not in keep]

            # Remove from gamelist
            for rom in to_remove:
                if rom.relative_path in gamelist.games:
                    gamelist.remove_game(rom.relative_path)
                    total_removed_from_xml += 1
                    console.print(f"[yellow]Removed from gamelist:[/yellow] {rom.filename}")

            # Delete physical files if requested
            if resolver.delete_files and to_remove:
                successful, failed = resolver.delete_rom_files(to_remove)
                total_deleted_files += successful

                if failed > 0:
                    console.print(f"[red]Failed to delete {failed} files[/red]")

        # Save gamelist
        gamelist.save(backup=True)

        # Summary
        console.print(f"\n[bold green]Duplicate resolution complete![/bold green]")
        console.print(f"Removed from gamelist: {total_removed_from_xml}")
        if resolver.delete_files:
            console.print(f"Deleted files: {total_deleted_files}")


# CLI Commands
@click.group()
@click.version_option(version="1.0.0")
def cli():
    """retroMaid - Batocera ROM Metadata Scraper"""
    pass


@cli.command()
@click.option('--system', '-s', help='System to list (e.g., psx, nes)')
def list_systems(system: Optional[str]):
    """List available systems or scan a specific system"""
    app = RetroMaid()

    if system:
        app.scan_system(system)
    else:
        systems = app.scanner.get_available_systems()
        console.print("\n[bold cyan]Available systems:[/bold cyan]")
        for sys in systems:
            console.print(f"  - {sys}")


@cli.command()
@click.argument('system')
@click.option('--no-images', is_flag=True, help='Skip image downloads')
@click.option('--videos', is_flag=True, help='Download videos (disabled by default)')
@click.option('--force', is_flag=True, help='Reprocess already processed ROMs')
def scrape(system: str, no_images: bool, videos: bool, force: bool):
    """Scrape metadata for a system"""
    app = RetroMaid()
    app.process_system(
        system,
        scrape_images=not no_images,
        scrape_videos=videos,
        force=force
    )


@cli.command()
@click.argument('system')
@click.option('--resolve', is_flag=True, help='Interactively resolve duplicates')
@click.option('--delete', is_flag=True, help='Delete ROM files from disk (not just gamelist)')
def duplicates(system: str, resolve: bool, delete: bool):
    """Find duplicate ROMs"""
    app = RetroMaid()
    app.find_duplicates(system, resolve=resolve, delete_files=delete)


@cli.command()
@click.option('--system', '-s', help='System to show status for')
def status(system: Optional[str]):
    """Show processing status"""
    app = RetroMaid()

    if system:
        summary = app.state_manager.get_summary(system)
        if not summary:
            console.print(f"[yellow]No processing history for {system}[/yellow]")
            return

        table = Table(title=f"{system.upper()} Processing Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="magenta")

        for key, value in summary.items():
            table.add_row(key.replace('_', ' ').title(), str(value))

        console.print(table)

        # Show errors if any
        if app.state_manager.has_errors(system):
            console.print("\n[bold red]Errors:[/bold red]")
            for path, error in app.state_manager.get_errors(system).items():
                console.print(f"  {path}: {error}")
    else:
        console.print("[yellow]Specify --system to see status[/yellow]")


@cli.command()
@click.option('--system', '-s', help='System to clear (all if not specified)')
@click.confirmation_option(prompt='Are you sure you want to clear the checkpoint?')
def clear(system: Optional[str]):
    """Clear processing checkpoint"""
    app = RetroMaid()
    app.state_manager.clear(system)
    console.print("[green]Checkpoint cleared![/green]")


@cli.command()
@click.option('--interactive/--no-interactive', default=True, help='Ask for each game individually')
@click.option('--delete-zips', is_flag=True, help='Delete ZIP files after extraction (batch mode only)')
@click.option('--no-defaults', is_flag=True, help='Skip default behavior prompts in batch mode')
@click.option('--focus-zips', is_flag=True, help='Only process ZIP files (ignore folders)')
def convert_dos(interactive: bool, delete_zips: bool, no_defaults: bool, focus_zips: bool):
    """
    Convert DOS games to Batocera format.

    Creates .pc folders with proper dosbox.bat files for each game.
    Automatically detects the correct executable to launch.

    Examples:
      retromaid.py convert-dos                    # Interactive mode
      retromaid.py convert-dos --no-interactive   # Batch with prompts
      retromaid.py convert-dos --no-interactive --delete-zips  # Batch, delete ZIPs
      retromaid.py convert-dos --focus-zips       # Only convert ZIPs
    """
    app = RetroMaid()

    dos_path = app.scanner.roms_base_path / "dos"

    if not dos_path.exists():
        console.print(f"[red]DOS directory not found:[/red] {dos_path}")
        return

    converter = DOSConverter(dos_path)

    console.print("\n[bold cyan]Scanning DOS games...[/bold cyan]")
    games = converter.scan_dos_games()

    if not games:
        console.print("[green]No DOS games need conversion![/green]")
        return

    # Filter out already converted
    unconverted = [g for g in games if not g.is_converted]

    # Filter to only ZIPs if requested
    if focus_zips:
        unconverted = [g for g in unconverted if g.path.suffix == '.zip']
        console.print("[cyan]Focusing on ZIP files only[/cyan]")

    if not unconverted:
        console.print("[green]All DOS games are already converted![/green]")
        return

    console.print(f"Found [yellow]{len(unconverted)}[/yellow] games to convert")

    # Show summary
    from rich.table import Table
    table = Table(title="DOS Games to Convert")
    table.add_column("Game Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Executables", justify="right")

    for game in unconverted:
        game_type = "ZIP" if game.path.suffix == '.zip' else "Folder"
        exe_count = len(game.executables) if game.executables else "?"
        table.add_row(game.name, game_type, str(exe_count))

    console.print(table)

    if not Confirm.ask("\nProceed with conversion?", default=True):
        return

    # Convert games
    successful, failed = converter.batch_convert(
        unconverted,
        interactive=interactive,
        delete_zips=delete_zips if delete_zips else None,
        ask_for_defaults=not no_defaults
    )

    # Summary
    console.print(f"\n[bold green]Conversion complete![/bold green]")
    console.print(f"Successful: {successful}")
    console.print(f"Failed: {failed}")

    # Update gamelist.xml paths
    if successful > 0:
        console.print("\n[cyan]Updating gamelist.xml...[/cyan]")
        gamelist_path = dos_path / "gamelist.xml"

        if gamelist_path.exists():
            from core.xml_manager import GameListXML

            gamelist = GameListXML(gamelist_path)

            # Update paths for converted games
            updated = 0
            for game in unconverted:
                old_path = f"./{game.name}.zip" if game.path.suffix == '.zip' else f"./{game.name}"
                new_path = f"./{game.name}.pc"

                # Check if old path exists in gamelist
                if old_path in gamelist.games:
                    metadata = gamelist.games[old_path]
                    gamelist.remove_game(old_path)
                    metadata.path = new_path
                    gamelist.add_or_update_game(metadata)
                    updated += 1

            if updated > 0:
                gamelist.save(backup=True)
                console.print(f"[green]Updated {updated} entries in gamelist.xml[/green]")
        else:
            console.print("[yellow]No gamelist.xml found - create one by scraping[/yellow]")


if __name__ == '__main__':
    cli()
