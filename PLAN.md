# Implementation plan

## Outcome

Deliver an independently implemented CollFace scraper with programmatic CAS authentication,
exhaustive and resumable discovery, dynamic field extraction, conservative request pacing,
validated UTF-8 CSV output, a public GitHub repository, and a reviewer-accessible Google Sheet.

## Milestones

1. Scaffold the isolated Python 3.12 project and establish Git hygiene.
2. Implement fail-closed CAS authentication and distinguish Duo from ordinary login failure.
3. Derive a sanitized parser contract from bounded authenticated inspection.
4. Implement stable-ID discovery and two-pass membership reconciliation.
5. Implement dynamic visible-field extraction without a field allowlist.
6. Add transactional SQLite state, throttled retries, deterministic export, and validation.
7. Complete synthetic and bounded live tests, documentation, full collection, and submission.

## Completion standard

Completion requires a clean-clone single-command run, reconciled exhaustive membership, no
unresolved profiles, browser fidelity evidence, a round-trip-verified CSV, a private-data scan,
and a Google Sheet restricted to Princeton-authenticated viewers.

