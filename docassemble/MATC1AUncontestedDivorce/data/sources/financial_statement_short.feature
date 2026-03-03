Feature: Financial statement short path

Scenario: Short form without Schedule A or Schedule B
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 50000 | |
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
    | income_list[0].value | 900 | |
    | income_list[0].use_default_cadence | True | |
    | expense_list.selected_types['rent'] | True | |
    | expense_list[0].source | rent | |
    | expense_list[0].value | 700 | |
    | expense_list[0].times_per_year | 52 | |
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Short form with employer details
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 52000 | |
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
    | income_list[0].value | 950 | |
    | income_list[0].use_default_cadence | True | |
    | expense_list.selected_types['rent'] | True | |
    | expense_list[0].source | rent | |
    | expense_list[0].value | 725 | |
    | expense_list[0].times_per_year | 52 | |
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Short form with zero-valued income and expense entries
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 50000 | |
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
    | expense_list.selected_types['rent'] | True | |
    | expense_list[0].source | rent | |
    | expense_list[0].value | 0 | |
    | expense_list[0].times_per_year | 52 | |
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"

Scenario: Short form with children, health insurance, and manual income cadence
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | gross_annual_income | 60000 | |
    | trial_court.name | Probate and Family Court | |
    | users[0].name.first | Sam | |
    | users[0].name.last | Tester | |
    | other_parties[0].name.first | Alex | |
    | other_parties[0].name.last | Tester | |
    | users[0].birthdate | 1990-01-01 | |
    | user_has_children | True | |
    | children_living_with_user_count | 2 | user_has_children |
    | users[0].address.address | 1 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | user_has_health_insurance | True | |
    | user_health_insurance_provider | Blue Cross | user_has_health_insurance |
    | financial_cadence_default | biweekly | |
    | income_list.selected_types['wages'] | True | |
    | income_list[0].source | wages | |
    | income_list[0].value | 1800 | |
    | income_list[0].use_default_cadence | False | |
    | income_list[0].times_per_year | 26 | income_list[0].use_default_cadence |
    | expense_list.selected_types['rent'] | True | |
    | expense_list[0].source | rent | |
    | expense_list[0].value | 1400 | |
    | expense_list[0].times_per_year | 12 | |
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"
