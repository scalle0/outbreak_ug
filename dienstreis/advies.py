"""`dienstreis advies`: the whole workflow from a request mail to a checked reply, run on the user's PC.

    1 read the request (.msg/.eml/.txt, or a folder with all its mails)  deterministic
    2 itinerary from the mail -> stops.yaml, user confirms       LLM (stops)
      and the outbreaks that apply to it (routing)               deterministic
    3 per outbreak: data, risk per stop, map, epicurve; facts, QA   deterministic
    4 optional: advisories, border measures and news not yet in the data   LLM with web access (web)
    5 short reply to An, dossier fields for Steven               LLM (reply)
    A case or a question (type casus / vraag) takes the same road with its own web and reply
    prompts (web_consult, consult); its map and curve stay in the dossier. A mail that looks like
    health data about a person is only sent after the user agrees (decision 2026-09-25).
    6 text checks (em-dash, banned words, placeholders), one repair round, the dossier
      (dossier.py), log, context line, browser, optional Outlook draft   deterministic
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from datetime import date, datetime
from importlib import metadata
from pathlib import Path

import yaml

from . import archive, countries, data, fiche, llm, log, mail, outbreak, route
from . import trip as trip_mod
from .pipeline import _slug, analyse, log_row, outbreak_ids
from .msg import health_signals, parse_request

CONTEXT = Path(os.environ.get("DIENSTREIS_CONTEXT", Path.home() / ".config" / "dienstreis" / "context.md"))


def edit_file(path: Path) -> None:
    """Open a file in the user's editor and wait (Notepad on Windows)."""
    ed = os.environ.get("EDITOR") or ("notepad" if sys.platform.startswith("win") else "nano")
    subprocess.run([ed, str(path)])


_known_places = trip_mod.known_places


def _say(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def _trip_from_llm(d: dict, req: dict) -> dict:
    keep = ("type", "traveller", "note", "situation", "profile", "sent_to_ugent_address", "review_on", "stops")
    t = {k: d[k] for k in keep if k in d}
    # whether the thread used the ugent.be address is read from the mail itself, never from the model
    t["sent_to_ugent_address"] = bool(req.get("sent_to_ugent_address")) or bool(t.get("sent_to_ugent_address"))
    return trip_mod.coerce(t)


def _routed(trip: dict, mentioned=()) -> list[str]:
    """The outbreaks routing gives for the stops as they are now, ignoring what the trip names.

    A case or a question without a place gets the active outbreaks its diseases name, or `geen`.
    """
    if not trip.get("stops"):
        return route.by_disease(mentioned or []) or [outbreak.NONE]
    return [sp.id for sp in route.outbreaks_for({**trip, "outbreaks": None})]


def _consent(signals: list[str], backend: str, yes: bool, health_ok: bool, already_sent: bool = False) -> None:
    """Ask before a mail with health data about a person goes to a model (decision 2026-09-25).

    `--yes` does not answer this question: confirming an itinerary is not agreeing to send health
    data. `--gezondheidsgegevens-ok` does, for a run without a keyboard. The manual backend sends nothing.
    """
    if health_ok or backend == "manual":
        return
    what = ("De mail ging al naar het model om het reisschema te lezen; nu gaan ook de webstap en het "
            "schrijven van de mail erover." if already_sent else
            f"Onderwerp, tekst en bijlagen van de mail gaan naar het model ({backend}).")
    print(f"\n  Deze aanvraag lijkt gezondheidsgegevens over een persoon te bevatten ({', '.join(signals)}). {what}")
    if yes:
        raise SystemExit("Gestopt: bevestig het versturen van gezondheidsgegevens met --gezondheidsgegevens-ok, "
                         "draai zonder --yes, of gebruik --llm manual.")
    if not input("  Doorgaan? [j/n]: ").strip().lower().startswith("j"):
        raise SystemExit("Gestopt op vraag van de gebruiker" + ("." if already_sent else "; er is niets verstuurd."))


def _print_trip(trip: dict, d: dict, issues: list[str]) -> None:
    print(f"Type: {trip.get('type') or 'reisadvies'}")
    if trip.get("situation"):
        print(f"Toestand: {trip['situation']}")
    print(f"Reiziger: {trip.get('traveller')}  |  {trip.get('note', '')}  |  profiel: {trip.get('profile')}")
    names = []
    for oid in trip.get("outbreaks") or []:
        try:
            names.append(f"{oid} ({outbreak.load(oid).name})")
        except outbreak.ProfileError:
            names.append(f"{oid} (onbekend)")
    print(f"Uitbraken: {', '.join(names) or '-'}")
    for s in trip.get("stops") or []:
        extra = " (transit)" if s.get("transit_only") else ""
        extra += f" [{s['lodging']}]" if s.get("lodging") else ""
        extra += f" lat/lon {s['lat']}, {s['lon']}" if "lat" in s else ""
        print(f"  {s.get('from')} tot {s.get('to') or '(open)'}  {s.get('place')}{extra}")
    print(f"Go/no-go: {trip.get('review_on')}")
    specs = [outbreak.load(i) for i in trip.get("outbreaks") or [] if i in outbreak.ids()]
    for x in route.unmatched_diseases(d.get("diseases_mentioned") or [], specs):
        print(f"  Genoemd, zonder uitbraakprofiel: {x}")
    for k, t in (("contradictions", "Tegenstrijdig"), ("missing_info", "Ontbreekt"), ("questions_from_an", "Vragen An")):
        for x in d.get(k, []):
            print(f"  {t}: {x}")
    for x in issues:
        print(f"  FOUT: {x}")


def _check_trip(trip: dict, today: date | None = None) -> list[str]:
    return trip_mod.validate(trip, known_places=_known_places(), today=today)


def confirm_trip(trip: dict, d: dict, out: Path, yes: bool, fixed_outbreaks: bool = False,
                 today: date | None = None) -> dict:
    """Show the itinerary with its problems and let the user confirm, edit or stop.

    An itinerary with problems is never analysed: the places and dates are the input to every
    calculation that follows, so a wrong one produces a wrong risk table rather than an error.
    The outbreaks follow the stops after an edit, unless the user changed them in the file or
    named them on the command line.
    """
    path = out / "stops.yaml"
    path.write_text(yaml.safe_dump(trip, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = _check_trip(trip, today)
    _print_trip(trip, d, issues)
    if yes:
        if issues:
            raise SystemExit(f"Reisschema niet bruikbaar ({len(issues)} fout(en), zie hierboven). "
                             f"Corrigeer {path} en draai `dienstreis run` of `dienstreis advies` opnieuw.")
        return trip
    while True:
        opts = "[b]ewerken / [s]toppen" if issues else "[j]a / [b]ewerken / [s]toppen"
        a = input(f"\nKlopt dit reisschema? {opts}: ").strip().lower() or ("b" if issues else "j")
        if (a.startswith("j") or a.startswith("y")) and not issues:
            return trip_mod.coerce(yaml.safe_load(path.read_text(encoding="utf-8")))
        if a.startswith("j") or a.startswith("y"):
            print("  Eerst de fouten hierboven oplossen; kies [b]ewerken.")
        elif a.startswith("b") or a.startswith("e"):
            before = trip.get("outbreaks")
            edit_file(path)
            trip = trip_mod.coerce(yaml.safe_load(path.read_text(encoding="utf-8")))
            if not fixed_outbreaks and trip.get("outbreaks") == before:
                trip["outbreaks"] = _routed(trip, d.get("diseases_mentioned"))
            path.write_text(yaml.safe_dump(trip, allow_unicode=True, sort_keys=False), encoding="utf-8")
            issues = _check_trip(trip, today)
            _print_trip(trip, d, issues)
        elif a.startswith("s") or a.startswith("n"):
            raise SystemExit("Gestopt; stops.yaml blijft staan in " + str(out))


def _context_text() -> str:
    return CONTEXT.read_text(encoding="utf-8") if CONTEXT.exists() else "(geen contextbestand)"


def _history(trip: dict) -> list[dict]:
    seen, rows = set(), []
    keys = [s["place"] for s in trip.get("stops", [])]
    if trip.get("type") in ("casus", "vraag") and trip.get("traveller"):
        keys.append(trip["traveller"])            # a case follows up on the same person
    for key in keys:
        for r in log.history(key):
            key = tuple(r.values())
            if key not in seen:
                seen.add(key)
                rows.append(r)
    return rows[-15:]


def maybe_apply_web(webd: dict, apply_web: bool, outbreak_id: str = outbreak.DEFAULT, specs=(),
                    proef: bool = False) -> bool | None:
    """Show what the web step found that the country registry does not hold; on confirmation keep it locally.

    Overwriting a travel advisory or a border measure is a judgement, not a confirmation of something
    already shown: it changes the flags of every later advice. So this asks even under --yes, unless
    --apply-web says otherwise. Accepting also records that the countries were checked today, so a
    country stops being "never verified" once you have seen what was found for it.

    Newer or new key documents per outbreak (`document_updates`) are kept the same way, in a local
    copy of the outbreak's documents list. A statement of a fiche that newer guidance contradicts
    (`fiche_flags`) is only shown: the fiche is changed by the clinician, never by the code.

    Returns whether it was kept, or None when there was nothing to propose (for the dossier). A dry run
    (`proef`) shows everything and keeps nothing.
    """
    for n in webd.get("news", []):
        print(f"  nieuws {n.get('date')}: {n.get('item')} ({n.get('url')})")
    changed = [a for a in webd.get("advisories", []) if a.get("changed")]
    measures = [m for m in webd.get("measures", []) if m.get("changed")]
    found = [x for x in webd.get("sources", []) if x.get("country") and x.get("url")]
    for x in [x for x in found if countries.excluded(x["url"])]:
        print(f"  BRON overgeslagen (uitgesloten): {x.get('name')}  {x['url']}")
    found = [x for x in found if not countries.excluded(x["url"])]
    checked = sorted({a["country"] for a in webd.get("advisories", []) if a.get("country")})
    first = [i for i in checked if countries.age_days(countries.load(i)) is None]
    tables = {sp.id: sp for sp in specs if sp.adapter.get("type") == "table"}
    rows = [r for r in webd.get("case_updates", []) if r.get("outbreak") in tables and r.get("date")]
    by_id = {sp.id: sp for sp in specs}
    docs = [u for u in webd.get("document_updates", []) if isinstance(u, dict) and u.get("outbreak") in by_id
            and u.get("level") in fiche.LEVELS and u.get("url") and not countries.excluded(u["url"])]
    for f in [x for x in webd.get("fiche_flags", []) if isinstance(x, dict)]:
        print(f"  FICHE {f.get('outbreak')}, {f.get('section')}: \"{f.get('statement')}\" -> {f.get('newer')} "
              f"({f.get('date')})  [{f.get('source')}]  (enkel ter info: de fiche pas je zelf aan)")
    for r in rows:
        print(f"  CIJFERS {r['outbreak']} {r.get('date')} {r.get('admin1')} {r.get('admin2') or ''}: "
              f"{r.get('cases_cum')} gevallen, {r.get('deaths_cum')} overlijdens ({r.get('case_def')})  "
              f"[{r.get('source_url')}]")
    if not (changed or measures or found or first or rows or docs):
        print("  landenregister: geen wijzigingen gevonden")
        return None
    for a in changed:
        print(f"  WIJZIGING {a.get('country')} {a.get('region') or '(heel het land)'}: FOD {a.get('fod')} "
              f"({a.get('fod_reason')}), CDC {a.get('cdc')}  [{a.get('source')}]")
    for m in measures:
        print(f"  GRENS {m.get('country')}: {m.get('text')} ({m.get('date')})  [{m.get('source')}]")
    for x in found:
        print(f"  BRON {x['country']} ({x.get('kind')}): {x.get('name')}  {x['url']}")
    if first:
        print(f"  voor het eerst nagekeken: {', '.join(first)}")
    for u in docs:
        what = f"vervangt {u.get('replaces')}" if u.get("action") == "nieuwere_versie" else "nieuw"
        print(f"  DOCUMENT {u['outbreak']} ({fiche.LEVELS[u['level']]}, {what}): {u.get('title')} "
              f"({u.get('org')}, {u.get('date')})  [{u['url']}]")
    if proef:
        print("  proefrun: niets overgenomen")
        return False
    if apply_web or input("Dit lokaal overnemen (landenregister, cijfers, documenten)? [j/n]: ").strip().lower().startswith("j"):
        for c in countries.apply_web(webd, outbreak_id).values():
            countries.save_local(c)
        for oid in sorted({r["outbreak"] for r in rows}):
            p = data.append_local_table(tables[oid], [r for r in rows if r["outbreak"] == oid])
            print(f"  cijfers bewaard in {p}")
        for oid in sorted({u["outbreak"] for u in docs}):
            sp = by_id[oid]
            p = fiche.save_local_documents(sp, fiche.apply_updates(sp, [u for u in docs if u["outbreak"] == oid]))
            print(f"  documenten bewaard in {p}")
        print(f"  bewaard in {countries.LOCAL} (zet het ook in de repo als het blijvend is)")
        return True
    return False


def _soft_notes(d: dict, overall: str | None, specs=None, coverage: bool = True,
                questions: list[str] | None = None) -> list[str]:
    """Things worth one more try but never worth refusing a correct reply over."""
    specs = specs or []
    reply = d["reply"]
    limit = mail.MAX_WORDS + 50 * max(0, len(specs) - 1) if coverage else mail.MAX_WORDS
    return [n for n in (mail.verdict_note(reply, overall), mail.length_note(reply, limit),
                        mail.coverage_note(reply, specs) if coverage else None,
                        mail.questions_note(d.get("dossier"), questions or [])) if n]


# the dossier fields of the reply step, in the order the notes list them
DOSSIER_FIELDS = (("beoordeling", "Beoordeling"), ("weggelaten", "Uit de mail gelaten"),
                  ("na_te_kijken", "Na te kijken"), ("toezeggingen", "Toezegging in de mail"),
                  ("vragen_aan_behandelaar", "Vraag aan de behandelende arts"))


def dossier_notes(d: dict) -> list[str]:
    """The model's notes for Steven as lines: the dossier fields, then any free suggestions."""
    dos = d.get("dossier") or {}
    out = []
    for key, label in DOSSIER_FIELDS:
        items = dos.get(key) or []
        out += [f"{label}: {x}" for x in (items if isinstance(items, list) else [items]) if str(x).strip()]
    return out + [str(x) for x in d.get("suggestions") or []]


def write_reply(backend, inputs: dict, sources: list[str], overall: str | None = None,
                numbers: bool = True, specs=None, step: str = "reply", coverage: bool = True,
                questions: list[str] | None = None) -> dict:
    """Write the reply, check it against the facts it came from, and allow one repair round.

    `issues` keeps the dossier's copy button off (style, invented numbers); `notes` only warn (the
    rule verdict not coming back in the letter, a letter grown too long, a question of An left
    unanswered). Both drive the repair round.
    """
    d = llm.ask_json(backend, step, inputs, required=["reply"], specs=specs)
    issues = mail.check_reply(d["reply"], sources, numbers=numbers, specs=specs)
    notes = _soft_notes(d, overall, specs, coverage, questions)
    if issues or notes:   # one repair round with the concrete problems
        _say("Controle faalt (" + "; ".join(issues + notes) + "), herstelronde")
        inputs = {**inputs, "vorige_versie": d["reply"], "problemen": issues + notes}
        d = llm.ask_json(backend, step, inputs, required=["reply"], repair=True, specs=specs)
        issues = mail.check_reply(d["reply"], sources, numbers=numbers, specs=specs)
        notes = _soft_notes(d, overall, specs, coverage, questions)
    d["reply"] = d["reply"].replace("\r\n", "\n").strip() + "\n"
    d["issues"], d["notes"] = issues, notes
    return d


def _tables_for_web(specs) -> dict:
    """For every outbreak with a hand-kept table: its level, case definition, last date and last figures."""
    out = {}
    for sp in specs:
        if sp.adapter.get("type") != "table":
            continue
        path = data.table_path(sp)
        t = data.read_table(path) if path.exists() else None
        last = t[t["date"] == t["date"].max()] if t is not None and len(t) else None
        out[sp.id] = {"naam": sp.name, "niveau": sp.adapter["level"], "casusdefinitie": sp.adapter.get("case_def"),
                      "laatste_datum": str(t["date"].max().date()) if last is not None else None,
                      "laatste_cijfers": [] if last is None else
                      last.assign(date=last["date"].dt.strftime("%Y-%m-%d")).to_dict("records")}
    return out


def _version() -> str:
    try:
        return metadata.version("dienstreis-advies")
    except metadata.PackageNotFoundError:
        return "onbekend"


def _epi_view(epi: dict | None) -> dict | None:
    """The national figures for the mail step: the eight-week table is for the dossier, not the letter."""
    return {k: v for k, v in epi.items() if k != "weeks_last8"} if epi else epi


def _context_lines(trip: dict, summary: dict) -> list[str]:
    """The lines of context.md about the same places, zones or person, for the dossier."""
    if not CONTEXT.exists():
        return []
    keys = {str(x).lower() for s in summary.get("stops", []) for x in (s.get("place"), s.get("zone")) if x}
    if trip.get("traveller"):
        keys.add(str(trip["traveller"]).lower())
    keys.discard("")
    return [ln.strip().lstrip("- ").strip() for ln in CONTEXT.read_text(encoding="utf-8").splitlines()
            if ln.strip() and any(k in ln.lower() for k in keys)][-20:]


def _stop_view(s: dict) -> dict:
    return {k: s.get(k) for k in ("place", "start", "end", "nights", "zone", "province", "category", "verdict",
                                  "label", "cases", "deaths", "new14", "days_since_last", "neighbours_active",
                                  "nearest_active", "fod", "fod_reason", "cdc", "flags", "lodging", "transit_only")}


def _table_notes(summary: dict) -> list[str]:
    """A hand-kept table that is empty or old: the categories that rest on recent cases cannot be trusted."""
    parts = summary.get("outbreaks") or {summary.get("outbreak"): {"qa": summary["qa"]}}
    out = []
    for oid, o in parts.items():
        q = o["qa"]
        if q.get("table_empty"):
            out.append(f"De cijfertabel van {oid} is leeg: dit advies rust voor die uitbraak niet op cijfers. "
                       f"Vul de tabel, of aanvaard wat de webstap voorstelt.")
        elif q.get("table_stale"):
            out.append(f"De cijfertabel van {oid} is {q.get('table_days_old')} dagen oud (laatste datum "
                       f"{q.get('table_last_date')}): de categorieën A en B zijn daardoor niet betrouwbaar. "
                       f"Werk de tabel bij, of aanvaard wat de webstap voorstelt.")
    return out


def _unreachable(summary: dict) -> list[tuple[str, str]]:
    """Every source that could not be read, for every outbreak of the advice: (label, reason)."""
    parts = summary.get("outbreaks") or {summary.get("outbreak"): {"qa": summary["qa"]}}
    several = len(parts) > 1
    return [(k.upper() + (f" ({oid})" if several else ""), str((o["qa"].get(k) or {}).get("reason")))
            for oid, o in parts.items() for k in o["qa"].get("sources_unreachable", [])]


def run_advies(src: str, out: str | None = None, backend: str = "claude-code", model: str | None = None,
               yes: bool = False, web: bool = True, outlook: bool = False, asof: str | None = None,
               refresh: bool = False, open_browser: bool = True, llm_backend=None,
               apply_web: bool = False, numbers: bool = True, uitbraken: list[str] | None = None,
               health_ok: bool = False, proef: bool = False) -> dict:
    """The whole advice. `proef` is a dry run (F-018): every step runs, the model included, and the run's
    folder with its dossier is written, but nothing lasting: no archive, no log row, no context line,
    no Outlook draft, nothing taken over into the registry, the tables or the documents."""
    t0 = time.time()
    req = parse_request(src)
    _say(f"Aanvraag: {req.get('subject')}")
    tmp_out = Path(out or f"out_{_slug(Path(src).stem)}")
    tmp_out.mkdir(parents=True, exist_ok=True)
    be = llm_backend or llm.get_backend(backend, model, tmp_out)
    signals = health_signals(req)
    if signals:                                   # ask before anything about a person's health leaves
        _consent(signals, be.name, yes, health_ok)
    consented = bool(signals) or health_ok or be.name == "manual"

    _say(f"Reisschema uit de mail ({be.name})")
    req_in = {k: req.get(k) for k in ("subject", "sender", "body", "sent_to_ugent_address",
                                      "traveller_mentions_outbreak")}
    per_mail = req.get("mail_count") or 1          # a folder of mails keeps room for every mail
    req_in["body"] = (req_in["body"] or "")[:12000 * per_mail]
    req_in["attachments"] = [{"name": a["name"], "text": (a.get("text") or "")[:6000]} for a in req.get("attachments", [])]
    d = llm.ask_json(be, "stops", {"vandaag": date.today().isoformat(), "bekende_plaatsen": _known_places(),
                                   "aanvraag": req_in}, required=["traveller", "stops"])
    trip = _trip_from_llm(d, req)
    outp = Path(out or f"out_{_slug(trip.get('traveller', 'trip'))}")
    if outp != tmp_out:
        outp.mkdir(parents=True, exist_ok=True)
        for f in tmp_out.glob("*"):
            f.replace(outp / f.name)
        try:
            tmp_out.rmdir()
        except OSError:
            pass
        if hasattr(be, "workdir"):
            be.workdir = outp   # the backend must not keep working in the renamed folder
    # which outbreaks apply: named on the command line, or routed from the countries of the stops
    trip["outbreaks"] = list(uitbraken) if uitbraken else _routed(trip, d.get("diseases_mentioned"))
    today = date.fromisoformat(asof) if asof else None
    trip = confirm_trip(trip, d, outp, yes, fixed_outbreaks=bool(uitbraken), today=today)
    kind = trip.get("type") or "reisadvies"
    if kind != "reisadvies" and not consented:    # the model called it a case: ask before the next steps
        _consent([kind], be.name, yes, health_ok, already_sent=True)

    _say("Analyse (data, zones, kaart, curve)")
    summary = analyse(trip, outp, refresh=refresh, asof=asof)
    ids = outbreak_ids(summary)
    specs = [outbreak.load(i) for i in ids]
    unmatched = route.unmatched_diseases(d.get("diseases_mentioned") or [], specs)
    print(summary["table"])
    if summary.get("overrides"):
        print(f"Oordeel (regels): {summary['rule_overall']}")
        for o in summary["overrides"]:
            print(f"  OVERRULE {o['scope']}: {o['van']} -> {o['naar']} ({o['reason']})")
        print(f"Oordeel (na overrule): {summary['overall']}")
    else:
        print(f"Oordeel (regels): {summary['overall']}")
    qa = summary["qa"]
    bad = [k for k in ("zone_sum_matches_national",) if qa.get(k) is False]
    if qa.get("ecdc_matches") is False:
        bad.append("ecdc_matches")
    if qa.get("advisories_unverified"):
        print(f"  let op: reisadviezen voor {', '.join(qa['advisories_unverified'])} nog nooit nagekeken; "
              f"de webstap zoekt ze op en stelt ze voor")
    elif qa.get("advisories_stale"):
        print(f"  let op: reisadviezen {qa['advisories_verified_days_ago']} dagen oud; "
              f"de webstap werkt ze bij, of pas het landenregister aan")
    who = qa.get("who") or {}
    if who.get("ok"):
        print(f"  WHO: {who.get('item')} ({who.get('date')}, {who.get('days_old')} dagen oud)")
    unreachable = _unreachable(summary)
    for label, reason in unreachable:
        print(f"  let op: {label} niet bereikbaar ({reason}); die kruiscontrole ontbreekt in dit advies")
    concept = {x: route.inactive_for(x, trip) for x in unmatched}
    for x in unmatched:
        hint = (f" (er is een profiel in concept: --uitbraak {concept[x][0]})" if concept[x] else "")
        print(f"  let op: de aanvraag noemt {x}, maar daarvoor geldt geen actief uitbraakprofiel{hint}")
    table_notes = _table_notes(summary)
    for x in table_notes:
        print(f"  let op: {x}")
    if qa.get("map_label_overlaps") or qa.get("map_labels_clipped"):
        print(f"  let op: kaartlabels overlappen ({qa['map_label_overlaps']}) of vallen weg ({qa.get('map_labels_clipped')}); bekijk de kaart")
    if bad:
        print(f"  QA faalt: {bad}; het advies wordt gemaakt maar de notities vermelden dit")

    webd, web_accepted, web_failed = {}, None, None
    if web:
        _say("Reisadviezen (FOD, CDC), grensmaatregelen, WHO en nieuws op het web")
        provs = sorted({s["province"] for s in summary["stops"] if s.get("province")})
        trip_iso = list(dict.fromkeys(s["country"] for s in summary["stops"] if s.get("country")))
        home = list(dict.fromkeys(c for sp in specs for c in sp.countries))
        # countries on the trip that border an outbreak country: their border measures are checked every run
        border = [i for i in trip_iso if i not in home and set(countries.neighbours(i)) & set(home)]
        landen = {i: countries.for_prompt(countries.load(i) or countries.blank(i))
                  for i in dict.fromkeys(trip_iso + home)}
        who_in = (summary["qa"].get("who") if len(ids) == 1 else
                  {i: o.get("who") for i, o in summary["outbreaks"].items()})
        if kind == "reisadvies":
            web_in = {"vandaag": date.today().isoformat(),
                      "uitbraken": [{"id": sp.id, "naam": sp.name} for sp in specs], "provincies": provs,
                      "landen": landen, "buurlanden": border,
                      "internationaal": countries.international(),
                      "who_laatste_don": who_in, "reisschema": summary["table"]}
        else:                                     # a case or a question: guidance first, then the place
            web_in = {"vandaag": date.today().isoformat(), "type": kind, "casus": trip.get("situation"),
                      "vragen": d.get("questions_from_an") or [],
                      "uitbraken": [{"id": sp.id, "naam": sp.name} for sp in specs], "landen": landen,
                      "internationaal": countries.international(), "who_laatste_don": who_in}
        if unmatched:
            web_in["ziekten_zonder_profiel"] = unmatched
        tabellen = _tables_for_web(specs)
        if tabellen:
            web_in["tabellen"] = tabellen
        fiches = {sp.id: fiche.for_prompt(sp) for sp in specs if sp.id != outbreak.NONE}
        if fiches:
            web_in["fiches"] = fiches
        # a failed web step does not cost the confirmed itinerary and the analysis: the advice goes on
        # without it and says so, like a source that could not be reached
        try:
            webd = llm.ask_json(be, "web" if kind == "reisadvies" else "web_consult", web_in,
                                required=["advisories", "news", "who"] if kind == "reisadvies" else ["guidance", "news"],
                                web=True, specs=specs)
        except llm.LLMError as e:
            web_failed = str(e)
            print(f"  let op: de webstap faalde ({web_failed}); het advies gaat verder zonder")
        if webd:
            web_accepted = maybe_apply_web(webd, apply_web, ids[0], specs, proef=proef)
            (outp / "web.json").write_text(json.dumps(webd, ensure_ascii=False, indent=1, default=str),
                                           encoding="utf-8")

    _say("Mail schrijven")
    stops_view = [_stop_view(s) for s in summary["stops"]]
    feiten_txt = (outp / "feiten.txt").read_text(encoding="utf-8")
    # map and curve go along with a trip advice; a case or a question keeps them in the dossier
    attach = list(summary.get("attachments") or []) if kind == "reisadvies" else []
    inputs = {"vandaag": date.today().isoformat(),
              "feiten": feiten_txt, "bijlagen": [Path(a).name for a in attach],
              "risico_per_stop": stops_view, "regel_oordeel": summary["overall"], "epi": _epi_view(summary["epi"]),
              "qa": {k: v for k, v in qa.items() if k not in ("ecdc", "far_stops_in_inset")}, "ecdc": qa.get("ecdc"),
              "aanvraag": {k: d.get(k) for k in ("traveller", "note", "nationality", "profile", "work_nature", "transport",
                                                 "questions_from_an", "contradictions", "missing_info", "review_on")},
              "aanvraag_tekst": req_in["body"][:6000 * per_mail],
              "context": _context_text(), "geschiedenis": _history(trip),
              "eerdere_adviezen": archive.for_trip(trip, summary),
              "overrules": summary.get("overrides", []), "regel_oordeel_zonder_overrule": summary.get("rule_overall"),
              "web": webd or ("(niet beschikbaar)" if web_failed else "(niet gevraagd)")}
    if len(ids) > 1:            # the strictest outbreak is above; every other one in the same shape
        inputs["andere_uitbraken"] = [
            {"id": i, "naam": o["name"], "regel_oordeel": o["overall"], "epi": _epi_view(o["epi"]),
             "risico_per_stop": [_stop_view(s) for s in o["stops"]], "overrules": o["overrides"]}
            for i, o in summary["outbreaks"].items() if i != ids[0]]
    if unmatched:
        inputs["ziekten_zonder_profiel"] = unmatched
    confirmed = {sp.id: t for sp in specs if (t := fiche.confirmed_text(sp))}
    if confirmed:                                 # a concept fiche never reaches the letter
        inputs["fiche"] = confirmed
    if kind != "reisadvies":                      # a case letter: facts, not a trip verdict
        inputs = {"vandaag": inputs["vandaag"], "type": kind, "casus": trip.get("situation"),
                  **{k: v for k, v in inputs.items() if k not in ("vandaag", "regel_oordeel", "overrules",
                                                                   "regel_oordeel_zonder_overrule")}}
    # every number in the mail must come from one of these; see mail.unknown_numbers
    sources = [feiten_txt, json.dumps(summary, ensure_ascii=False, default=str),
               json.dumps(webd, ensure_ascii=False, default=str) if webd else "", req_in["body"] or "",
               *confirmed.values()]
    questions = d.get("questions_from_an") or []
    if kind == "reisadvies":
        r = write_reply(be, inputs, sources, overall=summary["overall"], numbers=numbers, specs=specs,
                        questions=questions)
    else:
        r = write_reply(be, inputs, sources, overall=None, numbers=numbers, specs=specs, step="consult",
                        coverage=False, questions=questions)
    r["reply"] = mail.with_redirect(r["reply"], bool(trip.get("sent_to_ugent_address")))

    (outp / "reply.txt").write_text(r["reply"], encoding="utf-8")
    warnings = [f"QA faalde: {bad}. Controleer de cijfers voor verzending."] if bad else []
    for x in unmatched:
        hint = (f" Er is een profiel in concept ({', '.join(concept[x])}): na bevestiging van de parameters "
                f"kan het mee, of nu al met --uitbraak." if concept[x] else " Kijk of er een profiel nodig is.")
        warnings.append(f"De aanvraag noemt {x}, maar daarvoor geldt geen actief uitbraakprofiel: de cijfers en "
                        f"regels van dit advies gaan daar niet over. Kijk wat de webstap vond.{hint}")
    warnings += table_notes
    warnings += [f"{label} was niet bereikbaar tijdens deze run; die kruiscontrole ontbreekt. "
                 f"Kijk de bron na voor verzending." for label, _ in unreachable]
    if web_failed:
        what = ("de FOD- en CDC-reisadviezen, grensmaatregelen, WHO, nieuws en nieuwere richtlijnen"
                if kind == "reisadvies" else "nieuwere richtlijnen, WHO en nieuws")
        warnings.append(f"De webstap faalde ({web_failed}): {what} zijn in dit advies niet live nagekeken. "
                        f"Kijk ze na voor verzending, of draai het advies opnieuw.")
    rebuild = f'dienstreis dossier "{outp}"'
    blocking = (["Controle faalt nog: " + "; ".join(r["issues"]) + f". Pas reply.txt aan en draai `{rebuild}`."]
                if r["issues"] else [])
    sugg = blocking + warnings + list(r["notes"]) + dossier_notes(r)
    (outp / "sugg.txt").write_text("\n".join(sugg) + "\n", encoding="utf-8")
    if r["issues"]:
        print(f"\nKopiëren staat uit in het dossier; {outp / 'reply.txt'} bevat nog: " + "; ".join(r["issues"]))
        print(f"Corrigeer de tekst en draai:\n  {rebuild}")

    # what the model was given and answered, for every step and retry of this run
    (outp / "llm_trace.json").write_text(
        json.dumps(llm.trace_of(be), ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    review = r.get("review_on") or trip.get("review_on")
    # read before this advice joins the archive and the log
    earlier, history = archive.for_trip(trip, summary, with_dir=True), _history(trip)
    context_line = (r.get("context_update") or "").strip()
    if proef:
        advice_dir = None
        print("\nProefrun: niets bewaard (geen archief, logregel, contextregel of Outlook-concept).")
    else:
        advice_dir = archive.save(trip, summary, r["reply"], request=req_in["body"] or "", suggestions=sugg,
                                  context_line=context_line)
        log_row(trip, summary, review_on=str(review or ""), advice_dir=str(advice_dir))
        print(f"Bewaard in {advice_dir}")

    # what the dossier needs that no other file of the run keeps; see dossier.py
    from . import dossier
    dos_data = {
        "created": datetime.now().isoformat(timespec="seconds"), "version": _version(), "type": kind,
        "aanvraag": {**{k: req.get(k) for k in ("subject", "sender", "mail_count")},
                     "attachments": [a["name"] for a in req.get("attachments", [])], "body": req.get("body") or "",
                     **{k: d.get(k) for k in ("questions_from_an", "missing_info", "contradictions", "nationality",
                                              "work_nature", "transport", "diseases_mentioned")}},
        "unmatched": unmatched, "model": r.get("dossier") or {}, "suggestions": list(r.get("suggestions") or []),
        "checks": {"issues": r["issues"], "notes": r["notes"]}, "warnings": warnings, "numbers": numbers,
        "review_on": str(review or ""), "attachments_sent": [Path(a).name for a in attach],
        "web_accepted": web_accepted, "web_failed": web_failed, "earlier": earlier, "history": history,
        "context_lines": _context_lines(trip, summary), "advice_dir": str(advice_dir or ""), "proef": proef}
    (outp / dossier.DATA).write_text(json.dumps(dos_data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    html_path = dossier.build(outp)
    if advice_dir:
        shutil.copy2(html_path, Path(advice_dir) / dossier.PAGE)
    if context_line and not proef:
        CONTEXT.parent.mkdir(parents=True, exist_ok=True)
        with open(CONTEXT, "a", encoding="utf-8") as f:
            f.write(("" if not CONTEXT.exists() or CONTEXT.read_text(encoding="utf-8").endswith("\n") else "\n")
                    + "- " + context_line + "\n")

    if outlook and not r["issues"] and not proef:
        from .outlook import draft
        try:
            draft(req, r["reply"], attach)
            print("Conceptmail staat open in Outlook (niet verzonden).")
        except Exception as e:
            print(f"Outlook-concept niet gelukt ({e}); kopieer de mail uit het dossier.")
    if open_browser:
        webbrowser.open(html_path.resolve().as_uri())

    _say(f"Klaar in {time.time() - t0:.0f} s")
    print(f"Dossier: {html_path}")
    for a in attach:
        print(f"Bijlage: {a}")
    print("Notities:")
    for s in sugg:
        print(f"  - {s}")
    return {"out": str(outp), "reply": r["reply"], "suggestions": sugg, "summary": summary, "trip": trip,
            "issues": r["issues"], "advice_dir": str(advice_dir) if advice_dir else None, "dossier": str(html_path)}
