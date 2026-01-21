Feature: Financial statement short path

Scenario: Short form without Schedule A or Schedule B
  Given the max seconds for each Step is 90
  And I start the interview at "financial_statement.yml"
  Then I get to the question id "fs_download" with this data:
    | var | value | trigger |
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
    | has_self_employment_income | False | |
    | has_rental_income | False | |
    | motor_vehicles.there_are_any | False | |
    | pensions.there_are_any | False | |
    | other_assets.there_are_any | False | |
    | liabilities.there_are_any | False | |
    | has_attorney | False | |
  Then the question id should be "fs_download"
