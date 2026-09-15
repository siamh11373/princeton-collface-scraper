## Problem decomposition

I split the project into five parts: authentication, complete discovery, visible-field extraction,
resumability, and CSV validation. I only mark a run complete when two discovery passes agree, the
record count matches, and no profile is pending or failed. Missing fields become empty cells;
extraction errors remain failures.

## Approach exploration

I considered direct HTTP requests, browser scraping, and a hybrid approach. I chose the hybrid:
authenticate in a browser, then use the same request CollFace uses.

CollFace returns its directory in one same-origin JSON response. It contained 5,768 records, which
matched the reported total. This was faster and placed less load on the site than opening every
card separately.

I exported only fields shown on the page: name, class year, email, program, and photo URL. Hidden
backend values were excluded.

## Technical tradeoffs

Email was not a reliable ID because one record had no email, and names can repeat. I hash the
backend ID into an anonymous `profile_id` instead.

SQLite stores progress so interrupted runs can resume without repeating completed work. The
scraper uses one session, one worker, and one request per second. Temporary errors are retried;
persistent access errors or page changes stop the run.

I create two CSVs. The raw file preserves the displayed values. The Sheets-safe file prevents
spreadsheet formulas and automatic number conversion. Testing the Sheet found that class years
needed a leading apostrophe, so I fixed the extraction rule and regenerated the output.

## Obstacles and solutions

Duo was the main obstacle. It requires human approval using biometric fingerprint or FaceID, so I did not try to bypass it. Headless
authentication stops and reports the issue.

For a reproducible run, the script now opens a clean Google Chrome window. The reviewer logs in,
approves Duo, and the script automatically continues. The temporary Chrome profile and cookies are
deleted afterward.

The live sample found three bugs: an unreliable account marker, an incorrect `--limit` rule, and
photo URLs missing `/img/`. I fixed all three and reran the sample successfully. The final checks
pass Ruff and all 62 tests. No credentials, cookies, student data, database, PDF, or browser
captures are committed.

## AI collaboration

I used Codex to convert requirements into tests, draft code, create failure cases, and review the
project. I never shared my password, cookies, or Duo approval with it.

Specific prompts were more useful than broad ones. I asked it to prove authentication,
completeness, resume behavior, and CSV accuracy. I corrected its suggestions when the evidence did
not match, including the site contract, retry logic, clean-clone test, class-year formatting, and
the original manual-download workflow.

The attended Chrome command is reproducible, but it is not fully unattended because Duo still
requires a person.
