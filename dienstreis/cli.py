"""Command line: dienstreis {msg,data,run,check,due}."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40]


def cmd_msg(a):
    from .msg import parse_msg
    d = parse_msg(a.file, a.attach_dir)
    if not a.full:
        d["body"] = d["body"][:6000]
        for x in d["attachments"]:
            x["text"] = (x["text"] or "")[:4000]
    print(json.dumps(d, ensure_ascii=False, indent=2, default=str))


def cmd_data(a):
    from . import data
    ob = data.load(refresh=a.refresh, asof=a.asof)
    ecdc = data.ecdc_snapshot()
    z = ob.zones
    prov = z[z.cases > 0].groupby("PROVINCE")[["cases", "deaths", "new14"]].sum().sort_values("cases", ascending=False)
    print(f"Data tot {ob.asof:%Y-%m-%d} | checks: {ob.checks} | unmatched: {ob.unmatched}")
    print(f"ECDC: {ecdc}")
    print(prov.to_string())
    if a.zone:
        cols = ["Nom", "PROVINCE", "cases", "deaths", "new14", "days_since_last"]
        print(z[z.Nom.str.contains(a.zone, case=False)][cols].to_string(index=False))


def cmd_run(a):
    from . import data, figures, log, mail, risk
    trip = yaml.safe_load(open(a.stops))
    out = Path(a.out or f"out_{_slug(trip.get('traveller', 'trip'))}")
    out.mkdir(parents=True, exist_ok=True)
    ob = data.load(refresh=a.refresh, asof=a.asof)
    ecdc = data.ecdc_snapshot() if not a.asof else {"ok": False, "reason": "asof run"}
    rs = risk.assess(trip, ob)
    tab = risk.table(rs)
    tab.to_csv(out / "risk.csv", index=False)
    (out / "risk.md").write_text(tab.to_markdown(index=False) if hasattr(tab, "to_markdown") else tab.to_string())

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
    (out / "reply_skeleton.txt").write_text(skel)
    (out / "sources.txt").write_text(mail.sources_block())

    adv = risk.advisories()
    age = (date.today() - adv["verified"]).days if isinstance(adv["verified"], date) else None
    qa = {"zone_sum_matches_national": ob.checks["zone_sum_matches_national"],
          "ecdc_matches": (ecdc.get("cases") == epi["last_total"]) if ecdc.get("ok") else None,
          "ecdc": ecdc, "unmatched_zone_names": ob.unmatched,
          "advisories_verified_days_ago": age, "advisories_stale": age is None or age > 14,
          "map_label_overlaps": mp["label_overlaps"], "far_stops_in_inset": mp["far_stops_in_inset"],
          "skeleton_issues": mail.check_text(skel)}
    summary = {"asof": str(ob.asof.date()), "overall": risk.overall(rs), "epi": epi,
               "stops": [{**{k: v for k, v in r.__dict__.items() if k not in ("lat", "lon")},
                          "verdict": r.verdict, "label": risk.LABEL[r.category]} for r in rs],
               "qa": qa, "files": sorted(str(p) for p in out.iterdir())}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    if a.log:
        review = trip.get("review_on")
        log.append({"advised_on": date.today().isoformat(), "traveller": trip.get("traveller", ""),
                    "departure": str(first or ""), "stops": "; ".join(f"{r.place}/{r.zone or r.country}" for r in rs),
                    "categories": "".join(r.category for r in rs), "overall": risk.overall(rs),
                    "review_on": str(review or ""), "note": trip.get("note", "")})
    print(tab.drop(columns=["signalen"]).to_string(index=False))
    print(f"\nOordeel (regels): {risk.overall(rs)}")
    print(f"Wekelijks (laatste 4 volle weken): {epi['weekly_cases_last4_full_weeks']}")
    print(f"QA: {json.dumps(qa, default=str)}")
    print(f"Uitvoer in {out}/")


def cmd_check(a):
    from .mail import check_text
    txt = Path(a.file).read_text()
    m = re.search(r'<pre id="t"[^>]*>(.*?)</pre>', txt, re.S)
    issues = check_text(m.group(1) if m else txt)
    print("OK" if not issues else "\n".join(issues))
    sys.exit(1 if issues else 0)


def cmd_widget(a):
    from .mail import check_text, widget
    txt = Path(a.text).read_text()
    sug = Path(a.suggestions).read_text().strip().splitlines() if a.suggestions else []
    issues = check_text(txt)
    if issues:
        print("Niet gebouwd:", "; ".join(issues)); sys.exit(1)
    Path(a.out).write_text(widget(txt, sug, a.title))
    print(a.out)


def cmd_due(a):
    from .log import due
    for r in due():
        print(f"{r['review_on']}  {r['traveller']}  {r['stops']}  ({r['overall']})")


def main(argv=None):
    p = argparse.ArgumentParser(prog="dienstreis")
    s = p.add_subparsers(dest="cmd", required=True)
    m = s.add_parser("msg", help="Outlook .msg naar JSON"); m.add_argument("file"); m.add_argument("--attach-dir"); m.add_argument("--full", action="store_true"); m.set_defaults(f=cmd_msg)
    d = s.add_parser("data", help="actuele cijfers en controles"); d.add_argument("--refresh", action="store_true"); d.add_argument("--asof"); d.add_argument("--zone"); d.set_defaults(f=cmd_data)
    r = s.add_parser("run", help="volledige analyse voor stops.yaml"); r.add_argument("stops"); r.add_argument("--out"); r.add_argument("--refresh", action="store_true"); r.add_argument("--asof"); r.add_argument("--log", action="store_true"); r.set_defaults(f=cmd_run)
    c = s.add_parser("check", help="controle van een mailtekst of widget"); c.add_argument("file"); c.set_defaults(f=cmd_check)
    w = s.add_parser("widget", help="HTML-widget uit afgewerkte mailtekst"); w.add_argument("text"); w.add_argument("--suggestions"); w.add_argument("--out", required=True); w.add_argument("--title", default="Reply Team Actueel"); w.set_defaults(f=cmd_widget)
    u = s.add_parser("due", help="adviezen die opnieuw bekeken moeten worden"); u.set_defaults(f=cmd_due)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
