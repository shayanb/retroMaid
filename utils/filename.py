"""
Filename sanitization and normalization utilities
"""
import re
from pathlib import Path
from typing import Dict, Optional, Tuple


# Common region tags in ROM filenames
REGION_TAGS = {
    "USA": "us",
    "US": "us",
    "U": "us",
    "Europe": "eu",
    "EUR": "eu",
    "E": "eu",
    "Japan": "jp",
    "JPN": "jp",
    "J": "jp",
    "World": "wor",
    "W": "wor",
}

# Common language tags
LANGUAGE_TAGS = {
    "En": "en",
    "English": "en",
    "Fr": "fr",
    "French": "fr",
    "De": "de",
    "German": "de",
    "Es": "es",
    "Spanish": "es",
    "It": "it",
    "Italian": "it",
    "Ja": "ja",
    "Japanese": "ja",
}

# Patterns to remove from filenames
REMOVE_PATTERNS = [
    r'\[.*?\]',  # Remove [square brackets] content
    r'\(.*?Rev.*?\)',  # Remove (Rev X) version markers
    r'\(.*?Beta.*?\)',  # Remove beta markers
    r'\(.*?Proto.*?\)',  # Remove prototype markers
    r'\(.*?Unl.*?\)',  # Remove unlicensed markers
    r'\(.*?Hack.*?\)',  # Remove hack markers
    r'\(.*?Pirate.*?\)',  # Remove pirate markers
    r'\(.*?Trainer.*?\)',  # Remove trainer markers
    r'\(.*?\+\d+.*?\)',  # Remove (+3 trainer) style markers
    r'!',  # Remove exclamation marks
    r'\+',  # Remove plus signs
    r'\[',  # Remove leftover open brackets
    r'\]',  # Remove leftover close brackets
]


def sanitize_filename(filename: str, for_matching: bool = True) -> str:
    """
    Sanitize filename for better matching with online databases

    Args:
        filename: Original filename
        for_matching: If True, apply aggressive sanitization for matching

    Returns:
        Sanitized filename
    """
    # Remove file extension
    name = Path(filename).stem

    if for_matching:
        # Remove common tags and markers
        for pattern in REMOVE_PATTERNS:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        # Remove disc/CD numbers but keep the base name
        name = re.sub(r'\(Disc\s*\d+\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\(CD\s*\d+\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Disc\s*\d+', '', name, flags=re.IGNORECASE)

        # Remove version numbers (but not in middle of words)
        name = re.sub(r'\s+v?\d+\.\d+', '', name)
        name = re.sub(r'v?\d+\.\d+\s+', '', name)

        # Remove common suffixes like _prv, _demo, etc.
        name = re.sub(r'[_\-](prv|demo|preview|final|remastered)', '', name, flags=re.IGNORECASE)

        # Remove ALL remaining parentheses content (region tags, etc.)
        # This catches (E), (U), (JUE), (USA), etc. that weren't caught above
        name = re.sub(r'\([^)]*\)', '', name)

        # Normalize & to 'and' for better matching
        name = re.sub(r'\s*&\s*', ' and ', name)

    # Replace underscores, hyphens, and dots with spaces
    # This is important for C64 games like "night_shift" or "nodes.of.yesod"
    name = re.sub(r'[_\-]', ' ', name)

    # Replace dots with spaces, but be careful with version numbers
    # Only replace dots that are clearly word separators (surrounded by letters)
    name = re.sub(r'([a-zA-Z])\.([a-zA-Z])', r'\1 \2', name)

    # Remove multiple spaces
    name = re.sub(r'\s+', ' ', name)

    # Remove leading/trailing special characters
    name = name.strip(' ._-')

    return name.strip()


def extract_region_from_filename(filename: str) -> Optional[str]:
    """
    Extract region code from filename

    Args:
        filename: ROM filename

    Returns:
        Region code (e.g., "us", "eu", "jp") or None
    """
    # Look for region in parentheses
    matches = re.findall(r'\((.*?)\)', filename)

    for match in matches:
        # Check each part of the match (in case of multiple tags like "(USA, Europe)")
        parts = [part.strip() for part in match.split(',')]

        for part in parts:
            # Check against known region tags
            for tag, code in REGION_TAGS.items():
                if part.upper() == tag.upper():
                    return code

    return None


def extract_language_from_filename(filename: str) -> Optional[str]:
    """
    Extract language code from filename

    Args:
        filename: ROM filename

    Returns:
        Language code (e.g., "en", "fr") or None
    """
    matches = re.findall(r'\((.*?)\)', filename)

    for match in matches:
        parts = [part.strip() for part in match.split(',')]

        for part in parts:
            for tag, code in LANGUAGE_TAGS.items():
                if part.lower() == tag.lower():
                    return code

    return None


def normalize_game_name(name: str) -> str:
    """
    Normalize game name for comparison

    Args:
        name: Game name

    Returns:
        Normalized name (lowercase, no special chars)
    """
    # Convert to lowercase
    normalized = name.lower()

    # Remove special characters but keep alphanumeric and spaces
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

    # Remove multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()


def calculate_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two game names using simple ratio

    Args:
        name1: First game name
        name2: Second game name

    Returns:
        Similarity score (0-100)
    """
    # Normalize both names
    n1 = normalize_game_name(name1)
    n2 = normalize_game_name(name2)

    if n1 == n2:
        return 100.0

    # Simple substring matching
    if n1 in n2 or n2 in n1:
        shorter = min(len(n1), len(n2))
        longer = max(len(n1), len(n2))
        return (shorter / longer) * 100

    # Count matching words
    words1 = set(n1.split())
    words2 = set(n2.split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    # Jaccard similarity
    return (len(intersection) / len(union)) * 100


def get_base_name_and_disc(filename: str) -> Tuple[str, Optional[int]]:
    """
    Extract base game name and disc number from multi-disc games

    Args:
        filename: ROM filename

    Returns:
        Tuple of (base_name, disc_number)
    """
    # Check for disc number patterns
    disc_patterns = [
        r'\(Disc\s*(\d+)\)',
        r'\(CD\s*(\d+)\)',
        r'Disc\s*(\d+)',
        r'CD\s*(\d+)',
    ]

    disc_number = None
    base_name = filename

    for pattern in disc_patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            disc_number = int(match.group(1))
            # Remove the disc number from the name
            base_name = re.sub(pattern, '', base_name, flags=re.IGNORECASE)
            break

    # Clean up the base name
    base_name = sanitize_filename(base_name, for_matching=True)

    return base_name, disc_number
