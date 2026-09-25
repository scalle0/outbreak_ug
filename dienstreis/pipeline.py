"""The deterministic core: data, risk per stop, map, epicurve, reply skeleton, QA.

Everything here is arithmetic on the itinerary and the outbreak's figures; no model is involved. Kept
apart from cli.py so that `advies` can call it without importing the argument parser, and so that
the boundary between "calculated" and "written by a model" is visible in the imports.

A trip is assessed against every outbreak that applies to it (route.outbreaks_for), each on its
own figures, or at country level with the profile `geen` when none applies. The summary keeps its
familiar shape for the strictest outbreak; with several, every outbreak is also under `outbreaks`.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40]


def _assess_one(trip: dict, spec, out: Path, tag: str, refresh: bool, asof: str | None, multi: bool) -> dict:
    """One outbreak: its figures, the risk per stop, and its map and curve (file names carry its id when
    there are several). A profile without figures (`geen`) gives the stops at country level only."""
    from . import data, figures, mail, outbreak, risk
    ob = data.load(refresh=refresh, asof=asof, spec=spec) if spec.has_data else None
    src = data.sources_snapshot(asof, spec=spec)
    rs = risk.assess(trip, ob, spec)
    sfx = f"_{spec.id}" if multi else ""
    epi = mp = curve = None
    if ob is not None:
        curve = out / f"epicurve{sfx}_{ob.asof:%Y%m%d}.png"
        epi = figures.epicurve(ob, str(curve), src["ecdc"])
        first = min((r.start for r in rs if r.start), default=None)
        last = max((r.end for r in rs if r.end), default=None)
        sub = (f"{trip.get('traveller', '')}, {mail.d(first)} {first.year if first else ''} tot {mail.d(last)} "
               f"{last.year if last else ''}. Nationaal: {mail.n(epi['last_total'])} gevallen, "
               f"{mail.n(epi['last_deaths'])} overlijdens (data tot {ob.asof:%d-%m-%Y})")
        mp = figures.itinerary_map(rs, ob, spec.figures["map_title"], sub, str(out / f"kaart_{tag}{sfx}.png"))
    ecdc, who = src["ecdc"], src["who"]
    qa = {"zone_sum_matches_national": ob.checks["zone_sum_matches_national"] if ob is not None else None,
          "ecdc_matches": (ecdc.get("cases") == epi["last_total"]) if ecdc.get("ok") and epi else None,
          "ecdc": ecdc, "who": who, "who_days_old": who.get("days_old"),
          "sources_unreachable": [k for k, v in src.items() if not v.get("ok")
                                  and v.get("reason") not in ("asof run", data.NOT_CONFIGURED)],
          "unmatched_zone_names": ob.unmatched if ob is not None else [],
          "map_label_overlaps": mp["label_overlaps"] if mp else 0,
          "map_labels_clipped": mp.get("labels_clipped", 0) if mp else 0,
          "far_stops_in_inset": mp["far_stops_in_inset"] if mp else []}
    # with several outbreaks the trip-level verdict override belongs to the whole advice, not to one
    t = None if multi else trip
    return {"spec": spec, "ob": ob, "rs": rs, "tab": risk.table(rs), "epi": epi, "map": mp,
            "curve": str(curve) if curve else None, "qa": qa, "who": who,
            "level": outbreak.strictest(spec.level(r.category) for r in rs) if spec.has_data else None,
            "overall": risk.overall(rs, t), "rule_overall": risk.rule_overall(rs), "overrides": risk.overrides(rs, t)}


def _stops(rs) -> list[dict]:
    return [{**{k: v for k, v in r.__dict__.items() if k not in ("lat", "lon", "spec")},
             "verdict": r.verdict, "label": r.outbreak_spec.label(r.category)} for r in rs]


def analyse(trip: dict, out: Path, refresh: bool = False, asof: str | None = None, log_it: bool = False,
            spec=None, specs=None) -> dict:
    """Deterministic core: data, risk per stop, map, epicurve, reply skeleton, QA. Returns summary.

    `spec` or `specs` name the outbreaks to assess the trip against; by default those of the trip
    (`outbreaks:` in stops.yaml), else the routing.
    """
    import pandas as pd
    from . import countries, mail, outbreak, route
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    specs = [spec] if spec else list(specs or route.outbreaks_for(trip))
    multi = len(specs) > 1
    tag = _slug(trip.get("traveller", "trip"))
    parts = [_assess_one(trip, s, out, tag, refresh, asof, multi) for s in specs]
    order = {lv: i for i, lv in enumerate(outbreak.LEVELS)}
    parts.sort(key=lambda p: order.get(p["level"], len(order)))       # strictest first, stable
    main, others = parts[0], parts[1:]

    if multi:
        tab = pd.concat([p["tab"].assign(uitbraak=p["spec"].id) for p in parts], ignore_index=True)
        tab = tab[["uitbraak"] + [c for c in tab.columns if c != "uitbraak"]]
    else:
        tab = main["tab"]
    tab.to_csv(out / "risk.csv", index=False, encoding="utf-8")
    (out / "risk.md").write_text(tab.to_markdown(index=False) if hasattr(tab, "to_markdown") else tab.to_string(),
                                 encoding="utf-8")

    trip_override = trip.get("override") or {}
    if multi:
        effective = "; ".join(f"{p['spec'].name}: {p['overall']}" for p in parts)
        overall = str(trip_override["verdict"]) if trip_override.get("verdict") else effective
        rule_overall = "; ".join(f"{p['spec'].name}: {p['rule_overall']}" for p in parts)
        overrides = [{**o, "outbreak": p["spec"].id} for p in parts for o in p["overrides"]]
        if trip_override.get("verdict"):
            overrides.append({"scope": "eindoordeel", "van": effective, "naar": trip_override["verdict"],
                              "reason": trip_override.get("reason")})
    else:
        overall, rule_overall, overrides = main["overall"], main["rule_overall"], main["overrides"]

    redirect = bool(trip.get("sent_to_ugent_address", False))
    skel = mail.skeleton(trip, main["rs"], main["epi"], main["qa"]["ecdc"], redirect,
                         others=[(p["rs"], p["epi"], p["qa"]["ecdc"]) for p in others], overrides=overrides)
    (out / "reply_skeleton.txt").write_text(skel, encoding="utf-8")
    trip_iso = list(dict.fromkeys(r.country for r in main["rs"] if r.country))
    (out / "sources.txt").write_text(mail.sources_block(main["spec"], trip_iso, [p["spec"] for p in others]),
                                     encoding="utf-8")

    # advisories are per country now: name the ones nobody has checked instead of hiding them in one date
    reg = {i: countries.load(i) for i in trip_iso}
    ages = {i: countries.age_days(c) for i, c in reg.items()}
    unverified = [i for i in trip_iso if ages.get(i) is None]
    age = max((a for a in ages.values() if a is not None), default=None)
    m = main["qa"]
    qa = {**{k: m[k] for k in ("zone_sum_matches_national", "ecdc_matches", "ecdc", "who", "who_days_old",
                               "sources_unreachable", "unmatched_zone_names")},
          "advisories_verified_days_ago": age,
          "advisories_stale": bool(unverified) or age is None or age > countries.STALE_DAYS,
          "advisories_unverified": unverified,
          "advisories_source": {i: c["_source"] for i, c in reg.items() if c},
          **{k: m[k] for k in ("map_label_overlaps", "map_labels_clipped", "far_stops_in_inset")},
          "skeleton_issues": mail.check_text(skel),
          "overrules_count": len(overrides)}
    first = min((r.start for r in main["rs"] if r.start), default=None)
    ob = main["ob"]
    summary = {"asof": str(ob.asof.date()) if ob is not None else None, "outbreak": main["spec"].id,
               "overall": overall, "rule_overall": rule_overall, "overrides": overrides, "epi": main["epi"],
               "stops": _stops(main["rs"]),
               "qa": qa, "files": sorted(str(p) for p in out.iterdir()),
               "who": main["who"], "map": main["map"]["path"] if main["map"] else None, "epicurve": main["curve"],
               "departure": str(first or ""), "table": tab.drop(columns=["signalen"]).to_string(index=False),
               "overall_level": outbreak.strictest(p["level"] for p in parts if p["level"]),
               "attachments": [x for p in parts for x in ((p["map"] or {}).get("path"), p["curve"]) if x]}
    if multi:
        summary["outbreaks"] = {
            p["spec"].id: {"name": p["spec"].name,
                           "asof": str(p["ob"].asof.date()) if p["ob"] is not None else None,
                           "overall": p["overall"], "rule_overall": p["rule_overall"], "level": p["level"],
                           "overrides": [{**o, "outbreak": p["spec"].id} for o in p["overrides"]],
                           "epi": p["epi"], "stops": _stops(p["rs"]), "qa": p["qa"], "who": p["who"],
                           "map": (p["map"] or {}).get("path"), "epicurve": p["curve"],
                           "table": p["tab"].drop(columns=["signalen"]).to_string(index=False)}
            for p in parts}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if log_it:
        log_row(trip, summary)
    return summary


def outbreak_ids(summary: dict) -> list[str]:
    """Every outbreak an advice was assessed against, strictest first."""
    ids = list(summary.get("outbreaks") or [])
    return ids or ([summary["outbreak"]] if summary.get("outbreak") else [])


def log_row(trip: dict, summary: dict, review_on: str | None = None,
            advice_dir: str = "") -> None:
    from . import log
    log.append({"advised_on": date.today().isoformat(), "traveller": trip.get("traveller", ""),
                "departure": summary.get("departure", ""),
                "stops": "; ".join(f"{s['place']}/{s.get('zone') or s.get('country')}" for s in summary["stops"]),
                "categories": "".join(s["category"] for s in summary["stops"]), "overall": summary["overall"],
                "review_on": str(review_on or trip.get("review_on") or ""), "note": trip.get("note", ""),
                "overrules": "; ".join(f"{o['scope']}: {o['van']} -> {o['naar']} ({o['reason']})"
                                       for o in summary.get("overrides", [])),
                "advice_dir": advice_dir, "outbreaks": " ".join(outbreak_ids(summary))})
