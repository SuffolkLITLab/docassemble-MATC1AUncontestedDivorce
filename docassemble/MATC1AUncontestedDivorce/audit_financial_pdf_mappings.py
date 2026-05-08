#!/usr/bin/env python3
"""Audit financial-statement PDF field mappings.

Checks that every AcroForm field in the financial PDFs is mapped in
financial_statement.yml, and flags unexpected literal blank mappings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
QUESTION_FILE = ROOT / "docassemble/MATC1AUncontestedDivorce/data/questions/financial_statement.yml"
TEMPLATE_DIR = ROOT / "docassemble/MATC1AUncontestedDivorce/data/templates"

PDFS = {
    "financial_statement_short.pdf",
    "financial_statement_long.pdf",
    "financial_statement_schedule_a.pdf",
    "financial_statement_schedule_b.pdf",
}

# These fields are intentionally blank because the interview does not collect
# separately structured values for them.
ALLOWED_BLANKS = {
    "attorney_address_city",
    "attorney_address_state",
    "attorney_address_zip",
    "notary_signature",
    "attorney_city",
    "attorney_state",
    "attorney_zip",
}


def pdf_fields(path: Path) -> set[str]:
    reader = PdfReader(str(path))
    fields = reader.get_fields() or {}
    return set(fields)


def parse_mappings() -> dict[str, dict[str, object]]:
    current_pdf = None
    mappings: dict[str, dict[str, object]] = {}
    pdf_re = re.compile(r"^\s*pdf template file:\s*(\S+)\s*$")
    field_re = re.compile(r'^\s*-\s+"([^"]+)":\s*(.*)$')

    for line_number, line in enumerate(QUESTION_FILE.read_text().splitlines(), start=1):
        pdf_match = pdf_re.match(line)
        if pdf_match:
            current_pdf = pdf_match.group(1)
            continue
        if current_pdf not in PDFS:
            continue
        field_match = field_re.match(line)
        if not field_match:
            continue
        field_name, expression = field_match.groups()
        mappings.setdefault(current_pdf, {})[field_name] = {
            "line": line_number,
            "expression": expression.strip(),
        }

    return mappings


def main() -> int:
    mappings = parse_mappings()
    failures: list[str] = []

    for pdf_name in sorted(PDFS):
        actual_fields = pdf_fields(TEMPLATE_DIR / pdf_name)
        mapped_fields = set(mappings.get(pdf_name, {}))

        missing = sorted(actual_fields - mapped_fields)
        extra = sorted(mapped_fields - actual_fields)
        blank = sorted(
            field
            for field, info in mappings.get(pdf_name, {}).items()
            if info["expression"] == '""' and field not in ALLOWED_BLANKS
        )

        print(f"{pdf_name}: {len(actual_fields)} PDF fields, {len(mapped_fields)} mapped")
        if missing:
            failures.append(f"{pdf_name}: unmapped PDF fields: {', '.join(missing)}")
        if extra:
            failures.append(f"{pdf_name}: mapped fields not in PDF: {', '.join(extra)}")
        if blank:
            blank_details = ", ".join(
                f"{field} line {mappings[pdf_name][field]['line']}" for field in blank
            )
            failures.append(f"{pdf_name}: unexpected literal blank mappings: {blank_details}")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
