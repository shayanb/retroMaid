"""
State and checkpoint management for resume functionality
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()


@dataclass
class ProcessingState:
    """Represents the state of processing"""
    system: str
    total_games: int = 0
    processed_games: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0

    # List of processed ROM paths
    processed_paths: Set[str] = field(default_factory=set)

    # Errors encountered
    errors: Dict[str, str] = field(default_factory=dict)

    # Timestamp
    started_at: Optional[str] = None
    last_updated: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert set to list for JSON
        data['processed_paths'] = list(self.processed_paths)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessingState':
        """Create from dictionary"""
        # Convert list back to set
        if 'processed_paths' in data:
            data['processed_paths'] = set(data['processed_paths'])
        return cls(**data)


class StateManager:
    """Manages processing state and checkpoints"""

    def __init__(self, checkpoint_file: str = ".retromaid_checkpoint.json"):
        """
        Initialize state manager

        Args:
            checkpoint_file: Path to checkpoint file
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.states: Dict[str, ProcessingState] = {}
        self.save_frequency = 5  # Save every N games

        # Load existing state
        self.load()

    def get_or_create_state(self, system: str) -> ProcessingState:
        """
        Get existing state for a system or create new one

        Args:
            system: System name

        Returns:
            ProcessingState object
        """
        if system not in self.states:
            self.states[system] = ProcessingState(
                system=system,
                started_at=datetime.now().isoformat()
            )

        return self.states[system]

    def mark_processed(
        self,
        system: str,
        rom_path: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Mark a ROM as processed

        Args:
            system: System name
            rom_path: ROM relative path
            success: Whether processing was successful
            error: Error message if failed
        """
        state = self.get_or_create_state(system)

        state.processed_paths.add(rom_path)
        state.processed_games += 1

        if success:
            state.successful += 1
        else:
            state.failed += 1
            if error:
                state.errors[rom_path] = error

        state.last_updated = datetime.now().isoformat()

        # Auto-save based on frequency
        if state.processed_games % self.save_frequency == 0:
            self.save()

    def mark_skipped(self, system: str, rom_path: str) -> None:
        """
        Mark a ROM as skipped

        Args:
            system: System name
            rom_path: ROM relative path
        """
        state = self.get_or_create_state(system)
        state.processed_paths.add(rom_path)
        state.skipped += 1
        state.last_updated = datetime.now().isoformat()

    def is_processed(self, system: str, rom_path: str) -> bool:
        """
        Check if a ROM has been processed

        Args:
            system: System name
            rom_path: ROM relative path

        Returns:
            True if already processed
        """
        if system not in self.states:
            return False

        return rom_path in self.states[system].processed_paths

    def get_unprocessed_count(self, system: str, total: int) -> int:
        """
        Get count of unprocessed games

        Args:
            system: System name
            total: Total games count

        Returns:
            Number of unprocessed games
        """
        if system not in self.states:
            return total

        return total - len(self.states[system].processed_paths)

    def save(self) -> None:
        """Save state to checkpoint file"""
        try:
            data = {
                system: state.to_dict()
                for system, state in self.states.items()
            }

            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved checkpoint to {self.checkpoint_file}")

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load(self) -> bool:
        """
        Load state from checkpoint file

        Returns:
            True if loaded successfully
        """
        if not self.checkpoint_file.exists():
            return False

        try:
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)

            self.states = {
                system: ProcessingState.from_dict(state_data)
                for system, state_data in data.items()
            }

            logger.info(f"Loaded checkpoint from {self.checkpoint_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False

    def clear(self, system: Optional[str] = None) -> None:
        """
        Clear state for a system or all systems

        Args:
            system: System name or None for all
        """
        if system:
            if system in self.states:
                del self.states[system]
        else:
            self.states = {}

        self.save()

    def get_summary(self, system: str) -> Optional[Dict]:
        """
        Get processing summary for a system

        Args:
            system: System name

        Returns:
            Summary dictionary or None
        """
        if system not in self.states:
            return None

        state = self.states[system]

        return {
            'total': state.total_games,
            'processed': state.processed_games,
            'successful': state.successful,
            'failed': state.failed,
            'skipped': state.skipped,
            'remaining': state.total_games - state.processed_games,
            'started_at': state.started_at,
            'last_updated': state.last_updated,
        }

    def has_errors(self, system: str) -> bool:
        """Check if there are any errors for a system"""
        if system not in self.states:
            return False

        return len(self.states[system].errors) > 0

    def get_errors(self, system: str) -> Dict[str, str]:
        """Get errors for a system"""
        if system not in self.states:
            return {}

        return self.states[system].errors.copy()

    def delete_checkpoint(self) -> None:
        """Delete the checkpoint file"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info("Checkpoint file deleted")
