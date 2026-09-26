"""Advice log: what was advised, for whom, and when it must be reviewed again."""
from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path

LOG = Path(os.environ.get("DIENSTREIS_LOG", Path.home() / ".config" / "dienstreis" / "advice_log.csv"))
FIELDS = ["advised_on", "traveller", "departure", "stops", "categories", "overall", "review_on",
          "note", "overrules", "advice_dir", "outbreaks", "type"]


def _upgrade(path: Path) -> None:
    """Rewrite a log written before a column was added, so every row has every column.

    New columns only ever go at the end. Rows from before 0.3 were all about the Ebola outbreak.
    """
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if r.fieldnames == FIELDS or not r.fieldnames:
            return
        rows = list(r)
    for row in rows:
        row["outbreaks"] = row.get("outbreaks") or "ebola_cod_2026"
        row["type"] = row.get("type") or "reisadvies"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows({k: row.get(k, "") for k in FIELDS} for row in rows)


def append(row: dict, path: Path | None = None) -> Path:
    path = path or LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    if not new:
        _upgrade(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
    return path


def relabel(advice_dir: str, values: dict, path: Path | None = None) -> bool:
    """Change columns of the row that points to an archived advice; True if there was one."""
    path = path or LOG
    if not path.exists():
        return False
    _upgrade(path)
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    hit = False
    for row in rows:
        if row.get("advice_dir") and Path(row["advice_dir"]) == Path(advice_dir):
            row.update(values)
            hit = True
    if hit:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows({k: row.get(k, "") for k in FIELDS} for row in rows)
    return hit


def remove(advice_dir: str, path: Path | None = None) -> list[dict]:
    """Take out the rows that point to an archived advice, and return them (to put back on restore)."""
    path = path or LOG
    if not path.exists():
        return []
    _upgrade(path)
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    gone = [r for r in rows if r.get("advice_dir") and Path(r["advice_dir"]) == Path(advice_dir)]
    if gone:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows({k: row.get(k, "") for k in FIELDS} for row in rows if row not in gone)
    return gone


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
