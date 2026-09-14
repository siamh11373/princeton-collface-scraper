# Experiment log

This log contains sanitized facts only. Do not include credentials, cookies, tokens, student
names, profile values, authenticated HTML, screenshots, or response bodies.

## 2026-09-14 - environment

- The project directory did not exist before scaffolding.
- `collface-scraper` was not installed on the current PATH.
- The system `python3` is 3.9.6.
- `uv` located an isolated CPython 3.12 runtime.
- The GitHub CLI is configured for `siamh11373`, but its saved token is invalid.

## 2026-09-14 - verification

- Ruff lint and format checks pass.
- All 42 synthetic tests pass, including CAS/Duo failures, exact service callbacks, session
  renewal, discovery, dynamic
  Unicode fields, hidden-value exclusion, `Retry-After`,
  interruption/resume, retries, reconciliation, and CSV round-trip validation.
- A clean clone installed under Python 3.12.13, passed its command-line doctor check and Ruff
  checks, and passed all 36 tests.
- No CollFace credentials are present in the execution environment, so no authenticated live
  contract, profile data, or full-run completion is claimed.
- The tracked-file scan found no databases, CSVs, browser captures, assessment PDF, or credentials.
  The only credential-like match is the documented password-manager placeholder in the README.
