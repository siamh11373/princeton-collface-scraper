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
authorized installed-Chrome run can accept manual Princeton login and Duo approval, then continue
through discovery, collection, reconciliation, and CSV export without a manual download. A live
three-profile clean-session run verified this path. A separate full run enumerated 5,768 records
with zero extraction failures. All outputs remain ignored by Git.
If Duo appears during a headless run, the command exits with `auth_unattended_blocked`; it does not
automate or bypass MFA.

## Prerequisites

- Python 3.12
- Google Chrome installed (required for attended Duo authentication)
- An account explicitly authorized to access and collect CollFace data
- An approved noninteractive authentication path for a truly unattended final run

## Install

```bash
uv sync --locked --all-extras
uv run playwright install chromium
```

The second command installs the headless browser used by the non-interactive path and the test
suite. Attended Duo authentication uses the reviewer's installed Google Chrome. The
`requirements.txt` path remains available for reviewers who use `venv` and `pip`; `uv.lock` is the
exact reproducible environment used for verification.

Credentials are optional for attended mode. A reviewer can enter them directly in the clean Chrome
window. To have the script fill the verified CAS form instead, set both variables in the process
environment. Do not put real values in `.env` files or shell history:

```bash
export COLLFACE_USERNAME='your-netid'
export COLLFACE_PASSWORD='read-from-your-password-manager'
```

## Commands

```bash
uv run python -m collface_scraper --doctor --json
uv run python -m collface_scraper --check-auth
uv run python -m collface_scraper --check-auth --allow-interactive
uv run python -m collface_scraper --inspect --allow-interactive
uv run python -m collface_scraper --limit 3
uv run python -m collface_scraper
uv run python -m collface_scraper --export-only
uv run python -m collface_scraper --browser-export /path/to/collface-export.json
```

`--inspect` writes a value-free structural observation under `output/inspection/`. The reviewed
contract records the observed Vue search response and visible card fields. `--allow-interactive`
launches installed Google Chrome in a temporary isolated profile. If credential variables are set,
the script fills the verified CAS form; otherwise the reviewer enters credentials directly in
Chrome. The reviewer approves Duo, and the same command completes the remaining pipeline. The
temporary Chrome profile is removed when the command exits.

For a Duo-enabled account, the reproducible attended command is:

```bash
uv run python -m collface_scraper --allow-interactive
```

That one command opens a separate clean Chrome window. Enter Princeton credentials there if they
were not supplied through the environment, approve Duo, and leave the window open. After CollFace
loads, the program discovers the directory, collects the visible fields, reconciles the result,
and writes the CSVs without another manual step.

`--browser-export` remains a recovery tool for processing a temporary same-origin response, but it
is no longer required for the normal attended workflow. See
[docs/INSPECTION.md](docs/INSPECTION.md).

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

Attended runs use `output/attended-full/`; attended samples use `output/attended-sample/`.

Exit code `0` means the command produced complete data; this includes an explicitly attended full
run whose report transparently lists `attended_authentication`. Exit code `2` means a limited or
otherwise incomplete result, `3` means configuration/auth/access blocking, and `130` means
interruption. Re-running resumes the same account, scope, limit, and contract; mismatched state
fails closed.

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
- `browser_session.py`: isolated installed-Chrome lifecycle for attended login and Duo approval
- `state.py` and `runner.py`: SQLite queue, atomic page commits, resume, reconciliation
- `fetch.py`: global pacing, bounded backoff, `Retry-After`
- `export.py`: deterministic headers, atomic UTF-8 CSVs, hashes, completion report

## Troubleshooting

- `auth_unattended_blocked`: Duo or another human challenge appeared in a headless run. Re-run with
  `--allow-interactive`, or obtain Princeton's approved noninteractive path if unattended execution
  is required.
- `state_mismatch`: move the old ignored output directory aside or resume with the exact original
  account, contract, scope, and limit.
- `access_blocked`: stop. Persistent 429 and HTTP 403 are not retried indefinitely.
- `configuration_error`: verify both environment variables and the reviewed contract path.
- `--allow-interactive` is reproducible attended execution, not proof of unattended CAS
  compliance. The report records `attended_authentication` for that reason.

Run checks with `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and
`.venv/bin/pytest -q`.
