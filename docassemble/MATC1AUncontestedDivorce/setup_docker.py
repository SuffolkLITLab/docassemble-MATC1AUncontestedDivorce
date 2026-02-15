#!/usr/bin/env python3
"""
One-time setup for the local docassemble Docker testing environment.

What this does:
  1. Checks Docker is installed and running
  2. Starts the docassemble container (first run pulls ~4GB, takes 10-15 min)
  3. Waits for the server to be ready
  4. Guides you through creating an API key
  5. Saves the API key to scripts/.env

Usage:
    python scripts/setup_docker.py              # Interactive setup
    python scripts/setup_docker.py --api-key KEY  # Non-interactive (provide key)
    python scripts/setup_docker.py --status     # Check if server is running
    python scripts/setup_docker.py --stop       # Stop the server
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_FILE = SCRIPT_DIR / ".env"
DEFAULT_SERVER = "http://localhost:5050"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check_docker():
    """Verify Docker is installed and the daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"{RED}Docker is not installed.{RESET}")
            print("Install Docker Desktop: https://www.docker.com/products/docker-desktop")
            return False
    except FileNotFoundError:
        print(f"{RED}Docker is not installed.{RESET}")
        print("Install Docker Desktop: https://www.docker.com/products/docker-desktop")
        return False

    result = subprocess.run(
        ["docker", "info"], capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        print(f"{RED}Docker daemon is not running.{RESET}")
        print("Start Docker Desktop and try again.")
        return False

    print(f"{GREEN}Docker is installed and running.{RESET}")
    return True


def start_container():
    """Start the docassemble container via docker compose."""
    print(f"\n{BOLD}Starting docassemble container...{RESET}")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{RED}Failed to start container:{RESET}")
        print(result.stderr)
        return False

    print(result.stdout)
    return True


def stop_container():
    """Stop the docassemble container."""
    print(f"\n{BOLD}Stopping docassemble container...{RESET}")
    result = subprocess.run(
        ["docker", "compose", "down"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"{RED}Failed to stop container:{RESET}")
        print(result.stderr)
        return False

    print(f"{GREEN}Container stopped.{RESET}")
    return True


def wait_for_server(server=DEFAULT_SERVER, timeout=600):
    """Poll the server until it responds or timeout is reached."""
    print(f"\n{BOLD}Waiting for docassemble server to be ready...{RESET}")
    print(f"  (First run takes 10-15 minutes while the image initializes)")
    print(f"  Server URL: {server}")

    start = time.time()
    last_status = ""
    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        try:
            r = requests.get(f"{server}/health_check", timeout=5)
            if r.status_code == 200:
                print(f"\n{GREEN}Server is ready! ({elapsed}s){RESET}")
                return True
            status = f"HTTP {r.status_code}"
        except requests.ConnectionError:
            status = "connecting..."
        except requests.Timeout:
            status = "timeout..."
        except Exception as e:
            status = str(e)[:50]

        if status != last_status:
            print(f"  [{elapsed:>3}s] {status}")
            last_status = status
        else:
            # Print a dot to show progress
            print(".", end="", flush=True)

        time.sleep(5)

    print(f"\n{RED}Server did not become ready within {timeout}s.{RESET}")
    print(f"Check logs: docker compose logs -f")
    return False


def check_server_status(server=DEFAULT_SERVER):
    """Quick check if server is up."""
    try:
        r = requests.get(f"{server}/health_check", timeout=5)
        if r.status_code == 200:
            print(f"{GREEN}Server is running at {server}{RESET}")
            return True
    except Exception:
        pass
    print(f"{YELLOW}Server is not responding at {server}{RESET}")
    return False


def save_env(server, api_key):
    """Save configuration to .env file."""
    content = f"DA_SERVER={server}\nDA_API_KEY={api_key}\n"
    ENV_FILE.write_text(content)
    print(f"\n{GREEN}Saved configuration to {ENV_FILE}{RESET}")


def load_env():
    """Load existing .env if present."""
    if not ENV_FILE.exists():
        return None, None
    server = None
    key = None
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("DA_SERVER="):
            server = line.split("=", 1)[1]
        elif line.startswith("DA_API_KEY="):
            key = line.split("=", 1)[1]
    return server, key


def verify_api_key(server, api_key):
    """Test that the API key works."""
    try:
        r = requests.get(
            f"{server}/api/user",
            params={"key": api_key},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            email = data.get("email", "unknown")
            print(f"{GREEN}API key is valid (user: {email}){RESET}")
            return True
        else:
            print(f"{RED}API key rejected (HTTP {r.status_code}){RESET}")
            return False
    except Exception as e:
        print(f"{RED}Could not verify API key: {e}{RESET}")
        return False


def interactive_api_key_setup(server):
    """Guide the user through creating an API key."""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  API Key Setup{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"""
To run interview tests, you need a docassemble API key.

  1. Open {server} in your browser
  2. If this is your first visit, create an admin account
  3. Log in, then go to:
     Profile → Other Settings → API Keys → Add
  4. Give it a name like "testing" and click Save
  5. Copy the API key that appears

""")
    api_key = input("Paste your API key here (or 'skip' to do this later): ").strip()

    if api_key.lower() == "skip" or not api_key:
        print(f"\n{YELLOW}Skipped API key setup.{RESET}")
        print(f"Run this again later, or manually create scripts/.env with:")
        print(f"  DA_SERVER={server}")
        print(f"  DA_API_KEY=your_key_here")
        save_env(server, "")
        return False

    if verify_api_key(server, api_key):
        save_env(server, api_key)
        return True
    else:
        print(f"\n{YELLOW}Key didn't work. Saving anyway — you can update scripts/.env later.{RESET}")
        save_env(server, api_key)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup local docassemble Docker environment for testing"
    )
    parser.add_argument(
        "--api-key", help="Provide API key non-interactively"
    )
    parser.add_argument(
        "--server", default=DEFAULT_SERVER,
        help=f"Server URL (default: {DEFAULT_SERVER})"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Check if server is running and exit"
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="Stop the docassemble container"
    )
    parser.add_argument(
        "--no-wait", action="store_true",
        help="Start container without waiting for it to be ready"
    )
    args = parser.parse_args()

    if args.status:
        existing_server, existing_key = load_env()
        server = existing_server or args.server
        ok = check_server_status(server)
        if existing_key:
            verify_api_key(server, existing_key)
        sys.exit(0 if ok else 1)

    if args.stop:
        stop_container()
        sys.exit(0)

    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Docassemble Local Testing Setup{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # Step 1: Check Docker
    if not check_docker():
        sys.exit(1)

    # Step 2: Start container
    if not start_container():
        sys.exit(1)

    if args.no_wait:
        print(f"\n{YELLOW}Container started. Run --status later to check.{RESET}")
        sys.exit(0)

    # Step 3: Wait for server
    if not wait_for_server(args.server):
        sys.exit(1)

    # Step 4: API key
    if args.api_key:
        if verify_api_key(args.server, args.api_key):
            save_env(args.server, args.api_key)
        else:
            print(f"{RED}Provided API key is invalid.{RESET}")
            sys.exit(1)
    else:
        interactive_api_key_setup(args.server)

    # Done
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{GREEN}Setup complete!{RESET}")
    print(f"  Server: {args.server}")
    print(f"  Config: {ENV_FILE}")
    print(f"\nNext steps:")
    print(f"  python scripts/deploy_to_docker.py   # Upload your package")
    print(f"  python scripts/test_interview.py      # Run interview tests")


if __name__ == "__main__":
    main()
