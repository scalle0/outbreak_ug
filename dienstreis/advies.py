"""`dienstreis advies`: the whole workflow from a request mail to a checked reply, run on the user's PC.

    1 read the request (.msg/.eml/.txt)                          deterministic
    2 itinerary from the mail -> stops.yaml, user confirms       LLM (stops)
    3 data, risk per stop, map, epicurve, skeleton, QA           deterministic
    4 optional: advisories and news not yet in the data          LLM with web access (web)
    5 reply mail and notes for Steven                            LLM (reply)
    6 text checks (em-dash, banned words, placeholders), one repair round, widget,
      log, context line, browser, optional Outlook draft         deterministic
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import webbrowser
from datetime import date
from pathlib import Path

import yaml

from . import archive, llm, log, mail, risk
from . import trip as trip_mod
from .pipeline import _slug, analyse, log_row
from .msg import parse_request

CONTEXT = Path(os.environ.get("DIENSTREIS_CONTEXT", Path.home() / ".config" / "dienstreis" / "context.md"))


def edit_file(path: Path) -> None:
    """Open a file in the user's editor and wait (Notepad on Windows)."""
    ed = os.environ.get("EDITOR") or ("notepad" if sys.platform.startswith("win") else "nano")
    subprocess.run([ed, str(path)])


_known_places = trip_mod.known_places


def _say(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def _trip_from_llm(d: dict, req: dict) -> dict:
    keep = ("traveller", "note", "profile", "sent_to_ugent_address", "review_on", "stops")
    t = {k: d[k] for k in keep if k in d}
    # whether the thread used the ugent.be address is read from the mail itself, never from the model
    t["sent_to_ugent_address"] = bool(req.get("sent_to_ugent_address")) or bool(t.get("sent_to_ugent_address"))
    return trip_mod.coerce(t)


def _print_trip(trip: dict, d: dict, issues: list[str]) -> None:
    print(f"Reiziger: {trip.get('traveller')}  |  {trip.get('note', '')}  |  profiel: {trip.get('profile')}")
    for s in trip.get("stops") or []:
        extra = " (transit)" if s.get("transit_only") else ""
        extra += f" [{s['lodging']}]" if s.get("lodging") else ""
        extra += f" lat/lon {s['lat']}, {s['lon']}" if "lat" in s else ""
        print(f"  {s.get('from')} tot {s.get('to')}  {s.get('place')}{extra}")
    print(f"Go/no-go: {trip.get('review_on')}")
    for k, t in (("contradictions", "Tegenstrijdig"), ("missing_info", "Ontbreekt"), ("questions_from_an", "Vragen An")):
        for x in d.get(k, []):
            print(f"  {t}: {x}")
    for x in issues:
        print(f"  FOUT: {x}")


def _check_trip(trip: dict) -> list[str]:
    return trip_mod.validate(trip, known_places=_known_places())


def confirm_trip(trip: dict, d: dict, out: Path, yes: bool) -> dict:
    """Show the itinerary with its problems and let the user confirm, edit or stop.

    An itinerary with problems is never analysed: the places and dates are the input to every
    calculation that follows, so a wrong one produces a wrong risk table rather than an error.
    """
    path = out / "stops.yaml"
    path.write_text(yaml.safe_dump(trip, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = _check_trip(trip)
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
            edit_file(path)
            trip = trip_mod.coerce(yaml.safe_load(path.read_text(encoding="utf-8")))
            path.write_text(yaml.safe_dump(trip, allow_unicode=True, sort_keys=False), encoding="utf-8")
            issues = _check_trip(trip)
            _print_trip(trip, d, issues)
        elif a.startswith("s") or a.startswith("n"):
            raise SystemExit("Gestopt; stops.yaml blijft staan in " + str(out))


def _context_text() -> str:
    return CONTEXT.read_text(encoding="utf-8") if CONTEXT.exists() else "(geen contextbestand)"


def _history(trip: dict) -> list[dict]:
    seen, rows = set(), []
    for s in trip.get("stops", []):
        for r in log.history(s["place"]):
            key = tuple(r.values())
            if key not in seen:
                seen.add(key)
                rows.append(r)
    return rows[-15:]


def maybe_apply_web(webd: dict, apply_web: bool) -> None:
    """Show advisory changes found online; on confirmation write a newer local advisories table.

    Overwriting a travel advisory is a judgement, not a confirmation of something already shown:
    it changes the FOD and CDC flags of every later advice. So this asks even under --yes, unless
    --apply-web says otherwise.
    """
    changed = [a for a in webd.get("advisories", []) if a.get("changed")]
    for n in webd.get("news", []):
        print(f"  nieuws {n.get('date')}: {n.get('item')} ({n.get('url')})")
    if not changed:
        print("  reisadviezen: geen wijzigingen gevonden")
        return
    for a in changed:
        print(f"  WIJZIGING {a['province']}: FOD {a.get('fod')} ({a.get('fod_reason')}), CDC {a.get('cdc')}  [{a.get('source')}]")
    if apply_web or input("Deze wijzigingen lokaal overnemen in advisories.yaml? [j/n]: ").strip().lower().startswith("j"):
        adv = {k: v for k, v in risk.advisories().items() if k != "_source"}
        for a in changed:
            adv.setdefault("provinces", {})[a["province"]] = {"fod": a.get("fod"), "fod_reason": a.get("fod_reason"),
                                                              "cdc": a.get("cdc")}
        adv["verified"] = date.today()
        risk.LOCAL_ADVISORIES.parent.mkdir(parents=True, exist_ok=True)
        risk.LOCAL_ADVISORIES.write_text(yaml.safe_dump(adv, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"  bewaard in {risk.LOCAL_ADVISORIES} (zet het ook in de repo als het blijvend is)")


def write_reply(backend, inputs: dict, sources: list[str], overall: str | None = None,
                numbers: bool = True) -> dict:
    """Write the reply, check it against the facts it came from, and allow one repair round.

    `issues` blocks the widget (style, invented numbers); `notes` only warns (the rule verdict not
    coming back in the letter). Both drive the repair round.
    """
    d = llm.ask_json(backend, "reply", inputs, required=["reply", "suggestions"])
    issues = mail.check_reply(d["reply"], sources, numbers=numbers)
    note = mail.verdict_note(d["reply"], overall)
    if issues or note:   # one repair round with the concrete problems
        _say("Controle faalt (" + "; ".join(issues + ([note] if note else [])) + "), herstelronde")
        inputs = {**inputs, "vorige_versie": d["reply"], "problemen": issues + ([note] if note else [])}
        d = llm.ask_json(backend, "reply", inputs, required=["reply", "suggestions"])
        issues = mail.check_reply(d["reply"], sources, numbers=numbers)
        note = mail.verdict_note(d["reply"], overall)
    d["reply"] = d["reply"].replace("\r\n", "\n").strip() + "\n"
    d["issues"], d["notes"] = issues, [note] if note else []
    return d


def run_advies(src: str, out: str | None = None, backend: str = "claude-code", model: str | None = None,
               yes: bool = False, web: bool = True, outlook: bool = False, asof: str | None = None,
               refresh: bool = False, open_browser: bool = True, llm_backend=None,
               apply_web: bool = False, numbers: bool = True) -> dict:
    t0 = time.time()
    req = parse_request(src)
    _say(f"Aanvraag: {req.get('subject')}")
    tmp_out = Path(out or f"out_{_slug(Path(src).stem)}")
    tmp_out.mkdir(parents=True, exist_ok=True)
    be = llm_backend or llm.get_backend(backend, model, tmp_out)

    _say(f"Reisschema uit de mail ({be.name})")
    req_in = {k: req.get(k) for k in ("subject", "sender", "body", "sent_to_ugent_address",
                                      "traveller_mentions_outbreak")}
    req_in["body"] = (req_in["body"] or "")[:12000]
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
    trip = confirm_trip(trip, d, outp, yes)

    _say("Analyse (data, zones, kaart, curve)")
    summary = analyse(trip, outp, refresh=refresh, asof=asof)
    print(summary["table"])
    if summary.get("overrides"):
        print(f"Oordeel (regels): {summary['rule_overall']}")
        for o in summary["overrides"]:
            print(f"  OVERRULE {o['scope']}: {o['van']} -> {o['naar']} ({o['reason']})")
        print(f"Oordeel (na overrule): {summary['overall']}")
    else:
        print(f"Oordeel (regels): {summary['overall']}")
    qa = summary["qa"]
    bad = [k for k in ("zone_sum_matches_national",) if not qa[k]]
    if qa.get("ecdc_matches") is False:
        bad.append("ecdc_matches")
    if qa.get("advisories_stale"):
        print(f"  let op: reisadviezen {qa['advisories_verified_days_ago']} dagen oud; "
              f"de webstap werkt ze bij, of pas advisories.yaml aan")
    who = qa.get("who") or {}
    if who.get("ok"):
        print(f"  WHO: {who.get('item')} ({who.get('date')}, {who.get('days_old')} dagen oud)")
    for src in qa.get("sources_unreachable", []):
        print(f"  let op: {src.upper()} niet bereikbaar ({(qa.get(src) or {}).get('reason')}); "
              f"die kruiscontrole ontbreekt in dit advies")
    if qa.get("map_label_overlaps") or qa.get("map_labels_clipped"):
        print(f"  let op: kaartlabels overlappen ({qa['map_label_overlaps']}) of vallen weg ({qa.get('map_labels_clipped')}); bekijk de kaart")
    if bad:
        print(f"  QA faalt: {bad}; het advies wordt gemaakt maar de notities vermelden dit")

    webd = {}
    if web:
        _say("Reisadviezen (FOD, CDC), WHO en nieuws op het web")
        provs = sorted({s["province"] for s in summary["stops"] if s.get("province")})
        webd = llm.ask_json(be, "web", {"vandaag": date.today().isoformat(), "provincies": provs,
                                        "huidige_tabel": {k: v for k, v in risk.advisories().items() if k != "_source"},
                                        "who_laatste_don": summary["qa"].get("who"),
                                        "reisschema": summary["table"]},
                            required=["advisories", "news", "who"], web=True)
        maybe_apply_web(webd, apply_web)
        (outp / "web.json").write_text(json.dumps(webd, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    _say("Mail schrijven")
    stops_view = [{k: s.get(k) for k in ("place", "start", "end", "nights", "zone", "province", "category", "verdict",
                                         "label", "cases", "deaths", "new14", "days_since_last", "neighbours_active",
                                         "nearest_active", "fod", "fod_reason", "cdc", "flags", "lodging", "transit_only")}
                  for s in summary["stops"]]
    inputs = {"vandaag": date.today().isoformat(),
              "skelet": (outp / "reply_skeleton.txt").read_text(encoding="utf-8"),
              "risico_per_stop": stops_view, "regel_oordeel": summary["overall"], "epi": summary["epi"],
              "qa": {k: v for k, v in qa.items() if k not in ("ecdc", "far_stops_in_inset")}, "ecdc": qa.get("ecdc"),
              "aanvraag": {k: d.get(k) for k in ("traveller", "note", "nationality", "profile", "work_nature", "transport",
                                                 "questions_from_an", "contradictions", "missing_info", "review_on")},
              "aanvraag_tekst": req_in["body"][:6000],
              "context": _context_text(), "geschiedenis": _history(trip),
              "eerdere_adviezen": archive.for_trip(trip, summary),
              "overrules": summary.get("overrides", []), "regel_oordeel_zonder_overrule": summary.get("rule_overall"),
              "web": webd or "(niet gevraagd)"}
    # every number in the mail must come from one of these; see mail.unknown_numbers
    sources = [inputs["skelet"], json.dumps(summary, ensure_ascii=False, default=str),
               json.dumps(webd, ensure_ascii=False, default=str) if webd else "", req_in["body"] or ""]
    r = write_reply(be, inputs, sources, overall=summary["overall"], numbers=numbers)

    (outp / "reply.txt").write_text(r["reply"], encoding="utf-8")
    sugg = list(r.get("suggestions", []))
    for n in r["notes"]:
        sugg.insert(0, n)
    for src in qa.get("sources_unreachable", []):
        sugg.insert(0, f"{src.upper()} was niet bereikbaar tijdens deze run; die kruiscontrole "
                       f"ontbreekt. Kijk de bron na voor verzending.")
    if bad:
        sugg.insert(0, f"QA faalde: {bad}. Controleer de cijfers voor verzending.")
    if r["issues"]:
        sugg.insert(0, "Controle faalt nog: " + "; ".join(r["issues"]) + ". Pas reply.txt aan en draai `dienstreis widget`.")
    (outp / "sugg.txt").write_text("\n".join(sugg) + "\n", encoding="utf-8")

    # the widget is the copy-to-Outlook page: it is only built for a reply that passed every check
    html_path = outp / f"reply_{_slug(trip.get('traveller', 'trip'))}.html"
    if r["issues"]:
        html_path = None
        print(f"\nWidget niet gebouwd; {outp / 'reply.txt'} bevat nog: " + "; ".join(r["issues"]))
        print(f"Corrigeer de tekst en draai:\n  dienstreis widget {outp / 'reply.txt'} "
              f"--suggestions {outp / 'sugg.txt'} --out {outp / 'reply.html'}")
    else:
        html_path.write_text(mail.widget(r["reply"], sugg, "Reply Team Actueel"), encoding="utf-8")

    # what the model was given and answered, for every step and retry of this run
    (outp / "llm_trace.json").write_text(
        json.dumps(llm.trace_of(be), ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    review = r.get("review_on") or trip.get("review_on")
    advice_dir = archive.save(trip, summary, r["reply"], request=req_in["body"] or "", suggestions=sugg)
    log_row(trip, summary, review_on=str(review or ""), advice_dir=str(advice_dir))
    print(f"Bewaard in {advice_dir}")
    if r.get("context_update"):
        CONTEXT.parent.mkdir(parents=True, exist_ok=True)
        with open(CONTEXT, "a", encoding="utf-8") as f:
            f.write(("" if not CONTEXT.exists() or CONTEXT.read_text(encoding="utf-8").endswith("\n") else "\n")
                    + "- " + r["context_update"].strip() + "\n")

    if outlook and not r["issues"]:
        from .outlook import draft
        try:
            draft(req, r["reply"], [summary["map"], summary["epicurve"]])
            print("Conceptmail staat open in Outlook (niet verzonden).")
        except Exception as e:
            print(f"Outlook-concept niet gelukt ({e}); gebruik de widget.")
    if open_browser and html_path:
        webbrowser.open(html_path.resolve().as_uri())

    _say(f"Klaar in {time.time() - t0:.0f} s")
    print(f"Widget: {html_path or '(niet gebouwd)'}\nKaart: {summary['map']}\n"
          f"Curve: {summary['epicurve']}\nNotities:")
    for s in sugg:
        print(f"  - {s}")
    return {"out": str(outp), "reply": r["reply"], "suggestions": sugg, "summary": summary, "trip": trip,
            "issues": r["issues"], "advice_dir": str(advice_dir),
            "widget": str(html_path) if html_path else None}
