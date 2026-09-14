"""Bounded, sanitized observation for deriving a reviewed site contract."""

import json
from pathlib import Path
from urllib.parse import urlsplit

from .config import TARGET, origin
from .errors import DiscoveryError


def inspect_surface(page, destination: Path) -> dict:
    if origin(page.url) != TARGET:
        raise DiscoveryError("Inspection is not on verified protected CollFace content.")
    surface = page.evaluate(
        """() => {
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const classes = {};
          for (const element of document.querySelectorAll('[class]')) {
            if (!visible(element)) continue;
            for (const name of element.classList) classes[name] = (classes[name] || 0) + 1;
          }
          return {
            title: document.title,
            forms: [...document.forms].map(f => ({
              action_origin: new URL(f.action, location.href).origin,
              method: (f.method || 'get').toLowerCase()
            })),
            controls: [...document.querySelectorAll('input,select,button')]
              .filter(visible).map(e => ({tag: e.tagName.toLowerCase(), type: e.type || null})),
            visible_class_counts: Object.fromEntries(
              Object.entries(classes).filter(([, count]) => count > 1).sort()
            ),
            links: [...document.querySelectorAll('a[href]')].filter(visible).reduce(
              (counts, a) => {
                const u = new URL(a.href, location.href);
                const key = u.origin === location.origin ? 'same_origin' : 'external';
                counts[key] = (counts[key] || 0) + 1;
                return counts;
              }, {}
            )
          };
        }"""
    )
    observation = {
        "target": TARGET,
        "page_origin": origin(page.url),
        "page_path": urlsplit(page.url).path,
        "contains_values": False,
        "surface": surface,
        "next_step": "Review in the browser and encode only observed stable selectors.",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n", "utf-8")
    return observation
