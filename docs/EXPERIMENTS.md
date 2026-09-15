# Experiment log

This log contains sanitized facts only. Do not include credentials, cookies, tokens, student
names, profile values, authenticated HTML, screenshots, or response bodies.

## 2026-09-14 - Google Sheets fidelity audit

- Imported the ignored full CSV into a native Sheet in the author's Princeton account.
- Verified 5,768 data rows, seven columns, frozen header, filter, and stable cell count.
- Normal Chrome showed that CollFace renders class years with a leading apostrophe even though the
  response value contains only two digits.
- Moved that observed transformation into `site-contract.json`; the raw CSV now matches the card,
  and the Sheets-safe CSV doubles the leading marker so one apostrophe remains visible on import.
- Corrected the live Sheet and verified all 5,768 nonempty class-year cells preserve the prefix.

## 2026-09-14 - environment

- The project directory did not exist before scaffolding.
- `collface-scraper` was not installed on the current PATH.
- The system `python3` is 3.9.6.
- `uv` located an isolated CPython 3.12 runtime.
- The GitHub CLI was reauthenticated and the private assessment repository was created.

## 2026-09-14 - verification

- Ruff lint and format checks pass.
- All 55 synthetic tests pass, including CAS/Duo failures, exact service callbacks, session
  renewal, discovery, dynamic
  Unicode fields, hidden-value exclusion, `Retry-After`,
  interruption/resume, retries, reconciliation, and CSV round-trip validation.
- A clean clone of commit `26c9837` installed under Python 3.12.13, passed its command-line doctor
  check and Ruff checks, and passed all 53 tests.
- Authenticated normal-Chrome traffic established one exhaustive response with an authoritative
  total of 5,768 records and five rendered-card fields. A temporary local response was processed
  into 5,768 rows with zero failures; its report remains partial because authentication was
  attended and the Google Sheet is not yet verified.
- One record lacks visible email, while every record has a unique source ID. The raw ID is hashed
  into the exported opaque profile ID; backend-only fields are excluded.
- A three-result Chrome search was compared against the raw CSV. All five visible fields matched
  for all three rendered cards, including same-origin photo URLs.
- The tracked-file scan found no databases, CSVs, browser captures, assessment PDF, or credentials.
  The only credential-like match is the documented password-manager placeholder in the README.
