#!/usr/bin/env python3
"""Test script to verify svg_to_jpg functionality"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "skills" / "ppt-master" / "scripts"))

# Test imports
try:
    from PIL import Image
    print("✓ PIL (Pillow) is available")
except ImportError:
    print("✗ PIL (Pillow) is NOT available")

try:
    import cairosvg
    cairosvg.svg2png
    print("✓ CairoSVG is available")
except (ImportError, OSError, AttributeError) as e:
    print(f"✗ CairoSVG is NOT available: {e}")

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    print("✓ svglib is available")
except ImportError as e:
    print(f"✗ svglib is NOT available: {e}")

import shutil
if shutil.which('inkscape'):
    print("✓ Inkscape is available")
else:
    print("✗ Inkscape is NOT available in PATH")

if shutil.which('rsvg-convert'):
    print("✓ rsvg-convert is available")
else:
    print("✗ rsvg-convert is NOT available in PATH")

# Check output directory name
print("\n--- Configuration Check ---")
print("Output directory will be: svg_output_images/")

# List project structure
project_path = Path("projects/我是中国人_ppt169_20260430")
if project_path.exists():
    print(f"\n--- Project Structure ({project_path.name}) ---")
    for item in sorted(project_path.iterdir()):
        if item.is_dir():
            print(f"  📁 {item.name}/")
        else:
            print(f"  📄 {item.name}")
