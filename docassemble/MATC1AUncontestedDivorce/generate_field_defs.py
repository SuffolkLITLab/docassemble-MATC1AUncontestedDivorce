#!/usr/bin/env python3
"""
Generate field definition JSON files for Massachusetts court financial statement PDFs.

This script produces field definition files that specify where to add AcroForm text
fields and checkboxes to flat PDF forms so they become fillable. Each field definition
includes the field name, type, page, bounding rectangle, and suggested font size.

Currently supports:
  - CJD-301S: Financial Statement (Short Form) -- 4 pages

Future forms (to be added):
  - CJD-301L: Financial Statement (Long Form)
  - CJD-304:  Child Support Guidelines Worksheet
  - CJD-305:  Child Support Guidelines Findings

Usage:
    python generate_field_defs.py [--form FORM_ID] [--all]

    --form FORM_ID   Generate field definitions for a specific form.
                     Supported: short, long, guidelines, findings
    --all            Generate field definitions for all forms (default).
    --output DIR     Output directory (default: field_definitions/)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
COORDS_DIR = SCRIPT_DIR / "coords"
OUTPUT_DIR = SCRIPT_DIR / "field_definitions"

PAGE_WIDTH = 612
PAGE_HEIGHT = 792

# Standard field dimensions
FIELD_HEIGHT = 14
AMOUNT_X0 = 485
AMOUNT_X1 = 590
AMOUNT_WIDTH = AMOUNT_X1 - AMOUNT_X0  # 105 points


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_field(name: str, field_type: str, page: int, rect: list, font_size: int = 8) -> dict:
    """Create a single field definition dict."""
    return {
        "name": name,
        "type": field_type,
        "page": page,
        "rect": rect,
        "font_size": font_size,
    }


def amount_field(name: str, page: int, y: float, font_size: int = 8,
                 x0: float = AMOUNT_X0, x1: float = AMOUNT_X1) -> dict:
    """Shortcut for a dollar-amount text field in the right-hand column."""
    return make_field(name, "text", page, [x0, y, x1, y + FIELD_HEIGHT], font_size)


def text_field(name: str, page: int, x0: float, y: float, x1: float,
               font_size: int = 8) -> dict:
    """Shortcut for a text field with explicit horizontal bounds."""
    return make_field(name, "text", page, [x0, y, x1, y + FIELD_HEIGHT], font_size)


def checkbox_field(name: str, page: int, x: float, y: float, size: float = 12) -> dict:
    """Shortcut for a checkbox field."""
    return make_field(name, "checkbox", page, [x, y, x + size, y + size], 10)


# ---------------------------------------------------------------------------
# Short Form (CJD-301S) field definitions
# ---------------------------------------------------------------------------

def build_short_form_fields() -> dict:
    """Build the complete field definition structure for CJD-301S."""
    fields = []

    # -----------------------------------------------------------------------
    # PAGE 0 -- Header + Personal Information + Gross Weekly Income
    # -----------------------------------------------------------------------

    # -- Header --
    fields.append(text_field("trial_court_division", 0, 60, 34, 200, font_size=10))
    fields.append(text_field("docket_number", 0, 485, 80, 590, font_size=10))
    fields.append(text_field("plaintiff_petitioner_name", 0, 37, 112, 295, font_size=10))
    fields.append(text_field("defendant_petitioner_name", 0, 320, 112, 590, font_size=10))

    # -- Section 1: Personal Information --
    fields.append(text_field("user_name", 0, 90, 174, 360, font_size=10))
    fields.append(text_field("user_ssn", 0, 449, 174, 590, font_size=10))
    fields.append(text_field("user_address_street", 0, 75, 193, 355))
    fields.append(text_field("user_address_city", 0, 360, 193, 478))
    fields.append(text_field("user_address_state", 0, 481, 193, 530))
    fields.append(text_field("user_address_zip", 0, 535, 193, 590))
    fields.append(text_field("user_phone", 0, 38, 221, 207))
    fields.append(text_field("user_birthdate", 0, 267, 221, 397))
    fields.append(text_field("children_living_count", 0, 530, 221, 590))
    fields.append(text_field("user_occupation", 0, 90, 239, 288))
    fields.append(text_field("user_employer_name", 0, 334, 240, 590))
    fields.append(text_field("employer_address_street", 0, 132, 260, 373))
    fields.append(text_field("employer_address_city", 0, 376, 260, 476))
    fields.append(text_field("employer_address_state", 0, 479, 260, 530))
    fields.append(text_field("employer_address_zip", 0, 535, 260, 590))
    fields.append(text_field("employer_phone", 0, 38, 281, 210))

    # Health insurance checkboxes and provider
    fields.append(checkbox_field("health_insurance_yes", 0, 483, 284))
    fields.append(checkbox_field("health_insurance_no", 0, 534, 284))
    fields.append(text_field("health_insurance_provider", 0, 220, 307, 590))

    # -- Section 2: Gross Weekly Income --
    income_items = [
        ("income_base_pay",         343),
        ("income_overtime",         361),
        ("income_part_time",        379),
        ("income_self_employment",  397),
        ("income_tips",             415),
        ("income_commissions",      433),
        ("income_dividends",        451),
        ("income_trusts",           469),
        ("income_pensions",         487),
        ("income_social_security",  505),
        ("income_disability",       523),
        ("income_public_assistance", 541),
        ("income_child_support",    559),
        ("income_rental",           577),
        ("income_royalties",        595),
        ("income_contributions",    613),
        ("income_other",            631),
    ]
    for name, y in income_items:
        fields.append(amount_field(name, 0, y))

    # Other income: specify text field
    fields.append(text_field("income_other_specify", 0, 108, 632, 475))

    # Total gross weekly income
    fields.append(amount_field("income_total", 0, 691))

    # -----------------------------------------------------------------------
    # PAGE 1 -- Deductions, Net Income, Expenses, Counsel Fees
    # -----------------------------------------------------------------------

    # -- Section 3: Itemized Deductions --
    fields.append(amount_field("deduction_federal", 1, 118))
    fields.append(text_field("deduction_federal_exemptions", 1, 210, 118, 322))
    fields.append(amount_field("deduction_state", 1, 136))
    fields.append(text_field("deduction_state_exemptions", 1, 200, 136, 322))
    fields.append(amount_field("deduction_fica", 1, 154))
    fields.append(amount_field("deduction_medical", 1, 172))
    fields.append(amount_field("deduction_union", 1, 190))
    fields.append(amount_field("deduction_total", 1, 208))

    # -- Section 4: Adjusted Net Weekly Income --
    fields.append(amount_field("adjusted_net_weekly", 1, 235))

    # -- Section 5: Other Deductions --
    fields.append(amount_field("other_deduction_credit_union", 1, 280))
    fields.append(amount_field("other_deduction_savings", 1, 298))
    fields.append(amount_field("other_deduction_retirement", 1, 316))
    fields.append(amount_field("other_deduction_other", 1, 334))
    fields.append(text_field("other_deduction_other_specify", 1, 317, 335, 475, font_size=7))
    fields.append(amount_field("other_deduction_total", 1, 352))

    # -- Section 6: Net Weekly Income --
    fields.append(amount_field("net_weekly_income", 1, 379))

    # -- Section 7: Gross Yearly Income from Prior Year --
    fields.append(amount_field("prior_year_gross", 1, 406))
    fields.append(text_field("social_security_years", 1, 319, 439, 440))

    # -- Section 8: Weekly Expenses (left column) --
    left_expense_items = [
        ("expense_rent",                489),
        ("expense_homeowner_insurance", 503),
        ("expense_maintenance",         518),
        ("expense_heat",                532),
        ("expense_electricity",         546),
        ("expense_telephone",           561),
        ("expense_water",               575),
        ("expense_food",                589),
        ("expense_house_supplies",      604),
        ("expense_laundry",             618),
        ("expense_clothing",            633),
    ]
    for name, y in left_expense_items:
        fields.append(amount_field(name, 1, y, x0=184, x1=310))

    # -- Section 8: Weekly Expenses (right column) --
    right_expense_items = [
        ("expense_life_insurance",      489),
        ("expense_medical_insurance",   503),
        ("expense_uninsured_medical",   518),
        ("expense_incidentals",         532),
        ("expense_motor_vehicle",       546),
        ("expense_motor_payment",       561),
        ("expense_child_care",          575),
        ("expense_other",              604),
    ]
    for name, y in right_expense_items:
        fields.append(amount_field(name, 1, y, x0=494, x1=590))

    # Expense other: explain text
    fields.append(text_field("expense_other_explain", 1, 410, 589, 485, font_size=7))

    # Total weekly expenses
    fields.append(amount_field("expense_total", 1, 656, x0=494, x1=590))

    # -- Section 9: Counsel Fees --
    fields.append(amount_field("counsel_retainer", 1, 703))
    fields.append(amount_field("counsel_fees_incurred", 1, 722))
    fields.append(text_field("counsel_anticipated_from", 1, 359, 741, 462))
    fields.append(amount_field("counsel_anticipated_to", 1, 741))

    # -----------------------------------------------------------------------
    # PAGE 2 -- Assets (Section 10) + Liabilities (Section 11)
    # -----------------------------------------------------------------------

    # -- Section 10a: Real Estate --
    fields.append(text_field("asset_real_estate_location", 2, 82, 128, 590))
    fields.append(text_field("asset_real_estate_title", 2, 144, 146, 590))
    fields.append(text_field("asset_real_estate_fmv", 2, 127, 164, 269))
    fields.append(text_field("asset_real_estate_mortgage", 2, 324, 164, 448))
    fields.append(amount_field("asset_real_estate_equity", 2, 163, x0=494, x1=590))

    # -- Section 10b: Motor Vehicles --
    # Vehicle 1 (y ~ 199-213)
    fields.append(text_field("asset_vehicle1_fmv", 2, 125, 199, 266))
    fields.append(text_field("asset_vehicle1_loan", 2, 360, 199, 445))
    fields.append(amount_field("asset_vehicle1_equity", 2, 199, x0=490, x1=590))
    # Vehicle 2 (y ~ 217-231)
    fields.append(text_field("asset_vehicle2_fmv", 2, 125, 217, 266))
    fields.append(text_field("asset_vehicle2_loan", 2, 360, 217, 445))
    fields.append(amount_field("asset_vehicle2_equity", 2, 217, x0=490, x1=590))

    # -- Section 10c: IRA/Keogh/Pension (3 rows) --
    # $ signs at y~270, 289, 307
    pension_rows = [
        ("asset_pension1", 265, 270),
        ("asset_pension2", 283, 289),
        ("asset_pension3", 301, 307),
    ]
    for prefix, inst_y, amt_y in pension_rows:
        fields.append(text_field(f"{prefix}_institution", 2, 46, inst_y, 475))
        fields.append(amount_field(f"{prefix}_account", 2, amt_y))

    # -- Section 10d: Tax Deferred Annuity --
    fields.append(amount_field("asset_annuity", 2, 325))

    # -- Section 10e: Life Insurance Cash Value --
    fields.append(amount_field("asset_life_insurance_cash", 2, 343))

    # -- Section 10f: Savings/Checking (3 rows) --
    # $ signs at y~415, 433, 451
    savings_rows = [
        ("asset_savings1", 409, 415),
        ("asset_savings2", 427, 433),
        ("asset_savings3", 445, 451),
    ]
    for prefix, inst_y, amt_y in savings_rows:
        fields.append(text_field(f"{prefix}_institution", 2, 46, inst_y, 475))
        fields.append(amount_field(f"{prefix}_account", 2, amt_y))

    # -- Section 10g: Other Assets (2 rows) --
    # $ signs at y~487, 505
    fields.append(text_field("asset_other1", 2, 46, 482, 475))
    fields.append(amount_field("asset_other1_value", 2, 487))
    fields.append(text_field("asset_other2", 2, 46, 500, 475))
    fields.append(amount_field("asset_other2_value", 2, 505))

    # -- Section 10h: Total Assets --
    # $ at y~541
    fields.append(amount_field("asset_total", 2, 541))

    # -- Section 11: Liabilities --
    # Column headers at y~595: Creditor | Nature of Debt | Date Incurred | Amount Due | Weekly Payment
    # Rows a-d at y~618, 645, 672, 699
    liability_rows = [
        ("liability1", 618),
        ("liability2", 645),
        ("liability3", 672),
        ("liability4", 699),
    ]
    for prefix, y in liability_rows:
        fields.append(text_field(f"{prefix}_creditor", 2, 42, y, 170))
        fields.append(text_field(f"{prefix}_nature", 2, 172, y, 282))
        fields.append(text_field(f"{prefix}_date", 2, 284, y, 373))
        fields.append(text_field(f"{prefix}_amount_due", 2, 383, y, 480))
        fields.append(text_field(f"{prefix}_weekly_payment", 2, 491, y, 590))

    # Total liabilities row (y~739)
    fields.append(text_field("liability_total_due", 2, 388, 739, 494))
    fields.append(text_field("liability_total_weekly", 2, 505, 739, 590))

    # -----------------------------------------------------------------------
    # PAGE 3 -- Certification + Statement by Attorney
    # -----------------------------------------------------------------------

    # Certification (y~155-172)
    fields.append(text_field("cert_date", 3, 52, 155, 210, font_size=10))
    fields.append(text_field("cert_signature", 3, 260, 155, 590, font_size=10))

    # Attorney section
    fields.append(text_field("attorney_date", 3, 52, 418, 210, font_size=10))
    fields.append(text_field("attorney_signature", 3, 326, 418, 590, font_size=10))
    fields.append(text_field("attorney_name", 3, 326, 445, 590, font_size=10))
    fields.append(text_field("attorney_address_street", 3, 326, 472, 590))
    fields.append(text_field("attorney_address_city", 3, 326, 500, 445))
    fields.append(text_field("attorney_address_state", 3, 448, 500, 510))
    fields.append(text_field("attorney_address_zip", 3, 515, 500, 590))
    fields.append(text_field("attorney_phone", 3, 362, 532, 590, font_size=10))
    fields.append(text_field("attorney_bbo", 3, 365, 550, 590, font_size=10))

    return {
        "form_id": "CJD-301S",
        "form_name": "Financial Statement (Short Form)",
        "page_count": 4,
        "page_size": [PAGE_WIDTH, PAGE_HEIGHT],
        "fields": fields,
    }


# ---------------------------------------------------------------------------
# Placeholder builders for future forms
# ---------------------------------------------------------------------------

def build_long_form_fields() -> dict:
    """Build field definitions for CJD-301L (Long Form). Not yet implemented."""
    raise NotImplementedError(
        "Long form (CJD-301L) field definitions are not yet implemented. "
        "Add the field layout data and implement this function."
    )


def build_guidelines_fields() -> dict:
    """Build field definitions for CJD-304 (Child Support Guidelines). Not yet implemented."""
    raise NotImplementedError(
        "Child Support Guidelines (CJD-304) field definitions are not yet implemented."
    )


def build_findings_fields() -> dict:
    """Build field definitions for CJD-305 (Guidelines Findings). Not yet implemented."""
    raise NotImplementedError(
        "Guidelines Findings (CJD-305) field definitions are not yet implemented."
    )


# ---------------------------------------------------------------------------
# Registry of form builders
# ---------------------------------------------------------------------------

FORM_BUILDERS = {
    "short": {
        "builder": build_short_form_fields,
        "output_file": "short_form_fields.json",
        "description": "Financial Statement (Short Form) CJD-301S",
    },
    "long": {
        "builder": build_long_form_fields,
        "output_file": "long_form_fields.json",
        "description": "Financial Statement (Long Form) CJD-301L",
    },
    "guidelines": {
        "builder": build_guidelines_fields,
        "output_file": "guidelines_fields.json",
        "description": "Child Support Guidelines Worksheet CJD-304",
    },
    "findings": {
        "builder": build_findings_fields,
        "output_file": "findings_fields.json",
        "description": "Child Support Guidelines Findings CJD-305",
    },
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_fields(form_data: dict) -> list:
    """Run basic validation on the generated field definitions.

    Returns a list of warning strings. Empty list means no issues.
    """
    warnings = []
    names_seen = set()
    page_count = form_data.get("page_count", 0)
    pw, ph = form_data.get("page_size", [612, 792])

    for i, f in enumerate(form_data.get("fields", [])):
        name = f.get("name", f"<field {i}>")

        # Duplicate name check
        if name in names_seen:
            warnings.append(f"Duplicate field name: {name}")
        names_seen.add(name)

        # Page bounds
        page = f.get("page", -1)
        if page < 0 or page >= page_count:
            warnings.append(f"{name}: page {page} out of range [0, {page_count - 1}]")

        # Rect sanity
        rect = f.get("rect", [])
        if len(rect) != 4:
            warnings.append(f"{name}: rect has {len(rect)} elements, expected 4")
            continue
        x0, y0, x1, y1 = rect
        if x0 >= x1:
            warnings.append(f"{name}: x0 ({x0}) >= x1 ({x1})")
        if y0 >= y1:
            warnings.append(f"{name}: y0 ({y0}) >= y1 ({y1})")
        if x0 < 0 or y0 < 0:
            warnings.append(f"{name}: negative coordinate in rect {rect}")
        if x1 > pw:
            warnings.append(f"{name}: x1 ({x1}) exceeds page width ({pw})")
        if y1 > ph:
            warnings.append(f"{name}: y1 ({y1}) exceeds page height ({ph})")

        # Type check
        ftype = f.get("type", "")
        if ftype not in ("text", "checkbox"):
            warnings.append(f"{name}: unknown type '{ftype}'")

    return warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_form(form_key: str, output_dir: Path, verbose: bool = True) -> Path:
    """Generate and write field definitions for one form.

    Returns the path of the written file.
    """
    entry = FORM_BUILDERS[form_key]
    builder = entry["builder"]
    output_file = output_dir / entry["output_file"]

    if verbose:
        print(f"Generating: {entry['description']} ...")

    form_data = builder()

    # Validate
    warnings = validate_fields(form_data)
    if warnings:
        print(f"  Warnings for {form_key}:")
        for w in warnings:
            print(f"    - {w}")

    field_count = len(form_data.get("fields", []))

    # Write
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as fp:
        json.dump(form_data, fp, indent=2)
        fp.write("\n")

    if verbose:
        print(f"  Wrote {field_count} fields to {output_file}")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate field definition JSON files for MA court financial statement PDFs."
    )
    parser.add_argument(
        "--form",
        choices=list(FORM_BUILDERS.keys()),
        help="Generate definitions for a specific form only.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Generate definitions for all implemented forms (default behavior when no --form given).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        default=False,
        help="Validate existing field definition files without regenerating.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    if args.validate_only:
        # Validate existing files
        any_warnings = False
        for form_key, entry in FORM_BUILDERS.items():
            fpath = output_dir / entry["output_file"]
            if not fpath.exists():
                continue
            print(f"Validating: {fpath}")
            with open(fpath, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            warnings = validate_fields(data)
            if warnings:
                any_warnings = True
                for w in warnings:
                    print(f"  - {w}")
            else:
                print(f"  OK ({len(data.get('fields', []))} fields)")
        sys.exit(1 if any_warnings else 0)

    # Determine which forms to generate
    if args.form:
        form_keys = [args.form]
    else:
        # Default: generate all implemented forms (skip unimplemented)
        form_keys = []
        for key, entry in FORM_BUILDERS.items():
            try:
                entry["builder"]
                form_keys.append(key)
            except Exception:
                pass
        # Filter to only those that won't raise NotImplementedError
        implemented = []
        for key in form_keys:
            try:
                # Quick test: can we call it?
                FORM_BUILDERS[key]["builder"]()
                implemented.append(key)
            except NotImplementedError:
                pass
            except Exception:
                implemented.append(key)  # let it fail loudly during generation
        form_keys = implemented if not args.form else form_keys

    if not form_keys:
        print("No forms to generate. Use --form to specify one.")
        sys.exit(1)

    for key in form_keys:
        try:
            generate_form(key, output_dir)
        except NotImplementedError as e:
            print(f"Skipping {key}: {e}")
        except Exception as e:
            print(f"Error generating {key}: {e}", file=sys.stderr)
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
