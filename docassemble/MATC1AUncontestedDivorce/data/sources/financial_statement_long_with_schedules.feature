Feature: Financial statement long path with schedules

Scenario: Long form with Schedule A and Schedule B
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 100000 | |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_has_health_insurance | False | |
    | financial_cadence_default | weekly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 1500 | |
    | income_list[0].use_default_cadence | True | |
    | long_expense_list.selected_types['rent'] | True | |
    | long_expense_list[0].source | rent | |
    | long_expense_list[0].value | 900 | |
    | long_expense_list[0].times_per_year | 52 | |
    | has_self_employment_income | True | |
    | has_rental_income | True | |
    | schedule_a_gross_monthly_receipts | 5000 | |
    | schedule_a_expenses.there_are_any | False | |
    | schedule_a_is_seasonal | False | |
    | schedule_a_accounting_basis | calendar | |
    | schedule_b_annual_rent_received | 12000 | |
    | schedule_b_expenses.there_are_any | False | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | will_notarize_now | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Long form with schedules and employer details
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 120000 | |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_employer_name | Acme Corp | |
    | user_job_title | Analyst | |
    | user_employer_address_street | 10 Market St | |
    | user_employer_address_city | Boston | |
    | user_employer_address_state | MA | |
    | user_employer_address_zip | 02110 | |
    | user_employer_phone | 617-555-0101 | |
    | user_has_health_insurance | False | |
    | financial_cadence_default | weekly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 1700 | |
    | income_list[0].use_default_cadence | True | |
    | long_expense_list.selected_types['rent'] | True | |
    | long_expense_list[0].source | rent | |
    | long_expense_list[0].value | 950 | |
    | long_expense_list[0].times_per_year | 52 | |
    | has_self_employment_income | True | |
    | has_rental_income | True | |
    | schedule_a_gross_monthly_receipts | 5000 | |
    | schedule_a_expenses.there_are_any | False | |
    | schedule_a_is_seasonal | False | |
    | schedule_a_accounting_basis | calendar | |
    | schedule_b_annual_rent_received | 12000 | |
    | schedule_b_expenses.there_are_any | False | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | will_notarize_now | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Long form with zero-valued expense entry
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 90000 | |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_has_health_insurance | False | |
    | financial_cadence_default | weekly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 1600 | |
    | income_list[0].use_default_cadence | True | |
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | long_expense_list.selected_types['rent'] | True | |
    | long_expense_list[0].source | rent | |
    | long_expense_list[0].value | 0 | |
    | long_expense_list[0].times_per_year | 52 | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | will_notarize_now | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Long form with zero-valued income entry
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 90000 | |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_has_health_insurance | False | |
    | financial_cadence_default | weekly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 0 | |
    | income_list[0].use_default_cadence | True | |
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | long_expense_list.selected_types['rent'] | True | |
    | long_expense_list[0].source | rent | |
    | long_expense_list[0].value | 900 | |
    | long_expense_list[0].times_per_year | 52 | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | will_notarize_now | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Long form self-employment only with deep branch coverage
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 130000 | |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_has_health_insurance | False | |
    | financial_cadence_default | weekly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 1800 | |
    | income_list[0].use_default_cadence | True | |
    | has_self_employment_income | True | |
    | has_rental_income | False | |
    | schedule_a_gross_monthly_receipts | 8000 | |
    | schedule_a_expenses.there_are_any | True | |
    | schedule_a_expenses[0].source | utilities_phones | |
    | schedule_a_expenses[0].value | 1200 | |
    | schedule_a_expenses.there_is_another | False | |
    | schedule_a_is_seasonal | True | |
    | schedule_a_january_income_pct | 10 | |
    | schedule_a_january_expense_pct | 8 | |
    | schedule_a_accounting_basis | fiscal | |
    | schedule_a_fiscal_start | 2025-07-01 | |
    | schedule_a_fiscal_end | 2026-06-30 | |
    | schedule_a_gross_receipts_ytd | 45000 | |
    | schedule_a_gross_expenses_ytd | 12000 | |
    | long_expense_list.selected_types['rent'] | True | |
    | long_expense_list[0].source | rent | |
    | long_expense_list[0].value | 1000 | |
    | long_expense_list[0].times_per_year | 52 | |
    | motor_vehicles.there_are_any | True | |
    | motor_vehicles[0].vehicle_type | car | |
    | motor_vehicles[0].make | Toyota | |
    | motor_vehicles[0].model | Camry | |
    | motor_vehicles[0].fair_market_value | 12000 | |
    | motor_vehicles[0].outstanding_loan | 5000 | |
    | motor_vehicles[0].equity | 7000 | |
    | motor_vehicles.there_is_another | False | |
    | pensions.there_are_any | True | |
    | pensions[0].institution | Fidelity | |
    | pensions[0].account_number | 1234 | |
    | pensions[0].defined_contribution_amount | 20000 | |
    | pensions.there_is_another | False | |
    | other_assets.there_are_any | True | |
    | other_assets[0].asset_type | checking | |
    | other_assets[0].institution | Bank of America | |
    | other_assets[0].current_balance | 1500 | |
    | other_assets.there_is_another | False | |
    | liabilities.there_are_any | True | |
    | liabilities[0].creditor | Visa | |
    | liabilities[0].amount_due | 3000 | |
    | liabilities[0].weekly_payment | 100 | |
    | liabilities.there_is_another | False | |
    | will_notarize_now | True | |
    | notary_county | Suffolk | will_notarize_now |
    | notary_name | Jane Notary | will_notarize_now |
    | notary_commission_expires | 2028-12-31 | will_notarize_now |
    | has_attorney | True | |
    | attorney_signature | Pat Counsel | has_attorney |
    | attorney_print_name | Pat Counsel | has_attorney |
    | attorney_address | 100 Court St, Boston MA | has_attorney |
    | attorney_phone | 6175552222 | has_attorney |
    | attorney_bbo | 123456 | has_attorney |
  Then the question id should be "fs_download"

Scenario: Long form rental-only path with Schedule B expense item
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 110000 | |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_has_health_insurance | False | |
    | financial_cadence_default | weekly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 1700 | |
    | income_list[0].use_default_cadence | True | |
    | has_self_employment_income | False | |
    | has_rental_income | True | |
    | schedule_b_annual_rent_received | 24000 | |
    | schedule_b_expenses.there_are_any | True | |
    | schedule_b_expenses[0].source | repairs | |
    | schedule_b_expenses[0].value | 4000 | |
    | schedule_b_expenses.there_is_another | False | |
    | long_expense_list.selected_types['rent'] | True | |
    | long_expense_list[0].source | rent | |
    | long_expense_list[0].value | 950 | |
    | long_expense_list[0].times_per_year | 52 | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | will_notarize_now | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Long form with unknown annual income and manual income cadence
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income_unknown | True | |
    | gross_annual_income_estimate | 98000 | gross_annual_income_unknown |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_has_health_insurance | True | |
    | user_health_insurance_provider | Blue Cross | user_has_health_insurance |
    | financial_cadence_default | monthly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 4200 | |
    | income_list[0].use_default_cadence | False | |
    | income_list[0].times_per_year | 12 | income_list[0].use_default_cadence |
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | long_expense_list.selected_types['rent'] | True | |
    | long_expense_list[0].source | rent | |
    | long_expense_list[0].value | 1600 | |
    | long_expense_list[0].times_per_year | 12 | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | will_notarize_now | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"
