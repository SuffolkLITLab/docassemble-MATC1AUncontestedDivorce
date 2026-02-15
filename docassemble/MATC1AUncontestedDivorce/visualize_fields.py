#!/usr/bin/env python3
"""
Generate visual overlay PDFs showing exactly where each AcroForm field is placed
relative to the original document content.

This draws a colored translucent rectangle + label for every field on top of
the original PDF. Open the output in Preview to verify alignment.

Field types are color-coded:
  - Text fields: blue rectangles with blue labels
  - Checkboxes: green rectangles with green labels

Usage:
    python scripts/visualize_fields.py                   # All forms
    python scripts/visualize_fields.py --form short       # Specific form
    python scripts/visualize_fields.py --form long --page 3  # Specific page
"""

import json
import sys
import argparse
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

try:
    import pikepdf
except ImportError:
    print("ERROR: pikepdf not installed. Run: pip install pikepdf")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "data" / "templates"
FIELD_DEFS_DIR = SCRIPT_DIR / "field_definitions"
REF_DIR = PROJECT_ROOT.parent / "docassembly-documentation" / "docs" / "MATC1AUncontestedDivorce-reference"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Map form names to their reference (original flat) PDFs and field definitions
FORM_CONFIG = {
    "short": {
        "reference": REF_DIR / "Financial statement (short form) (CJD-301S)_01-20-2026_1340.pdf",
        "template": TEMPLATES_DIR / "financial_statement_short.pdf",
        "fields": FIELD_DEFS_DIR / "short_form_fields.json",
    },
    "long": {
        "reference": REF_DIR / "Financial statement (long form) (CJD-301L)_01-20-2026_1341.pdf",
        "template": TEMPLATES_DIR / "financial_statement_long.pdf",
        "fields": FIELD_DEFS_DIR / "long_form_fields.json",
    },
    "schedule_a": {
        "reference": REF_DIR / "Financial Statement Schedule A (CJ-D 301)_01-20-2026_1341.pdf",
        "template": TEMPLATES_DIR / "financial_statement_schedule_a.pdf",
        "fields": FIELD_DEFS_DIR / "schedule_a_fields.json",
    },
    "schedule_b": {
        "reference": REF_DIR / "Financial Statement Schedule B (CJ-D 301)_01-20-2026_1341.pdf",
        "template": TEMPLATES_DIR / "financial_statement_schedule_b.pdf",
        "fields": FIELD_DEFS_DIR / "schedule_b_fields.json",
    },
}

# Colors (RGB 0-1 scale)
TEXT_COLOR = (0.0, 0.2, 0.8)       # Blue for text fields
CHECKBOX_COLOR = (0.0, 0.6, 0.2)   # Green for checkboxes
TEXT_FILL = (0.7, 0.8, 1.0)        # Light blue fill
CHECKBOX_FILL = (0.7, 1.0, 0.8)    # Light green fill
LABEL_COLOR_TEXT = (0.0, 0.0, 0.6)
LABEL_COLOR_CB = (0.0, 0.4, 0.0)


def visualize_form(form_name, page_filter=None):
    """Create an overlay PDF showing field positions on the original document."""
    config = FORM_CONFIG.get(form_name)
    if not config:
        print(f"  ERROR: Unknown form '{form_name}'")
        return False

    ref_path = config["reference"]
    fields_path = config["fields"]

    if not ref_path.exists():
        print(f"  ERROR: Reference PDF not found: {ref_path}")
        return False
    if not fields_path.exists():
        print(f"  ERROR: Field definitions not found: {fields_path}")
        return False

    # Load field definitions
    with open(fields_path) as f:
        field_data = json.load(f)

    fields = field_data.get("fields", [])
    page_size = field_data.get("page_size", [612, 792])

    # Open the reference PDF with PyMuPDF for rendering
    doc = fitz.open(str(ref_path))

    print(f"  Form: {form_name}")
    print(f"  Pages: {len(doc)}")
    print(f"  Fields: {len(fields)}")

    # Group fields by page
    fields_by_page = {}
    for field in fields:
        pg = field["page"]
        if pg not in fields_by_page:
            fields_by_page[pg] = []
        fields_by_page[pg].append(field)

    drawn = 0
    for page_num in range(len(doc)):
        if page_filter is not None and page_num != page_filter:
            continue

        page = doc[page_num]
        page_fields = fields_by_page.get(page_num, [])

        if not page_fields:
            continue

        # PDF coordinates have origin at bottom-left
        # PyMuPDF (fitz) uses origin at top-left
        # Field definitions use PDF coordinates (bottom-left origin)
        # We need to convert: fitz_y = page_height - pdf_y
        page_height = page.rect.height

        for field in page_fields:
            name = field["name"]
            ftype = field["type"]
            rect = field["rect"]  # [x0, y0, x1, y1] in PDF coords (bottom-left origin)

            # Convert from PDF coords (bottom-left) to fitz coords (top-left)
            # In PDF: y0 is bottom of field, y1 is top of field
            # In fitz: y increases downward
            fitz_x0 = rect[0]
            fitz_y0 = page_height - rect[3]  # top of field in fitz
            fitz_x1 = rect[2]
            fitz_y1 = page_height - rect[1]  # bottom of field in fitz

            fitz_rect = fitz.Rect(fitz_x0, fitz_y0, fitz_x1, fitz_y1)

            if ftype == "checkbox":
                stroke = CHECKBOX_COLOR
                fill = CHECKBOX_FILL
                label_color = LABEL_COLOR_CB
            else:
                stroke = TEXT_COLOR
                fill = TEXT_FILL
                label_color = LABEL_COLOR_TEXT

            # Draw filled rectangle with border
            shape = page.new_shape()
            shape.draw_rect(fitz_rect)
            shape.finish(color=stroke, fill=fill, width=0.5, fill_opacity=0.4)
            shape.commit()

            # Add field name as tiny label inside the rectangle
            label_size = min(6, (fitz_rect.height - 1) * 0.9)
            if label_size >= 3:
                # Truncate label if field is narrow
                max_chars = max(3, int((fitz_rect.width - 2) / (label_size * 0.5)))
                label = name[:max_chars]
                if len(name) > max_chars:
                    label = label[:-1] + "…"

                text_point = fitz.Point(fitz_rect.x0 + 1, fitz_rect.y0 + label_size + 0.5)
                page.insert_text(
                    text_point,
                    label,
                    fontsize=label_size,
                    color=label_color,
                    fontname="helv",
                )

            drawn += 1

    # Save output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_page{page_filter}" if page_filter is not None else ""
    output_path = OUTPUT_DIR / f"OVERLAY_{form_name}{suffix}.pdf"
    doc.save(str(output_path))
    doc.close()

    print(f"  Drew: {drawn} field overlays")
    print(f"  Output: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Visualize AcroForm field placement on original PDF forms"
    )
    parser.add_argument("--form", choices=list(FORM_CONFIG.keys()),
                        help="Visualize a specific form")
    parser.add_argument("--page", type=int, default=None,
                        help="Visualize only a specific page (0-indexed)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.form:
        forms = [args.form]
    else:
        forms = list(FORM_CONFIG.keys())

    print("=== Field Placement Visualization ===")
    for form_name in forms:
        config = FORM_CONFIG[form_name]
        if not config["fields"].exists():
            print(f"\n  SKIP: {form_name} (no field definitions)")
            continue

        print(f"\nProcessing: {form_name}")
        visualize_form(form_name, page_filter=args.page)

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("Open the OVERLAY_*.pdf files to see field rectangles on original forms.")
    print("Blue rectangles = text fields, Green rectangles = checkboxes.")


if __name__ == "__main__":
    main()
