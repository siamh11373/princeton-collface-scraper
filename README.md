# Princeton CollFace scraper

A greenfield Python application for authorized, resumable collection of the Princeton
Residential College Student Facebook. It discovers the live site contract through ordinary
authenticated browser behavior, captures dynamically labelled visible fields, and validates a
UTF-8 CSV for import into Google Sheets.

This repository contains source code and synthetic tests only. Credentials, browser state,
authenticated captures, student records, databases, and exports are excluded from Git.

## Status

Initial scaffold. Authentication, discovery, extraction, persistence, and export are built and
verified in separate milestones. A successful redirect is never treated as proof of protected
directory access, and a human Duo challenge is reported as an unattended-authentication blocker.

## Planned command surface

```bash
python -m collface_scraper
python -m collface_scraper --limit 3
python -m collface_scraper --check-auth
python -m collface_scraper --inspect
python -m collface_scraper --export-only
python -m collface_scraper --doctor --json
```

See [PLAN.md](PLAN.md) for the implementation sequence and [THINKING.md](THINKING.md) for the
evolving engineering narrative.

