#!/usr/bin/env python3
"""
Inject AcroForm fields into flat (non-fillable) court PDF forms.

Reads field definitions from JSON files and uses pikepdf to add text fields
and checkboxes to copies of the original court PDFs.

Usage:
    python scripts/add_pdf_fields.py --form short
    python scripts/add_pdf_fields.py --all
    python scripts/add_pdf_fields.py --form short --dry-run

Output PDFs are saved to docassemble/MATC1AUncontestedDivorce/data/templates/
"""

import json
import sys
import argparse
from pathlib import Path

try:
    import pikepdf
    from pikepdf import Dictionary, Name, Array, String
except ImportError:
    print("ERROR: pikepdf not installed. Run: pip install pikepdf")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
REF_DIR = PROJECT_ROOT.parent / "docassembly-documentation" / "docs" / "MATC1AUncontestedDivorce-reference"
TEMPLATES_DIR = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "data" / "templates"
FIELD_DEFS_DIR = SCRIPT_DIR / "field_definitions"

# Map form names to source PDFs and output filenames
FORM_CONFIG = {
    "short": {
        "source": REF_DIR / "Financial statement (short form) (CJD-301S)_01-20-2026_1340.pdf",
        "output": TEMPLATES_DIR / "financial_statement_short.pdf",
        "fields": FIELD_DEFS_DIR / "short_form_fields.json",
    },
    "long": {
        "source": REF_DIR / "Financial statement (long form) (CJD-301L)_01-20-2026_1341.pdf",
        "output": TEMPLATES_DIR / "financial_statement_long.pdf",
        "fields": FIELD_DEFS_DIR / "long_form_fields.json",
    },
    "schedule_a": {
        "source": REF_DIR / "Financial Statement Schedule A (CJ-D 301)_01-20-2026_1341.pdf",
        "output": TEMPLATES_DIR / "financial_statement_schedule_a.pdf",
        "fields": FIELD_DEFS_DIR / "schedule_a_fields.json",
    },
    "schedule_b": {
        "source": REF_DIR / "Financial Statement Schedule B (CJ-D 301)_01-20-2026_1341.pdf",
        "output": TEMPLATES_DIR / "financial_statement_schedule_b.pdf",
        "fields": FIELD_DEFS_DIR / "schedule_b_fields.json",
    },
}


def ensure_acroform(pdf):
    """Ensure the PDF has an AcroForm dictionary with a Fields array."""
    if "/AcroForm" not in pdf.Root:
        helv_font = Dictionary()
        helv_font["/Type"] = Name.Font
        helv_font["/Subtype"] = Name("/Type1")
        helv_font["/BaseFont"] = Name("/Helvetica")

        font_dict = Dictionary()
        font_dict["/Helv"] = helv_font

        dr = Dictionary()
        dr["/Font"] = font_dict

        acroform = Dictionary()
        acroform["/Fields"] = Array()
        acroform["/DA"] = String("/Helv 8 Tf 0 g")
        acroform["/DR"] = dr
        acroform["/NeedAppearances"] = pikepdf.Object.parse(b"true")

        pdf.Root["/AcroForm"] = pdf.make_indirect(acroform)
    else:
        acroform = pdf.Root["/AcroForm"]
        if "/Fields" not in acroform:
            acroform["/Fields"] = Array()
        # Always set NeedAppearances for reliable rendering
        acroform["/NeedAppearances"] = pikepdf.Object.parse(b"true")
        # Ensure font resources exist
        if "/DR" not in acroform:
            helv_font = Dictionary()
            helv_font["/Type"] = Name.Font
            helv_font["/Subtype"] = Name("/Type1")
            helv_font["/BaseFont"] = Name("/Helvetica")

            font_dict = Dictionary()
            font_dict["/Helv"] = helv_font

            dr = Dictionary()
            dr["/Font"] = font_dict
            acroform["/DR"] = dr

    return pdf.Root["/AcroForm"]


def add_text_field(pdf, acroform, page, field_name, rect, font_size=8):
    """Add a text field to a PDF page.

    Args:
        pdf: pikepdf.Pdf object
        acroform: AcroForm dictionary
        page: pikepdf page object
        field_name: string name for the field
        rect: [x0, y0, x1, y1] bounding box in PDF points
        font_size: font size in points
    """
    bs = Dictionary()
    bs["/W"] = pikepdf.Object.parse(b"0.5")
    bs["/S"] = Name("/S")

    mk = Dictionary()
    mk["/BC"] = Array([0.7, 0.7, 0.7])

    field = Dictionary()
    field["/Type"] = Name.Annot
    field["/Subtype"] = Name.Widget
    field["/FT"] = Name.Tx
    field["/T"] = String(field_name)
    field["/Rect"] = Array([rect[0], rect[1], rect[2], rect[3]])
    field["/F"] = 4
    field["/Ff"] = 0
    field["/DA"] = String(f"/Helv {font_size} Tf 0 g")
    field["/P"] = page
    field["/BS"] = bs
    field["/MK"] = mk

    field = pdf.make_indirect(field)

    # Add to page annotations
    if Name.Annots not in page:
        page[Name.Annots] = Array()
    page[Name.Annots].append(field)

    # Add to AcroForm fields
    acroform["/Fields"].append(field)
    return field


def add_checkbox(pdf, acroform, page, field_name, rect):
    """Add a checkbox field to a PDF page.

    Args:
        pdf: pikepdf.Pdf object
        acroform: AcroForm dictionary
        page: pikepdf page object
        field_name: string name for the field
        rect: [x0, y0, x1, y1] bounding box
    """
    mk = Dictionary()
    mk["/CA"] = String("4")

    yes_stream = pikepdf.Stream(pdf, b"")
    ap_n = Dictionary()
    ap_n["/Yes"] = yes_stream
    ap = Dictionary()
    ap["/N"] = ap_n

    field = Dictionary()
    field["/Type"] = Name.Annot
    field["/Subtype"] = Name.Widget
    field["/FT"] = Name("/Btn")
    field["/T"] = String(field_name)
    field["/Rect"] = Array([rect[0], rect[1], rect[2], rect[3]])
    field["/F"] = 4
    field["/AS"] = Name("/Off")
    field["/V"] = Name("/Off")
    field["/DA"] = String("/ZaDb 0 Tf 0 g")
    field["/P"] = page
    field["/MK"] = mk
    field["/AP"] = ap

    field = pdf.make_indirect(field)

    # Add to page annotations
    if Name.Annots not in page:
        page[Name.Annots] = Array()
    page[Name.Annots].append(field)

    # Add to AcroForm fields
    acroform["/Fields"].append(field)
    return field


def process_form(form_name, dry_run=False):
    """Process a single form: read field defs, inject fields, save PDF."""
    config = FORM_CONFIG.get(form_name)
    if not config:
        print(f"  ERROR: Unknown form '{form_name}'. Available: {list(FORM_CONFIG.keys())}")
        return False

    source_path = config["source"]
    output_path = config["output"]
    fields_path = config["fields"]

    # Validate inputs
    if not source_path.exists():
        print(f"  ERROR: Source PDF not found: {source_path}")
        return False
    if not fields_path.exists():
        print(f"  ERROR: Field definitions not found: {fields_path}")
        return False

    # Load field definitions
    with open(fields_path) as f:
        field_data = json.load(f)

    form_info = field_data.get("form_info", {})
    fields = field_data.get("fields", [])

    print(f"  Form: {form_info.get('title', form_name)}")
    print(f"  Source: {source_path.name}")
    print(f"  Fields: {len(fields)} definitions loaded")

    if dry_run:
        # Just validate and report
        text_count = sum(1 for f in fields if f["type"] == "text")
        cb_count = sum(1 for f in fields if f["type"] == "checkbox")
        pages_used = sorted(set(f["page"] for f in fields))
        print(f"  Types: {text_count} text, {cb_count} checkbox")
        print(f"  Pages: {pages_used}")
        print(f"  DRY RUN - no PDF created")
        return True

    # Open source PDF (read-only copy)
    pdf = pikepdf.open(str(source_path))
    acroform = ensure_acroform(pdf)

    # Track stats
    added = 0
    errors = 0

    for field_def in fields:
        name = field_def["name"]
        ftype = field_def["type"]
        page_num = field_def["page"]
        rect = field_def["rect"]
        font_size = field_def.get("font_size", 8)

        # Validate page number
        if page_num >= len(pdf.pages):
            print(f"    WARNING: Field '{name}' references page {page_num} but PDF only has {len(pdf.pages)} pages")
            errors += 1
            continue

        page = pdf.pages[page_num]
        page_obj = page.obj  # Get underlying Object for pikepdf references

        try:
            if ftype == "text":
                add_text_field(pdf, acroform, page_obj, name, rect, font_size)
            elif ftype == "checkbox":
                add_checkbox(pdf, acroform, page_obj, name, rect)
            else:
                print(f"    WARNING: Unknown field type '{ftype}' for '{name}'")
                errors += 1
                continue
            added += 1
        except Exception as e:
            print(f"    ERROR adding field '{name}': {e}")
            errors += 1

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(str(output_path))
    pdf.close()

    print(f"  Added: {added} fields")
    if errors:
        print(f"  Errors: {errors}")
    print(f"  Output: {output_path}")

    # Verify the output
    verify_pdf = pikepdf.open(str(output_path))
    if Name.AcroForm in verify_pdf.Root:
        verify_fields = verify_pdf.Root[Name.AcroForm].get("/Fields", [])
        print(f"  Verified: {len(list(verify_fields))} AcroForm fields in output PDF")
    verify_pdf.close()

    return errors == 0


def main():
    parser = argparse.ArgumentParser(description="Inject AcroForm fields into court PDF forms")
    parser.add_argument("--form", choices=list(FORM_CONFIG.keys()),
                        help="Process a specific form")
    parser.add_argument("--all", action="store_true",
                        help="Process all forms with available field definitions")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate field definitions without creating PDFs")
    args = parser.parse_args()

    if not args.form and not args.all:
        parser.print_help()
        sys.exit(1)

    forms_to_process = [args.form] if args.form else list(FORM_CONFIG.keys())

    print("=== PDF Field Injection ===")
    success = 0
    skipped = 0
    failed = 0

    for form_name in forms_to_process:
        config = FORM_CONFIG[form_name]
        if not config["fields"].exists():
            print(f"\n  SKIP: {form_name} (no field definitions yet)")
            skipped += 1
            continue

        print(f"\nProcessing: {form_name}")
        if process_form(form_name, dry_run=args.dry_run):
            success += 1
        else:
            failed += 1

    print(f"\n=== Summary: {success} success, {skipped} skipped, {failed} failed ===")


if __name__ == "__main__":
    main()
