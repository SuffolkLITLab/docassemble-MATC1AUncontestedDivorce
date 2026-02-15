#!/usr/bin/env python3
"""
Fill PDFs with sample data and save to output/ for visual inspection.
No docassemble server needed — immediate visual feedback on field placement.

Usage:
    python scripts/test_fill_pdf.py                  # Fill all available forms
    python scripts/test_fill_pdf.py --form short      # Fill specific form
    python scripts/test_fill_pdf.py --list-fields short  # List all field names
"""

import json
import sys
import argparse
from pathlib import Path

try:
    import pikepdf
    from pikepdf import String, Name
except ImportError:
    print("ERROR: pikepdf not installed. Run: pip install pikepdf")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "data" / "templates"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Form PDF filenames
FORM_PDFS = {
    "short": "financial_statement_short.pdf",
    "long": "financial_statement_long.pdf",
    "schedule_a": "financial_statement_schedule_a.pdf",
    "schedule_b": "financial_statement_schedule_b.pdf",
}

# ---------------------------------------------------------------------------
# Sample data for testing — realistic but clearly fake values
# Every single field is populated so we can see where ALL fields land.
# ---------------------------------------------------------------------------
SAMPLE_DATA = {
    "short": {
        # Header
        "trial_court_division": "Middlesex",
        "docket_number": "26-D-TEST-001",
        "plaintiff_petitioner_name": "Sam A. Tester",
        "defendant_petitioner_name": "Alex B. Tester",
        # Personal Info (page 0)
        "user_name": "Sam A. Tester",
        "user_ssn": "123-45-6789",
        "user_address_street": "123 Main Street",
        "user_address_city": "Cambridge",
        "user_address_state": "MA",
        "user_address_zip": "02139",
        "user_phone": "(617) 555-0100",
        "user_birthdate": "01/15/1985",
        "children_living_count": "2",
        "user_occupation": "Software Engineer",
        "user_employer_name": "Test Corp Inc.",
        "employer_address_street": "456 Tech Blvd",
        "employer_address_city": "Boston",
        "employer_address_state": "MA",
        "employer_address_zip": "02210",
        "employer_phone": "(617) 555-0200",
        "health_insurance_provider": "Blue Cross Blue Shield",
        # Income sub-type checkboxes (Section 2)
        "income_check_salary": True,
        "income_check_wages": True,
        "income_check_dividends": True,
        "income_check_interest": True,
        "income_check_trusts": True,
        "income_check_annuities": True,
        "income_check_pensions": True,
        "income_check_retirement": True,
        "income_check_disability": True,
        "income_check_unemployment": True,
        "income_check_workers_comp": True,
        "income_check_child_support": True,
        "income_check_alimony": True,
        # Division/Docket repeated on all pages
        "trial_court_division_p2": "Middlesex",
        "docket_number_p2": "24D-0001",
        "trial_court_division_p3": "Middlesex",
        "docket_number_p3": "24D-0001",
        "trial_court_division_p4": "Middlesex",
        "docket_number_p4": "24D-0001",
        # Income (Section 2)
        "income_base_pay": "1,200.00",
        "income_overtime": "150.00",
        "income_part_time": "0.00",
        "income_self_employment": "0.00",
        "income_tips": "0.00",
        "income_commissions": "75.00",
        "income_dividends": "25.00",
        "income_trusts": "0.00",
        "income_pensions": "0.00",
        "income_social_security": "0.00",
        "income_disability": "0.00",
        "income_public_assistance": "0.00",
        "income_child_support": "0.00",
        "income_rental": "0.00",
        "income_royalties": "0.00",
        "income_contributions": "0.00",
        "income_other": "0.00",
        "income_other_specify": "N/A",
        "income_total": "1,450.00",
        # Deductions (Section 3)
        "deduction_federal": "200.00",
        "deduction_federal_exemptions": "2",
        "deduction_state": "75.00",
        "deduction_state_exemptions": "2",
        "deduction_fica": "110.00",
        "deduction_medical": "85.00",
        "deduction_union": "0.00",
        "deduction_total": "470.00",
        # Section 4
        "adjusted_net_weekly": "980.00",
        # Other Deductions (Section 5)
        "other_deduction_credit_union": "0.00",
        "other_deduction_savings": "50.00",
        "other_deduction_retirement": "100.00",
        "other_deduction_other": "0.00",
        "other_deduction_other_specify": "N/A",
        "other_deduction_total": "150.00",
        # Section 6
        "net_weekly_income": "830.00",
        # Section 7
        "prior_year_gross": "68,500.00",
        "social_security_years": "15",
        # Expenses (Section 8)
        "expense_rent": "450.00",
        "expense_homeowner_insurance": "25.00",
        "expense_maintenance": "15.00",
        "expense_heat": "30.00",
        "expense_electricity": "25.00",
        "expense_telephone": "20.00",
        "expense_water": "10.00",
        "expense_food": "150.00",
        "expense_house_supplies": "15.00",
        "expense_laundry": "10.00",
        "expense_clothing": "20.00",
        "expense_life_insurance": "15.00",
        "expense_medical_insurance": "85.00",
        "expense_uninsured_medical": "10.00",
        "expense_incidentals": "15.00",
        "expense_motor_vehicle": "40.00",
        "expense_motor_payment": "75.00",
        "expense_child_care": "100.00",
        "expense_other": "0.00",
        "expense_other_explain": "N/A",
        "expense_total": "1,100.00",
        # Counsel Fees (Section 9)
        "counsel_retainer": "5,000.00",
        "counsel_fees_incurred": "3,200.00",
        "counsel_anticipated_from": "8,000.00",
        "counsel_anticipated_to": "12,000.00",
        # Assets (Section 10)
        "asset_real_estate_location": "123 Main St, Cambridge MA",
        "asset_real_estate_title": "Sam A. Tester",
        "asset_real_estate_fmv": "450,000.00",
        "asset_real_estate_mortgage": "280,000.00",
        "asset_real_estate_equity": "170,000.00",
        "asset_vehicle1_fmv": "18,000.00",
        "asset_vehicle1_loan": "8,000.00",
        "asset_vehicle1_equity": "10,000.00",
        "asset_vehicle2_fmv": "0.00",
        "asset_vehicle2_loan": "0.00",
        "asset_vehicle2_equity": "0.00",
        "asset_pension1_institution": "Fidelity 401(k)",
        "asset_pension1_account": "XXX-1234",
        "asset_pension2_institution": "",
        "asset_pension2_account": "",
        "asset_pension3_institution": "",
        "asset_pension3_account": "",
        "asset_annuity": "0.00",
        "asset_life_insurance_cash": "5,000.00",
        "asset_savings1_institution": "Bank of America Checking",
        "asset_savings1_account": "XXX-5678",
        "asset_savings2_institution": "Bank of America Savings",
        "asset_savings2_account": "XXX-9012",
        "asset_savings3_institution": "",
        "asset_savings3_account": "",
        "asset_other1": "Stock portfolio",
        "asset_other1_value": "15,000.00",
        "asset_other2": "",
        "asset_other2_value": "0.00",
        "asset_total": "668,000.00",
        # Liabilities (Section 11)
        "liability1_creditor": "Wells Fargo",
        "liability1_nature": "Mortgage",
        "liability1_date": "2018",
        "liability1_amount_due": "280,000.00",
        "liability1_weekly_payment": "350.00",
        "liability2_creditor": "Toyota Financial",
        "liability2_nature": "Auto Loan",
        "liability2_date": "2023",
        "liability2_amount_due": "8,000.00",
        "liability2_weekly_payment": "75.00",
        "liability3_creditor": "Visa",
        "liability3_nature": "Credit Card",
        "liability3_date": "Various",
        "liability3_amount_due": "4,500.00",
        "liability3_weekly_payment": "25.00",
        "liability4_creditor": "",
        "liability4_nature": "",
        "liability4_date": "",
        "liability4_amount_due": "",
        "liability4_weekly_payment": "",
        "liability_total_due": "292,500.00",
        "liability_total_weekly": "450.00",
        # Certification
        "cert_date": "02/11/2026",
        "cert_signature": "[Signature]",
        "attorney_date": "02/11/2026",
        "attorney_signature": "[Attorney Signature]",
        "attorney_name": "Jane Q. Lawyer",
        "attorney_address_street": "789 Legal Way",
        "attorney_address_city": "Boston",
        "attorney_address_state": "MA",
        "attorney_address_zip": "02108",
        "attorney_phone": "(617) 555-0300",
        "attorney_bbo": "654321",
    },
    "long": {
        # Header (page 0)
        "trial_court_division": "Middlesex",
        "docket_number": "26-D-TEST-001",
        "plaintiff_petitioner_name": "Sam A. Tester",
        "defendant_petitioner_name": "Alex B. Tester",
        # Personal Info (page 0)
        "user_name": "Sam A. Tester",
        "user_ssn": "123-45-6789",
        "user_address_street": "123 Main Street",
        "user_address_city": "Cambridge",
        "user_address_state": "MA",
        "user_address_zip": "02139",
        "user_phone": "(617) 555-0100",
        "user_birthdate": "01/15/1985",
        "children_living_count": "2",
        "user_occupation": "Software Engineer",
        "user_employer_name": "Test Corp Inc.",
        "employer_address_street": "456 Tech Blvd",
        "employer_address_city": "Boston",
        "employer_address_state": "MA",
        "employer_address_zip": "02210",
        "employer_phone": "(617) 555-0200",
        "health_insurance_yes": True,
        "health_insurance_no": False,
        "health_insurance_provider": "BCBS of MA",
        # Income sub-type checkboxes (page 0)
        "income_check_salary": True,
        "income_check_wages": True,
        "income_check_dividends": True,
        "income_check_interest": True,
        "income_check_trusts": False,
        "income_check_annuities": False,
        "income_check_pensions": False,
        "income_check_retirement": False,
        "income_check_disability": False,
        "income_check_unemployment": False,
        "income_check_workers_comp": False,
        "income_check_child_support": False,
        "income_check_alimony": False,
        # Division/Docket repeated on all pages
        "trial_court_division_p2": "Middlesex",
        "docket_number_p2": "26-D-TEST-001",
        "trial_court_division_p3": "Middlesex",
        "docket_number_p3": "26-D-TEST-001",
        "trial_court_division_p4": "Middlesex",
        "docket_number_p4": "26-D-TEST-001",
        "trial_court_division_p5": "Middlesex",
        "docket_number_p5": "26-D-TEST-001",
        "trial_court_division_p6": "Middlesex",
        "docket_number_p6": "26-D-TEST-001",
        "trial_court_division_p7": "Middlesex",
        "docket_number_p7": "26-D-TEST-001",
        "trial_court_division_p8": "Middlesex",
        "docket_number_p8": "26-D-TEST-001",
        "trial_court_division_p9": "Middlesex",
        "docket_number_p9": "26-D-TEST-001",
        # Expense sub-type checkboxes (page 2)
        "expense_check_maintenance": True,
        "expense_check_condo": False,
        "expense_check_water": True,
        "expense_check_sewer": True,
        "expense_check_propane": False,
        "expense_check_natural_gas": True,
        # Income (page 0)
        "income_base_pay": "1,200.00",
        "income_overtime": "150.00",
        "income_part_time": "0.00",
        "income_self_employment": "200.00",
        "income_tips": "0.00",
        "income_commissions": "75.00",
        "income_dividends": "25.00",
        "income_trusts": "0.00",
        "income_pensions": "0.00",
        "income_social_security": "0.00",
        "income_disability": "0.00",
        "income_public_assistance": "0.00",
        "income_child_support": "0.00",
        "income_rental": "400.00",
        "income_royalties": "0.00",
        "income_contributions": "0.00",
        "income_other": "50.00",
        "income_other_specify": "Freelance work",
        "income_total": "2,100.00",
        # Deductions (page 1) — long form has more categories
        "deduction_federal": "250.00",
        "deduction_federal_allowances": "2",
        "deduction_state": "95.00",
        "deduction_state_allowances": "2",
        "deduction_fica": "130.00",
        "deduction_medicare": "31.00",
        "deduction_medical": "85.00",
        "deduction_dental": "12.00",
        "deduction_vision": "5.00",
        "deduction_union": "25.00",
        "deduction_child_support": "0.00",
        "deduction_spousal_support": "0.00",
        "deduction_retirement": "150.00",
        "deduction_savings": "50.00",
        "deduction_deferred_comp": "0.00",
        "deduction_credit_union_loan": "0.00",
        "deduction_credit_union_savings": "25.00",
        "deduction_charity": "10.00",
        "deduction_life_insurance": "15.00",
        "deduction_other": "0.00",
        "deduction_other_specify": "",
        "deduction_total": "883.00",
        # Net income (page 1)
        "net_income_gross": "2,100.00",
        "net_income_deductions": "883.00",
        "net_income_net": "1,217.00",
        # Prior year (page 1)
        "prior_year_gross": "95,000.00",
        "social_security_years": "18",
        # Expenses (pages 2-3) — long form has many more categories
        "expense_rent": "550.00",
        "expense_mortgage": "0.00",
        "expense_property_tax": "85.00",
        "expense_home_insurance": "30.00",
        "expense_maintenance_fees": "15.00",
        "expense_heat": "35.00",
        "expense_electric": "30.00",
        "expense_gas": "10.00",
        "expense_phone": "25.00",
        "expense_water": "12.00",
        "expense_food": "175.00",
        "expense_supplies": "20.00",
        "expense_laundry": "10.00",
        "expense_dry_cleaning": "5.00",
        "expense_clothing": "25.00",
        "expense_life_insurance": "15.00",
        "expense_medical_insurance": "85.00",
        "expense_dental_insurance": "12.00",
        "expense_vision_insurance": "5.00",
        "expense_uninsured_medical": "15.00",
        "expense_uninsured_dental": "8.00",
        "expense_motor_vehicle": "45.00",
        "expense_fuel": "30.00",
        "expense_vehicle_insurance": "25.00",
        "expense_vehicle_maintenance": "10.00",
        "expense_loan_payments": "75.00",
        "expense_entertainment": "20.00",
        "expense_vacation": "15.00",
        "expense_cable": "18.00",
        "expense_child_support": "0.00",
        "expense_child_day_care": "125.00",
        "expense_child_education": "30.00",
        "expense_education_self": "0.00",
        "expense_uniforms": "5.00",
        "expense_employment_travel": "10.00",
        "expense_continuing_education": "0.00",
        "expense_employment_other": "0.00",
        "expense_employment_other_specify": "",
        "expense_lottery": "2.00",
        "expense_charity": "10.00",
        "expense_child_allowance": "15.00",
        "expense_visitation_travel": "0.00",
        "expense_other": "10.00",
        "expense_other_specify": "Miscellaneous",
        "expense_total": "1,732.00",
        # Counsel Fees (page 3)
        "counsel_retainer": "7,500.00",
        "counsel_fees_incurred": "4,800.00",
        "counsel_anticipated_from": "10,000.00",
        "counsel_anticipated_to": "18,000.00",
        # Primary Real Estate (pages 3-4)
        "primary_re_address": "123 Main Street",
        "primary_re_city": "Cambridge",
        "primary_re_state": "MA",
        "primary_re_title": "Sam A. Tester & Alex B. Tester",
        "primary_re_purchase_price": "325,000.00",
        "primary_re_purchase_year": "2015",
        "primary_re_assessed_value": "480,000.00",
        "primary_re_assessment_date": "01/01/2025",
        "primary_re_fmv": "525,000.00",
        "primary_re_first_mortgage": "210,000.00",
        "primary_re_second_mortgage": "0.00",
        "primary_re_equity": "315,000.00",
        # Secondary Real Estate (page 4)
        "secondary_re_address": "45 Lake Road",
        "secondary_re_city": "Wareham",
        "secondary_re_state": "MA",
        "secondary_re_title": "Sam A. Tester",
        "secondary_re_purchase_price": "175,000.00",
        "secondary_re_purchase_year": "2020",
        "secondary_re_assessed_value": "195,000.00",
        "secondary_re_assessment_date": "01/01/2025",
        "secondary_re_fmv": "210,000.00",
        "secondary_re_first_mortgage": "120,000.00",
        "secondary_re_second_mortgage": "0.00",
        "secondary_re_equity": "90,000.00",
        # Vehicles (page 4)
        "vehicle1_type": "Sedan",
        "vehicle1_make": "Toyota",
        "vehicle1_model": "Camry",
        "vehicle1_purchase_price": "28,000.00",
        "vehicle1_purchase_year": "2022",
        "vehicle1_fmv": "22,000.00",
        "vehicle1_loan": "12,000.00",
        "vehicle1_equity": "10,000.00",
        "vehicle2_type": "SUV",
        "vehicle2_make": "Honda",
        "vehicle2_model": "CR-V",
        "vehicle2_purchase_price": "32,000.00",
        "vehicle2_purchase_year": "2023",
        "vehicle2_fmv": "29,000.00",
        "vehicle2_loan": "20,000.00",
        "vehicle2_equity": "9,000.00",
        # Pensions (page 4)
        "pension_institution": "Fidelity 401(k)",
        "pension_account": "XXX-1234",
        "pension_beneficiary": "Alex B. Tester",
        "pension_defined_benefit": "0.00",
        "pension_defined_contribution": "85,000.00",
        "pension_dc_institution": "Vanguard 403(b)",
        "pension_dc_account": "XXX-5678",
        "pension_dc_beneficiary": "Sam A. Tester",
        # Other Assets (pages 5-6) — long form has 28+ asset categories
        # Page 5: financial assets with institution/account/beneficiary columns
        "asset_checking": "4,500.00",
        "checking_institution": "Bank of America",
        "checking_account": "XXX-1234",
        "checking_beneficiary": "N/A",
        "asset_savings": "12,000.00",
        "savings_institution": "Bank of America",
        "savings_account": "XXX-5678",
        "savings_beneficiary": "N/A",
        "asset_cash": "200.00",
        "cash_institution": "N/A",
        "cash_account": "N/A",
        "cash_beneficiary": "N/A",
        "asset_cd": "5,000.00",
        "cd_institution": "Citizens Bank",
        "cd_account": "XXX-9012",
        "cd_beneficiary": "Alex B. Tester",
        "asset_credit_union": "1,500.00",
        "credit_union_institution": "Metro CU",
        "credit_union_account": "XXX-3456",
        "credit_union_beneficiary": "N/A",
        "asset_escrow": "3,200.00",
        "escrow_institution": "Wells Fargo",
        "escrow_account": "XXX-7890",
        "escrow_beneficiary": "N/A",
        "asset_stocks": "15,000.00",
        "stocks_institution": "Fidelity",
        "stocks_account": "XXX-2345",
        "stocks_beneficiary": "Alex B. Tester",
        "asset_bonds": "0.00",
        "bonds_institution": "",
        "bonds_account": "",
        "bonds_beneficiary": "",
        "asset_bond_funds": "2,500.00",
        "bond_funds_institution": "Vanguard",
        "bond_funds_account": "XXX-6789",
        "bond_funds_beneficiary": "N/A",
        "asset_notes": "0.00",
        "notes_institution": "",
        "notes_account": "",
        "notes_beneficiary": "",
        "asset_brokerage": "8,000.00",
        "brokerage_institution": "Charles Schwab",
        "brokerage_account": "XXX-0123",
        "brokerage_beneficiary": "N/A",
        "asset_money_market": "3,000.00",
        "money_market_institution": "Ally Bank",
        "money_market_account": "XXX-4567",
        "money_market_beneficiary": "N/A",
        # Page 6: financial assets with institution/account/beneficiary columns
        "asset_us_savings_bonds": "1,000.00",
        "us_savings_bonds_institution": "US Treasury",
        "us_savings_bonds_account": "XXX-8901",
        "us_savings_bonds_beneficiary": "Alex B. Tester",
        "asset_ira": "45,000.00",
        "ira_institution": "Fidelity",
        "ira_account": "XXX-2345",
        "ira_beneficiary": "Alex B. Tester",
        "asset_keogh": "0.00",
        "keogh_institution": "",
        "keogh_account": "",
        "keogh_beneficiary": "",
        "asset_profit_sharing": "0.00",
        "profit_sharing_institution": "",
        "profit_sharing_account": "",
        "profit_sharing_beneficiary": "",
        "asset_deferred_comp": "0.00",
        "deferred_comp_institution": "",
        "deferred_comp_account": "",
        "deferred_comp_beneficiary": "",
        "asset_other_retirement": "0.00",
        "other_retirement_institution": "",
        "other_retirement_account": "",
        "other_retirement_beneficiary": "",
        "asset_annuity": "0.00",
        "annuity_institution": "",
        "annuity_account": "",
        "annuity_beneficiary": "",
        "asset_life_insurance_cash": "8,500.00",
        "life_insurance_cash_institution": "Northwestern Mutual",
        "life_insurance_cash_account": "POL-12345",
        "life_insurance_cash_beneficiary": "Alex B. Tester",
        "asset_judgments": "0.00",
        "asset_inheritances": "0.00",
        "asset_jewelry": "2,000.00",
        "asset_safe_deposit": "500.00",
        "asset_firearms": "0.00",
        "asset_collections": "1,500.00",
        "asset_tools": "800.00",
        "asset_crops": "0.00",
        "asset_furnishings": "10,000.00",
        "asset_arts": "0.00",
        "asset_other1": "Cryptocurrency",
        "asset_other1_value": "3,000.00",
        "asset_other2": "",
        "asset_other2_value": "0.00",
        "asset_total": "932,200.00",
        # Liabilities (page 7) — long form has 11 rows
        "liability1_creditor": "Wells Fargo",
        "liability1_nature": "1st Mortgage",
        "liability1_date": "2015",
        "liability1_amount_due": "210,000.00",
        "liability1_weekly_payment": "285.00",
        "liability2_creditor": "Wareham CU",
        "liability2_nature": "2nd Mortgage",
        "liability2_date": "2020",
        "liability2_amount_due": "120,000.00",
        "liability2_weekly_payment": "175.00",
        "liability3_creditor": "Toyota Financial",
        "liability3_nature": "Auto Loan",
        "liability3_date": "2022",
        "liability3_amount_due": "12,000.00",
        "liability3_weekly_payment": "60.00",
        "liability4_creditor": "Honda Financial",
        "liability4_nature": "Auto Loan",
        "liability4_date": "2023",
        "liability4_amount_due": "20,000.00",
        "liability4_weekly_payment": "85.00",
        "liability5_creditor": "Chase Visa",
        "liability5_nature": "Credit Card",
        "liability5_date": "2019",
        "liability5_amount_due": "6,500.00",
        "liability5_weekly_payment": "30.00",
        "liability6_creditor": "Discover",
        "liability6_nature": "Credit Card",
        "liability6_date": "2021",
        "liability6_amount_due": "3,200.00",
        "liability6_weekly_payment": "15.00",
        "liability7_creditor": "Navient",
        "liability7_nature": "Student Loan",
        "liability7_date": "2008",
        "liability7_amount_due": "18,000.00",
        "liability7_weekly_payment": "50.00",
        "liability8_creditor": "",
        "liability8_nature": "",
        "liability8_date": "",
        "liability8_amount_due": "",
        "liability8_weekly_payment": "",
        "liability9_creditor": "",
        "liability9_nature": "",
        "liability9_date": "",
        "liability9_amount_due": "",
        "liability9_weekly_payment": "",
        "liability10_creditor": "",
        "liability10_nature": "",
        "liability10_date": "",
        "liability10_amount_due": "",
        "liability10_weekly_payment": "",
        "liability11_creditor": "",
        "liability11_nature": "",
        "liability11_date": "",
        "liability11_amount_due": "",
        "liability11_weekly_payment": "",
        "liability_total_due": "389,700.00",
        "liability_total_weekly": "700.00",
        # Certification (page 8)
        "cert_date": "02/11/2026",
        "cert_signature": "[Signature]",
        # Notary (page 8)
        "notary_county": "Middlesex",
        "notary_name": "Maria C. Notary",
        "notary_date": "02/11/2026",
        "notary_signature": "[Notary Signature]",
        "notary_commission_expires": "06/30/2028",
        # Attorney (page 8)
        "attorney_date": "02/11/2026",
        "attorney_signature": "[Attorney Signature]",
        "attorney_name": "Jane Q. Lawyer, Esq.",
        "attorney_address": "789 Legal Way, Suite 300",
        "attorney_city": "Boston",
        "attorney_state": "MA",
        "attorney_zip": "02108",
        "attorney_phone": "(617) 555-0300",
        "attorney_bbo": "654321",
    },
    "schedule_a": {
        # Header
        "sa_name": "Sam A. Tester",
        "sa_docket_number": "26-D-TEST-001",
        # Gross receipts
        "sa_gross_monthly_receipts": "8,500.00",
        # Expenses (29 categories)
        "sa_cost_goods": "1,200.00",
        "sa_advertising": "150.00",
        "sa_bad_debts": "0.00",
        "sa_motor_vehicle_gas": "180.00",
        "sa_motor_vehicle_insurance": "95.00",
        "sa_motor_vehicle_maintenance": "40.00",
        "sa_motor_vehicle_registration": "15.00",
        "sa_commissions": "0.00",
        "sa_depletion": "0.00",
        "sa_dues_publications": "25.00",
        "sa_employee_benefits": "0.00",
        "sa_freight": "0.00",
        "sa_insurance_other": "120.00",
        "sa_insurance_other_specify": "General liability",
        "sa_mortgage_interest": "0.00",
        "sa_loan_interest": "45.00",
        "sa_legal_professional": "200.00",
        "sa_office_expenses": "85.00",
        "sa_laundry_cleaning": "0.00",
        "sa_pension_profit_sharing": "0.00",
        "sa_rent_leased_equipment": "150.00",
        "sa_machinery_equipment": "0.00",
        "sa_other_business_property": "0.00",
        "sa_repairs": "30.00",
        "sa_supplies": "75.00",
        "sa_taxes": "350.00",
        "sa_travel": "120.00",
        "sa_meals_entertainment": "60.00",
        "sa_utilities_phones": "95.00",
        "sa_wages": "0.00",
        "sa_other_expenses": "50.00",
        "sa_other_expenses_specify": "Software subscriptions",
        # Totals
        "sa_total_monthly_expenses": "3,085.00",
        "sa_weekly_business_income": "1,259.30",
        # Business nature
        "sa_business_nature": "Technology consulting",
        # Seasonal
        "sa_is_seasonal_yes": False,
        "sa_is_seasonal_no": True,
        "sa_jan_income_pct": "",
        "sa_jan_expense_pct": "",
        "sa_feb_income_pct": "",
        "sa_feb_expense_pct": "",
        "sa_mar_income_pct": "",
        "sa_mar_expense_pct": "",
        "sa_apr_income_pct": "",
        "sa_apr_expense_pct": "",
        "sa_may_income_pct": "",
        "sa_may_expense_pct": "",
        "sa_jun_income_pct": "",
        "sa_jun_expense_pct": "",
        "sa_jul_income_pct": "",
        "sa_jul_expense_pct": "",
        "sa_aug_income_pct": "",
        "sa_aug_expense_pct": "",
        "sa_sep_income_pct": "",
        "sa_sep_expense_pct": "",
        "sa_oct_income_pct": "",
        "sa_oct_expense_pct": "",
        "sa_nov_income_pct": "",
        "sa_nov_expense_pct": "",
        "sa_dec_income_pct": "",
        "sa_dec_expense_pct": "",
        # Accounting
        "sa_calendar_year": True,
        "sa_fiscal_year": False,
        "sa_fiscal_start": "",
        "sa_fiscal_end": "",
        # Year-to-date
        "sa_gross_receipts_ytd": "12,750.00",
        "sa_gross_expenses_ytd": "4,628.00",
    },
    "schedule_b": {
        # Header
        "sb_name": "Sam A. Tester",
        "sb_docket_number": "26-D-TEST-001",
        # Rent
        "sb_annual_rent_received": "24,000.00",
        # Expenses (14 categories)
        "sb_advertising": "300.00",
        "sb_motor_vehicle_travel": "150.00",
        "sb_insurance": "1,200.00",
        "sb_cleaning_maintenance": "800.00",
        "sb_commissions": "0.00",
        "sb_mortgage_interest": "4,800.00",
        "sb_other_interest_specify": "HELOC",
        "sb_other_interest": "600.00",
        "sb_legal_professional": "500.00",
        "sb_repairs": "1,500.00",
        "sb_supplies": "200.00",
        "sb_taxes": "3,600.00",
        "sb_utilities": "2,400.00",
        "sb_wages": "0.00",
        "sb_other_expenses_specify": "Landscaping",
        "sb_other_expenses": "1,200.00",
        # Totals
        "sb_total_annual_expenses": "17,250.00",
        "sb_weekly_rental_income": "129.81",
    },
}


def get_pdf_fields(pdf_path):
    """Extract all field names from a PDF."""
    pdf = pikepdf.open(str(pdf_path))
    if "/AcroForm" not in pdf.Root:
        pdf.close()
        return []
    fields = []
    for f in pdf.Root["/AcroForm"]["/Fields"]:
        name = str(f.get("/T", ""))
        ftype = str(f.get("/FT", ""))
        fields.append((name, ftype))
    pdf.close()
    return fields


def fill_pdf(pdf_path, data, output_path):
    """Fill a PDF with data and save to output path."""
    pdf = pikepdf.open(str(pdf_path))
    if "/AcroForm" not in pdf.Root:
        print(f"  No AcroForm in {pdf_path.name}")
        pdf.close()
        return False

    fields = list(pdf.Root["/AcroForm"]["/Fields"])
    filled = 0
    unfilled = []
    total = len(fields)

    for field in fields:
        name = str(field.get("/T", ""))
        ftype = str(field.get("/FT", ""))

        if name in data:
            value = data[name]
            if ftype == "/Btn":
                # Checkbox: set to /Yes or /Off
                if value in (True, "True", "true", "Yes", "yes", "1"):
                    field["/V"] = Name("/Yes")
                    field["/AS"] = Name("/Yes")
                else:
                    field["/V"] = Name("/Off")
                    field["/AS"] = Name("/Off")
            else:
                # Text field
                field["/V"] = String(str(value))
            filled += 1
        else:
            unfilled.append(name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(str(output_path))
    pdf.close()

    print(f"  {pdf_path.name}: filled {filled}/{total} fields -> {output_path.name}")
    if unfilled:
        print(f"    Unfilled ({len(unfilled)}): {', '.join(unfilled[:10])}")
        if len(unfilled) > 10:
            print(f"    ... and {len(unfilled) - 10} more")
    return True


def list_fields(form_name):
    """List all field names in a form's PDF."""
    pdf_name = FORM_PDFS.get(form_name)
    if not pdf_name:
        print(f"Unknown form: {form_name}")
        return

    pdf_path = TEMPLATES_DIR / pdf_name
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return

    fields = get_pdf_fields(pdf_path)
    print(f"\n=== {pdf_name}: {len(fields)} fields ===")
    for name, ftype in fields:
        type_label = "checkbox" if ftype == "/Btn" else "text"
        has_data = name in SAMPLE_DATA.get(form_name, {})
        marker = " [HAS DATA]" if has_data else " [NO DATA]"
        print(f"  [{type_label}] {name}{marker}")

    covered = sum(1 for n, _ in fields if n in SAMPLE_DATA.get(form_name, {}))
    print(f"\n  Sample data coverage: {covered}/{len(fields)} fields")


def fill_all(forms=None):
    """Fill all available form PDFs with sample data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if forms is None:
        forms = list(FORM_PDFS.keys())

    for form_name in forms:
        pdf_name = FORM_PDFS[form_name]
        pdf_path = TEMPLATES_DIR / pdf_name
        if not pdf_path.exists():
            print(f"  SKIP: {form_name} ({pdf_name} not found)")
            continue

        data = SAMPLE_DATA.get(form_name, {})
        if not data:
            print(f"  SKIP: {form_name} (no sample data)")
            continue

        output_path = OUTPUT_DIR / f"FILLED_{pdf_name}"
        fill_pdf(pdf_path, data, output_path)


def main():
    parser = argparse.ArgumentParser(description="Fill PDFs with sample test data")
    parser.add_argument("--form", choices=list(FORM_PDFS.keys()),
                        help="Fill a specific form")
    parser.add_argument("--list-fields", metavar="FORM",
                        choices=list(FORM_PDFS.keys()),
                        help="List all field names in a form's PDF")
    args = parser.parse_args()

    if args.list_fields:
        list_fields(args.list_fields)
    elif args.form:
        print(f"=== Filling: {args.form} ===")
        fill_all([args.form])
    else:
        print("=== Filling all available forms ===")
        fill_all()

    if not args.list_fields:
        print(f"\nOutput directory: {OUTPUT_DIR}")
        print("Open the FILLED_*.pdf files in Preview to verify field placement.")


if __name__ == "__main__":
    main()
