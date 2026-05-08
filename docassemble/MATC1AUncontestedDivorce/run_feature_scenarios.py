#!/usr/bin/env python3
"""Run existing docassemble .feature scenario tables through the API harness."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from test_interview import (
    BOLD,
    GREEN,
    RED,
    RESET,
    DocassembleClient,
    load_env,
    run_scenario,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / "docassemble/MATC1AUncontestedDivorce/data/sources"
DEFAULT_INTERVIEW = "docassemble.MATC1AUncontestedDivorce:financial_statement.yml"


def parse_value(raw):
    value = raw.strip()
    if value == "True":
        return True
    if value == "False":
        return False
    if value == "":
        return ""
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def add_variable(variables, key, value):
    match = re.fullmatch(r"(.+)\['([^']+)'\]", key)
    if match:
        base, dict_key = match.groups()
        existing = variables.setdefault(base, {})
        if isinstance(existing, dict):
            existing[dict_key] = value
            return
    variables[key] = value


def parse_feature(path):
    scenarios = []
    current = None
    current_interview = DEFAULT_INTERVIEW
    in_table = False

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if line.startswith("Scenario:"):
            if current:
                scenarios.append(current)
            name = line.split(":", 1)[1].strip()
            current = {
                "_file": f"{path.stem}: {name}",
                "name": f"{path.stem}: {name}",
                "description": f"Imported from {path.name}",
                "interview": current_interview,
                "max_steps": 340,
                "variables": {
                    "al_intro_screen": True,
                    "fs_intro": True,
                },
            }
            in_table = False
            continue

        if current is None:
            continue

        interview_match = re.search(r'I start the interview at "([^"]+)"', line)
        if interview_match:
            interview_name = interview_match.group(1)
            current["interview"] = (
                interview_name
                if ":" in interview_name
                else f"docassemble.MATC1AUncontestedDivorce:{interview_name}"
            )
            continue

        if line.startswith("| var | value |"):
            in_table = True
            continue

        if in_table and line.startswith("|"):
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) >= 2:
                add_variable(current["variables"], parts[0], parse_value(parts[1]))
            continue

        if in_table and line:
            in_table = False

    if current:
        scenarios.append(current)
    return scenarios


def load_feature_scenarios(filter_name=None):
    scenarios = []
    for path in sorted(SOURCES_DIR.glob("financial_statement*.feature")):
        scenarios.extend(parse_feature(path))
    if filter_name:
        needle = filter_name.lower()
        scenarios = [
            scenario
            for scenario in scenarios
            if needle in scenario["name"].lower() or needle in scenario["_file"].lower()
        ]
    return scenarios


def main():
    parser = argparse.ArgumentParser(
        description="Run existing financial statement .feature scenarios through the API harness"
    )
    parser.add_argument("--scenario", help="Run only scenarios matching this text")
    parser.add_argument("--server", help="Override server URL from .env")
    parser.add_argument("--api-key", help="Override API key from .env")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "scripts/test_output/feature_scenarios"),
        help="Directory for feature scenario artifacts",
    )
    args = parser.parse_args()

    scenarios = load_feature_scenarios(args.scenario)
    if not scenarios:
        print(f"{RED}No feature scenarios found.{RESET}")
        return 1

    server, api_key = load_env(quiet=bool(args.server and args.api_key))
    server = args.server or server
    api_key = args.api_key or api_key
    client = DocassembleClient(server, api_key)
    if not server or not api_key:
        print(f"{RED}Server URL or API key not configured.{RESET}")
        return 1
    if not client.health_check():
        print(f"{RED}Cannot reach docassemble server at {server}{RESET}")
        return 1

    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  Financial Statement Feature Scenarios{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"  Server: {server}")
    print(f"  Scenarios: {len(scenarios)}")

    passed = 0
    failed = 0
    for scenario in scenarios:
        ok, steps, message, details = run_scenario(
            client,
            scenario,
            output_dir=Path(args.output_dir),
        )
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {status} {scenario['name']} ({steps} steps) — {message}")
        if not ok:
            failed += 1
            for detail in details[:8]:
                print(f"    {detail}")
        else:
            passed += 1

    print(f"\n  Total: {len(scenarios)} scenarios, {GREEN}{passed} passed{RESET}", end="")
    if failed:
        print(f", {RED}{failed} failed{RESET}")
        return 1
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
