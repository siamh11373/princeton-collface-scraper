# Engineering thinking and AI collaboration

This document is AI-assisted and will be reviewed and corrected by the author before submission.
It records only decisions and experiments that actually occurred; future results are not written
as though they already happened.

## Problem decomposition

The work is divided into authentication, exhaustive discovery, dynamic extraction, durable state,
resilient fetching, output validation, and independent completion checks. Authentication and
enumeration are tested before optimizing throughput because a fast parser is not useful if it
cannot reproducibly enter the directory or prove population coverage.

I turned the broad request into explicit gates rather than treating “CSV exists” as success:

1. prove fresh CAS authentication by checking protected page markers;
2. observe, rather than guess, the directory's listing and profile contract;
3. identify profiles by a stable source ID, never by a display name;
4. commit each discovered page and queue update transactionally;
5. extract labels dynamically with section context and ordered repeated values;
6. repeat discovery and reconcile membership before claiming completeness;
7. round-trip both exact and spreadsheet-safe CSVs; and
8. keep authenticated artifacts and student data outside the public repository.

This decomposition made “partial” a first-class result. A three-profile sample, interrupted run,
failed profile, changed membership, or unverified field audit can produce useful evidence, but it
cannot accidentally receive a complete status.

## Approach exploration

The initial approach is browser-first because the logged-out CollFace origin redirects to
Princeton CAS and the authenticated implementation has not yet been observed. Direct requests
will be considered only for endpoints exposed through ordinary browser behavior and only after
their output matches the rendered page.

I considered three implementation shapes:

- **Direct HTTP:** potentially faster and simpler to deploy, but it would require reproducing CAS
  cookies and form state before the authenticated application contract had been observed.
- **Browser only:** slower, but it naturally executes CAS redirects and lets extraction correspond
  to what the authorized account can actually see.
- **Browser-authenticated HTTP hybrid:** potentially the best later optimization, but only if
  ordinary browser traffic reveals a stable endpoint and its fields match the rendered profiles.

I chose browser only for the first correct implementation. I rejected copying endpoints or code
from the prior TigerNet project: those are unverified for CollFace and would violate the clean-room
boundary of this project. I also rejected writing a plausible `site-contract.json` from the
logged-out page. The contract is deliberately absent until an authenticated observation exists.

## Technical tradeoffs

The project starts with one session, one worker, and one request per second. This favors server
safety and reproducibility over speed. SQLite adds local complexity but gives transactional
checkpoints and avoids restarting a long collection after interruption.

Playwright is a heavier dependency than an HTTP client, and browser navigation lowers throughput.
That cost buys a clearer security boundary: credentials are submitted only after validating the
CAS origin, service callback, form action, and POST method. One process-wide pacing gate prevents
login, discovery, audit, and profile requests from accidentally exceeding the intended rate.

SQLite is the source of truth; CSV is a derived artifact. A listing page and all IDs discovered on
it are committed in one transaction, and completed profiles are not fetched again after restart.
The database identity includes a one-way account key, target, scope, limit, and contract hash so a
resume cannot silently mix incompatible runs.

For spreadsheet safety, I kept two exports. The raw CSV preserves exact values for validation;
the presentation CSV prefixes formula-like values and leading-zero identifiers so Google Sheets
does not reinterpret them. Headers are the deterministic union of observed section/label keys.

Retries are bounded. Timeouts and server errors back off with jitter, and `Retry-After` is honored.
HTTP 403, persistent 429, unexpected origins, repeated authentication loops, and structural drift
stop collection because continuing could be unsafe or produce misleading data.

## Obstacles and solutions

The machine's default Python is 3.9, while the project requires Python 3.12. An existing isolated
Python 3.12 runtime managed by `uv` was selected without copying the prior scraper environment.
The GitHub CLI's saved token is currently invalid, so remote creation is a separate explicit
checkpoint after local initialization.

The available account uses Duo. If a clean-context CAS attempt requires human approval, the
final unattended-authentication requirement remains blocked unless Princeton provides an
approved noninteractive account or supported exemption. The implementation will detect and
report that state instead of bypassing MFA.

The first integrated state/export test run exposed formatting drift rather than a behavioral
failure. Ruff reformatted the scaffold, then reported one import-order issue after retry logic was
added. Applying its mechanical correction produced a clean lint run and 35 passing tests. A later
inspection test increased that count. The PDF audit then found two real gaps: expired sessions
were detected but not renewed, and links inside an otherwise visible value could include hidden
descendants. I added one safe renewal attempt and visibility filtering, plus `Retry-After` recovery
coverage. A final authentication review made the CAS `service` callback mandatory rather than
merely rejecting a foreign callback. The final local suite reached 39 passing tests.

The inspection command intentionally does not synthesize selectors. It records only value-free
DOM structure because inventing a selector from a logged-out page would create false confidence
about discovery completeness and could accidentally preserve student data.

The first clean-clone installation test also caught a verification mistake: I invoked an absolute
requirements file while the working directory was still the source repository, so editable `.`
resolved to the original checkout. I uninstalled it, repeated installation from the clone's own
directory, and verified that the installed package path pointed into the temporary clone before
running its checks. I then added `uv.lock` so the transitive environment is reproducible.

Document extraction had two small failures. `pdftotext` was unavailable, and the system Python did
not contain `pypdf`. I used the workspace's bundled document runtime instead and extracted all six
pages. That second reading prompted the session-renewal and THINKING.md depth audit.

GitHub publication did not fail because of repository code; the locally saved GitHub token had
expired. A device login was started and remains an explicit release checkpoint. Likewise, no
CollFace credentials were present in the process environment. I opened the authorized CAS page
for user-controlled login rather than requesting or handling credentials in chat.

## AI collaboration

Codex helped translate the assessment into testable requirements, challenged the assumption that
a CAS redirect proves authenticated access, and proposed a browser-first contract inspection.
The author changed the schedule from seven days to completion today and explicitly chose an
AI-assisted THINKING.md. This file must be updated with real commands, failures, corrections, and
author overrides as implementation proceeds.

The main prompt that worked was the user's concrete implementation plan. It specified exact
commands, state/output paths, completion invariants, and failure behavior, which let Codex convert
the request into small test-backed commits. The most important user override was: “this plan needs
to be changed, i need it to be done today.” That changed sequencing from a seven-day calendar to
same-day risk-first execution; it did not lower the completion gate.

Codex was most useful for threat-modeling CAS callbacks, generating synthetic browser fixtures,
enumerating failure paths, reviewing the PDF against the implementation, and performing repetitive
clean-clone and privacy checks. Narrow prompts such as “verify fresh auth,” “prove exhaustive
membership,” and “round-trip the safe and raw CSV” led to testable behavior.

AI suggestions needed correction in three places:

- It initially treated a sanitized inspection report as enough progress toward a site contract. I
  preserved the report but refused to generate a real contract without authenticated evidence.
- Its first clean-clone command accidentally installed the editable package from the source
  checkout. Inspection of the installation output exposed this, and the check was repeated from
  the correct directory.
- The first adapter stopped on every 429 and on session expiry. Comparing the code back to the
  acceptance plan led to bounded `Retry-After` recovery and one safe CAS renewal.

AI did not receive Princeton credentials, approve Duo, inspect hidden backend fields, or invent a
successful full run. The remaining authenticated observations and the final Google Sheet must be
recorded here only after they actually occur. The author should edit this narrative into their own
voice before submission, especially where personal reasoning or intent cannot be inferred from
the engineering log.
