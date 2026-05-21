Feature: Generated docassemble test

Scenario: Generated scenario
  Given I start the interview at "main.yml"
  And the user gets to "download cjd101a" with this data:
    | var | value | trigger |
    | acknowledged_information_use | True | |
    | user_ask_role | plaintiff | |
    | user_detailed_role_started_case | started | |
    | user_detailed_role | petitioner | |
    | users[0].name.first | Jane | |
    | users[0].name.last | Smith | |
    | users[0].name.suffix | Jr. | |
    | users[0].address | users[0].address if defined(\"users[0].address.address\") else None | |
    | users[0].address.address | 123 Main St | |
    | users[0].address.city | Boston | |
    | users[0].address.state | MA | |
    | users[0].address.zip | 02108 | |
    | x.mailing_address | x.address | |
    | x.service_address | x.address if defined(x.address.attr_name(\"address\")) else None | |
    | users[0].phone_number | 6175551212 | |
    | users[0].email | user@example.com | |
    | dont_know_docket_number | True | |
    | dont_know_case_number | True | |
    | x.name.first | Jane | |
    | x.name.last | Smith | |
    | x.name.suffix | Jr. | |
    | children.target_number | 1 | |
    | children[0].name.first | Jane | |
    | children[0].name.last | Smith | |
    | children[0].name.suffix | Jr. | |
    | witnesses.target_number | 1 | |
    | witnesses[0].name.first | Jane | |
    | witnesses[0].name.last | Smith | |
    | witnesses[0].name.suffix | Jr. | |
    | x[0].name.first | Jane | |
    | x[0].name.last | Smith | |
    | x[0].name.suffix | Jr. | |
    | other_parties[0].name.first | Jane | |
    | other_parties[0].name.last | Smith | |
    | other_parties[0].name.last | Smith | other_parties[0].name.first |
    | other_parties[0].name.suffix | Jr. | |
    | other_parties[0].name.suffix | Jr. | other_parties[0].name.first |
    | x.address.address | 123 Main St | |
    | x.address.city | Boston | |
    | x.address.state | MA | |
    | x.address.zip | 02108 | |
    | x.address.country | US | |
    | x.phone_number | 6175551212 | |
    | x.email | user@example.com | |
    | signature_date | 01/02/2026 | |
    | x.gender | female | |
    | users[0].states_above_true['states_true'] | True | |
    | users[0].marital_status | married | |
    | x.marital_status | married | |
    | signature_choice | this_device | |
    | text_link | True | |
    | should_cc_user | True | |
    | x.has_no_file | True | |
    | users[0].language | en | |
    | x.language | en | |
    | marriage_date | 01/02/2026 | |
    | petitioners_last_living_together_date | 01/02/2026 | |
    | living_together | True | |
    | petitioners1_addressstate | AAAAA | |
    | petitioners1_addresszip | 11111111 | |
    | change_name_petitioners1 | True | |
    | petitioners2_addresszip | 11111111 | |
    | petitioners2_addressstate | AAAAA | |
    | change_name_petitioners2 | True | |
    | marriage_breakdown_date | 01/02/2026 | |
    | request_divorce_nofault | True | |
    | request_separation_agreement_approval | True | |
    | merge_agreement | True | |
    | surivive_agreement | True | |
    | additional_request | True | |
    | petitioners1_addressstate_2 | AAAAAAAA | |
    | petitioners1_addresszip_2 | 11111111 | |
    | petitioners2_addressstate_2 | AAAAAAAA | |
    | petitioners2_addresszip_2 | 11111111 | |
    | github_repo_name | docassemble-Cjd101A | |
    | interview_short_title | Married spouses jointly file for divorce. | |
    | allowed_courts | Probate and Family Court | |
    | user_role | plaintiff | |
    | petitioners[0].phone_number | 6175551212 | |
    | petitioners[1].phone_number | 6175551212 | |
    | interview_order_cjd101a | True | |
    | cjd101a_preview_question | True | |
    | signature_fields | petitioners[1].signature | |
    | petitioners.revisit | True | |
    | cjd101a_attachment.overflow_fields["previous_action_detail"].overflow_trigger | 252 | |
    | cjd101a_attachment.overflow_fields["previous_action_detail"].label | Previous action detail | |
    | cjd101a_attachment.overflow_fields.gathered | True | |
    | trial_court | YWxsX2NvdXJ0c1s2XQ | |
    | other_parties.target_number | 1 | |
    | petitioners.target_number | 2 | |
    | users.target_number | 2 | |
    | x.target_number | 1 | |
    | cjd101a_intro | True | |
    | children2_name_full_plus_birthdate | 01/02/2026 | |
    | children1_name_full_plus_birthdate | 01/02/2026 | |
    | children3_name_full_plus_birthdate | 01/02/2026 | |
    | children4_name_full_plus_birthdate | 01/02/2026 | |
    | users[1].name.first | Sample answer | |
    | users[1].name.last | Sample answer | users[1].name.first |
    | users[1].name.middle | Sample answer | users[1].name.first |
    | petitioners2_name_full_1 | Sample answer | |
    | petitioners1_name_full_1 | Sample answer | |
    | marriage_place | Sample answer | |
    | petitioners_last_living_together_place | Sample answer | |
    | petitioners1_addresson_one_line | Sample answer | |
    | petitioners1_addresscity | Sample answer | |
    | petitioners1_former_name | Sample answer | |
    | petitioners2_addresson_one_line | Sample answer | |
    | petitioners2_addresscity | Sample answer | |
    | petitioners2_former_name | Sample answer | |
    | previous_action_detail | Sample answer | |
    | additonal_request_detail | Sample answer | |
    | attorneys1_bbo_number | Sample answer | |
    | attorneys2_bbo_number | Sample answer | |
    | petitioners2_name_full_2 | Sample answer | |
    | petitioners1_name_full_2 | Sample answer | |
    | petitioners1_addresson_one_line_2 | Sample answer | |
    | petitioners2addresson_one_line_2 | Sample answer | |
    | petitioners1_addresscity_2 | Sample answer | |
    | petitioners2_addresscity_2 | Sample answer | |
    | users.there_is_another | True | |
    | other_parties[0].person_type | ALIndividual | other_parties[0].name.first |
    | other_parties[0].name.middle | Sample answer | other_parties[0].name.first |
