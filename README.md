# Princeton CollFace scraper

An independently implemented Python application for authorized, resumable collection of the
Princeton Residential College Student Facebook. It discovers students through an observed site
contract, extracts every visible labelled field dynamically, and produces a UTF-8 CSV validated
for Google Sheets.

This public-code project never stores credentials, cookies, browser state, authenticated HTML,
student photos, student records, SQLite state, or CSV exports in Git. The assessment PDF is also
excluded and is not reproduced here.

## Safety and current status

The implementation, synthetic test suite, and reviewed `site-contract.json` are complete. An
authorized normal-Chrome run enumerated 5,768 records with zero extraction failures and produced
validated local CSVs. Those outputs remain ignored by Git. Standard Princeton Duo is supported
for attended development inspection only.
If Duo appears during a headless run, the command exits with `auth_unattended_blocked`; it does not
automate or bypass MFA.

## Prerequisites

- Python 3.12
- An account explicitly authorized to access and collect CollFace data
- An approved noninteractive authentication path for a truly unattended final run

## Install

```bash
uv sync --locked --all-extras
.venv/bin/playwright install chromium
```

The `requirements.txt` path remains available for reviewers who use `venv` and `pip`; `uv.lock`
is the exact reproducible environment used for verification.

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
python -m collface_scraper --browser-export /path/to/collface-export.json
```

`--inspect` writes a value-free structural observation under `output/inspection/`. The reviewed
contract records the observed Vue search response and visible card fields. When Duo cannot finish
inside Playwright, `--browser-export` processes a temporary same-origin response downloaded from
an authenticated normal Chrome tab. The response file must remain outside Git and should be
removed after validation. See [docs/INSPECTION.md](docs/INSPECTION.md).

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

`profiles.csv` prefixes spreadsheet-formula and numeric-identifier values with an apostrophe. If
a visible source value already begins with an apostrophe (as CollFace class years do), the safe
CSV doubles that marker so Google Sheets displays the original single apostrophe.
`profiles.raw.csv` preserves exact rendered values for validation. Repeated visible fields are
ordered JSON arrays. Missing values are empty cells; failed profiles are not silently represented
as missing.

## Architecture

- `auth.py`: exact-origin CAS validation, protected-content proof, Duo detection
- `contract.py` and `inspection.py`: reviewed observed structure, sanitized inspection
- `adapter.py`: same-origin pagination and dynamic visible-field extraction
- `search_adapter.py`: observed exhaustive Vue response, opaque stable IDs, browser-card audits
- `browser_export.py`: normal-Chrome fallback that filters the temporary response to visible fields
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
- `--browser-export` is attended evidence, not proof of unattended CAS compliance.

Run checks with `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and
`.venv/bin/pytest -q`.
