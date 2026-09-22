"""The deterministic core: data, risk per stop, map, epicurve, reply skeleton, QA.

Everything here is arithmetic on the itinerary and the INSP figures; no model is involved. Kept
apart from cli.py so that `advies` can call it without importing the argument parser, and so that
the boundary between "calculated" and "written by a model" is visible in the imports.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40]


def analyse(trip: dict, out: Path, refresh: bool = False, asof: str | None = None, log_it: bool = False) -> dict:
    """Deterministic core: data, risk per stop, map, epicurve, reply skeleton, QA. Returns summary."""
    from . import data, figures, log, mail, risk
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ob = data.load(refresh=refresh, asof=asof)
    ecdc = data.ecdc_snapshot() if not asof else {"ok": False, "reason": "asof run"}
    rs = risk.assess(trip, ob)
    tab = risk.table(rs)
    tab.to_csv(out / "risk.csv", index=False, encoding="utf-8")
    (out / "risk.md").write_text(tab.to_markdown(index=False) if hasattr(tab, "to_markdown") else tab.to_string(),
                                 encoding="utf-8")

    tag = _slug(trip.get("traveller", "trip"))
    epi = figures.epicurve(ob, str(out / f"epicurve_{ob.asof:%Y%m%d}.png"), ecdc)
    first = min((r.start for r in rs if r.start), default=None)
    last = max((r.end for r in rs if r.end), default=None)
    sub = (f"{trip.get('traveller', '')}, {mail.d(first)} {first.year if first else ''} tot {mail.d(last)} "
           f"{last.year if last else ''}. Nationaal: {mail.n(epi['last_total'])} gevallen, "
           f"{mail.n(epi['last_deaths'])} overlijdens (data tot {ob.asof:%d-%m-%Y})")
    mp = figures.itinerary_map(rs, ob, "Ebola (Bundibugyo-virus), DRC: situatie per gezondheidszone langs het reisschema",
                               sub, str(out / f"kaart_{tag}.png"))

    redirect = bool(trip.get("sent_to_ugent_address", False))
    skel = mail.skeleton(trip, rs, epi, ecdc, redirect)
    (out / "reply_skeleton.txt").write_text(skel, encoding="utf-8")
    (out / "sources.txt").write_text(mail.sources_block(), encoding="utf-8")

    adv = risk.advisories()
    age = (date.today() - adv["verified"]).days if isinstance(adv["verified"], date) else None
    qa = {"zone_sum_matches_national": ob.checks["zone_sum_matches_national"],
          "ecdc_matches": (ecdc.get("cases") == epi["last_total"]) if ecdc.get("ok") else None,
          "ecdc": ecdc, "unmatched_zone_names": ob.unmatched,
          "advisories_verified_days_ago": age, "advisories_stale": age is None or age > 14,
          "advisories_source": adv.get("_source", "package"),
          "map_label_overlaps": mp["label_overlaps"], "map_labels_clipped": mp.get("labels_clipped", 0),
          "far_stops_in_inset": mp["far_stops_in_inset"],
          "skeleton_issues": mail.check_text(skel)}
    summary = {"asof": str(ob.asof.date()), "overall": risk.overall(rs), "epi": epi,
               "stops": [{**{k: v for k, v in r.__dict__.items() if k not in ("lat", "lon")},
                          "verdict": r.verdict, "label": risk.LABEL[r.category]} for r in rs],
               "qa": qa, "files": sorted(str(p) for p in out.iterdir()),
               "map": mp["path"], "epicurve": str(out / f"epicurve_{ob.asof:%Y%m%d}.png"),
               "departure": str(first or ""), "table": tab.drop(columns=["signalen"]).to_string(index=False)}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if log_it:
        log_row(trip, summary)
    return summary


def log_row(trip: dict, summary: dict, review_on: str | None = None) -> None:
    from . import log
    log.append({"advised_on": date.today().isoformat(), "traveller": trip.get("traveller", ""),
                "departure": summary.get("departure", ""),
                "stops": "; ".join(f"{s['place']}/{s.get('zone') or s.get('country')}" for s in summary["stops"]),
                "categories": "".join(s["category"] for s in summary["stops"]), "overall": summary["overall"],
                "review_on": str(review_on or trip.get("review_on") or ""), "note": trip.get("note", "")})
