"""Advice log: what was advised, for whom, and when it must be reviewed again."""
from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path

LOG = Path(os.environ.get("DIENSTREIS_LOG", Path.home() / ".config" / "dienstreis" / "advice_log.csv"))
FIELDS = ["advised_on", "traveller", "departure", "stops", "categories", "overall", "review_on", "note"]


def append(row: dict, path: Path | None = None) -> Path:
    path = path or LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
    return path


def due(today: date | None = None, path: Path | None = None) -> list[dict]:
    path = path or LOG
    today = today or date.today()
    if not path.exists():
        return []
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r.get("review_on") and date.fromisoformat(r["review_on"]) <= today:
            out.append(r)
    return out


def history(place_or_name: str, path: Path | None = None) -> list[dict]:
    path = path or LOG
    if not path.exists():
        return []
    q = place_or_name.lower()
    return [r for r in csv.DictReader(open(path, encoding="utf-8")) if q in r["stops"].lower() or q in r["traveller"].lower()]
