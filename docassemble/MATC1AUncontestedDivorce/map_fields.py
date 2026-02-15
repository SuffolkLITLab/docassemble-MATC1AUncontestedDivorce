#!/usr/bin/env python3
"""
Generate corrected field definition JSONs by:
1. Converting ALL existing field coordinates from PyMuPDF space to PDF space
2. Refining positions using FormFyxer's auto-detected field positions where available

The existing field definitions have correct semantic names and correct x-positions,
but y-coordinates are in PyMuPDF space (top-left origin, y increases down).
PDF space has origin at bottom-left (y increases up).

Conversion: pdf_y = page_height - pymupdf_y

Usage:
    python scripts/map_fields.py --form short   # Process one form
    python scripts/map_fields.py --all           # Process all forms
    python scripts/map_fields.py --all --no-refine  # Skip FormFyxer refinement
"""

import json
import sys
import math
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FIELD_DEFS_DIR = SCRIPT_DIR / "field_definitions"
DETECTED_DIR = SCRIPT_DIR / "detected_fields"

PAGE_HEIGHT = 792  # Standard US Letter

FORM_CONFIG = {
    "short": {
        "field_defs": FIELD_DEFS_DIR / "short_form_fields.json",
        "detected": DETECTED_DIR / "short_detected.json",
    },
    "long": {
        "field_defs": FIELD_DEFS_DIR / "long_form_fields.json",
        "detected": DETECTED_DIR / "long_detected.json",
    },
    "schedule_a": {
        "field_defs": FIELD_DEFS_DIR / "schedule_a_fields.json",
        "detected": DETECTED_DIR / "schedule_a_detected.json",
    },
    "schedule_b": {
        "field_defs": FIELD_DEFS_DIR / "schedule_b_fields.json",
        "detected": DETECTED_DIR / "schedule_b_detected.json",
    },
}


def convert_rect_to_pdf_space(rect, page_height=PAGE_HEIGHT):
    """Convert a rect from PyMuPDF (top-left origin) to PDF (bottom-left origin).

    PyMuPDF rect: [x0, y0_top, x1, y1_bottom] — y0 is top edge, y1 is bottom
    PDF rect: [x0, y0_bottom, x1, y1_top] — y0 is bottom edge, y1 is top
    """
    x0, y0_pymupdf, x1, y1_pymupdf = rect
    pdf_y0 = page_height - y1_pymupdf  # bottom of field in PDF space
    pdf_y1 = page_height - y0_pymupdf  # top of field in PDF space
    return [round(x0, 1), round(pdf_y0, 1), round(x1, 1), round(pdf_y1, 1)]


def load_detected_fields(detected_path):
    """Load FormFyxer auto-detected fields, indexed by page."""
    if not detected_path.exists():
        return {}

    with open(detected_path) as f:
        data = json.load(f)

    by_page = {}
    for page_data in data.get("pages", []):
        page_num = page_data["page"]
        by_page[page_num] = page_data.get("fields", [])

    return by_page


def detected_to_rect(d):
    """Convert a FormFyxer detected field (x, y, width, height) to rect [x0, y0, x1, y1].

    FormFyxer uses x,y as bottom-left corner of field in PDF space.
    Our rect format is [x0, y0_bottom, x1, y1_top] in PDF space.
    """
    x0 = d["x"]
    y0 = d["y"]
    x1 = x0 + d["width"]
    y1 = y0 + d["height"]
    return [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]


def rect_center(rect):
    """Get the center point of a rect."""
    return ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)


def rect_distance(r1, r2):
    """Euclidean distance between centers of two rects."""
    c1 = rect_center(r1)
    c2 = rect_center(r2)
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)


def find_best_match(converted_rect, detected_fields, field_type="text"):
    """Find the closest FormFyxer detection to a converted field rect.

    Only matches fields of compatible type. Returns (detected_rect, distance) or None.
    """
    best = None
    best_dist = float('inf')

    type_compat = {
        "text": {"text", "textarea"},
        "checkbox": {"checkbox"},
    }
    allowed_types = type_compat.get(field_type, {field_type})

    for d in detected_fields:
        if d["type"] not in allowed_types:
            continue

        d_rect = detected_to_rect(d)
        dist = rect_distance(converted_rect, d_rect)

        if dist < best_dist:
            best_dist = dist
            best = d_rect

    if best is None:
        return None

    return best, best_dist


def process_form(form_name, use_refinement=True):
    """Convert field coordinates and optionally refine with FormFyxer detections."""
    config = FORM_CONFIG.get(form_name)
    if not config:
        print(f"  ERROR: Unknown form '{form_name}'")
        return False

    field_defs_path = config["field_defs"]
    if not field_defs_path.exists():
        print(f"  ERROR: Field definitions not found: {field_defs_path}")
        return False

    # Load existing field definitions
    with open(field_defs_path) as f:
        data = json.load(f)

    fields = data.get("fields", [])
    print(f"  Fields: {len(fields)}")

    # Load FormFyxer detections if available
    detected_by_page = {}
    if use_refinement:
        detected_by_page = load_detected_fields(config["detected"])
        if detected_by_page:
            total_detected = sum(len(v) for v in detected_by_page.values())
            print(f"  FormFyxer detections loaded: {total_detected} fields")
        else:
            print(f"  No FormFyxer detections available — using coordinate conversion only")

    # Process each field
    converted_count = 0
    refined_count = 0
    kept_converted_count = 0

    # Threshold: if FormFyxer detection is within this distance (in points), use it
    REFINE_THRESHOLD = 50  # generous threshold — if within ~50pt, it's the same field
    # Only use FormFyxer rect if it's significantly different (>5pt) from converted rect
    SIGNIFICANT_DIFF = 5

    for field in fields:
        old_rect = field["rect"]

        # Step 1: Convert from PyMuPDF to PDF space
        converted_rect = convert_rect_to_pdf_space(old_rect)

        # Step 2: Try to refine with FormFyxer detection
        new_rect = converted_rect  # default

        if use_refinement and field["page"] in detected_by_page:
            match = find_best_match(
                converted_rect,
                detected_by_page[field["page"]],
                field["type"]
            )

            if match is not None:
                detected_rect, dist = match
                if dist < REFINE_THRESHOLD:
                    # Found a close match
                    diff = rect_distance(converted_rect, detected_rect)
                    if diff > SIGNIFICANT_DIFF:
                        # FormFyxer position is meaningfully different — use it
                        # But preserve the original width from our definition (FormFyxer
                        # may detect a wider/narrower field)
                        new_rect = detected_rect
                        refined_count += 1
                    else:
                        # Positions are close enough — keep converted
                        kept_converted_count += 1
                else:
                    kept_converted_count += 1
            else:
                kept_converted_count += 1
        else:
            kept_converted_count += 1

        field["rect"] = new_rect
        converted_count += 1

    # Save corrected field definitions (overwrite)
    with open(field_defs_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  Converted: {converted_count} fields (PyMuPDF → PDF space)")
    if use_refinement:
        print(f"  Refined with FormFyxer: {refined_count} fields")
        print(f"  Kept converted coords: {kept_converted_count} fields")
    print(f"  Saved: {field_defs_path}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert field coordinates from PyMuPDF to PDF space, refine with FormFyxer"
    )
    parser.add_argument("--form", choices=list(FORM_CONFIG.keys()),
                        help="Process a specific form")
    parser.add_argument("--all", action="store_true",
                        help="Process all forms")
    parser.add_argument("--no-refine", action="store_true",
                        help="Skip FormFyxer refinement (coordinate conversion only)")
    args = parser.parse_args()

    if not args.form and not args.all:
        parser.print_help()
        sys.exit(1)

    forms = [args.form] if args.form else list(FORM_CONFIG.keys())

    print("=== Field Coordinate Correction ===")
    for form_name in forms:
        print(f"\nProcessing: {form_name}")
        process_form(form_name, use_refinement=not args.no_refine)

    print(f"\nDone. Field definitions updated in: {FIELD_DEFS_DIR}")
    print("Next: run 'python scripts/add_pdf_fields.py --all' to regenerate PDFs")


if __name__ == "__main__":
    main()
