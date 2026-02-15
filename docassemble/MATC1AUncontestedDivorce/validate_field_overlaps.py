#!/usr/bin/env python3
"""
Comprehensive field definition validation with 4 automated quality gates.

1. Overlap Detection — fields whose bounding rectangles overlap significantly
2. Header Coverage — every page has division and docket number fields
3. Detection Coverage — compare FormFyxer detections vs defined fields per page
4. Field-on-Label Collision — fields sitting on text labels instead of input areas

Usage:
    python scripts/validate_field_overlaps.py              # All checks, all forms
    python scripts/validate_field_overlaps.py --form short  # Specific form
    python scripts/validate_field_overlaps.py --threshold 30 # 30% overlap threshold
    python scripts/validate_field_overlaps.py --check overlaps  # Run only overlap check
    python scripts/validate_field_overlaps.py --check all       # Run all checks (default)
"""

import json
import sys
import argparse
from pathlib import Path
from itertools import combinations

SCRIPT_DIR = Path(__file__).parent
FIELD_DEFS_DIR = SCRIPT_DIR / "field_definitions"
COORDS_DIR = SCRIPT_DIR / "coords"
DETECTED_DIR = SCRIPT_DIR / "detected_fields"

FORM_CONFIG = {
    "short": "short_form_fields.json",
    "long": "long_form_fields.json",
    "schedule_a": "schedule_a_fields.json",
    "schedule_b": "schedule_b_fields.json",
}

COORDS_CONFIG = {
    "short": "short_form_coords.json",
    "long": "long_form_coords.json",
    "schedule_a": "schedule_a_coords.json",
    "schedule_b": "schedule_b_coords.json",
}

DETECTED_CONFIG = {
    "short": "short_detected.json",
    "long": "long_detected.json",
    "schedule_a": "schedule_a_detected.json",
    "schedule_b": "schedule_b_detected.json",
}


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def rect_area(r):
    """Area of a rect [x0, y0, x1, y1]."""
    w = max(0, r[2] - r[0])
    h = max(0, r[3] - r[1])
    return w * h


def rect_intersection_area(r1, r2):
    """Compute intersection area of two rects [x0, y0, x1, y1]."""
    ix0 = max(r1[0], r2[0])
    iy0 = max(r1[1], r2[1])
    ix1 = min(r1[2], r2[2])
    iy1 = min(r1[3], r2[3])
    if ix1 > ix0 and iy1 > iy0:
        return (ix1 - ix0) * (iy1 - iy0)
    return 0


def overlap_percentage(r1, r2):
    """Overlap as percentage of the smaller field's area."""
    area1 = rect_area(r1)
    area2 = rect_area(r2)
    if area1 == 0 or area2 == 0:
        return 0
    inter = rect_intersection_area(r1, r2)
    return inter / min(area1, area2) * 100


def load_field_defs(form_name):
    """Load field definitions for a form. Returns (data_dict, fields_list) or (None, [])."""
    json_path = FIELD_DEFS_DIR / FORM_CONFIG[form_name]
    if not json_path.exists():
        return None, []
    with open(json_path) as f:
        data = json.load(f)
    return data, data.get("fields", [])


# ---------------------------------------------------------------------------
# Check 1: Overlap Detection
# ---------------------------------------------------------------------------

def check_overlaps(form_name, threshold=50.0):
    """Check a form's field definitions for overlapping fields.

    Returns list of overlap tuples: (field1_name, field2_name, page, pct).
    """
    _, fields = load_field_defs(form_name)
    if not fields:
        print(f"  WARNING: {FORM_CONFIG[form_name]} not found, skipping")
        return []

    # Group by page
    pages = {}
    for field in fields:
        pg = field["page"]
        pages.setdefault(pg, []).append(field)

    overlaps = []
    for pg in sorted(pages.keys()):
        page_fields = pages[pg]
        for f1, f2 in combinations(page_fields, 2):
            pct = overlap_percentage(f1["rect"], f2["rect"])
            if pct >= threshold:
                overlaps.append((f1["name"], f2["name"], pg, pct))

    return overlaps


# ---------------------------------------------------------------------------
# Check 2: Header Coverage (Division / Docket on every page)
# ---------------------------------------------------------------------------

def check_header_coverage(form_name):
    """Verify every page has at least one division and one docket field.

    Returns list of (page, missing_type) tuples.
    """
    data, fields = load_field_defs(form_name)
    if not fields:
        return []

    page_count = data.get("page_count", 0)
    if page_count == 0:
        # Infer from fields
        page_count = max(f["page"] for f in fields) + 1

    # Schedules A & B are single-page and use different naming — skip
    if form_name in ("schedule_a", "schedule_b"):
        return []

    missing = []
    for pg in range(page_count):
        page_fields = [f["name"] for f in fields if f["page"] == pg]
        has_division = any("division" in n.lower() for n in page_fields)
        has_docket = any("docket" in n.lower() for n in page_fields)
        if not has_division:
            missing.append((pg, "division"))
        if not has_docket:
            missing.append((pg, "docket"))

    return missing


# ---------------------------------------------------------------------------
# Check 3: FormFyxer Detection Coverage
# ---------------------------------------------------------------------------

def check_detection_coverage(form_name, gap_threshold=0.20):
    """Compare FormFyxer-detected field count vs defined field count per page.

    Flags pages where we have >gap_threshold fewer defined fields than detected.
    Returns list of (page, defined_count, detected_count, gap_pct) tuples.
    """
    detected_file = DETECTED_DIR / DETECTED_CONFIG.get(form_name, "")
    if not detected_file.exists():
        return []

    _, fields = load_field_defs(form_name)
    if not fields:
        return []

    with open(detected_file) as f:
        detected_data = json.load(f)

    # Count defined fields per page
    defined_per_page = {}
    for field in fields:
        pg = field["page"]
        defined_per_page[pg] = defined_per_page.get(pg, 0) + 1

    # Count detected fields per page
    detected_per_page = {}
    for page_info in detected_data.get("pages", []):
        pg = page_info.get("page", 0)
        detected_per_page[pg] = page_info.get("filtered_count", 0)

    gaps = []
    all_pages = set(defined_per_page.keys()) | set(detected_per_page.keys())
    for pg in sorted(all_pages):
        defined = defined_per_page.get(pg, 0)
        detected = detected_per_page.get(pg, 0)
        if detected > 0 and defined < detected:
            gap_pct = (detected - defined) / detected
            if gap_pct >= gap_threshold:
                gaps.append((pg, defined, detected, gap_pct))

    return gaps


# ---------------------------------------------------------------------------
# Check 4: Field-on-Label Collision Detection
# ---------------------------------------------------------------------------

def check_field_label_collisions(form_name, threshold=50.0):
    """Check if any field rect significantly overlaps with a text label.

    Uses coords JSON for label positions. Returns list of
    (field_name, label_text, page, overlap_pct) tuples.
    """
    coords_file = COORDS_DIR / COORDS_CONFIG.get(form_name, "")
    if not coords_file.exists():
        return []

    _, fields = load_field_defs(form_name)
    if not fields:
        return []

    with open(coords_file) as f:
        coords_data = json.load(f)

    # Build label rects per page
    # Coords JSON has labels with bbox [x0, y0, x1, y1] in PyMuPDF coords (top-left origin)
    # Field defs use PDF coords (bottom-left origin), page_height = 792
    page_height = 792

    label_pages = {}
    for page_info in coords_data.get("pages", []):
        pg = page_info.get("page", 0)
        labels = []
        for label in page_info.get("labels", []):
            bbox = label.get("bbox")
            text = label.get("text", "")
            if not bbox or not text.strip():
                continue
            # Convert PyMuPDF bbox to PDF coords
            pdf_rect = [
                bbox[0],
                page_height - bbox[3],
                bbox[2],
                page_height - bbox[1],
            ]
            labels.append((text, pdf_rect))
        label_pages[pg] = labels

    collisions = []
    for field in fields:
        pg = field["page"]
        frect = field["rect"]
        fname = field["name"]
        farea = rect_area(frect)
        if farea == 0:
            continue

        for label_text, lrect in label_pages.get(pg, []):
            larea = rect_area(lrect)
            if larea == 0:
                continue
            inter = rect_intersection_area(frect, lrect)
            if inter == 0:
                continue
            # Overlap as percentage of the field area
            pct = inter / farea * 100
            if pct >= threshold:
                collisions.append((fname, label_text, pg, pct))

    return collisions


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive field definition validation"
    )
    parser.add_argument(
        "--form",
        choices=list(FORM_CONFIG.keys()),
        help="Check a specific form (default: all)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="Overlap percentage threshold (default: 50%%)",
    )
    parser.add_argument(
        "--check",
        choices=["all", "overlaps", "headers", "coverage", "collisions"],
        default="all",
        help="Which check to run (default: all)",
    )
    args = parser.parse_args()

    forms = [args.form] if args.form else list(FORM_CONFIG.keys())
    total_issues = 0
    total_warnings = 0

    # --- Check 1: Overlap Detection ---
    if args.check in ("all", "overlaps"):
        print(f"=== Check 1: Field Overlap Detection (threshold: {args.threshold}%) ===\n")
        for form_name in forms:
            print(f"--- {form_name} ---")
            overlaps = check_overlaps(form_name, args.threshold)
            if overlaps:
                for f1, f2, pg, pct in overlaps:
                    print(f"  OVERLAP page {pg}: {f1} <-> {f2} ({pct:.0f}%)")
                total_issues += len(overlaps)
            else:
                print("  No overlaps found")
            print()

    # --- Check 2: Header Coverage ---
    if args.check in ("all", "headers"):
        print("=== Check 2: Division/Docket Header Coverage ===\n")
        for form_name in forms:
            if form_name in ("schedule_a", "schedule_b"):
                continue
            print(f"--- {form_name} ---")
            missing = check_header_coverage(form_name)
            if missing:
                for pg, field_type in missing:
                    print(f"  MISSING page {pg}: no {field_type} field")
                total_issues += len(missing)
            else:
                print("  All pages have division and docket fields")
            print()

    # --- Check 3: Detection Coverage ---
    if args.check in ("all", "coverage"):
        print("=== Check 3: FormFyxer Detection Coverage ===\n")
        for form_name in forms:
            print(f"--- {form_name} ---")
            gaps = check_detection_coverage(form_name)
            if gaps:
                for pg, defined, detected, gap_pct in gaps:
                    print(
                        f"  WARNING page {pg}: {defined} defined vs "
                        f"{detected} detected ({gap_pct:.0%} gap)"
                    )
                total_warnings += len(gaps)
            else:
                print("  Coverage OK (or no detection data)")
            print()

    # --- Check 4: Field-on-Label Collisions ---
    if args.check in ("all", "collisions"):
        print(
            f"=== Check 4: Field-on-Label Collision Detection "
            f"(threshold: {args.threshold}%) ===\n"
        )
        for form_name in forms:
            print(f"--- {form_name} ---")
            collisions = check_field_label_collisions(form_name, args.threshold)
            if collisions:
                # Group by field to avoid flooding output
                shown = set()
                for fname, ltext, pg, pct in collisions:
                    key = (fname, pg)
                    if key not in shown:
                        print(
                            f"  COLLISION page {pg}: {fname} overlaps "
                            f"label \"{ltext[:40]}\" ({pct:.0f}%)"
                        )
                        shown.add(key)
                total_warnings += len(shown)
            else:
                print("  No collisions found")
            print()

    # --- Summary ---
    print("=" * 50)
    if total_issues > 0:
        print(f"FAIL: {total_issues} error(s) found")
        if total_warnings > 0:
            print(f"      {total_warnings} warning(s)")
        sys.exit(1)
    elif total_warnings > 0:
        print(f"PASS with {total_warnings} warning(s)")
        sys.exit(0)
    else:
        print("PASS: All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
