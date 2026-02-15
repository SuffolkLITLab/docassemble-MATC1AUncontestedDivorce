#!/usr/bin/env python3
"""
Auto-detect fillable field positions in flat court PDFs using FormFyxer.

Uses computer vision (OpenCV + boxdetect) to find text input lines and checkboxes,
giving us "ground truth" positions in correct PDF coordinate space (bottom-left origin).

Usage:
    python scripts/auto_detect_fields.py --form short    # Detect one form
    python scripts/auto_detect_fields.py --all            # Detect all forms
    python scripts/auto_detect_fields.py --all --visualize  # Also generate overlay PDFs
"""

import json
import sys
import argparse
from pathlib import Path

try:
    from formfyxer import get_possible_fields
    from formfyxer.pdf_wrangling import FormField, FieldType
except ImportError:
    print("ERROR: formfyxer not installed. Run: pip install formfyxer")
    sys.exit(1)

try:
    import fitz  # PyMuPDF — for visualization only
except ImportError:
    fitz = None

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
REF_DIR = PROJECT_ROOT.parent / "docassembly-documentation" / "docs" / "MATC1AUncontestedDivorce-reference"
DETECTED_DIR = SCRIPT_DIR / "detected_fields"
OUTPUT_DIR = SCRIPT_DIR / "output"

FORM_CONFIG = {
    "short": {
        "source": REF_DIR / "Financial statement (short form) (CJD-301S)_01-20-2026_1340.pdf",
        "expected_fields": 148,
    },
    "long": {
        "source": REF_DIR / "Financial statement (long form) (CJD-301L)_01-20-2026_1341.pdf",
        "expected_fields": 266,
    },
    "schedule_a": {
        "source": REF_DIR / "Financial Statement Schedule A (CJ-D 301)_01-20-2026_1341.pdf",
        "expected_fields": 70,
    },
    "schedule_b": {
        "source": REF_DIR / "Financial Statement Schedule B (CJ-D 301)_01-20-2026_1341.pdf",
        "expected_fields": 21,
    },
}

# Page dimensions for standard US Letter
PAGE_WIDTH = 612
PAGE_HEIGHT = 792


def serialize_field(field, page_idx, field_idx):
    """Convert a FormFyxer FormField to a serializable dict."""
    ftype = "text"
    width = 100
    height = 14
    if hasattr(field, 'type'):
        if field.type == FieldType.CHECK_BOX:
            ftype = "checkbox"
        elif field.type == FieldType.AREA:
            ftype = "textarea"
    if hasattr(field, 'configs') and field.configs:
        width = field.configs.get('width', 100)
        height = field.configs.get('height', 14)
        if ftype == "checkbox":
            size = field.configs.get('size', 12)
            width = size
            height = size

    return {
        "auto_name": field.field_name if hasattr(field, 'field_name') else f"page_{page_idx}_field_{field_idx}",
        "type": ftype,
        "x": round(field.x, 1) if hasattr(field, 'x') else 0,
        "y": round(field.y, 1) if hasattr(field, 'y') else 0,
        "width": round(width, 1),
        "height": round(height, 1),
        "font_size": field.font_size if hasattr(field, 'font_size') else 10,
    }


def filter_false_positives(fields, page_width=PAGE_WIDTH):
    """Remove likely false positives: full-width lines, section dividers, etc."""
    filtered = []
    for f in fields:
        # Skip fields spanning nearly the full page width (decorative lines / section dividers)
        if f["width"] > page_width * 0.8:
            continue
        # Skip fields with zero or negative dimensions
        if f["width"] <= 0 or f["height"] <= 0:
            continue
        filtered.append(f)
    return filtered


def detect_form(form_name, visualize=False):
    """Run FormFyxer detection on a single form."""
    config = FORM_CONFIG.get(form_name)
    if not config:
        print(f"  ERROR: Unknown form '{form_name}'")
        return False

    source_path = config["source"]
    if not source_path.exists():
        print(f"  ERROR: Source PDF not found: {source_path}")
        return False

    print(f"  Source: {source_path.name}")
    print(f"  Expected fields: {config['expected_fields']}")
    print(f"  Running FormFyxer detection (this may take a moment)...")

    try:
        # get_possible_fields returns List[List[FormField]] — fields per page
        fields_per_page = get_possible_fields(str(source_path))
    except Exception as e:
        print(f"  ERROR during detection: {e}")
        return False

    # Build output structure
    result = {
        "source": source_path.name,
        "detection_method": "formfyxer.get_possible_fields",
        "coordinate_system": "pdf_bottom_left_origin",
        "page_size": [PAGE_WIDTH, PAGE_HEIGHT],
        "pages": [],
    }

    total_detected = 0
    total_filtered = 0

    for page_idx, page_fields in enumerate(fields_per_page):
        raw_fields = []
        for field_idx, field in enumerate(page_fields):
            raw_fields.append(serialize_field(field, page_idx, field_idx))

        filtered = filter_false_positives(raw_fields)
        total_detected += len(raw_fields)
        total_filtered += len(filtered)

        text_count = sum(1 for f in filtered if f["type"] in ("text", "textarea"))
        cb_count = sum(1 for f in filtered if f["type"] == "checkbox")

        result["pages"].append({
            "page": page_idx,
            "raw_count": len(raw_fields),
            "filtered_count": len(filtered),
            "fields": filtered,
        })

        print(f"    Page {page_idx}: {len(raw_fields)} detected, {len(filtered)} after filtering ({text_count} text, {cb_count} checkbox)")

    result["total_detected"] = total_detected
    result["total_filtered"] = total_filtered

    # Save detection results
    DETECTED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DETECTED_DIR / f"{form_name}_detected.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  Total: {total_filtered} fields (from {total_detected} raw detections)")
    print(f"  Expected: {config['expected_fields']}")
    coverage_pct = round(total_filtered / max(config['expected_fields'], 1) * 100)
    print(f"  Coverage: ~{coverage_pct}%")
    print(f"  Saved: {output_path}")

    # Optional visualization
    if visualize and fitz:
        visualize_detections(form_name, source_path, result)

    return True


def visualize_detections(form_name, source_path, detection_data):
    """Draw detected field positions on the original PDF using PyMuPDF."""
    if not fitz:
        print("  SKIP visualization: PyMuPDF not available")
        return

    doc = fitz.open(str(source_path))

    for page_data in detection_data["pages"]:
        page_idx = page_data["page"]
        if page_idx >= len(doc):
            continue

        page = doc[page_idx]
        page_height = page.rect.height

        for field in page_data["fields"]:
            # FormFyxer coords are in PDF space (bottom-left origin)
            # PyMuPDF needs top-left origin
            x = field["x"]
            y_pdf = field["y"]
            w = field["width"]
            h = field["height"]

            # Convert: fitz_y = page_height - pdf_y
            fitz_y_top = page_height - (y_pdf + h)  # top edge
            fitz_y_bottom = page_height - y_pdf      # bottom edge

            fitz_rect = fitz.Rect(x, fitz_y_top, x + w, fitz_y_bottom)

            if field["type"] == "checkbox":
                color = (0.0, 0.6, 0.2)
                fill = (0.7, 1.0, 0.8)
            else:
                color = (0.8, 0.2, 0.0)
                fill = (1.0, 0.85, 0.7)

            shape = page.new_shape()
            shape.draw_rect(fitz_rect)
            shape.finish(color=color, fill=fill, width=0.5, fill_opacity=0.4)
            shape.commit()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"DETECTED_{form_name}.pdf"
    doc.save(str(output_path))
    doc.close()
    print(f"  Visualization: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Auto-detect fillable field positions using FormFyxer")
    parser.add_argument("--form", choices=list(FORM_CONFIG.keys()),
                        help="Detect fields in a specific form")
    parser.add_argument("--all", action="store_true",
                        help="Detect fields in all forms")
    parser.add_argument("--visualize", action="store_true",
                        help="Generate overlay PDFs showing detected field positions")
    args = parser.parse_args()

    if not args.form and not args.all:
        parser.print_help()
        sys.exit(1)

    forms = [args.form] if args.form else list(FORM_CONFIG.keys())

    print("=== FormFyxer Auto-Detection ===")
    for form_name in forms:
        print(f"\nProcessing: {form_name}")
        detect_form(form_name, visualize=args.visualize)

    print(f"\nDetected fields saved to: {DETECTED_DIR}")
    if args.visualize:
        print(f"Visualizations saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
