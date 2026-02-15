#!/usr/bin/env python3
"""
Build and deploy the docassemble package to the local Docker server.

Workflow:
  1. Build the package zip (calls build_package.py)
  2. Upload via the docassemble REST API
  3. Wait for installation to complete
  4. Report success/failure

Usage:
    python scripts/deploy_to_docker.py          # Build + deploy
    python scripts/deploy_to_docker.py --skip-build  # Deploy existing zip only
"""

import argparse
import glob
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_FILE = SCRIPT_DIR / ".env"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_env():
    """Load server URL and API key from .env file."""
    if not ENV_FILE.exists():
        print(f"{RED}No .env file found at {ENV_FILE}{RESET}")
        print(f"Run: python scripts/setup_docker.py")
        sys.exit(1)

    config = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()

    server = config.get("DA_SERVER")
    api_key = config.get("DA_API_KEY")

    if not server or not api_key:
        print(f"{RED}Missing DA_SERVER or DA_API_KEY in {ENV_FILE}{RESET}")
        print(f"Run: python scripts/setup_docker.py")
        sys.exit(1)

    return server, api_key


def build_package():
    """Build the package zip. Returns path to the zip file."""
    print(f"\n{BOLD}Step 1: Building package...{RESET}")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "build_package.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"{RED}Build failed:{RESET}")
        print(result.stdout)
        print(result.stderr)
        return None

    print(result.stdout)

    # Find the most recent zip
    zips = sorted(
        PROJECT_ROOT.glob("docassemble-MATC1AUncontestedDivorce-*-nogit.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not zips:
        print(f"{RED}No zip file found after build.{RESET}")
        return None

    return zips[0]


def find_existing_zip():
    """Find the most recent existing zip."""
    zips = sorted(
        PROJECT_ROOT.glob("docassemble-MATC1AUncontestedDivorce-*-nogit.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not zips:
        print(f"{RED}No existing zip file found. Run without --skip-build.{RESET}")
        return None
    return zips[0]


def upload_package(server, api_key, zip_path):
    """Upload the package zip to the docassemble server."""
    print(f"\n{BOLD}Step 2: Uploading {zip_path.name}...{RESET}")
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  File: {zip_path.name} ({size_mb:.1f} MB)")

    try:
        with open(zip_path, "rb") as f:
            r = requests.post(
                f"{server}/api/package",
                data={"key": api_key},
                files={"zip": (zip_path.name, f, "application/zip")},
                timeout=120,
            )

        if r.status_code == 200:
            data = r.json()
            task_id = data.get("task_id")
            print(f"  {GREEN}Upload accepted.{RESET} Task ID: {task_id}")
            return task_id
        else:
            print(f"  {RED}Upload failed (HTTP {r.status_code}){RESET}")
            try:
                print(f"  Response: {r.json()}")
            except Exception:
                print(f"  Response: {r.text[:500]}")
            return None

    except requests.ConnectionError:
        print(f"  {RED}Cannot connect to {server}{RESET}")
        print(f"  Is the Docker container running? Try: docker compose up -d")
        return None
    except Exception as e:
        print(f"  {RED}Upload error: {e}{RESET}")
        return None


def wait_for_install(server, api_key, task_id=None, timeout=120):
    """Wait for the package installation to complete."""
    print(f"\n{BOLD}Step 3: Waiting for installation...{RESET}")

    start = time.time()
    while time.time() - start < timeout:
        try:
            params = {"key": api_key}
            if task_id:
                params["task_id"] = task_id

            r = requests.get(
                f"{server}/api/package_update_status",
                params=params,
                timeout=10,
            )

            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "unknown")
                if status == "completed" or data.get("ok", False):
                    elapsed = int(time.time() - start)
                    print(f"  {GREEN}Installation complete ({elapsed}s){RESET}")
                    return True
                elif status == "failed" or data.get("error"):
                    print(f"  {RED}Installation failed: {data}{RESET}")
                    return False
                else:
                    elapsed = int(time.time() - start)
                    print(f"  [{elapsed:>3}s] Status: {status}")
        except Exception as e:
            elapsed = int(time.time() - start)
            print(f"  [{elapsed:>3}s] Checking... ({e})")

        time.sleep(3)

    # Timeout — but the package might have installed anyway
    print(f"  {YELLOW}Timed out waiting for install status.{RESET}")
    print(f"  The package may still have installed. Checking server...")

    # Try to verify the package exists
    try:
        r = requests.get(
            f"{server}/api/package",
            params={"key": api_key},
            timeout=10,
        )
        if r.status_code == 200:
            packages = r.json()
            for pkg in packages:
                if "MATC1AUncontestedDivorce" in pkg.get("name", ""):
                    print(f"  {GREEN}Package found on server: {pkg.get('name')}{RESET}")
                    return True
    except Exception:
        pass

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Build and deploy package to local docassemble Docker"
    )
    parser.add_argument(
        "--skip-build", action="store_true",
        help="Skip building, deploy the most recent existing zip"
    )
    parser.add_argument(
        "--server", help="Override server URL from .env"
    )
    args = parser.parse_args()

    server, api_key = load_env()
    if args.server:
        server = args.server

    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Deploy to Local Docassemble{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"  Server: {server}")

    # Build
    if args.skip_build:
        zip_path = find_existing_zip()
    else:
        zip_path = build_package()

    if not zip_path:
        sys.exit(1)

    # Upload
    task_id = upload_package(server, api_key, zip_path)
    if task_id is None:
        sys.exit(1)

    # Wait
    ok = wait_for_install(server, api_key, task_id)

    if ok:
        print(f"\n{GREEN}{'=' * 60}{RESET}")
        print(f"{GREEN}  Package deployed successfully!{RESET}")
        print(f"{GREEN}{'=' * 60}{RESET}")
        print(f"\nNext: python scripts/test_interview.py")
    else:
        print(f"\n{RED}Deployment may have failed. Check server logs.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
