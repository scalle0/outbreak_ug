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

from . import llm, log, mail, risk
from .cli import _slug, analyse, log_row
from .msg import parse_request

CONTEXT = Path(os.environ.get("DIENSTREIS_CONTEXT", Path.home() / ".config" / "dienstreis" / "context.md"))
PLACES = Path(__file__).parent / "config" / "places.csv"


def edit_file(path: Path) -> None:
    """Open a file in the user's editor and wait (Notepad on Windows)."""
    ed = os.environ.get("EDITOR") or ("notepad" if sys.platform.startswith("win") else "nano")
    subprocess.run([ed, str(path)])


def _known_places() -> list[str]:
    return [l.split(",")[0] for l in PLACES.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]


def _say(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def _trip_from_llm(d: dict, req: dict) -> dict:
    keep = ("traveller", "note", "profile", "sent_to_ugent_address", "review_on", "stops")
    trip = {k: d[k] for k in keep if k in d}
    trip["sent_to_ugent_address"] = bool(req.get("sent_to_ugent_address")) or bool(trip.get("sent_to_ugent_address"))
    for s in trip.get("stops", []):
        for k in ("from", "to"):
            if isinstance(s.get(k), str):
                s[k] = date.fromisoformat(s[k])
    if isinstance(trip.get("review_on"), str) and trip["review_on"]:
        trip["review_on"] = date.fromisoformat(trip["review_on"])
    return trip


def _print_trip(trip: dict, d: dict) -> None:
    print(f"Reiziger: {trip.get('traveller')}  |  {trip.get('note', '')}  |  profiel: {trip.get('profile')}")
    for s in trip["stops"]:
        extra = " (transit)" if s.get("transit_only") else ""
        extra += f" [{s['lodging']}]" if s.get("lodging") else ""
        extra += f" lat/lon {s['lat']}, {s['lon']}" if "lat" in s else ""
        print(f"  {s['from']} tot {s['to']}  {s['place']}{extra}")
    print(f"Go/no-go: {trip.get('review_on')}")
    for k, t in (("contradictions", "Tegenstrijdig"), ("missing_info", "Ontbreekt"), ("questions_from_an", "Vragen An")):
        for x in d.get(k, []):
            print(f"  {t}: {x}")


def confirm_trip(trip: dict, d: dict, out: Path, yes: bool) -> dict:
    path = out / "stops.yaml"
    path.write_text(yaml.safe_dump(trip, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _print_trip(trip, d)
    if yes:
        return trip
    while True:
        a = input("\nKlopt dit reisschema? [j]a / [b]ewerken / [s]toppen: ").strip().lower() or "j"
        if a.startswith("j") or a.startswith("y"):
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        if a.startswith("b") or a.startswith("e"):
            edit_file(path)
            trip = yaml.safe_load(path.read_text(encoding="utf-8"))
            _print_trip(trip, d)
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


def maybe_apply_web(webd: dict, yes: bool) -> None:
    """Show advisory changes found online; on confirmation write a newer local advisories table."""
    changed = [a for a in webd.get("advisories", []) if a.get("changed")]
    for n in webd.get("news", []):
        print(f"  nieuws {n.get('date')}: {n.get('item')} ({n.get('url')})")
    if not changed:
        print("  reisadviezen: geen wijzigingen gevonden")
        return
    for a in changed:
        print(f"  WIJZIGING {a['province']}: FOD {a.get('fod')} ({a.get('fod_reason')}), CDC {a.get('cdc')}  [{a.get('source')}]")
    if yes or input("Deze wijzigingen lokaal overnemen in advisories.yaml? [j/n]: ").strip().lower().startswith("j"):
        adv = {k: v for k, v in risk.advisories().items() if k != "_source"}
        for a in changed:
            adv.setdefault("provinces", {})[a["province"]] = {"fod": a.get("fod"), "fod_reason": a.get("fod_reason"),
                                                              "cdc": a.get("cdc")}
        adv["verified"] = date.today()
        risk.LOCAL_ADVISORIES.parent.mkdir(parents=True, exist_ok=True)
        risk.LOCAL_ADVISORIES.write_text(yaml.safe_dump(adv, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"  bewaard in {risk.LOCAL_ADVISORIES} (zet het ook in de repo als het blijvend is)")


def write_reply(backend, inputs: dict) -> dict:
    d = llm.ask_json(backend, "reply", inputs, required=["reply", "suggestions"])
    issues = mail.check_text(d["reply"])
    if issues:   # one repair round with the concrete problems
        _say("Tekstcontrole faalt (" + "; ".join(issues) + "), herstelronde")
        inputs = {**inputs, "vorige_versie": d["reply"], "problemen": issues}
        d = llm.ask_json(backend, "reply", inputs, required=["reply", "suggestions"])
        issues = mail.check_text(d["reply"])
    d["reply"] = d["reply"].replace("\r\n", "\n").strip() + "\n"
    d["issues"] = issues
    return d


def run_advies(src: str, out: str | None = None, backend: str = "claude-code", model: str | None = None,
               yes: bool = False, web: bool = False, outlook: bool = False, asof: str | None = None,
               refresh: bool = False, open_browser: bool = True, llm_backend=None) -> dict:
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
    print(f"Oordeel (regels): {summary['overall']}")
    qa = summary["qa"]
    bad = [k for k in ("zone_sum_matches_national",) if not qa[k]]
    if qa.get("ecdc_matches") is False:
        bad.append("ecdc_matches")
    if qa.get("advisories_stale"):
        print(f"  let op: reisadviezen {qa['advisories_verified_days_ago']} dagen oud; gebruik --web of werk advisories.yaml bij")
    if qa.get("map_label_overlaps") or qa.get("map_labels_clipped"):
        print(f"  let op: kaartlabels overlappen ({qa['map_label_overlaps']}) of vallen weg ({qa.get('map_labels_clipped')}); bekijk de kaart")
    if bad:
        print(f"  QA faalt: {bad}; het advies wordt gemaakt maar de notities vermelden dit")

    webd = {}
    if web:
        _say("Reisadviezen en nieuws op het web")
        provs = sorted({s["province"] for s in summary["stops"] if s.get("province")})
        webd = llm.ask_json(be, "web", {"vandaag": date.today().isoformat(), "provincies": provs,
                                        "huidige_tabel": {k: v for k, v in risk.advisories().items() if k != "_source"},
                                        "reisschema": summary["table"]},
                            required=["advisories", "news"], web=True)
        maybe_apply_web(webd, yes)
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
              "context": _context_text(), "geschiedenis": _history(trip), "web": webd or "(niet gevraagd)"}
    r = write_reply(be, inputs)

    (outp / "reply.txt").write_text(r["reply"], encoding="utf-8")
    sugg = list(r.get("suggestions", []))
    if bad:
        sugg.insert(0, f"QA faalde: {bad}. Controleer de cijfers voor verzending.")
    if r["issues"]:
        sugg.insert(0, "Tekstcontrole faalt nog: " + "; ".join(r["issues"]) + ". Pas reply.txt aan en draai `dienstreis widget`.")
    (outp / "sugg.txt").write_text("\n".join(sugg) + "\n", encoding="utf-8")
    html_path = outp / f"reply_{_slug(trip.get('traveller', 'trip'))}.html"
    html_path.write_text(mail.widget(r["reply"], sugg, "Reply Team Actueel"), encoding="utf-8")

    review = r.get("review_on") or trip.get("review_on")
    log_row(trip, summary, review_on=str(review or ""))
    if r.get("context_update"):
        CONTEXT.parent.mkdir(parents=True, exist_ok=True)
        with open(CONTEXT, "a", encoding="utf-8") as f:
            f.write(("" if not CONTEXT.exists() or CONTEXT.read_text(encoding="utf-8").endswith("\n") else "\n")
                    + "- " + r["context_update"].strip() + "\n")

    if outlook:
        from .outlook import draft
        try:
            draft(req, r["reply"], [summary["map"], summary["epicurve"]])
            print("Conceptmail staat open in Outlook (niet verzonden).")
        except Exception as e:
            print(f"Outlook-concept niet gelukt ({e}); gebruik de widget.")
    if open_browser:
        webbrowser.open(html_path.resolve().as_uri())

    _say(f"Klaar in {time.time() - t0:.0f} s")
    print(f"Widget: {html_path}\nKaart: {summary['map']}\nCurve: {summary['epicurve']}\nNotities:")
    for s in sugg:
        print(f"  - {s}")
    return {"out": str(outp), "reply": r["reply"], "suggestions": sugg, "summary": summary, "trip": trip,
            "widget": str(html_path)}
