#!/usr/bin/env python3
"""
PPT Master - SVG to JPG Conversion Tool

Converts SVG files to JPG images with Chinese font support using Playwright browser rendering.
This step runs between finalize_svg.py and svg_to_pptx.py.

Usage:
    python3 scripts/svg_to_jpg.py <project_directory>
    python3 scripts/svg_to_jpg.py <project_directory> --quality 100
    python3 scripts/svg_to_jpg.py <project_directory> --scale 3

Examples:
    python3 scripts/svg_to_jpg.py projects/my_project
    python3 scripts/svg_to_jpg.py projects/my_project --quality 100 --scale 3
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import Optional, Tuple

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# PIL is required for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[ERROR] Pillow is required. Please install: pip install Pillow")
    sys.exit(1)


# System font paths for Chinese support
CHINESE_FONT_PATHS = [
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # Windows
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialuni.ttf",
]


def find_chinese_font() -> Optional[str]:
    """Find an available font that supports Chinese characters."""
    for font_path in CHINESE_FONT_PATHS:
        if os.path.exists(font_path):
            return font_path
    return None


def safe_print(text: str) -> None:
    """Print text while tolerating encoding limits."""
    try:
        print(text)
    except UnicodeEncodeError:
        text = text.encode('ascii', 'replace').decode('ascii')
        print(text)


def get_svg_dimensions(svg_path: Path) -> Tuple[int, int]:
    """Extract width and height from SVG."""
    import xml.etree.ElementTree as ET
    import re

    try:
        tree = ET.parse(str(svg_path))
        root = tree.getroot()

        width_attr = root.get('width', '')
        height_attr = root.get('height', '')

        width_match = re.match(r'(\d+(?:\.\d+)?)', width_attr)
        height_match = re.match(r'(\d+(?:\.\d+)?)', height_attr)

        if width_match and height_match:
            return int(float(width_match.group(1))), int(float(height_match.group(1)))

        viewbox = root.get('viewBox', '')
        if viewbox:
            parts = viewbox.replace(',', ' ').split()
            if len(parts) >= 4:
                return int(float(parts[2])), int(float(parts[3]))
    except Exception:
        pass

    return 1280, 720


def convert_svg_to_jpg(svg_path: Path, jpg_path: Path, width: int, height: int, quality: int = 100, scale: int = 3) -> bool:
    """Convert SVG to JPG using Playwright browser rendering with high DPI support."""
    if not PLAYWRIGHT_AVAILABLE:
        safe_print("[ERROR] Playwright is not available. Please install: pip install playwright")
        return False

    try:
        import io

        # Read SVG content
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # Create HTML wrapper with high DPI scaling
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                svg {{
                    display: block;
                    width: {width}px;
                    height: {height}px;
                }}
            </style>
        </head>
        <body>
            {svg_content}
        </body>
        </html>
        '''

        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Create page with device scale factor for high DPI
            page = browser.new_page(
                viewport={'width': width, 'height': height},
                device_scale_factor=scale
            )
            page.set_content(html_content)
            page.wait_for_timeout(800)  # Wait for rendering

            # Take screenshot at high resolution
            screenshot = page.screenshot(
                type='png',
                full_page=False,
                scale='device'  # Use device scale for high DPI
            )
            browser.close()

        img = Image.open(io.BytesIO(screenshot))

        # Resize to target dimensions with high quality downsampling
        if img.size != (width, height):
            img = img.resize((width, height), Image.LANCZOS)

        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1] if len(img.split()) > 1 else None)
                img = background
            else:
                img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Save with high quality and subsampling for better color accuracy
        img.save(jpg_path, 'JPEG', quality=quality, optimize=True, subsampling=0)
        return True

    except Exception as e:
        safe_print(f"   [WARN] Conversion failed: {e}")

    return False


def convert_project_svgs(project_dir: Path, quality: int = 100, dpi: int = 150,
                         source: str = 'final', verbose: bool = True, scale: int = 3) -> bool:
    """Convert all SVG files in a project to JPG."""

    svg_dir = project_dir / ('svg_final' if source == 'final' else 'svg_output')
    jpg_output_dir = project_dir / 'svg_output_images'

    if not svg_dir.exists():
        safe_print(f"[ERROR] Source directory not found: {svg_dir}")
        return False

    svg_files = sorted(svg_dir.glob('*.svg'))
    if not svg_files:
        safe_print(f"[ERROR] No SVG files found in {svg_dir}")
        return False

    if verbose:
        print()
        safe_print(f"[DIR] Project: {project_dir.name}")
        safe_print(f"[FILE] {len(svg_files)} SVG file(s) to convert")
        safe_print(f"[INFO] Output directory: svg_output_images/")
        safe_print(f"[INFO] Quality: {quality}, DPI: {dpi}, Scale: {scale}x")

        chinese_font = find_chinese_font()
        if chinese_font:
            safe_print(f"[INFO] Chinese font detected: {Path(chinese_font).name}")
        print()

    # Create output directory
    if jpg_output_dir.exists():
        shutil.rmtree(jpg_output_dir)
    jpg_output_dir.mkdir(parents=True)

    # Convert each file
    success_count = 0
    failed_files = []

    for i, svg_file in enumerate(svg_files, 1):
        if verbose:
            safe_print(f"[{i}/{len(svg_files)}] {svg_file.name}")

        width, height = get_svg_dimensions(svg_file)
        jpg_filename = svg_file.stem + '.jpg'
        jpg_path = jpg_output_dir / jpg_filename

        if verbose:
            safe_print(f"   Converting {svg_file.name} ({width}x{height})...")

        if convert_svg_to_jpg(svg_file, jpg_path, width, height, quality, scale):
            if verbose:
                safe_print(f"   [OK] {jpg_filename}")
            success_count += 1
        else:
            failed_files.append(svg_file.name)

    # Summary
    if verbose:
        print()
        safe_print(f"[OK] Conversion complete: {success_count}/{len(svg_files)} files")
        if failed_files:
            safe_print(f"[ERROR] Failed files: {', '.join(failed_files)}")
        print()
        print("Next steps:")
        print(f"  python scripts/svg_to_pptx.py \"{project_dir}\" -s final")

    return success_count == len(svg_files)


def main():
    parser = argparse.ArgumentParser(
        description='PPT Master - SVG to JPG Conversion Tool (Playwright)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Dependencies:
  pip install playwright Pillow
  python3 -m playwright install chromium

Examples:
  %(prog)s projects/my_project                    # Default: quality=100, scale=3
  %(prog)s projects/my_project --quality 95       # Lower quality
  %(prog)s projects/my_project --scale 2          # Lower resolution
  %(prog)s projects/my_project -s output          # Convert from svg_output/
        '''
    )

    parser.add_argument('project_dir', type=Path, help='Project directory path')
    parser.add_argument('--quality', type=int, default=100, help='JPEG quality (1-100, default: 100)')
    parser.add_argument('--dpi', type=int, default=150, help='DPI for rendering (default: 150)')
    parser.add_argument('--scale', type=int, default=3, help='Rendering scale factor for high-res output (default: 3)')
    parser.add_argument('-s', '--source', choices=['final', 'output'], default='final',
                        help='Source directory: final (svg_final/) or output (svg_output/)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')

    args = parser.parse_args()

    if not args.project_dir.exists():
        safe_print(f"[ERROR] Project directory does not exist: {args.project_dir}")
        sys.exit(1)

    if args.quality < 1 or args.quality > 100:
        safe_print("[ERROR] Quality must be between 1 and 100")
        sys.exit(1)

    if args.scale < 1 or args.scale > 4:
        safe_print("[ERROR] Scale must be between 1 and 4")
        sys.exit(1)

    success = convert_project_svgs(
        args.project_dir,
        quality=args.quality,
        dpi=args.dpi,
        source=args.source,
        verbose=not args.quiet,
        scale=args.scale,
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
