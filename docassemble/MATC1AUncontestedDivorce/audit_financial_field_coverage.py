#!/usr/bin/env python3
"""Verify exhaustive runtime coverage for financial-statement PDF fields."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
QUESTION_FILE = ROOT / "docassemble/MATC1AUncontestedDivorce/data/questions/financial_statement.yml"
TEMPLATE_DIR = ROOT / "docassemble/MATC1AUncontestedDivorce/data/templates"
MANIFEST_FILE = SCRIPT_DIR / "financial_field_coverage_manifest.json"

PDFS = (
    "financial_statement_short.pdf",
    "financial_statement_long.pdf",
    "financial_statement_schedule_a.pdf",
    "financial_statement_schedule_b.pdf",
)

BLANK_REASONS = {
    "financial_statement_short.pdf": {
        "attorney_address_city": "The interview collects attorney address as one free-text line, not separate city/state/zip fields.",
        "attorney_address_state": "The interview collects attorney address as one free-text line, not separate city/state/zip fields.",
        "attorney_address_zip": "The interview collects attorney address as one free-text line, not separate city/state/zip fields.",
    },
    "financial_statement_long.pdf": {
        "notary_signature": "The interview records notary county/name/date/commission but does not collect a notary signature.",
        "attorney_city": "The interview collects attorney address as one free-text line, not separate city/state/zip fields.",
        "attorney_state": "The interview collects attorney address as one free-text line, not separate city/state/zip fields.",
        "attorney_zip": "The interview collects attorney address as one free-text line, not separate city/state/zip fields.",
    },
}


def pdf_field_values(path: Path) -> dict[str, str]:
    fields = PdfReader(str(path)).get_fields() or {}
    return {
        name: "" if field.get("/V") is None else str(field.get("/V")).lstrip("/")
        for name, field in fields.items()
    }


def template_fields() -> dict[str, set[str]]:
    return {pdf: set(pdf_field_values(TEMPLATE_DIR / pdf)) for pdf in PDFS}


def parse_mappings() -> dict[str, dict[str, str]]:
    current_pdf = None
    mappings: dict[str, dict[str, str]] = {}
    pdf_re = re.compile(r"^\s*pdf template file:\s*(\S+)\s*$")
    field_re = re.compile(r'^\s*-\s+"([^"]+)":\s*(.*)$')
    for line in QUESTION_FILE.read_text().splitlines():
        pdf_match = pdf_re.match(line)
        if pdf_match:
            current_pdf = pdf_match.group(1)
            continue
        if current_pdf not in PDFS:
            continue
        field_match = field_re.match(line)
        if field_match:
            field_name, expression = field_match.groups()
            mappings.setdefault(current_pdf, {})[field_name] = expression.strip()
    return mappings


def load_runtime_values(output_dir: Path) -> dict[str, dict[str, dict[str, str]]]:
    runtime: dict[str, dict[str, dict[str, str]]] = {}
    for scenario_dir in sorted(output_dir.iterdir() if output_dir.exists() else []):
        if not scenario_dir.is_dir():
            continue
        scenario = scenario_dir.name
        for pdf_path in sorted(scenario_dir.glob("*.pdf")):
            if pdf_path.name in PDFS:
                runtime.setdefault(scenario, {})[pdf_path.name] = pdf_field_values(pdf_path)
    return runtime


def generate_manifest(output_dir: Path) -> dict[str, object]:
    fields = template_fields()
    runtime = load_runtime_values(output_dir)
    manifest: dict[str, object] = {"version": 1, "pdfs": {}}
    for pdf in PDFS:
        pdf_manifest = {}
        for field in sorted(fields[pdf]):
            found = None
            for scenario, pdfs in sorted(runtime.items()):
                value = pdfs.get(pdf, {}).get(field, "")
                if str(value).strip():
                    found = (scenario, value)
                    break
            if found:
                scenario, value = found
                pdf_manifest[field] = {
                    "classification": "asserted",
                    "scenario": scenario,
                    "source": "runtime_pdf_field_value",
                    "value_type": "acroform_text",
                    "expected": value,
                }
            elif field in BLANK_REASONS.get(pdf, {}):
                pdf_manifest[field] = {
                    "classification": "intentionally_blank",
                    "reason": BLANK_REASONS[pdf][field],
                }
            else:
                pdf_manifest[field] = {
                    "classification": "unsupported",
                    "reason": "No current runtime scenario produces a value for this mapped field.",
                }
        manifest["pdfs"][pdf] = pdf_manifest
    return manifest


def write_report(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "financial_field_coverage_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True)
    )
    lines = ["# Financial Field Coverage Report", ""]
    for pdf, counts in report["counts"].items():
        lines.append(f"## {pdf}")
        lines.append("")
        for key, value in counts.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    if report["failures"]:
        lines.append("## Failures")
        lines.extend(f"- {failure}" for failure in report["failures"])
        lines.append("")
    (output_dir / "financial_field_coverage_report.md").write_text("\n".join(lines))


def verify_manifest(manifest: dict[str, object], output_dir: Path) -> tuple[bool, dict[str, object]]:
    fields = template_fields()
    mappings = parse_mappings()
    runtime = load_runtime_values(output_dir)
    failures: list[str] = []
    counts: dict[str, dict[str, int]] = {}

    manifest_pdfs = manifest.get("pdfs", {})
    if not isinstance(manifest_pdfs, dict):
        failures.append("manifest: missing pdfs object")
        manifest_pdfs = {}

    for pdf in PDFS:
        actual_fields = fields[pdf]
        mapped_fields = set(mappings.get(pdf, {}))
        pdf_manifest = manifest_pdfs.get(pdf, {})
        if not isinstance(pdf_manifest, dict):
            failures.append(f"{pdf}: manifest entry must be an object")
            pdf_manifest = {}

        missing = sorted(actual_fields - set(pdf_manifest))
        extra = sorted(set(pdf_manifest) - actual_fields)
        stale_mappings = sorted(mapped_fields - actual_fields)
        unmapped = sorted(actual_fields - mapped_fields)
        if missing:
            failures.append(f"{pdf}: fields missing from manifest: {', '.join(missing)}")
        if extra:
            failures.append(f"{pdf}: manifest fields not in PDF: {', '.join(extra)}")
        if unmapped:
            failures.append(f"{pdf}: unmapped PDF fields: {', '.join(unmapped)}")
        if stale_mappings:
            failures.append(f"{pdf}: stale mapped fields: {', '.join(stale_mappings)}")

        counter: Counter[str] = Counter()
        unknown = 0
        for field in sorted(actual_fields):
            entry = pdf_manifest.get(field, {})
            classification = entry.get("classification") if isinstance(entry, dict) else None
            if classification not in {
                "asserted",
                "computed",
                "constant",
                "intentionally_blank",
                "unsupported",
            }:
                unknown += 1
                failures.append(f"{pdf}.{field}: unknown or invalid classification")
                continue
            counter[classification] += 1
            if classification in {"asserted", "computed", "constant"}:
                scenario = entry.get("scenario")
                expected = entry.get("expected")
                if not scenario or "value_type" not in entry or "source" not in entry:
                    failures.append(f"{pdf}.{field}: asserted field lacks scenario/source/value_type")
                    continue
                actual = runtime.get(str(scenario), {}).get(pdf, {}).get(field)
                if actual is None:
                    failures.append(f"{pdf}.{field}: {scenario}/{pdf} was not downloaded")
                elif actual != str(expected):
                    failures.append(
                        f"{pdf}.{field}: expected {expected!r} from {scenario}, got {actual!r}"
                    )
            else:
                reason = entry.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    failures.append(f"{pdf}.{field}: {classification} field lacks reason")

        counts[pdf] = {
            "total": len(actual_fields),
            "asserted": counter["asserted"],
            "computed": counter["computed"],
            "constant": counter["constant"],
            "intentionally_blank": counter["intentionally_blank"],
            "unsupported": counter["unsupported"],
            "unknown": unknown,
        }

    report = {"counts": counts, "failures": failures}
    write_report(report, output_dir)
    return not failures, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit financial PDF field runtime coverage.")
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR / "test_output"),
        help="Directory containing downloaded runtime PDFs",
    )
    parser.add_argument(
        "--manifest",
        default=str(MANIFEST_FILE),
        help="Financial field coverage manifest path",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate the manifest from downloaded runtime PDFs",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest)

    if args.generate:
        manifest = generate_manifest(output_dir)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"Wrote {manifest_path}")
        return 0

    if not manifest_path.exists():
        print(f"Missing manifest: {manifest_path}")
        return 1
    manifest = json.loads(manifest_path.read_text())
    ok, report = verify_manifest(manifest, output_dir)
    for pdf, counts in report["counts"].items():
        print(
            f"{pdf}: total={counts['total']} asserted={counts['asserted']} "
            f"blank={counts['intentionally_blank']} unsupported={counts['unsupported']} "
            f"unknown={counts['unknown']}"
        )
    if not ok:
        print("\nFAIL")
        for failure in report["failures"]:
            print(f"- {failure}")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
