# Authorized inspection runbook

1. Set `COLLFACE_USERNAME` and `COLLFACE_PASSWORD` locally without committing them.
2. Run `python -m collface_scraper --check-auth` in a clean context first. Record
   `auth_unattended_blocked` if Duo appears.
3. For bounded development only, run `python -m collface_scraper --inspect --allow-interactive`
   and approve Duo yourself. The saved observation contains structure and counts, not values. The
   command keeps the authenticated browser open until you press Enter in the terminal.
4. Before pressing Enter, identify the listing URL, repeated student container, profile link, stable
   source ID, next-page control, authoritative total (if any), profile root, sections, headings,
   label/value rows, and visible photo element.
5. Encode those selectors in `site-contract.json`. Set `exhaustive` true only with concrete
   enumeration evidence. Never include student values, IDs, tokens, cookies, or raw captures.
6. Run `--limit 3`, compare all rendered fields and photo URLs in the browser, then interrupt and
   resume a sample to verify equality before starting the full run.

Attended Duo proves only development access. It does not satisfy unattended execution.
