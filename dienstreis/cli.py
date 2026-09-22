"""Command line: dienstreis {advies,msg,data,run,check,widget,due,zoek,context}."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

from .pipeline import _slug, analyse, log_row


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
    if a.reset_cache:
        was = data.reset_cache()
        print(f"Cache verwijderd ({was:.0f} MB); de volgende run haalt enkel de bestanden "
              f"die de analyse gebruikt.")
        return
    ob = data.load(refresh=a.refresh, asof=a.asof)
    ecdc = data.ecdc_snapshot()
    z = ob.zones
    prov = z[z.cases > 0].groupby("PROVINCE")[["cases", "deaths", "new14"]].sum().sort_values("cases", ascending=False)
    print(f"Data tot {ob.asof:%Y-%m-%d} | checks: {ob.checks} | unmatched: {ob.unmatched}")
    print(f"Cache: {data.cache_size_mb():.0f} MB in {data.CACHE}")
    print(f"ECDC: {ecdc}")
    print(prov.to_string())
    if a.zone:
        cols = ["Nom", "PROVINCE", "cases", "deaths", "new14", "days_since_last"]
        print(z[z.Nom.str.contains(a.zone, case=False)][cols].to_string(index=False))


def cmd_run(a):
    from . import trip as trip_mod
    trip = trip_mod.coerce(yaml.safe_load(open(a.stops, encoding="utf-8")))
    issues = trip_mod.validate(trip, known_places=trip_mod.known_places())
    if issues:
        print(f"{a.stops} is niet bruikbaar:")
        for x in issues:
            print(f"  - {x}")
        sys.exit(1)
    out = Path(a.out or f"out_{_slug(trip.get('traveller', 'trip'))}")
    s = analyse(trip, out, refresh=a.refresh, asof=a.asof, log_it=a.log)
    print(s["table"])
    print(f"\nOordeel (regels): {s['overall']}")
    print(f"Wekelijks (laatste 4 volle weken): {s['epi']['weekly_cases_last4_full_weeks']}")
    print(f"QA: {json.dumps(s['qa'], default=str)}")
    print(f"Uitvoer in {out}/")


def cmd_advies(a):
    from .advies import run_advies
    run_advies(a.file, out=a.out, backend=a.llm, model=a.model, yes=a.yes, outlook=a.outlook,
               asof=a.asof, refresh=a.refresh, open_browser=not a.no_open, apply_web=a.apply_web,
               web=not a.no_web,
               numbers=not a.no_number_check)


def cmd_context(a):
    from .advies import CONTEXT, edit_file
    CONTEXT.parent.mkdir(parents=True, exist_ok=True)
    if not CONTEXT.exists():
        CONTEXT.write_text("# Context voor dienstreisadviezen\n\n", encoding="utf-8")
    if a.show:
        print(CONTEXT.read_text(encoding="utf-8"))
    else:
        edit_file(CONTEXT)
    print(CONTEXT)


def cmd_zoek(a):
    from . import archive
    from datetime import date as _d
    rows = archive.search(a.term or "", verdict=a.oordeel or "",
                          since=_d.fromisoformat(a.sinds) if a.sinds else None,
                          until=_d.fromisoformat(a.tot) if a.tot else None,
                          overruled=True if a.overruled else None, limit=a.limit)
    if not rows:
        print("Geen advies gevonden.")
        return
    for r in rows:
        ov = f"  OVERRULE: {len(r['overrides'])}" if r.get("overrides") else ""
        print(f"{r['advised_on']}  {r['traveller']}  {', '.join(str(p) for p in r.get('places', []))}"
              f"  [{r.get('categories', '')}]  {r.get('overall', '')}{ov}")
        if a.vol:
            for line in str(r.get("reply", "")).splitlines():
                print(f"    {line}")
        print(f"    {r['dir']}")
    print(f"\n{len(rows)} advies(en).")


def cmd_check(a):
    from .mail import check_text
    txt = Path(a.file).read_text(encoding="utf-8")
    m = re.search(r'<pre id="t"[^>]*>(.*?)</pre>', txt, re.S)
    issues = check_text(m.group(1) if m else txt)
    print("OK" if not issues else "\n".join(issues))
    sys.exit(1 if issues else 0)


def cmd_widget(a):
    from .mail import check_text, widget
    txt = Path(a.text).read_text(encoding="utf-8")
    sug = Path(a.suggestions).read_text(encoding="utf-8").strip().splitlines() if a.suggestions else []
    issues = check_text(txt)
    if issues:
        print("Niet gebouwd:", "; ".join(issues)); sys.exit(1)
    Path(a.out).write_text(widget(txt, sug, a.title), encoding="utf-8")
    print(a.out)


def cmd_due(a):
    from .log import due
    for r in due():
        print(f"{r['review_on']}  {r['traveller']}  {r['stops']}  ({r['overall']})")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):   # Windows consoles default to cp1252
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(prog="dienstreis")
    s = p.add_subparsers(dest="cmd", required=True)
    v = s.add_parser("advies", help="volledige workflow: .msg in, widget en conceptmail uit (LLM enkel voor oordeel)")
    v.add_argument("file", help=".msg, .eml of .txt met de aanvraag")
    v.add_argument("--llm", default=os.environ.get("DIENSTREIS_LLM", "claude-code"),
                   choices=["claude-code", "api", "manual"], help="LLM-backend (standaard: claude-code)")
    v.add_argument("--model", default=os.environ.get("DIENSTREIS_MODEL"))
    v.add_argument("--no-web", action="store_true",
                   help="FOD, CDC en WHO niet live laten nakijken (sneller, maar op de tabel van de laatste keer)")
    v.add_argument("--web", action="store_true", help=argparse.SUPPRESS)   # standaard aan sinds 0.3
    v.add_argument("--yes", action="store_true", help="reisschema niet laten bevestigen (stopt wel bij fouten)")
    v.add_argument("--apply-web", action="store_true",
                   help="wijzigingen uit --web zonder vragen overnemen in de lokale advisories.yaml")
    v.add_argument("--no-number-check", action="store_true",
                   help="cijfers in de mail niet vergelijken met de berekende gegevens")
    v.add_argument("--outlook", action="store_true", help="conceptmail met bijlagen in Outlook (Windows)")
    v.add_argument("--no-open", action="store_true", help="widget niet in de browser openen")
    v.add_argument("--out"); v.add_argument("--asof"); v.add_argument("--refresh", action="store_true")
    v.set_defaults(f=cmd_advies)
    x = s.add_parser("context", help="context.md openen (eerdere adviezen, open toezeggingen)")
    x.add_argument("--show", action="store_true"); x.set_defaults(f=cmd_context)
    m = s.add_parser("msg", help="Outlook .msg naar JSON"); m.add_argument("file"); m.add_argument("--attach-dir"); m.add_argument("--full", action="store_true"); m.set_defaults(f=cmd_msg)
    d = s.add_parser("data", help="actuele cijfers en controles"); d.add_argument("--refresh", action="store_true"); d.add_argument("--asof"); d.add_argument("--zone")
    d.add_argument("--reset-cache", action="store_true",
                   help="datacache wissen; de volgende run haalt enkel wat de analyse gebruikt")
    d.set_defaults(f=cmd_data)
    r = s.add_parser("run", help="volledige analyse voor stops.yaml"); r.add_argument("stops"); r.add_argument("--out"); r.add_argument("--refresh", action="store_true"); r.add_argument("--asof"); r.add_argument("--log", action="store_true"); r.set_defaults(f=cmd_run)
    c = s.add_parser("check", help="controle van een mailtekst of widget"); c.add_argument("file"); c.set_defaults(f=cmd_check)
    w = s.add_parser("widget", help="HTML-widget uit afgewerkte mailtekst"); w.add_argument("text"); w.add_argument("--suggestions"); w.add_argument("--out", required=True); w.add_argument("--title", default="Reply Team Actueel"); w.set_defaults(f=cmd_widget)
    u = s.add_parser("due", help="adviezen die opnieuw bekeken moeten worden"); u.set_defaults(f=cmd_due)
    z = s.add_parser("zoek", help="eerdere adviezen zoeken op plaats, zone, provincie, reiziger of notitie")
    z.add_argument("term", nargs="?", default="")
    z.add_argument("--sinds", help="JJJJ-MM-DD"); z.add_argument("--tot", help="JJJJ-MM-DD")
    z.add_argument("--oordeel", help="filter op het eindoordeel, bv. afraden")
    z.add_argument("--overruled", action="store_true", help="enkel adviezen waarin een regel overruled is")
    z.add_argument("--vol", action="store_true", help="de volledige mailtekst tonen")
    z.add_argument("--limit", type=int, default=50)
    z.set_defaults(f=cmd_zoek)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
