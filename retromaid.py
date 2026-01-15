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

    def __init__(self, config_path: str = "config.yaml", roms_path_override: str = None):
        """Initialize retroMaid"""
        self.config = Config(config_path)
        self.config_path = config_path
        self.logger = Logger.setup(
            log_file=self.config.get("logging.log_file", "retromaid.log"),
            level=self.config.get("logging.level", "INFO"),
            console_output=self.config.get("logging.console", True)
        )

        # Initialize components
        roms_path = roms_path_override or self.config.get("roms_path")
        if not roms_path:
            raise ValueError("roms_path not configured in config.yaml")

        # Check if path exists before initializing scanner
        roms_path_obj = Path(roms_path)
        if not roms_path_obj.exists():
            raise FileNotFoundError(
                f"ROMs path not accessible: {roms_path}\n"
                f"This usually means the network share is not mounted or the path is incorrect.\n"
                f"Configure the correct path in: {Path(config_path).absolute()}"
            )

        self.scanner = ROMScanner(roms_path_obj)
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

    def _verify_scraper_access(self, scraper_name: str, scraper) -> bool:
        """
        Verify API access for a scraper

        Args:
            scraper_name: Name of the scraper
            scraper: Scraper instance

        Returns:
            True if accessible, False if failed
        """
        try:
            # Simple test: try to search for a common game
            # This will fail immediately if credentials are wrong
            test_result = scraper.search_by_name("Mario", "nes", "us")
            # Even if no results, if no exception was raised, auth is OK
            return True
        except Exception as e:
            error_str = str(e).lower()
            # Check for authentication/credential errors
            permanent_errors = ['403', '401', 'identifiants', 'credentials', 'unauthorized', 'forbidden', 'login']
            # Also check for JSON parsing errors which often mean HTML error page was returned
            json_errors = ['expecting value', 'json', 'decode']

            if any(err in error_str for err in permanent_errors):
                console.print(f"[red]⨯ {scraper_name}: Authentication failed ({str(e)[:50]}...)[/red]")
                self.failed_scrapers.add(scraper_name)
                return False
            elif any(err in error_str for err in json_errors):
                # JSON errors usually mean authentication failed and returned HTML error page
                logger.warning(f"{scraper_name} returned invalid response: {e}")
                console.print(f"[red]⨯ {scraper_name}: Invalid API response (likely auth error)[/red]")
                self.failed_scrapers.add(scraper_name)
                return False
            else:
                # Other errors might be temporary (network timeout, etc.)
                logger.warning(f"Scraper {scraper_name} test failed: {e}")
                # For now, mark as failed to be safe
                console.print(f"[yellow]⚠ {scraper_name}: Test failed, will try anyway[/yellow]")
                return True  # Give it a chance

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
                console.print(f"[red]⨯ {scraper_name}: Disabled due to authentication error[/red]")
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

        # Verify scraper access before starting
        console.print("\n[dim]Verifying scraper access...[/dim]")
        working_scrapers = []
        for name, scraper in self.scrapers:
            if name not in self.failed_scrapers:
                if self._verify_scraper_access(name, scraper):
                    console.print(f"[green]✓ {name}: Ready[/green]")
                    working_scrapers.append((name, scraper))
                # Failed scrapers already marked in _verify_scraper_access

        if not working_scrapers:
            console.print("\n[red]No working scrapers available! Check your API credentials.[/red]")
            return

        console.print(f"\n[cyan]{len(working_scrapers)} scraper(s) ready to use[/cyan]")

        # Confirm before proceeding
        if not Confirm.ask("\nProceed with scraping?", default=True):
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

                            logger.debug(f"Searching for: '{clean_name}' (from '{rom.filename}')")

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
                            # Show what was actually searched for
                            from utils.filename import sanitize_filename
                            searched_name = sanitize_filename(rom.filename, for_matching=True)
                            console.print(
                                f"[yellow]No match found:[/yellow] {rom.filename} "
                                f"[dim](searched: '{searched_name}' on {system})[/dim]"
                            )
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

        # Create a new console instance to avoid progress bar interference
        from rich.console import Console
        prompt_console = Console()

        # Clear formatting and show prompt
        prompt_console.print()  # Blank line
        prompt_console.print(f"[yellow]Low confidence match for:[/yellow] {rom_filename}")
        prompt_console.print(f"[bold]Found:[/bold] {game.name} [dim](confidence: {game.confidence:.0f}%)[/dim]")

        if game.description:
            # Limit description length
            desc = game.description[:150] + "..." if len(game.description) > 150 else game.description
            prompt_console.print(f"[dim]{desc}[/dim]")

        prompt_console.print()  # Blank line
        prompt_console.print("[bold cyan]Options:[/bold cyan]")
        prompt_console.print("  [bold]y[/bold] - Yes, accept this match")
        prompt_console.print("  [bold]n[/bold] - No, skip this ROM")
        prompt_console.print("  [bold]s[/bold] - Stop scraping and save progress")
        prompt_console.print()

        choice = Prompt.ask(
            "[bold]Your choice[/bold]",
            choices=["y", "n", "s"],
            default="y",
            show_choices=False,
            console=prompt_console
        )

        prompt_console.print()  # Blank line after

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
        # Helper to safely convert values to strings
        def to_str(value):
            """Convert value to string, handling None and non-string types"""
            if value is None:
                return None
            return str(value) if not isinstance(value, str) else value

        # Convert release date format
        releasedate = None
        if game.release_date:
            try:
                # Convert YYYY-MM-DD to YYYYMMDDTHHMMSS
                date_str = to_str(game.release_date)
                date_parts = date_str.split('-')
                if len(date_parts) == 3:
                    releasedate = f"{date_parts[0]}{date_parts[1]}{date_parts[2]}T000000"
            except:
                pass

        metadata = GameMetadata(
            path=rom.relative_path,
            name=to_str(game.name),
            desc=to_str(game.description),
            releasedate=releasedate,
            developer=to_str(game.developer),
            publisher=to_str(game.publisher),
            genre=to_str(game.genre),
            players=to_str(game.players),
            region=to_str(game.region),
            lang=to_str(game.language) or self.config.get("matching.language", "en"),
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
        """Find and optionally resolve duplicate ROMs (DEPRECATED - use run_duplicate_finder)"""
        console.print(f"\n[yellow]Note: Using CLI duplicate finder. Use main menu for full features.[/yellow]")
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

        # IMPROVED: Ask about deletion if not specified via CLI
        from rich.prompt import Confirm
        if delete_files is False:  # Not explicitly set via CLI
            console.print("\n[bold yellow]⚠ IMPORTANT: Choose deletion behavior[/bold yellow]")
            console.print("  • [green]Yes[/green] - Physically DELETE duplicate ROM files from disk")
            console.print("  • [red]No[/red] - Only remove from gamelist.xml (files stay on disk)")
            delete_files = Confirm.ask(
                "\n[bold]Delete ROM files from disk?[/bold]",
                default=True
            )

        # Interactive resolution
        strategy = self.config.get("duplicates.strategy", "ask")
        resolver = DuplicateResolver(strategy, delete_files=delete_files)

        system_path = self.scanner.roms_base_path / system
        gamelist = GameListXML(system_path / "gamelist.xml")

        total_deleted_files = 0
        total_removed_from_xml = 0
        total_groups_processed = 0
        total_files_to_remove = 0

        for name, roms in duplicates.items():
            group = DuplicateGroup(roms)
            keep = resolver.resolve(group)

            # Collect ROMs to remove (DEDUPLICATE to avoid deleting same file twice)
            # Use path-based comparison instead of object comparison
            keep_paths = {str(rom.path) for rom in keep}
            to_remove = []
            seen_paths = set()
            for rom in roms:
                rom_path = str(rom.path)
                if rom_path not in keep_paths and rom_path not in seen_paths:
                    to_remove.append(rom)
                    seen_paths.add(rom_path)

            if not to_remove:
                # No files to remove, skip this group
                continue

            total_groups_processed += 1
            total_files_to_remove += len(to_remove)

            # Show what's being kept vs removed
            if resolver.default_action:
                console.print(f"[dim]{name} ({len(roms)} files):[/dim]")
                console.print(f"  [green]→ Keeping ({len(keep)}):[/green] {', '.join(r.filename for r in keep)}")
                if to_remove:
                    delete_action = "DELETING" if resolver.delete_files else "Removing from gamelist"
                    console.print(f"  [red]→ {delete_action} ({len(to_remove)}):[/red] {', '.join(r.filename for r in to_remove)}")

            # Remove from gamelist
            for rom in to_remove:
                if rom.relative_path in gamelist.games:
                    gamelist.remove_game(rom.relative_path)
                    total_removed_from_xml += 1

            # Delete physical files if requested
            if resolver.delete_files and to_remove:
                successful, failed = resolver.delete_rom_files(to_remove)
                total_deleted_files += successful

                if failed > 0:
                    console.print(f"  [yellow]Warning: {failed} file(s) could not be deleted[/yellow]")

        # Save gamelist
        if total_removed_from_xml > 0:
            gamelist.save(backup=True)
            console.print(f"\n[green]✓ Gamelist updated and saved[/green]")

        # Summary
        console.print(f"\n{'='*80}")
        console.print(f"[bold green]DUPLICATE RESOLUTION COMPLETE[/bold green]")
        console.print(f"{'='*80}")
        console.print(f"  Groups processed: {total_groups_processed} of {len(duplicates)}")
        console.print(f"  Files marked for removal: {total_files_to_remove}")
        console.print(f"  Removed from gamelist: {total_removed_from_xml}")
        if resolver.delete_files:
            if total_deleted_files > 0:
                console.print(f"  [bold red]✓ DELETED FILES: {total_deleted_files}[/bold red]")
            else:
                console.print(f"  [yellow]⚠ No files deleted (0 deletions)[/yellow]")
        else:
            console.print(f"  [yellow]⚠ FILES NOT DELETED - only gamelist updated[/yellow]")
        console.print(f"{'='*80}")


def create_app() -> RetroMaid:
    """Create RetroMaid instance with proper error handling for CLI"""
    try:
        return RetroMaid()
    except FileNotFoundError as e:
        console.print(f"\n[red bold]Error: ROMs path not accessible[/red bold]")
        console.print(f"\n[yellow]{e}[/yellow]")
        console.print(f"\n[cyan]To fix:[/cyan]")
        console.print(f"  1. Mount your network share (if using SMB/NFS)")
        console.print(f"  2. Or edit [bold]config.yaml[/bold] and set the correct [bold]roms_path[/bold]")
        console.print(f"\n[dim]For interactive mode with manual path entry, run: python retromaid.py[/dim]")
        raise SystemExit(1)
    except ValueError as e:
        console.print(f"\n[red bold]Configuration Error[/red bold]")
        console.print(f"\n[yellow]{e}[/yellow]")
        console.print(f"\n[cyan]To fix:[/cyan]")
        console.print(f"  Edit [bold]config.yaml[/bold] and set [bold]roms_path[/bold] to your ROMs directory")
        console.print(f"  Example: [dim]roms_path: \"/Volumes/share/roms\"[/dim]")
        raise SystemExit(1)


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
    app = create_app()

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
    app = create_app()
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
    app = create_app()
    app.find_duplicates(system, resolve=resolve, delete_files=delete)


@cli.command()
@click.option('--system', '-s', help='System to show status for')
def status(system: Optional[str]):
    """Show processing status"""
    app = create_app()

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
    app = create_app()
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
    app = create_app()

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


# Helper functions for menu system
def run_scraper(retromaid: RetroMaid, system: str):
    """Run metadata scraping for a system (called from menu)"""
    retromaid.process_system(
        system=system,
        scrape_images=True,
        scrape_videos=False,
        force_reprocess=False
    )


def run_duplicate_finder(retromaid: RetroMaid, system: str):
    """Run duplicate finder for a system (called from menu)"""
    from rich.prompt import Confirm

    duplicates = retromaid.scanner.find_duplicates(system)

    if not duplicates:
        console.print(f"\n[green]No duplicates found in {system}![/green]")
        return

    console.print(f"\n[yellow]Found {len(duplicates)} duplicate groups in {system}[/yellow]\n")

    # Show duplicates
    from rich.table import Table
    for name, roms in duplicates.items():
        table = Table(title=f"'{name}' ({len(roms)} files)", show_header=True)
        table.add_column("#", width=4)
        table.add_column("Filename")
        table.add_column("Size", justify="right")
        table.add_column("Path", style="dim")

        for i, rom in enumerate(roms, 1):
            size_mb = rom.size / (1024 * 1024)
            table.add_row(
                str(i),
                rom.filename,
                f"{size_mb:.2f} MB",
                str(rom.path.parent)
            )

        console.print(table)

    # Ask if they want to resolve
    if Confirm.ask("\n[cyan]Resolve duplicates interactively?[/cyan]"):
        from core.duplicate_detector import DuplicateResolver, DuplicateGroup
        from core.xml_manager import GameListXML

        # Ask about deletion
        console.print("\n[bold yellow]⚠ IMPORTANT: Choose deletion behavior[/bold yellow]")
        console.print("  • [green]Yes[/green] - Physically DELETE duplicate ROM files from disk")
        console.print("  • [red]No[/red] - Only remove from gamelist.xml (files stay on disk)")
        delete_files = Confirm.ask(
            "\n[bold]Delete ROM files from disk?[/bold]",
            default=True  # Changed to True for deduplication
        )

        if delete_files:
            console.print("[yellow]⚠ Files will be PERMANENTLY deleted![/yellow]")

        resolver = DuplicateResolver(strategy="ask", delete_files=delete_files)

        system_path = retromaid.scanner.roms_base_path / system
        gamelist = GameListXML(system_path / "gamelist.xml")

        # Check if gamelist has any entries
        if not gamelist.games and not delete_files:
            console.print("\n[yellow]Warning: No gamelist.xml entries found![/yellow]")
            console.print("Without file deletion, there's nothing to clean up.")
            console.print("\nOptions:")
            console.print("  1. Re-run and choose 'yes' for file deletion")
            console.print("  2. First scrape metadata, then deduplicate")
            if not Confirm.ask("\nContinue anyway?", default=False):
                return

        total_deleted_files = 0
        total_removed_from_xml = 0
        total_groups_processed = 0
        total_files_to_remove = 0

        for name, roms in duplicates.items():
            group = DuplicateGroup(roms)
            keep = resolver.resolve(group)

            # Collect ROMs to remove (DEDUPLICATE to avoid deleting same file twice)
            # Use path-based comparison instead of object comparison
            keep_paths = {str(rom.path) for rom in keep}
            to_remove = []
            seen_paths = set()
            for rom in roms:
                rom_path = str(rom.path)
                if rom_path not in keep_paths and rom_path not in seen_paths:
                    to_remove.append(rom)
                    seen_paths.add(rom_path)

            if not to_remove:
                # No files to remove, skip this group
                continue  # Nothing to remove for this group

            total_groups_processed += 1
            total_files_to_remove += len(to_remove)

            # Show what's being kept vs removed (always show for clarity)
            if resolver.default_action:
                # Using default action, show compact output
                console.print(f"[dim]{name} ({len(roms)} files):[/dim]")
                console.print(f"  [green]→ Keeping ({len(keep)}):[/green] {', '.join(r.filename for r in keep)}")
                if to_remove:
                    delete_action = "DELETING" if resolver.delete_files else "Removing from gamelist"
                    console.print(f"  [red]→ {delete_action} ({len(to_remove)}):[/red] {', '.join(r.filename for r in to_remove)}")
            else:
                # Manual choice, show detailed output
                console.print(f"\n[cyan]{name}:[/cyan]")
                for rom in keep:
                    console.print(f"  [green]✓ Keeping:[/green] {rom.filename}")
                for rom in to_remove:
                    action = "DELETING" if resolver.delete_files else "Removing from gamelist"
                    console.print(f"  [red]✗ {action}:[/red] {rom.filename}")

            # Remove from gamelist
            for rom in to_remove:
                if rom.relative_path in gamelist.games:
                    gamelist.remove_game(rom.relative_path)
                    total_removed_from_xml += 1

            # Delete physical files if requested
            if resolver.delete_files and to_remove:
                deleted, failed = resolver.delete_rom_files(to_remove)
                total_deleted_files += deleted
                if failed > 0:
                    console.print(f"  [yellow]Warning: {failed} file(s) could not be deleted[/yellow]")

        # Save gamelist
        if total_removed_from_xml > 0:
            gamelist.save(backup=True)
            console.print(f"\n[green]✓ Gamelist updated and saved[/green]")
        elif total_groups_processed > 0:
            console.print(f"\n[yellow]Note: No gamelist entries to remove (ROMs not yet scraped)[/yellow]")

        console.print(f"\n{'='*80}")
        console.print(f"[bold green]DUPLICATE RESOLUTION COMPLETE[/bold green]")
        console.print(f"{'='*80}")
        console.print(f"  Groups processed: {total_groups_processed} of {len(duplicates)}")
        console.print(f"  Files marked for removal: {total_files_to_remove}")
        console.print(f"  Removed from gamelist: {total_removed_from_xml}")

        if resolver.delete_files:
            if total_deleted_files > 0:
                console.print(f"  [bold red]✓ DELETED FILES: {total_deleted_files}[/bold red]")
            else:
                console.print(f"  [yellow]⚠ No files deleted (0 deletions)[/yellow]")

            if total_files_to_remove > total_deleted_files:
                console.print(f"  [yellow]⚠ Failed deletions: {total_files_to_remove - total_deleted_files}[/yellow]")
        else:
            console.print(f"  [yellow]⚠ FILES NOT DELETED - only gamelist updated[/yellow]")
            if total_removed_from_xml == 0:
                console.print(f"  [yellow]⚠ No changes made (ROMs not in gamelist yet)[/yellow]")

        console.print(f"{'='*80}")


def run_dos_converter(retromaid: RetroMaid):
    """Run DOS converter (called from menu)"""
    from rich.prompt import Confirm

    dos_path = retromaid.scanner.roms_base_path / "dos"
    if not dos_path.exists():
        console.print("\n[yellow]DOS system directory not found[/yellow]")
        return

    converter = DOSConverter(dos_path)
    games = converter.scan_dos_games()

    if not games:
        console.print("\n[yellow]No DOS games found[/yellow]")
        return

    unconverted = [g for g in games if not g.is_converted]

    if not unconverted:
        console.print("\n[green]All DOS games are already converted![/green]")
        return

    console.print(f"\n[yellow]Found {len(unconverted)} games to convert[/yellow]\n")

    # Show summary
    from rich.table import Table
    table = Table(title="DOS Games to Convert")
    table.add_column("Game Name", style="cyan")
    table.add_column("Type", style="magenta")

    for game in unconverted[:20]:  # Show first 20
        game_type = "ZIP" if game.path.suffix == '.zip' else "Folder"
        table.add_row(game.name, game_type)

    if len(unconverted) > 20:
        table.add_row("...", f"[dim]and {len(unconverted) - 20} more[/dim]")

    console.print(table)

    if not Confirm.ask("\n[cyan]Proceed with conversion?[/cyan]", default=True):
        return

    # Convert
    successful, failed = converter.batch_convert(
        unconverted,
        interactive=False,
        delete_zips=None,
        ask_for_defaults=True
    )

    console.print(f"\n[bold green]Conversion complete![/bold green]")
    console.print(f"Successful: {successful}")
    console.print(f"Failed: {failed}")


def main_interactive():
    """Run retroMaid in interactive menu mode"""
    from rich.panel import Panel
    from utils.menu import ASCII_ART

    # Always show ASCII art header first
    console.clear()
    console.print(ASCII_ART)

    retromaid = None
    roms_path_override = None

    while retromaid is None:
        try:
            retromaid = RetroMaid(roms_path_override=roms_path_override)

        except FileNotFoundError as e:
            # ROMs path not accessible - offer to enter manually
            console.print()
            console.print(Panel(
                f"[red bold]ROMs Path Not Accessible[/red bold]\n\n"
                f"[yellow]The configured ROMs path could not be found.[/yellow]\n\n"
                f"This usually happens when:\n"
                f"  • The network share is not mounted\n"
                f"  • The path in config.yaml is incorrect\n"
                f"  • The drive/volume is not connected\n\n"
                f"[cyan]To fix permanently:[/cyan]\n"
                f"  Edit [bold]config.yaml[/bold] and set the correct [bold]roms_path[/bold]\n\n"
                f"[dim]Current configured path: {Config('config.yaml').get('roms_path', 'Not set')}[/dim]",
                title="Configuration Error",
                border_style="red"
            ))

            console.print()
            choice = Prompt.ask(
                "[cyan]Would you like to enter the ROMs path manually?[/cyan]",
                choices=["y", "n"],
                default="n"
            )

            if choice == "y":
                roms_path_override = Prompt.ask("[cyan]Enter ROMs path[/cyan]")
                # Strip quotes that user might have copy-pasted
                roms_path_override = roms_path_override.strip().strip("'\"")
                if not Path(roms_path_override).exists():
                    console.print(f"[red]Path does not exist: {roms_path_override}[/red]")
                    roms_path_override = None
                    continue
                # Try again with the new path
                continue
            else:
                console.print("\n[dim]Please mount the network share or update config.yaml and try again.[/dim]")
                return

        except ValueError as e:
            # Config error (e.g., roms_path not set at all)
            console.print()
            console.print(Panel(
                f"[red bold]Configuration Error[/red bold]\n\n"
                f"[yellow]{e}[/yellow]\n\n"
                f"[cyan]To fix:[/cyan]\n"
                f"  1. Open [bold]config.yaml[/bold]\n"
                f"  2. Set [bold]roms_path[/bold] to your ROMs directory\n"
                f"     Example: [dim]roms_path: \"/Volumes/share/roms\"[/dim]\n"
                f"  3. Run retroMaid again",
                title="Configuration Error",
                border_style="red"
            ))
            return

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted by user[/yellow]")
            return

    # Successfully initialized - run the menu
    try:
        from utils.menu import create_main_menu
        menu = create_main_menu(retromaid)
        menu.run(is_main_menu=True)

        console.print("\n[cyan]Thank you for using retroMaid![/cyan]")
        console.print("[dim]If you found this useful, consider supporting: [link=https://buymeacoffee.com/pangana]buymeacoffee.com/pangana[/link] ☕[/dim]")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import sys

    # If no arguments provided, run interactive menu
    # Otherwise, use Click CLI for backwards compatibility
    if len(sys.argv) == 1:
        main_interactive()
    else:
        cli()
