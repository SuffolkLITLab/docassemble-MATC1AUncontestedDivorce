#!/usr/bin/env python3
"""
Validate YAML syntax for all docassemble interview files.

Parses all .yml files using safe_load_all (since docassemble YAMLs use --- separators)
and reports syntax errors.

Usage:
    python scripts/validate_yaml.py
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
QUESTIONS_DIR = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "data" / "questions"


def validate_yaml_files(questions_dir=None):
    """Parse all YAML files and report syntax errors."""
    if questions_dir is None:
        questions_dir = QUESTIONS_DIR

    questions_dir = Path(questions_dir)
    if not questions_dir.exists():
        print(f"ERROR: Questions directory not found: {questions_dir}")
        return []

    errors = []
    total = 0

    for yml_file in sorted(questions_dir.glob("*.yml")):
        # Skip files starting with underscore or dot (inventory files, macOS resource forks)
        if yml_file.name.startswith("_") or yml_file.name.startswith("."):
            continue

        total += 1
        try:
            with open(yml_file, encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))

            doc_count = len([d for d in docs if d is not None])
            print(f"  OK: {yml_file.name} ({doc_count} blocks)")

        except yaml.YAMLError as e:
            errors.append((yml_file.name, str(e)))
            # Extract line info if available
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                print(f"  FAIL: {yml_file.name} (line {mark.line + 1}, col {mark.column + 1})")
                print(f"        {e.problem}")
            else:
                print(f"  FAIL: {yml_file.name}")
                print(f"        {e}")

    print(f"\n  Total: {total} files, {total - len(errors)} OK, {len(errors)} errors")
    return errors


if __name__ == "__main__":
    print("=== YAML Syntax Validation ===")
    print(f"Directory: {QUESTIONS_DIR}\n")
    errors = validate_yaml_files()
    if errors:
        sys.exit(1)
