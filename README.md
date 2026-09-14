# Princeton CollFace scraper

An independently implemented Python application for authorized, resumable collection of the
Princeton Residential College Student Facebook. It discovers students through an observed site
contract, extracts every visible labelled field dynamically, and produces a UTF-8 CSV validated
for Google Sheets.

This public-code project never stores credentials, cookies, browser state, authenticated HTML,
student photos, student records, SQLite state, or CSV exports in Git. The assessment PDF is also
excluded and is not reproduced here.

## Safety and current status

The synthetic implementation and test suite are complete. A real `site-contract.json`, full
directory run, and Google Sheet require an authorized authenticated session and are deliberately
not fabricated. Standard Princeton Duo is supported for attended development inspection only.
If Duo appears during a headless run, the command exits with `auth_unattended_blocked`; it does not
automate or bypass MFA.

## Prerequisites

- Python 3.12
- An account explicitly authorized to access and collect CollFace data
- An approved noninteractive authentication path for a truly unattended final run

## Install

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

Set credentials in the process environment. Do not put real values in `.env` files or shell
history:

```bash
export COLLFACE_USERNAME='your-netid'
export COLLFACE_PASSWORD='read-from-your-password-manager'
```

## Commands

```bash
python -m collface_scraper --doctor --json
python -m collface_scraper --check-auth
python -m collface_scraper --check-auth --allow-interactive
python -m collface_scraper --inspect --allow-interactive
python -m collface_scraper --limit 3
python -m collface_scraper
python -m collface_scraper --export-only
```

`--inspect` writes a value-free structural observation under `output/inspection/`. Review it in
the authenticated browser, create `site-contract.json` from selectors actually observed, and
record evidence for the stable identifier and exhaustive listing mechanism. The collector refuses
to run without this reviewed contract. See [docs/INSPECTION.md](docs/INSPECTION.md).

The default run uses one browser, one session, one worker, and a global limit of one navigation per
second. It performs discovery, transactional profile collection, a second discovery pass,
reconciliation, CSV validation, and reporting. `--limit 3` uses isolated sample state.

## Outputs and exit codes

Full-run artifacts are written to:

```text
output/full/run.sqlite
output/full/profiles.csv
output/full/profiles.raw.csv
output/full/report.json
```

Exit code `0` means the report passed all completion checks, `2` means a safe partial result, `3`
means configuration/auth/access blocking, and `130` means interruption. Re-running resumes the
same account, scope, limit, and contract; mismatched state fails closed.

`profiles.csv` prefixes spreadsheet-formula and numeric-identifier values with an apostrophe.
`profiles.raw.csv` preserves exact rendered values for validation. Repeated visible fields are
ordered JSON arrays. Missing values are empty cells; failed profiles are not silently represented
as missing.

## Architecture

- `auth.py`: exact-origin CAS validation, protected-content proof, Duo detection
- `contract.py` and `inspection.py`: reviewed observed structure, sanitized inspection
- `adapter.py`: same-origin pagination and dynamic visible-field extraction
- `state.py` and `runner.py`: SQLite queue, atomic page commits, resume, reconciliation
- `fetch.py`: global pacing, bounded backoff, `Retry-After`
- `export.py`: deterministic headers, atomic UTF-8 CSVs, hashes, completion report

## Troubleshooting

- `auth_unattended_blocked`: Duo or another human challenge appeared. Use attended mode only for
  inspection; obtain Princeton's approved noninteractive path for final compliance.
- `state_mismatch`: move the old ignored output directory aside or resume with the exact original
  account, contract, scope, and limit.
- `access_blocked`: stop. Persistent 429 and HTTP 403 are not retried indefinitely.
- `configuration_error`: verify both environment variables and the reviewed contract path.

Run checks with `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and
`.venv/bin/pytest -q`.
