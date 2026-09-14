# Engineering thinking and AI collaboration

This document is AI-assisted and will be reviewed and corrected by the author before submission.
It records only decisions and experiments that actually occurred; future results are not written
as though they already happened.

## Problem decomposition

The work is divided into authentication, exhaustive discovery, dynamic extraction, durable state,
resilient fetching, output validation, and independent completion checks. Authentication and
enumeration are tested before optimizing throughput because a fast parser is not useful if it
cannot reproducibly enter the directory or prove population coverage.

## Approach exploration

The initial approach is browser-first because the logged-out CollFace origin redirects to
Princeton CAS and the authenticated implementation has not yet been observed. Direct requests
will be considered only for endpoints exposed through ordinary browser behavior and only after
their output matches the rendered page.

## Technical tradeoffs

The project starts with one session, one worker, and one request per second. This favors server
safety and reproducibility over speed. SQLite adds local complexity but gives transactional
checkpoints and avoids restarting a long collection after interruption.

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
inspection test increased that count; exact final evidence is recorded in the release checks.

The inspection command intentionally does not synthesize selectors. It records only value-free
DOM structure because inventing a selector from a logged-out page would create false confidence
about discovery completeness and could accidentally preserve student data.

## AI collaboration

Codex helped translate the assessment into testable requirements, challenged the assumption that
a CAS redirect proves authenticated access, and proposed a browser-first contract inspection.
The author changed the schedule from seven days to completion today and explicitly chose an
AI-assisted THINKING.md. This file must be updated with real commands, failures, corrections, and
author overrides as implementation proceeds.
