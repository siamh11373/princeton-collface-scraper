## Problem decomposition

The work is divided into authentication, exhaustive discovery, dynamic extraction, durable state,
resilient fetching, output validation, and independent completion checks. Authentication and
enumeration are tested before optimizing throughput because a fast parser is not useful if it
cannot reproducibly enter the directory or prove population coverage.

I turned the broad request into explicit steps and prompted codex.

1. prove fresh CAS authentication by checking protected page markers;
2. observe the directory's listing and profile contract;
3. identify profiles by a stable source ID.
4. commit each discovered page and queue update transactionally;
5. extract labels dynamically with section context and ordered repeated values;
6. repeat discovery and reconcile membership before claiming completeness;
7. round-trip both exact and spreadsheet-safe CSVs; and
8. keep authenticated artifacts and student data outside the public repository.

This decomposition made “partial” a first-class result. A three-profile sample, interrupted run,
failed profile, changed membership, or unverified field audit can produce useful evidence, but it
cannot accidentally receive a complete status.

## Approach exploration

I considered three implementation strategies:

- **Direct HTTP:** potentially faster and simpler to deploy, but it would require reproducing CAS
  cookies and form state before the authenticated application contract had been observed.
- **Browser only:** slower, but it naturally executes CAS redirects and lets extraction correspond
  to what the authorized account can actually see.
- **Browser-authenticated HTTP hybrid:** potentially the best later optimization, but only if
  ordinary browser traffic reveals a stable endpoint and its fields match the rendered profiles.

I chose browser only for the first correct implementation. Live inspection later showed that the
rendered cards are backed by one exhaustive same-origin Vue response, so I replaced the assumed
link-by-link collection path with a browser-authenticated response adapter. I rejected copying endpoints or code
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

The available account uses Duo. A clean-context CAS attempt requires human approval, so the
final unattended-authentication requirement isn't possible Duo has strict automation restrictions.

The first integrated state/export test run exposed formatting drift rather than a behavioral
failure. Ruff reformatted the scaffold, then reported one import-order issue after retry logic was
added. Applying its mechanical correction produced a clean lint run and 35 passing tests. A later
inspection test increased that count. The PDF audit then found two real gaps: expired sessions
were detected but not renewed, and links inside an otherwise visible value could include hidden
descendants. I added one safe renewal attempt and visibility filtering, plus `Retry-After` recovery
coverage. A final authentication review made the CAS `service` callback mandatory rather than
merely rejecting a foreign callback. Further failure-path tests covered persistent 403/429 and
exhausted network retries. The final local suite reached 42 passing tests.

Authenticated inspection established an authoritative total of 5,768 records. The response has a
unique backend source ID and visible card values for name, class year, email, program, and photo.
One record has no visible email, which disproved the initial email-as-identity assumption. The
implementation now hashes the backend ID into an opaque stable `profile_id`; the hidden raw ID is
never exported. Backend-only year, academic-description, and college values are also excluded.

Playwright's attended Duo flow repeatedly failed during an IdP transition even after two narrow
redirect fixes. The author explicitly directed the live work to use a separate normal Chrome tab.
That tab authenticated successfully and downloaded a temporary same-origin JSON response. A new
Chrome-export adapter passed it through the same schema checks, SQLite queue, two-pass discovery,
dynamic field extraction, and CSV validation. The local run completed all 5,768 records with zero
failures; its report remains partial because attended authentication cannot satisfy the unattended
assessment requirement. The temporary response and all outputs remain ignored by Git.

For the browser fidelity checkpoint, the author made a separate Chrome tab available. A surname
query rendered exactly three cards. A value-free local comparison confirmed that every card's
name, class year, email, program, and same-origin photo URL matched the raw CSV. No student values
were copied into the repository or documentation.

The first clean-clone installation test also caught a verification mistake: I invoked an absolute
requirements file while the working directory was still the source repository, so editable `.`
resolved to the original checkout. I uninstalled it, repeated installation from the clone's own
directory, and verified that the installed package path pointed into the temporary clone before
running its checks. I then added `uv.lock` so the transitive environment is reproducible.

Document extraction had two small failures. `pdftotext` was unavailable, and the system Python did
not contain `pypdf`. I used the workspace's bundled document runtime instead and extracted all six
pages. That second reading prompted the session-renewal and THINKING.md depth audit.

No CollFace credentials were placed in the process environment or chat. Authentication stayed in
user-controlled Princeton and Duo pages, and normal Chrome reused the user's approved session.

## AI collaboration

Codex helped translate the assessment into testable requirements, I challenged the assumptions and proposed a browser-first contract inspection.
It executed the complete plan and I made changes to the code when errors appeared.

AI suggestions needed correction in two places:

- Its first clean-clone command accidentally installed the editable package from the source
  checkout. Inspection of the installation output exposed this, and the check was repeated from
  the correct directory.
- The first adapter stopped on every 429 and on session expiry. Comparing the code back to the
  acceptance plan led to bounded `Retry-After` recovery and one safe CAS renewal.

AI did not receive Princeton credentials or approve Duo. It observed response structure only to
decide which values corresponded to rendered cards; no student values were added to code or docs.

The final CSV was imported into a native Google Sheet owned by my Princeton Google
account. A programmatic read verified 5,768 data rows.

