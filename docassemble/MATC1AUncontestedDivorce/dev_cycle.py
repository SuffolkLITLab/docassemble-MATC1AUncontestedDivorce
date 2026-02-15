#!/usr/bin/env python3
"""
Full development iteration loop: validate → build → deploy → test.

One command to run the entire pipeline from editing YAML to seeing if
the interview works end-to-end.

Usage:
    python scripts/dev_cycle.py          # Full cycle
    python scripts/dev_cycle.py --quick  # Skip static checks, just deploy + test
    python scripts/dev_cycle.py --no-deploy  # Skip deploy (use already-deployed pkg)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_step(label, script_path, extra_args=None):
    """Run a script and return (success, duration_seconds)."""
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'=' * 60}")
    print(f"{BOLD}{label}{RESET}")
    print(f"{'=' * 60}")

    start = time.time()
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    duration = time.time() - start

    success = result.returncode == 0
    status = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
    print(f"\n  Result: {status} ({duration:.1f}s)")
    return success, duration


def main():
    parser = argparse.ArgumentParser(
        description="Full development cycle: validate → build → deploy → test"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Skip static validation, just deploy and test"
    )
    parser.add_argument(
        "--no-deploy", action="store_true",
        help="Skip deploy, just run interview tests against existing package"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Pass --verbose to interview tests"
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Development Cycle — Validate → Build → Deploy → Test{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    results = []
    all_ok = True

    # Phase 1: Static validation (optional with --quick)
    if not args.quick:
        ok, t = run_step(
            "Phase 1a: YAML Syntax Validation",
            SCRIPT_DIR / "validate_yaml.py",
        )
        results.append(("YAML Syntax", ok, t))
        if not ok:
            all_ok = False

        ok, t = run_step(
            "Phase 1b: PDF ↔ YAML Field Cross-Reference",
            SCRIPT_DIR / "validate_pdf_fields.py",
        )
        results.append(("PDF↔YAML Fields", ok, t))
        if not ok:
            all_ok = False

        ok, t = run_step(
            "Phase 1c: Field Overlap & Coverage Checks",
            SCRIPT_DIR / "validate_field_overlaps.py",
        )
        results.append(("Field Overlaps", ok, t))
        if not ok:
            all_ok = False

        if not all_ok:
            print(f"\n{RED}Static validation failed. Fix errors before deploying.{RESET}")
            _print_summary(results)
            sys.exit(1)

    # Phase 2: Deploy to Docker (optional with --no-deploy)
    if not args.no_deploy:
        ok, t = run_step(
            "Phase 2: Build & Deploy to Docker",
            SCRIPT_DIR / "deploy_to_docker.py",
        )
        results.append(("Deploy", ok, t))
        if not ok:
            print(f"\n{RED}Deploy failed. Is Docker running?{RESET}")
            print(f"  Start: docker compose up -d")
            print(f"  Setup: python scripts/setup_docker.py")
            _print_summary(results)
            sys.exit(1)

    # Phase 3: Interview runtime tests
    test_args = ["--verbose"] if args.verbose else []
    ok, t = run_step(
        "Phase 3: Interview Runtime Tests",
        SCRIPT_DIR / "test_interview.py",
        extra_args=test_args,
    )
    results.append(("Interview Tests", ok, t))
    if not ok:
        all_ok = False

    # Summary
    _print_summary(results)

    # Clean up build artifacts
    for zf in PROJECT_ROOT.glob("docassemble-MATC1AUncontestedDivorce-*-nogit.zip"):
        zf.unlink()

    sys.exit(0 if all_ok else 1)


def _print_summary(results):
    """Print final summary table."""
    total_time = sum(t for _, _, t in results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)

    print(f"\n{'=' * 60}")
    print(f"{BOLD}  DEV CYCLE SUMMARY{RESET}")
    print(f"{'=' * 60}")
    for name, ok, t in results:
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name} ({t:.1f}s)")

    print(f"\n  Total: {passed + failed} steps, "
          f"{GREEN}{passed} passed{RESET}", end="")
    if failed:
        print(f", {RED}{failed} failed{RESET}", end="")
    print(f"  ({total_time:.1f}s)")

    if failed:
        print(f"\n{RED}Some steps failed. See details above.{RESET}")
    else:
        print(f"\n{GREEN}All steps passed! Your changes are working.{RESET}")


if __name__ == "__main__":
    main()
