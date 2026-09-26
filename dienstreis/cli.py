"""Command line: dienstreis {advies,msg,data,run,check,dossier,fiche,opvolging,due,zoek,context,uitbraken,herlabel}."""
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
    from .msg import parse_msg, parse_request
    d = parse_request(a.file) if Path(a.file).is_dir() else parse_msg(a.file, a.attach_dir)
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
    from . import route
    from . import trip as trip_mod
    trip = trip_mod.coerce(yaml.safe_load(open(a.stops, encoding="utf-8")))
    if a.uitbraak:
        trip["outbreaks"] = a.uitbraak
    issues = trip_mod.validate(trip, known_places=trip_mod.known_places())
    if issues:
        print(f"{a.stops} is niet bruikbaar:")
        for x in issues:
            print(f"  - {x}")
        sys.exit(1)
    out = Path(a.out or f"out_{_slug(trip.get('traveller', 'trip'))}")
    print(f"Uitbraken: {', '.join(sp.id for sp in route.outbreaks_for(trip))}")
    s = analyse(trip, out, refresh=a.refresh, asof=a.asof, log_it=a.log)
    print(s["table"])
    print(f"\nOordeel (regels): {s['overall']}")
    if s.get("epi"):
        print(f"Wekelijks (laatste 4 volle weken): {s['epi']['weekly_cases_last4_full_weeks']}")
    print(f"QA: {json.dumps(s['qa'], default=str)}")
    print(f"Uitvoer in {out}/")


def cmd_advies(a):
    from .advies import run_advies
    run_advies(a.file, out=a.out, backend=a.llm, model=a.model, yes=a.yes, outlook=a.outlook,
               asof=a.asof, refresh=a.refresh, open_browser=not a.no_open, apply_web=a.apply_web,
               web=not a.no_web,
               numbers=not a.no_number_check, uitbraken=a.uitbraak, health_ok=a.gezondheidsgegevens_ok)


def cmd_herlabel(a):
    from . import archive, log
    r = archive.relabel(Path(a.dir), kind=a.type, outbreaks=a.uitbraak, reason=a.reden)
    in_log = log.relabel(a.dir, {k: v for k, v in (("type", a.type),
                                                   ("outbreaks", " ".join(a.uitbraak) if a.uitbraak else None)) if v})
    print(f"{a.dir}: type {r.get('type')}, uitbraken {', '.join(r.get('outbreaks', []))}"
          + ("; logregel aangepast" if in_log else "; geen logregel gevonden"))


def cmd_uitbraken(a):
    from . import countries, outbreak
    for i in outbreak.ids():
        sp = outbreak.load(i)
        kind = "landniveau, geen cijfers" if not sp.has_data else f"cijfers: {sp.adapter['type']}"
        state = "actief" if sp.active else "niet actief"
        where = ", ".join(sp.countries) or "-"
        near = sorted({n for c in sp.countries for n in countries.neighbours(c)} - set(sp.countries))
        print(f"{i:<18} {sp.name}  [{state}; {kind}]\n{'':<18} landen: {where}"
              + (f"; buurlanden: {', '.join(near)}" if near else ""))


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
                          overruled=True if a.overruled else None, outbreak=a.uitbraak or "", kind=a.type or "",
                          limit=a.limit)
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
        page = Path(r["dir"]) / "dossier.html"
        if page.exists():
            print(f"    {page.resolve().as_uri()}")
    print(f"\n{len(rows)} advies(en).")


def cmd_check(a):
    from .mail import check_text
    txt = Path(a.file).read_text(encoding="utf-8")
    m = re.search(r'<pre id="t"[^>]*>(.*?)</pre>', txt, re.S)
    issues = check_text(m.group(1) if m else txt)
    print("OK" if not issues else "\n".join(issues))
    sys.exit(1 if issues else 0)


def cmd_dossier(a):
    """Rebuild the dossier of a run, after reply.txt was edited by hand; the checks run again."""
    import webbrowser
    from . import dossier
    out = Path(a.out)
    if not (out / "summary.json").exists():
        print(f"Geen run in {out}: summary.json ontbreekt."); sys.exit(1)
    page = dossier.build(out, rebuilt=True)
    checks = json.loads((out / dossier.DATA).read_text(encoding="utf-8"))["checks"]
    for x in checks["notes"]:
        print(f"  let op: {x}")
    print(page)
    if not a.no_open:
        webbrowser.open(page.resolve().as_uri())
    if checks["issues"]:
        print("Kopiëren staat uit: " + "; ".join(checks["issues"])); sys.exit(1)


def cmd_fiche(a):
    """The fiche and documents of an outbreak: their state, or a concept drafted from sources (F-015)."""
    from datetime import date
    from . import countries, fiche, llm, outbreak
    sp = outbreak.load(a.id)
    if sp.id == outbreak.NONE:
        print("Het profiel 'geen' is geen ziekte en heeft geen fiche."); sys.exit(1)
    if a.opstellen:
        trace_dir = fiche.LOCAL / sp.id
        be = llm.get_backend(a.llm, a.model, trace_dir)
        cur = fiche.load(sp)
        inputs = {"vandaag": date.today().isoformat(),
                  "uitbraak": {"id": sp.id, "naam": sp.name, "landen": sp.countries, "cijfers": sp.case_words},
                  "secties": list(fiche.SECTIONS), "niveaus": fiche.LEVELS,
                  "bestaande_fiche": cur["body"] if cur else "",
                  "bestaande_documenten": fiche.documents(sp)["levels"],
                  "internationaal": countries.international()}
        print(f"Fiche opstellen voor {sp.name} ({be.name}, met webzoeken); dat duurt enkele minuten.")
        try:
            ans = llm.ask_json(be, "fiche", inputs, required=["secties", "documenten"], web=True, specs=[sp])
        finally:                           # what the model was given and answered, kept outside the repo
            trace_dir.mkdir(parents=True, exist_ok=True)
            (trace_dir / "fiche_trace.json").write_text(
                json.dumps(llm.trace_of(be), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        for path in fiche.write_draft(sp, ans, sp.dir if a.repo else trace_dir):
            print(f"  {path}")
        for n in ans.get("notities") or []:
            print(f"  - {n}")
        print("Een concept: lees het na, en zet dan status: bevestigd, bevestigd_door en bevestigd_op. "
              "Pas daarna steunt de mail erop.")
        return
    f, d = fiche.load(sp), fiche.documents(sp)
    if not f:
        print(f"{sp.id}: nog geen fiche. Maak een concept met: dienstreis fiche {sp.id} --opstellen")
    else:
        who = f" door {f['bevestigd_door']} op {f['bevestigd_op']}" if f["confirmed"] else ""
        print(f"{sp.id}: fiche {f['status']}{who}, bronnen nagekeken {f['verified'] or '-'} ({f['source']}: {f['path']})")
        ids = {x.get("id") for docs in d["levels"].values() for x in docs}
        for x in f["issues"] + [f"verwijzing zonder document: [{r}]" for r in f["refs"] if r not in ids]:
            print(f"  - {x}")
    counts = ", ".join(f"{lv} {len(docs)}" for lv, docs in d["levels"].items())
    print(f"documenten: {counts}; nagekeken {d['verified'] or '-'} ({d['source'] or 'geen lijst'}: {d['path'] or '-'})")
    for x in fiche.check_documents(d):
        print(f"  - {x}")


def cmd_opvolging(a):
    """The go/no-go checks that have come and the travellers in the field, on today's figures (F-017)."""
    import subprocess
    import webbrowser
    from datetime import date as _d
    from . import opvolging
    if a.plannen:
        if not sys.platform.startswith("win"):
            print("Plannen gaat via de Windows Taakplanner. Elders: zet `dienstreis opvolging --stil` in cron.")
            sys.exit(1)
        for cmd in opvolging.plan_commands(a.plannen, a.uur):
            r = subprocess.run(cmd, capture_output=True, text=True)
            print((r.stdout or r.stderr).strip())
            if r.returncode != 0:
                sys.exit(r.returncode)
        print("Planning verwijderd." if a.plannen == "uit" else
              f"Gepland ({a.plannen}, {a.uur}): de pagina opent enkel als er iets veranderde sinds de vorige check.")
        return
    if a.klaar:
        r = opvolging.mark_done(a.klaar, a.notitie)
        print(f"Go/no-go van {r.get('traveller')} genoteerd op {r['go_no_go']['op']}.")
        return
    rep = opvolging.run(today=_d.fromisoformat(a.asof) if a.asof else None, horizon=a.dagen, term=a.term or "",
                        asof=a.asof, refresh=a.refresh)
    for x in rep["results"]:
        flag = " GO/NO-GO" if x["due"] else ""
        print(f"{x['status']:<16}{flag:<10} {x['traveller']}  {', '.join(map(str, x['places']))}  "
              f"({x['first']} tot {x['last']})")
    if not rep["results"]:
        print(f"Niemand ter plaatse en geen vertrek binnen {a.dagen} dagen.")
    print(rep["page"])
    open_it = opvolging.news_since_last(rep) if a.stil else not a.no_open
    if open_it:
        webbrowser.open(Path(rep["page"]).resolve().as_uri())


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
    v = s.add_parser("advies", help="volledige workflow: .msg in, kort antwoord, intern dossier en conceptmail uit (LLM enkel voor oordeel)")
    v.add_argument("file", help=".msg, .eml of .txt met de aanvraag, of een map met alle mails van één aanvraag")
    v.add_argument("--llm", default=os.environ.get("DIENSTREIS_LLM", "claude-code"),
                   choices=["claude-code", "api", "manual"], help="LLM-backend (standaard: claude-code)")
    v.add_argument("--model", default=os.environ.get("DIENSTREIS_MODEL"))
    v.add_argument("--no-web", action="store_true",
                   help="FOD, CDC en WHO niet live laten nakijken (sneller, maar op de tabel van de laatste keer)")
    v.add_argument("--web", action="store_true", help=argparse.SUPPRESS)   # standaard aan sinds 0.3
    v.add_argument("--yes", action="store_true", help="reisschema niet laten bevestigen (stopt wel bij fouten)")
    v.add_argument("--apply-web", action="store_true",
                   help="wijzigingen uit de webstap zonder vragen overnemen in het lokale landenregister")
    v.add_argument("--uitbraak", action="append", metavar="ID",
                   help="beoordeel tegen deze uitbraak (herhaalbaar); standaard volgt het uit de landen van de reis")
    v.add_argument("--gezondheidsgegevens-ok", action="store_true",
                   help="een aanvraag met gezondheidsgegevens over een persoon zonder vragen naar het model sturen")
    v.add_argument("--no-number-check", action="store_true",
                   help="cijfers in de mail niet vergelijken met de berekende gegevens")
    v.add_argument("--outlook", action="store_true", help="conceptmail met bijlagen in Outlook (Windows)")
    v.add_argument("--no-open", action="store_true", help="het dossier niet in de browser openen")
    v.add_argument("--out"); v.add_argument("--asof"); v.add_argument("--refresh", action="store_true")
    v.set_defaults(f=cmd_advies)
    x = s.add_parser("context", help="context.md openen (eerdere adviezen, open toezeggingen)")
    x.add_argument("--show", action="store_true"); x.set_defaults(f=cmd_context)
    m = s.add_parser("msg", help="Outlook .msg (of een map met mails) naar JSON"); m.add_argument("file"); m.add_argument("--attach-dir"); m.add_argument("--full", action="store_true"); m.set_defaults(f=cmd_msg)
    d = s.add_parser("data", help="actuele cijfers en controles"); d.add_argument("--refresh", action="store_true"); d.add_argument("--asof"); d.add_argument("--zone")
    d.add_argument("--reset-cache", action="store_true",
                   help="datacache wissen; de volgende run haalt enkel wat de analyse gebruikt")
    d.set_defaults(f=cmd_data)
    r = s.add_parser("run", help="volledige analyse voor stops.yaml"); r.add_argument("stops"); r.add_argument("--out"); r.add_argument("--refresh", action="store_true"); r.add_argument("--asof"); r.add_argument("--log", action="store_true")
    r.add_argument("--uitbraak", action="append", metavar="ID", help="beoordeel tegen deze uitbraak (herhaalbaar)")
    r.set_defaults(f=cmd_run)
    ub = s.add_parser("uitbraken", help="de uitbraakprofielen, met hun landen en buurlanden"); ub.set_defaults(f=cmd_uitbraken)
    hl = s.add_parser("herlabel", help="een bewaard advies opnieuw labelen (type, uitbraken), met reden")
    hl.add_argument("dir", help="de map van het advies in het archief")
    hl.add_argument("--type", choices=["reisadvies", "casus", "vraag"])
    hl.add_argument("--uitbraak", action="append", metavar="ID")
    hl.add_argument("--reden", required=True)
    hl.set_defaults(f=cmd_herlabel)
    c = s.add_parser("check", help="controle van een mailtekst of dossier"); c.add_argument("file"); c.set_defaults(f=cmd_check)
    w = s.add_parser("dossier", help="het interne dossier opnieuw opbouwen, na een aanpassing van reply.txt")
    w.add_argument("out", help="de map van de run (out_...)")
    w.add_argument("--no-open", action="store_true", help="niet in de browser openen")
    w.set_defaults(f=cmd_dossier)
    fi = s.add_parser("fiche", help="de ziektefiche en documenten van een uitbraak: stand, of een concept laten opstellen")
    fi.add_argument("id", help="het id van de uitbraak (dienstreis uitbraken)")
    fi.add_argument("--opstellen", action="store_true",
                    help="een concept laten opstellen uit Belgische, Europese, WHO- en Amerikaanse bronnen (webzoeken)")
    fi.add_argument("--repo", action="store_true",
                    help="het concept in de map van het profiel zetten in plaats van lokaal (om te committen)")
    fi.add_argument("--llm", default=os.environ.get("DIENSTREIS_LLM", "claude-code"), choices=["claude-code", "api", "manual"])
    fi.add_argument("--model", default=os.environ.get("DIENSTREIS_MODEL"))
    fi.set_defaults(f=cmd_fiche)
    op = s.add_parser("opvolging", help="go/no-go-checks en reizigers ter plaatse, op de cijfers van vandaag (geen model)")
    op.add_argument("term", nargs="?", default="", help="enkel deze reiziger of plaats, ook verder dan --dagen (bv. op vraag van An)")
    op.add_argument("--dagen", type=int, default=30, help="een vertrek binnen zoveel dagen telt mee (standaard 30)")
    op.add_argument("--asof", help="JJJJ-MM-DD: de cijfers en de dag van die datum")
    op.add_argument("--refresh", action="store_true")
    op.add_argument("--stil", action="store_true",
                    help="voor een geplande run: de pagina enkel openen als er iets veranderde sinds de vorige check")
    op.add_argument("--no-open", action="store_true", help="de pagina niet openen")
    op.add_argument("--klaar", metavar="MAP", help="de go/no-go van dit advies (map in het archief) als beslist noteren")
    op.add_argument("--notitie", default="", help="bij --klaar: wat er beslist is")
    op.add_argument("--plannen", choices=["weekdagen", "dagelijks", "wekelijks", "uit"],
                    help="zelf een planning instellen of weghalen (Windows Taakplanner)")
    op.add_argument("--uur", default="08:00", help="bij --plannen: UU:MM (standaard 08:00)")
    op.set_defaults(f=cmd_opvolging)
    u = s.add_parser("due", help="adviezen die opnieuw bekeken moeten worden (zie ook opvolging)"); u.set_defaults(f=cmd_due)
    z = s.add_parser("zoek", help="eerdere adviezen zoeken op plaats, zone, provincie, reiziger of notitie")
    z.add_argument("term", nargs="?", default="")
    z.add_argument("--sinds", help="JJJJ-MM-DD"); z.add_argument("--tot", help="JJJJ-MM-DD")
    z.add_argument("--oordeel", help="filter op het eindoordeel, bv. afraden")
    z.add_argument("--overruled", action="store_true", help="enkel adviezen waarin een regel overruled is")
    z.add_argument("--uitbraak", metavar="ID", help="enkel adviezen over deze uitbraak")
    z.add_argument("--type", choices=["reisadvies", "casus", "vraag"], help="enkel adviezen van dit type")
    z.add_argument("--vol", action="store_true", help="de volledige mailtekst tonen")
    z.add_argument("--limit", type=int, default=50)
    z.set_defaults(f=cmd_zoek)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
