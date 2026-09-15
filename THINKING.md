## Problem decomposition

At first, this looked simple: log in, collect the directory, and write a CSV. The word “complete”
made it much harder. A CSV can look convincing while missing
hundreds of profiles, flattening fields incorrectly, or quietly mixing two interrupted runs. I
decided early that producing a file was not the finish line. I needed to prove where every row came
from and be able to stop safely when that proof broke down.

I split the project into six questions:

1. Can the program authenticate without sending credentials somewhere unexpected?
2. How does CollFace actually load the directory after login?
3. What is a stable identity for a student when names are not unique?
4. Which response values are genuinely visible to the user?
5. How can a failed run resume without duplicating or skipping work?
6. How do I know the CSV survived both serialization and Google Sheets import?

That order mattered. There was no value in optimizing extraction before I had verified access and
enumeration. I also treated “partial” as a real output state. A sample run, a changed directory, or
one unexplained profile should never be mislabeled as complete just because a CSV exists.

## Approach exploration

I considered direct HTTP requests, full browser automation, and a hybrid approach.

Direct HTTP would have been the fastest at runtime, but it required me to reproduce Princeton CAS
state before I understood the application. A browser-only scraper was easier to reason about for
authentication and visibility, but it would be slow and fragile if I had to visit thousands of
individual pages. The hybrid option—authenticate in a browser, then use the same application
request the browser uses—offered the best balance, but only if I could observe a stable endpoint
and verify that its values matched the page.

I started browser-first. I validated the CAS host, form action, method, service callback, and the
protected CollFace page after redirect. I did not treat “CAS redirected me back” as proof of
success; the returned page also had to contain protected directory markers.

Once I inspected the authenticated site, the architecture changed. CollFace is a Vue interface,
and its normal all-directory search returned the full dataset in one same-origin JSON response.
The response reported 5,768 records, and its `data` array also contained 5,768 items. The page then
paginated that dataset locally. Using this response was both more faithful and less abusive than
opening 5,768 rendered cards one at a time.

I did not blindly export the entire response. Some backend values were not shown on the card.
Including them would have violated the requirement to collect what CollFace surfaces to the
authorized user. I compared the component and rendered cards, then limited the contract to name,
class year, email, program, and photo URL. Internal ID, a second year value, an academic-plan
description, and college metadata stayed out of the CSV because they were not visibly rendered.

## Technical tradeoffs

### Identity, state, and completeness

My first identity idea was email. Live data disproved it: one record had no visible email. Names
were even less reliable because they can repeat or change. The response did contain a unique
backend ID, so I used it only as input to a deterministic hash. The exported `profile_id` is stable
for resuming and deduplication, while the private source ID never appears in the CSV.

SQLite is the source of truth; CSV is a derived artifact. Discovery records and queue updates are
transactional. A completed profile is not fetched again after restart. The database also stores a
run identity containing the target, scope, sample limit, contract hash, and a one-way account key.
If any of those change, the scraper refuses to merge the new run into old state.

A full run performs discovery twice. I only consider the population reconciled when both passes
terminate through the observed exhaustive mechanism, both contain the same unique IDs, the
authoritative total agrees with the membership count, and no profile remains pending or failed.
This cannot create a perfectly atomic snapshot of a live directory, but it can detect membership
changes during the collection window instead of silently ignoring them.

### Reliability and server safety

I deliberately began with one session, one worker, and a global pace of one request per second.
The goal was predictable load, not maximum speed. The same pacing gate covers authentication,
discovery, audit requests, and profile work so two code paths cannot accidentally exceed the
limit.

Timeouts and transient server errors use bounded exponential backoff with jitter. A valid
`Retry-After` header wins over the calculated delay. A 403, repeated authentication loop,
persistent 429, or changed source structure stops the run. Continuing after one of those events
would risk either abusing the service or creating an output that looked complete when it was not.

Missing fields are different from failed extraction. Missing visible values become empty cells;
an exception does not. Failed profiles stay failed in SQLite and force a partial report so the
problem cannot disappear into a blank column.

### CSV and Google Sheets

The exporter builds a deterministic union of observed section and label names. It writes UTF-8,
uses the CSV library for quotes and newlines, serializes repeated values as ordered JSON arrays,
and round-trips every generated row before replacing the previous output atomically.

I kept two versions of the export. `profiles.raw.csv` preserves the exact rendered values for
validation. `profiles.csv` protects formula-like strings and leading-zero identifiers from
spreadsheet coercion. This separation means spreadsheet safety does not destroy the evidence I
need to check fidelity.

The Google Sheets review caught a subtle bug. The API supplied class years as two digits, such as
`28`, while the live card displayed `'28`. My first reaction was to fix escaping only in the safe
CSV. That was incomplete because the raw CSV would still disagree with the page. I moved the
observed apostrophe into the site contract as a display transformation, applied it during
extraction, and doubled it only when necessary for Sheets import. The raw export now preserves
one apostrophe, while the Sheets-safe export retains the marker needed for import.

The finished Sheet contains 5,768 data rows and seven columns. I verified the row, column, and cell
counts after import, froze and styled the header, added a filter, and checked all 5,768 class-year
cells after the correction.

## Obstacles and solutions

Authentication was the largest obstacle. The available Princeton account uses Duo. The
programmatic CAS path correctly reached the identity provider, but a fresh context could not
finish Duo without human approval. I tried two narrow redirect-handling corrections, but the
remaining problem was not a selector bug; it was the MFA boundary. I chose not to automate around
or weaken it. The final code detects that state and reports `auth_unattended_blocked`.

For the authorized live inspection, I switched to a normal Chrome tab with my existing approved
session. I downloaded the same-origin directory response temporarily and passed it through the
same contract validation, SQLite queue, two-pass reconciliation, extraction, and export code. The
run completed all 5,768 records with zero pending or failed profiles. Its report remains honest:
the data run succeeded, but attended authentication does not satisfy the assessment's unattended
CAS requirement.

That fallback produced the data, but I would not call it reproducible for another reviewer. I
changed attended mode to launch the installed Google Chrome application in a clean temporary
profile and connect to it through Chrome's local debugging interface. The script validates and
fills the CAS form, pauses for the reviewer to approve Duo, and then resumes automatically in the
same process. The temporary profile, including its cookies, is deleted when the command exits.

The first end-to-end sample after that change exposed three bugs that the synthetic suite had not
caught. I was deriving the manual account fingerprint from a `nav` element that CollFace did not
reliably expose. I replaced it with a hash of normalized text from the already-verified protected
page; the text itself is never logged or stored. Next, `--limit 3` stopped after three successful
profiles rather than three attempts, so repeated extraction failures could exceed the limit. I
changed the invariant to cap attempts. Finally, every text field passed the live audit but every
photo URL failed. A value-free diagnostic showed that the API returns a filename while the Vue
card adds `/img/`. I recorded that transformation in the site contract and corrected all 5,768
photo links in the final Sheet.

After those fixes, a fresh-session command opened installed Chrome, accepted manual credentials
and Duo approval, discovered the authoritative 5,768-record population, collected three profiles,
matched all five visible fields for each profile, and wrote both CSV variants with zero failures.
No response download or cookie transfer was involved.

The clean-clone test also caught one of my own verification mistakes. I initially invoked an
absolute requirements file while my working directory still pointed at the source repository.
Because the project is installed as editable, that command tested the original checkout instead
of the clone. I noticed the installed path was wrong, uninstalled it, reran the setup from inside
the clone, and checked the import path before trusting the results. I then added `uv.lock` so the
complete dependency graph was reproducible.

Other failures were smaller but useful. Ruff caught an import-order issue after retry logic was
added. A security review showed that session expiry was detected but not renewed, so I added one
bounded renewal attempt. Another review found that a visible container could include hidden child
text; extraction now filters by actual visibility. I also tightened CAS validation so an absent
service callback fails just as an incorrect foreign callback does.

I also checked the repository from a clean clone under Python 3.12.13. Ruff formatting and lint
checks pass, all 62 tests pass, and the committed history contains no CSV, SQLite database,
assessment PDF, browser capture, credential file, or detected secret. I repeated the local checks
after adding the installed-Chrome workflow instead of assuming the earlier result still applied.

## AI collaboration

I used Codex heavily, but I did not let it decide what counted as evidence. It helped me turn vague
requirements into checks, generate synthetic failure cases, review security boundaries, and poke
holes in completion claims. I never gave it my Princeton password, cookies, or Duo approval, and I
did not treat generated guesses as evidence about the authenticated site.

Broad prompts were less useful than narrow ones. “Build the scraper” produced plausible structure,
but prompts such as “prove fresh authentication,” “show how this run establishes exhaustive
membership,” and “round-trip both CSV variants” produced decisions I could test. The detailed
implementation plan was especially useful because it named the desired commands, output paths,
failure states, and completion invariants.

AI accelerated the repetitive parts: enumerating CAS failure cases, creating synthetic pagination
and retry fixtures, checking interruption and resume behavior, and comparing the repository back
to the assessment. It was also useful as a skeptical reviewer. Asking it to assume completion was
unproven led to stronger checks for exact callback origins, membership reconciliation, hidden
values, and public-repository hygiene.

I overrode it several times. It initially treated a sanitized logged-out inspection as enough to
write a site contract; I waited for authenticated evidence. It first stopped on every 429 and did
not renew an expired session; I changed that to bounded recovery while keeping persistent failures
fatal. Its first clean-clone command accidentally tested the source checkout, which I caught by
checking the installed package path. It also focused on CSV escaping for the class-year apostrophe
when the real issue was extraction fidelity. I also rejected the idea that a browser download was
good enough for reproducibility and required one command that opens normal Chrome, waits for Duo,
and keeps going. The useful part was never the first answer. It was turning each answer into a
sharper test and following the evidence.

The biggest limitation is still unattended Duo authentication. I would rather state that plainly
than claim that an attended browser session meets a requirement it does not. With an approved
noninteractive Princeton account or supported CAS exemption, the same collection pipeline can run
through its intended one-command path without changing the data model or export logic.
