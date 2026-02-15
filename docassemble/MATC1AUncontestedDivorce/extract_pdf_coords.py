#!/usr/bin/env python3
"""
Extract text label positions from reference PDF forms.

Outputs JSON coordinate maps that show where each text label is located,
so we can determine where to place AcroForm input fields.

Usage:
    python scripts/extract_pdf_coords.py [pdf_path] [--output coords/]
    python scripts/extract_pdf_coords.py --all
"""

import json
import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)

# Reference PDF locations
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
REF_DIR = PROJECT_ROOT.parent / "docassembly-documentation" / "docs" / "MATC1AUncontestedDivorce-reference"
COORDS_DIR = SCRIPT_DIR / "coords"

REFERENCE_PDFS = {
    "short_form": REF_DIR / "Financial statement (short form) (CJD-301S)_01-20-2026_1340.pdf",
    "long_form": REF_DIR / "Financial statement (long form) (CJD-301L)_01-20-2026_1341.pdf",
    "schedule_a": REF_DIR / "Financial Statement Schedule A (CJ-D 301)_01-20-2026_1341.pdf",
    "schedule_b": REF_DIR / "Financial Statement Schedule B (CJ-D 301)_01-20-2026_1341.pdf",
}


def extract_text_positions(pdf_path):
    """Extract all text spans with their bounding boxes from a PDF."""
    doc = fitz.open(str(pdf_path))
    result = {
        "source": str(pdf_path.name),
        "page_count": len(doc),
        "pages": []
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_data = {
            "page": page_num,
            "width": page.rect.width,
            "height": page.rect.height,
            "labels": [],
            "lines": [],
        }

        # Extract text with position info
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:  # Skip image blocks
                continue
            for line in block["lines"]:
                line_text = ""
                line_bbox = None
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    bbox = span["bbox"]  # (x0, y0, x1, y1)
                    font_size = span["size"]

                    if line_bbox is None:
                        line_bbox = list(bbox)
                    else:
                        line_bbox[2] = max(line_bbox[2], bbox[2])
                        line_bbox[3] = max(line_bbox[3], bbox[3])

                    line_text += text + " "

                    page_data["labels"].append({
                        "text": text,
                        "bbox": [round(b, 1) for b in bbox],
                        "font_size": round(font_size, 1),
                        "font": span.get("font", ""),
                    })

                if line_text.strip():
                    page_data["lines"].append({
                        "text": line_text.strip(),
                        "bbox": [round(b, 1) for b in line_bbox] if line_bbox else None,
                    })

        # Extract drawing elements (lines, rectangles) which indicate form field areas
        drawings = page.get_drawings()
        drawn_rects = []
        for d in drawings:
            if d["type"] == "re":  # Rectangle
                rect = d["rect"]
                drawn_rects.append({
                    "type": "rect",
                    "bbox": [round(rect.x0, 1), round(rect.y0, 1),
                             round(rect.x1, 1), round(rect.y1, 1)],
                    "fill": d.get("fill"),
                    "stroke": d.get("color"),
                })
        if drawn_rects:
            page_data["drawn_rects"] = drawn_rects[:100]  # Limit to avoid huge output

        result["pages"].append(page_data)

    doc.close()
    return result


def extract_all():
    """Extract coordinates from all reference PDFs."""
    COORDS_DIR.mkdir(parents=True, exist_ok=True)

    for name, pdf_path in REFERENCE_PDFS.items():
        if not pdf_path.exists():
            print(f"  SKIP: {name} - file not found at {pdf_path}")
            continue

        print(f"  Extracting: {name} ({pdf_path.name})")
        coords = extract_text_positions(pdf_path)

        output_path = COORDS_DIR / f"{name}_coords.json"
        with open(output_path, "w") as f:
            json.dump(coords, f, indent=2)

        total_labels = sum(len(p["labels"]) for p in coords["pages"])
        total_lines = sum(len(p["lines"]) for p in coords["pages"])
        print(f"    {coords['page_count']} pages, {total_labels} text spans, {total_lines} text lines")
        print(f"    Saved: {output_path}")


def extract_single(pdf_path, output_dir=None):
    """Extract coordinates from a single PDF."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    output_dir = Path(output_dir) if output_dir else COORDS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting: {pdf_path.name}")
    coords = extract_text_positions(pdf_path)

    stem = pdf_path.stem.replace(" ", "_").replace("(", "").replace(")", "")
    output_path = output_dir / f"{stem}_coords.json"
    with open(output_path, "w") as f:
        json.dump(coords, f, indent=2)

    total_labels = sum(len(p["labels"]) for p in coords["pages"])
    print(f"  {coords['page_count']} pages, {total_labels} text spans")
    print(f"  Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print("=== Extracting coordinates from all reference PDFs ===")
        extract_all()
    elif len(sys.argv) > 1:
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        extract_single(sys.argv[1], output_dir)
    else:
        print("=== Extracting coordinates from all reference PDFs ===")
        extract_all()
    print("\nDone.")
