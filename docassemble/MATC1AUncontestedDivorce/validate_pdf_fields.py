#!/usr/bin/env python3
"""
Cross-reference PDF AcroForm fields against YAML attachment blocks.

Checks that:
1. Every field name in YAML attachment blocks exists in the corresponding PDF
2. Reports PDF fields that have no YAML mapping (potentially unmapped)
3. Reports YAML references to PDFs that don't exist

Usage:
    python scripts/validate_pdf_fields.py
"""

import re
import sys
from pathlib import Path

try:
    import yaml
    import pikepdf
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Run: pip install pyyaml pikepdf")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
QUESTIONS_DIR = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "data" / "questions"
TEMPLATES_DIR = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "data" / "templates"


def get_pdf_field_names(pdf_path):
    """Extract all AcroForm field names from a PDF."""
    pdf = pikepdf.open(str(pdf_path))
    if "/AcroForm" not in pdf.Root:
        pdf.close()
        return set()

    names = set()
    fields = pdf.Root["/AcroForm"].get("/Fields", [])
    for field in fields:
        t = field.get("/T")
        if t:
            names.add(str(t))
    pdf.close()
    return names


def get_yaml_field_refs(yml_path):
    """Extract field names from attachment blocks in a YAML file.

    Returns dict of {pdf_filename: set_of_field_names}
    """
    refs = {}
    try:
        with open(yml_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
    except (yaml.YAMLError, UnicodeDecodeError):
        return refs

    for doc in docs:
        if not doc or not isinstance(doc, dict):
            continue

        # Look for attachment blocks
        if "attachment" not in doc:
            continue

        att = doc["attachment"]
        if not isinstance(att, dict):
            continue

        pdf_file = att.get("pdf template file", "")
        fields = att.get("fields", [])

        if not pdf_file or not fields:
            continue

        field_names = set()
        for field in fields:
            if isinstance(field, dict):
                field_names.update(field.keys())

        if pdf_file in refs:
            refs[pdf_file].update(field_names)
        else:
            refs[pdf_file] = field_names

    return refs


def cross_reference(questions_dir=None, templates_dir=None):
    """Check that YAML-referenced fields exist in PDFs and vice versa."""
    if questions_dir is None:
        questions_dir = QUESTIONS_DIR
    if templates_dir is None:
        templates_dir = TEMPLATES_DIR

    questions_dir = Path(questions_dir)
    templates_dir = Path(templates_dir)

    issues = []

    # Collect all YAML references across all files
    all_refs = {}  # {pdf_name: {yaml_file: set_of_field_names}}

    for yml_file in sorted(questions_dir.glob("*.yml")):
        if yml_file.name.startswith("_") or yml_file.name.startswith("."):
            continue

        yaml_refs = get_yaml_field_refs(yml_file)
        for pdf_name, field_names in yaml_refs.items():
            if pdf_name not in all_refs:
                all_refs[pdf_name] = {}
            all_refs[pdf_name][yml_file.name] = field_names

    if not all_refs:
        print("  No attachment blocks found in any YAML files.")
        return issues

    # Check each referenced PDF
    for pdf_name, yaml_sources in sorted(all_refs.items()):
        pdf_path = templates_dir / pdf_name

        # Aggregate all YAML field names for this PDF
        all_yaml_fields = set()
        for field_set in yaml_sources.values():
            all_yaml_fields.update(field_set)

        source_files = ", ".join(yaml_sources.keys())

        if not pdf_path.exists():
            msg = f"MISSING PDF: {pdf_name} (referenced in {source_files})"
            print(f"  {msg}")
            issues.append(msg)
            continue

        pdf_fields = get_pdf_field_names(pdf_path)

        if not pdf_fields:
            msg = f"NO FIELDS: {pdf_name} has no AcroForm fields (referenced in {source_files})"
            print(f"  {msg}")
            issues.append(msg)
            continue

        # Fields in YAML but not in PDF
        missing_from_pdf = all_yaml_fields - pdf_fields
        # Fields in PDF but not in YAML
        unmapped_in_pdf = pdf_fields - all_yaml_fields

        if not missing_from_pdf and not unmapped_in_pdf:
            print(f"  OK: {pdf_name} <-> {source_files} ({len(all_yaml_fields)} fields match)")
        else:
            if missing_from_pdf:
                msg = f"YAML->PDF MISMATCH: {pdf_name} missing {len(missing_from_pdf)} field(s) from PDF"
                print(f"  {msg}")
                for f in sorted(missing_from_pdf):
                    print(f"    - {f}")
                issues.append(msg)

            if unmapped_in_pdf:
                msg = f"PDF->YAML INFO: {pdf_name} has {len(unmapped_in_pdf)} field(s) not referenced in YAML"
                print(f"  {msg}")
                for f in sorted(unmapped_in_pdf):
                    print(f"    - {f}")
                # This is informational, not an error

    # Also check for PDFs in templates dir that have fields but no YAML references
    print("\n  --- Template PDFs without YAML references ---")
    for pdf_file in sorted(templates_dir.glob("*.pdf")):
        if pdf_file.name.startswith("."):
            continue
        if pdf_file.name not in all_refs:
            fields = get_pdf_field_names(pdf_file)
            if fields:
                print(f"  INFO: {pdf_file.name} ({len(fields)} fields, no YAML attachment block)")
            else:
                print(f"  INFO: {pdf_file.name} (no AcroForm fields)")

    return issues


if __name__ == "__main__":
    print("=== PDF <-> YAML Field Cross-Reference ===")
    print(f"Questions: {QUESTIONS_DIR}")
    print(f"Templates: {TEMPLATES_DIR}\n")
    issues = cross_reference()
    if issues:
        print(f"\n  {len(issues)} issue(s) found")
        sys.exit(1)
    else:
        print(f"\n  All checks passed")
