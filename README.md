# docassemble.MATC1AUncontestedDivorce

A docassemble package for Massachusetts 1A uncontested divorce materials. This project aims to support the full set of forms and supporting documents needed for the 1A process:

- Joint Divorce Petition (CJD-101A)
- Separation Agreement
- Financial Statements (short & long forms) with Schedules A & B
- Child Care & Custody Disclosure
- Other required supporting documents

## Status

Ongoing work.

## What's Included

- **Interview YAML files** — the question flows, logic, and PDF field mappings
- **PDF form templates** — the court forms themselves
- **ALKiln test files** — `.feature` specs for automated testing
- **Test scenarios** — JSON definitions covering short form, long form, schedules, and various edge cases

## Testing

The package includes a CI pipeline (GitHub Actions) that runs on every push to `main`:

1. Static analysis — YAML syntax and interview logic validation
2. Runtime tests — spins up a docassemble server, installs the package, and runs all 9 test scenarios against the REST API

## Author

Court Forms Online

