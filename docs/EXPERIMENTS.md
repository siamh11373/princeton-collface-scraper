# Experiment log

This log contains sanitized facts only. Do not include credentials, cookies, tokens, student
names, profile values, authenticated HTML, screenshots, or response bodies.

## 2026-09-14 - environment

- The project directory did not exist before scaffolding.
- `collface-scraper` was not installed on the current PATH.
- The system `python3` is 3.9.6.
- `uv` located an isolated CPython 3.12 runtime.
- The GitHub CLI was reauthenticated and the private assessment repository was created.

## 2026-09-14 - verification

- Ruff lint and format checks pass.
- All 53 synthetic tests pass, including CAS/Duo failures, exact service callbacks, session
  renewal, discovery, dynamic
  Unicode fields, hidden-value exclusion, `Retry-After`,
  interruption/resume, retries, reconciliation, and CSV round-trip validation.
- A clean clone installed under Python 3.12.13, passed its command-line doctor check and Ruff
  checks, and passed all 36 tests.
- Authenticated normal-Chrome traffic established one exhaustive response with an authoritative
  total of 5,768 records and five rendered-card fields. A temporary local response was processed
  into 5,768 rows with zero failures; its report remains partial because authentication was
  attended and the Google Sheet is not yet verified.
- One record lacks visible email, while every record has a unique source ID. The raw ID is hashed
  into the exported opaque profile ID; backend-only fields are excluded.
- The tracked-file scan found no databases, CSVs, browser captures, assessment PDF, or credentials.
  The only credential-like match is the documented password-manager placeholder in the README.
