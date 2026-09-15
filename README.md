# Princeton CollFace Scraper

An authorized, resumable scraper for Princeton's Residential College Student Facebook. It collects
the fields visible in CollFace and creates UTF-8 CSV files for Google Sheets.

The repository does not include credentials, cookies, student data, browser captures, databases,
CSV exports, or the assessment PDF.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Google Chrome
- An account authorized to access CollFace

## Install

```bash
uv sync --locked --all-extras
uv run playwright install chromium
```

## Run with Princeton Duo

```bash
uv run python -m collface_scraper --allow-interactive
```

The script opens a clean Google Chrome window. Enter your Princeton credentials, approve Duo, and
leave the window open. The script continues automatically after CollFace loads. It discovers the
directory, collects the visible fields, checks completeness, and writes the CSV files.

The temporary Chrome profile and its cookies are deleted when the command ends. Duo is never
automated or bypassed.

### Optional environment credentials

If both variables are set, the script fills the CAS form before waiting for Duo:

```bash
export COLLFACE_USERNAME='your-netid'
export COLLFACE_PASSWORD='read-from-your-password-manager'
uv run python -m collface_scraper --allow-interactive
```

Do not save credentials in the repository or an `.env` file.

## Other commands

```bash
# Check local setup
uv run python -m collface_scraper --doctor --json

# Test authentication only
uv run python -m collface_scraper --check-auth --allow-interactive

# Collect a three-profile sample
uv run python -m collface_scraper --limit 3 --allow-interactive

# Inspect the authenticated page structure
uv run python -m collface_scraper --inspect --allow-interactive

# Rebuild CSVs from saved state
uv run python -m collface_scraper --export-only
```

Runs use one browser session, one worker, and a maximum rate of one request per second. Interrupted
runs resume from SQLite without collecting completed profiles again.

## Outputs

An attended full run writes:

```text
output/attended-full/run.sqlite
output/attended-full/profiles.csv
output/attended-full/profiles.raw.csv
output/attended-full/report.json
```

- `profiles.csv` is safe to import into Google Sheets.
- `profiles.raw.csv` preserves the exact displayed values for validation.
- `report.json` records counts, checks, hashes, and any reason the run is incomplete.
- `run.sqlite` stores progress for resumable runs.

Sample runs use `output/attended-sample/`. All output directories are ignored by Git.

## Exit codes

- `0`: complete data
- `2`: limited or incomplete result
- `3`: configuration, authentication, or access blocked
- `130`: interrupted

Attended runs record `attended_authentication` in the report. They are reproducible, but they are
not fully unattended because Duo requires human approval. A fully unattended run requires an
approved noninteractive Princeton account or CAS exemption.

## Troubleshooting

- `auth_unattended_blocked`: rerun with `--allow-interactive` to approve Duo.
- `state_mismatch`: resume with the same account, contract, scope, and limit, or use a new output
  directory.
- `access_blocked`: the site returned a persistent 403 or 429. Stop and confirm access.
- `configuration_error`: check the credentials, Chrome installation, and `site-contract.json`.

## Tests

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

See [THINKING.md](THINKING.md) for the design decisions, tradeoffs, and project limitations.
