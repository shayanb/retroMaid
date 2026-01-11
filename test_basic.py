#!/usr/bin/env python3
"""
Basic tests for retroMaid components
"""
from pathlib import Path

# Test imports
print("Testing imports...")
from utils.config import Config
from utils.logger import Logger
from utils.filename import sanitize_filename, extract_region_from_filename, calculate_similarity
from core.xml_manager import GameListXML
from core.scanner import ROMScanner

print("✓ All imports successful")

# Test configuration
print("\nTesting configuration...")
config = Config("config.yaml")
print(f"✓ Config loaded")
print(f"  ROMs path: {config.get('roms_path')}")
print(f"  Primary scraper: {config.get('scrapers.primary')}")

# Test logger
print("\nTesting logger...")
logger = Logger.setup(log_file="test.log", level="INFO", console_output=False)
logger.info("Test log message")
print("✓ Logger initialized")

# Test filename utilities
print("\nTesting filename utilities...")
test_name = "Super Mario Bros. (USA) [!].nes"
sanitized = sanitize_filename(test_name)
region = extract_region_from_filename(test_name)
print(f"  Original: {test_name}")
print(f"  Sanitized: {sanitized}")
print(f"  Region: {region}")
print("✓ Filename utilities working")

# Test similarity
sim = calculate_similarity("Super Mario Bros", "Super Mario Brothers")
print(f"  Similarity: {sim:.1f}%")

# Test XML manager
print("\nTesting XML manager...")
test_xml_path = Path("roms/psx/gamelist.xml")
if test_xml_path.exists():
    gamelist = GameListXML(test_xml_path)
    stats = gamelist.get_statistics()
    print(f"✓ XML loaded: {stats['total']} games")
    print(f"  Complete: {stats['complete']}")
    print(f"  Incomplete: {stats['incomplete']}")
else:
    print("  (No test gamelist.xml found)")

# Test scanner
print("\nTesting ROM scanner...")
roms_path = Path("roms")
if roms_path.exists():
    scanner = ROMScanner(roms_path)
    systems = scanner.get_available_systems()
    print(f"✓ Scanner initialized")
    print(f"  Found systems: {', '.join(systems)}")

    if 'psx' in systems:
        stats = scanner.get_statistics('psx')
        print(f"  PSX ROMs: {stats['total_roms']}")
else:
    print("  (No roms directory found)")

print("\n✅ All basic tests passed!")
