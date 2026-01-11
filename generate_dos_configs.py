#!/usr/bin/env python3
"""
Generate DOSBox configuration files for all converted DOS games
"""
from pathlib import Path
from core.dosbox_config import DOSBoxConfigGenerator

def main():
    """Generate configs for all DOS games"""
    # Adjust path as needed
    dos_path = Path("roms/dos")

    if not dos_path.exists():
        print(f"Error: {dos_path} not found")
        return

    gen = DOSBoxConfigGenerator()

    # Find all .pc folders
    pc_folders = list(dos_path.glob("*.pc"))

    if not pc_folders:
        print("No .pc folders found")
        return

    print(f"Found {len(pc_folders)} DOS games\n")

    for pc_folder in pc_folders:
        print(f"Processing: {pc_folder.name}")

        # Create dosbox.cfg with joystick enabled
        gen.create_basic_config(
            pc_folder,
            enable_joystick=True,
            cpu_cycles="auto",
            enable_mapper=True
        )

        # Add setup option if setup.exe exists
        if gen.add_setup_option(pc_folder):
            print(f"  ✓ Created setup launcher")

        # Create controller readme
        gen.create_controller_readme(pc_folder)

        print()

    print(f"✓ Generated configs for {len(pc_folders)} games")
    print("\nCreated files in each .pc folder:")
    print("  - dosbox.cfg: DOSBox configuration")
    print("  - dosbox_setup.bat: Setup launcher (if setup.exe found)")
    print("  - CONTROLLER_SETUP.txt: Controller mapping guide")

if __name__ == '__main__':
    main()
