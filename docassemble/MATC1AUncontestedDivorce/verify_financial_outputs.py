#!/usr/bin/env python3
"""Run the financial-statement release verification gate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run_command(command: list[str]) -> int:
    print(f"\n$ {' '.join(command)}")
    completed = subprocess.run(command, cwd=SCRIPT_DIR.parent)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run static and live PDF-output verification for financial statements."
    )
    parser.add_argument("--server", required=True, help="Docassemble server URL")
    parser.add_argument("--api-key", required=True, help="Docassemble API key")
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR / "test_output"),
        help="Directory for downloaded PDF assertion artifacts",
    )
    args = parser.parse_args()

    checks = [
        [sys.executable, str(SCRIPT_DIR / "audit_financial_pdf_mappings.py")],
        [
            sys.executable,
            str(SCRIPT_DIR / "test_interview.py"),
            "--scenario",
            "financial_",
            "--server",
            args.server,
            "--api-key",
            args.api_key,
            "--output-dir",
            args.output_dir,
        ],
        [
            sys.executable,
            str(SCRIPT_DIR / "audit_financial_field_coverage.py"),
            "--output-dir",
            args.output_dir,
        ],
        [
            sys.executable,
            str(SCRIPT_DIR / "run_feature_scenarios.py"),
            "--server",
            args.server,
            "--api-key",
            args.api_key,
            "--output-dir",
            str(Path(args.output_dir) / "feature_scenarios"),
        ],
    ]

    for command in checks:
        result = run_command(command)
        if result != 0:
            return result

    print("\nFinancial statement verification gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
