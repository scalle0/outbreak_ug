"""Every advice kept whole, dated and searchable.

The CSV log records that an advice happened; it does not record what was said. Two advices for the
same destination weeks apart can contradict each other in the reasoning while both look consistent
in one log line, so the full text is kept here and the matching ones are handed to the step that
writes the next mail.

One folder per advice under ~/.config/dienstreis/adviezen/JJJJ-MM-DD_reiziger/:
    advies.json   the searchable record (traveller, dates, stops, zones, verdict, overrules, reply)
    reply.txt     the mail as it was written
    summary.json  the calculated figures behind it
These are colleagues' travel details. They stay on the machine; `search` reads them, and only the
hits for the same destinations go to the model.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

ARCHIVE = Path(os.environ.get("DIENSTREIS_ARCHIVE",
                              Path.home() / ".config" / "dienstreis" / "adviezen"))


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")[:40] or "onbekend"


def save(trip: dict, summary: dict, reply: str, *, request: str = "",
         suggestions: list[str] | None = None, advised_on: date | None = None,
         root: Path | None = None) -> Path:
    """Write one advice to the archive and return its folder."""
    root = Path(root or ARCHIVE)
    day = advised_on or date.today()
    d = root / f"{day.isoformat()}_{_slug(trip.get('traveller', 'trip'))}"
    n, base = 2, d
    while d.exists():                 # two advices for the same person on one day
        d, n = base.with_name(f"{base.name}_{n}"), n + 1
    d.mkdir(parents=True, exist_ok=True)

    stops = summary.get("stops", [])
    record = {
        "advised_on": day.isoformat(),
        "traveller": trip.get("traveller", ""),
        "note": trip.get("note", ""),
        "departure": summary.get("departure", ""),
        "asof": summary.get("asof", ""),
        "overall": summary.get("overall", ""),
        "rule_overall": summary.get("rule_overall", ""),
        "overrides": summary.get("overrides", []),
        "review_on": str(trip.get("review_on") or ""),
        "places": [s.get("place") for s in stops],
        "zones": [s.get("zone") for s in stops if s.get("zone")],
        "provinces": sorted({s.get("province") for s in stops if s.get("province")}),
        "categories": "".join(s.get("category", "") for s in stops),
        "stops": [{k: s.get(k) for k in ("place", "start", "end", "zone", "province",
                                         "category", "verdict", "nights")} for s in stops],
        "suggestions": suggestions or [],
        "reply": reply,
        "request_excerpt": (request or "")[:2000],
    }
    (d / "advies.json").write_text(json.dumps(record, ensure_ascii=False, indent=1, default=str),
                                   encoding="utf-8")
    (d / "reply.txt").write_text(reply, encoding="utf-8")
    (d / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str),
                                    encoding="utf-8")
    return d


def all_advices(root: Path | None = None) -> list[dict]:
    root = Path(root or ARCHIVE)
    if not root.exists():
        return []
    out = []
    for f in sorted(root.glob("*/advies.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        r["dir"] = str(f.parent)
        out.append(r)
    return sorted(out, key=lambda r: r.get("advised_on", ""), reverse=True)


def _matches(r: dict, term: str) -> bool:
    t = term.lower()
    hay = " ".join(str(x) for x in (
        r.get("traveller", ""), r.get("note", ""), r.get("overall", ""),
        " ".join(str(p) for p in r.get("places", [])),
        " ".join(str(z) for z in r.get("zones", [])),
        " ".join(str(p) for p in r.get("provinces", [])),
    )).lower()
    return t in hay


def search(term: str = "", *, since: date | None = None, until: date | None = None,
           verdict: str = "", overruled: bool | None = None, limit: int = 50,
           root: Path | None = None) -> list[dict]:
    """Advices matching a place, zone, province, traveller or note, newest first."""
    out = []
    for r in all_advices(root):
        if term and not _matches(r, term):
            continue
        if verdict and verdict.lower() not in str(r.get("overall", "")).lower():
            continue
        if overruled is not None and bool(r.get("overrides")) != overruled:
            continue
        day = r.get("advised_on", "")
        if since and (not day or datetime.fromisoformat(day).date() < since):
            continue
        if until and (not day or datetime.fromisoformat(day).date() > until):
            continue
        out.append(r)
    return out[:limit]


def for_trip(trip: dict, summary: dict, *, limit: int = 5, root: Path | None = None) -> list[dict]:
    """Earlier advices for the same places or zones, trimmed for the prompt that writes the mail.

    The reply text is kept: that is the point. What the previous advice *said* is what a new one
    can contradict, and a one-line log row cannot show that.
    """
    wanted = {str(s.get("place", "")).lower() for s in summary.get("stops", [])}
    wanted |= {str(s.get("zone", "")).lower() for s in summary.get("stops", []) if s.get("zone")}
    wanted |= {str(s.get("province", "")).lower() for s in summary.get("stops", []) if s.get("province")}
    wanted.discard("")
    hits = []
    for r in all_advices(root):
        here = {str(x).lower() for x in r.get("places", []) + r.get("zones", []) + r.get("provinces", [])}
        if here & wanted:
            hits.append({k: r[k] for k in ("advised_on", "traveller", "places", "zones", "overall",
                                           "rule_overall", "overrides", "review_on", "reply")
                         if k in r})
    return hits[:limit]
