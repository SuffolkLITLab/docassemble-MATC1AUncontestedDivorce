#!/usr/bin/env python3
"""
Master local test runner for the docassemble-MATC1AUncontestedDivorce package.

Runs all validation scripts in sequence and reports overall results.

Usage:
    python scripts/test_local.py                    # Run all static checks
    python scripts/test_local.py --quick            # Skip visual PDF fill (faster)
    python scripts/test_local.py --with-docker      # Include interview runtime tests
    python scripts/test_local.py --quick --with-docker  # Quick + Docker tests
"""

import sys
import time
import subprocess
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
    import argparse
    parser = argparse.ArgumentParser(description="Run all local validation checks")
    parser.add_argument("--quick", action="store_true",
                        help="Skip visual PDF fill test (faster)")
    parser.add_argument("--with-docker", action="store_true",
                        help="Include interview runtime tests (requires Docker)")
    args = parser.parse_args()

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  MATC1A Uncontested Divorce — Local Test Suite{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    results = []

    # Step 1: YAML syntax validation
    ok, t = run_step(
        "Step 1: YAML Syntax Validation",
        SCRIPT_DIR / "validate_yaml.py",
    )
    results.append(("YAML Syntax", ok, t))

    # Step 2: Interview logic analysis (deep static analysis)
    ok, t = run_step(
        "Step 2: Interview Logic Analysis",
        SCRIPT_DIR / "validate_interview_logic.py",
    )
    results.append(("Interview Logic", ok, t))

    # Step 3: PDF ↔ YAML field cross-reference
    ok, t = run_step(
        "Step 3: PDF ↔ YAML Field Cross-Reference",
        SCRIPT_DIR / "validate_pdf_fields.py",
    )
    results.append(("PDF↔YAML Fields", ok, t))

    # Step 4: Visual PDF fill (optional)
    if not args.quick:
        ok, t = run_step(
            "Step 4: Test PDF Fill (sample data)",
            SCRIPT_DIR / "test_fill_pdf.py",
        )
        results.append(("PDF Fill Test", ok, t))
    else:
        print(f"\n{YELLOW}Skipping PDF fill test (--quick mode){RESET}")

    # Step 5: Package build (dry-run — just verify it builds)
    ok, t = run_step(
        f"Step {'4' if args.quick else '5'}: Package Build Test",
        SCRIPT_DIR / "build_package.py",
    )
    results.append(("Package Build", ok, t))

    # Step 6: Interview runtime tests (optional, requires server)
    if args.with_docker:
        test_interview = SCRIPT_DIR / "test_interview.py"
        env_file = SCRIPT_DIR / ".env"
        if not test_interview.exists():
            print(f"\n{YELLOW}Skipping Docker tests: test_interview.py not found{RESET}")
        elif not env_file.exists():
            print(f"\n{YELLOW}Skipping Docker tests: scripts/.env not configured{RESET}")
            print(f"  Run: python scripts/setup_docker.py")
        else:
            step_num = len(results) + 1
            ok, t = run_step(
                f"Step {step_num}: Interview Runtime Tests (Docker)",
                test_interview,
            )
            results.append(("Interview Tests", ok, t))

    # Clean up the test zip
    for zf in PROJECT_ROOT.glob("docassemble-MATC1AUncontestedDivorce-*-nogit.zip"):
        zf.unlink()
        print(f"  Cleaned up: {zf.name}")

    # Summary
    total_time = sum(t for _, _, t in results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)

    print(f"\n{'=' * 60}")
    print(f"{BOLD}  SUMMARY{RESET}")
    print(f"{'=' * 60}")
    for name, ok, t in results:
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name} ({t:.1f}s)")

    print(f"\n  Total: {passed + failed} checks, {GREEN}{passed} passed{RESET}", end="")
    if failed:
        print(f", {RED}{failed} failed{RESET}", end="")
    print(f"  ({total_time:.1f}s)")

    if failed:
        print(f"\n{RED}Some checks failed. See details above.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}All checks passed!{RESET}")


if __name__ == "__main__":
    main()
