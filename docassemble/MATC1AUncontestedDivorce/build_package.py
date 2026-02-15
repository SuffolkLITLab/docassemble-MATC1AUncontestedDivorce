#!/usr/bin/env python3
"""
Build a docassemble package zip for upload to a docassemble server/playground.

Usage:
    python scripts/build_package.py             # Build with current version
    python scripts/build_package.py --bump      # Increment version and build
    python scripts/build_package.py --version   # Show current version
"""

import os
import re
import sys
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SETUP_PY = PROJECT_ROOT / "setup.py"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
DIST_DIR = PROJECT_ROOT  # Zips go in project root (matches existing convention)

# Files/dirs to exclude from the zip
EXCLUDES = {
    ".git", "__pycache__", "*.pyc", ".gitignore", "*.egg-info",
    "venv", ".venv", ".vscode", "build", "dist", ".pytest_cache",
    "scripts", ".DS_Store", "._*", "_*", "node_modules",
}

# Only include these top-level items in the zip
INCLUDE_TOPLEVEL = {
    "setup.py", "setup.cfg", "pyproject.toml", "README.md", "LICENSE",
    "MANIFEST.in", "docassemble",
}


def get_version():
    """Read current version from setup.py."""
    with open(SETUP_PY) as f:
        match = re.search(r"version='([^']+)'", f.read())
        return match.group(1) if match else "0.0"


def bump_version(current):
    """Increment minor version: 1.24 -> 1.25"""
    parts = current.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def update_version_in_files(new_version):
    """Update version in setup.py, pyproject.toml, and __init__.py."""
    # setup.py
    with open(SETUP_PY) as f:
        content = f.read()
    content = re.sub(r"version='[^']+'", f"version='{new_version}'", content)
    with open(SETUP_PY, "w") as f:
        f.write(content)

    # pyproject.toml
    if PYPROJECT.exists():
        with open(PYPROJECT) as f:
            content = f.read()
        content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', content)
        with open(PYPROJECT, "w") as f:
            f.write(content)

    # __init__.py
    init_py = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "__init__.py"
    if init_py.exists():
        with open(init_py) as f:
            content = f.read()
        content = re.sub(
            r"__version__\s*=\s*'[^']+'",
            f"__version__ = '{new_version}'",
            content,
        )
        with open(init_py, "w") as f:
            f.write(content)

    print(f"  Updated version to {new_version}")


def should_exclude(path):
    """Check if a file/directory should be excluded from the zip."""
    name = path.name
    for pattern in EXCLUDES:
        if pattern.startswith("*."):
            if name.endswith(pattern[1:]):
                return True
        elif pattern == "_*":
            if name.startswith("_") and not name.startswith("__"):
                return True
        elif pattern.startswith("._"):
            if name.startswith("._"):
                return True
        elif name == pattern:
            return True
    return False


def build_zip(version):
    """Create the docassemble package zip."""
    zip_name = f"docassemble-MATC1AUncontestedDivorce-{version}-nogit.zip"
    zip_path = DIST_DIR / zip_name

    # The prefix inside the zip (matches docassemble expectations)
    prefix = f"docassemble-MATC1AUncontestedDivorce-{version}/"

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(PROJECT_ROOT.iterdir()):
            if item.name not in INCLUDE_TOPLEVEL:
                continue

            if item.is_file():
                arcname = prefix + item.name
                zf.write(item, arcname)
                file_count += 1
            elif item.is_dir():
                for root, dirs, files in os.walk(item):
                    # Filter out excluded directories in-place
                    dirs[:] = [d for d in dirs if not should_exclude(Path(d))]
                    for fname in sorted(files):
                        fpath = Path(root) / fname
                        if should_exclude(fpath):
                            continue
                        arcname = prefix + str(fpath.relative_to(PROJECT_ROOT))
                        zf.write(fpath, arcname)
                        file_count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  Built: {zip_path.name}")
    print(f"  Version: {version}")
    print(f"  Files: {file_count}")
    print(f"  Size: {size_mb:.1f} MB")
    return zip_path


def main():
    parser = argparse.ArgumentParser(description="Build docassemble package zip")
    parser.add_argument("--bump", action="store_true",
                        help="Increment version before building")
    parser.add_argument("--version", action="store_true",
                        help="Show current version and exit")
    args = parser.parse_args()

    current_version = get_version()

    if args.version:
        print(f"Current version: {current_version}")
        return

    print("=== Docassemble Package Builder ===")
    print(f"  Project: docassemble-MATC1AUncontestedDivorce")
    print(f"  Current version: {current_version}")

    if args.bump:
        new_version = bump_version(current_version)
        update_version_in_files(new_version)
        version = new_version
    else:
        version = current_version

    build_zip(version)
    print("\nDone. Upload the zip to your docassemble server's Package Management.")


if __name__ == "__main__":
    main()
