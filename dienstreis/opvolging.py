"""Follow-up after the advice (F-017): the go/no-go check and the watch on travellers in the field.

Two questions, answered on the current figures and without a model:

- go/no-go: an advice whose review date has come (`review_on` today or earlier) while the traveller has
  not left yet. Does every leg still get the category the letter was written on?
- the field: every traveller abroad now or leaving within HORIZON days, a case included. Has a zone of
  the itinerary changed since the advice: a stricter category, new cases, another FOD or CDC level,
  an outbreak that applies now and did not then?

Everything comes from the archive (the advice as it was: its itinerary, stops.yaml since F-017, and its
summary.json) and the current data. A leg is compared on its category by the rules then and now, so a
rule set aside by Steven stays set aside but a change under it still shows. The report is a page for
him, in the dossier's layout, with map and curve redrawn for a trip that became stricter or whose
go/no-go has come. Nothing goes to a model and no letter is written: he decides (decision 2026-09-26).

It runs by hand (`dienstreis opvolging`, or for one traveller when An asks) or on a schedule the user
sets himself (`dienstreis opvolging --plannen ...`, Windows Task Scheduler). A scheduled run is quiet:
the page opens only when something changed since the previous check.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from . import archive, outbreak

HORIZON = 30                     # days ahead: a trip leaving within this window is followed
ROOT = Path(os.environ.get("DIENSTREIS_OPVOLGING", Path.home() / ".config" / "dienstreis" / "opvolging"))
SEVERITY = "ABCDEFX"             # strictest first; X lies outside the outbreak's figures
TASK = "dienstreis opvolging"
SCHEDULES = {"weekdagen": ["/SC", "WEEKLY", "/D", "MON,TUE,WED,THU,FRI"], "dagelijks": ["/SC", "DAILY"],
             "wekelijks": ["/SC", "WEEKLY", "/D", "MON"]}
STATUS = {"strenger": ("stop", "strenger dan in het advies"), "milder": ("ok", "milder dan in het advies"),
          "nieuwe gevallen": ("cond", "nieuwe gevallen, zelfde categorie"), "ongewijzigd": ("", "ongewijzigd"),
          "onbekend": ("", "niet te beoordelen")}
ORDER = ("strenger", "nieuwe gevallen", "milder", "ongewijzigd", "onbekend")


def _day(x) -> date | None:
    if isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10]) if x else None
    except ValueError:
        return None


# ---------------------------------------------------------------- which advices
def _span(r: dict) -> tuple[date | None, date | None, bool]:
    """First departure, last day, and whether the stay is open-ended (a case without a return date)."""
    starts = [_day(s.get("start")) for s in r.get("stops") or []]
    ends = [_day(s.get("end")) for s in r.get("stops") or []]
    first = min((x for x in starts if x), default=None)
    return first, max((x for x in ends if x), default=None), any(e is None for e in ends)


def candidates(today: date, horizon: int = HORIZON, term: str = "", root: Path | None = None) -> list[dict]:
    """The advices to follow: not ended, and abroad now or leaving within `horizon` days; with a search
    term every advice that matches and has not ended. A general question has no traveller to follow.
    A newer advice for the same traveller replaces an older one."""
    out, seen = [], set()
    for r in archive.all_advices(root):                    # newest first
        if r.get("type") == "vraag" or not r.get("stops"):
            continue
        first, last, open_end = _span(r)
        if not open_end and last is not None and last < today:
            continue                                        # back home
        if term:
            if not archive._matches(r, term):
                continue
        elif first is not None and first > today + timedelta(days=horizon):
            continue                                        # too far ahead
        key = str(r.get("traveller") or r["dir"]).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def due(r: dict, today: date) -> bool:
    """The go/no-go has come: review date reached, not left yet, and not marked as done since."""
    review, (first, _, _) = _day(r.get("review_on")), _span(r)
    done = _day((r.get("go_no_go") or {}).get("op"))
    return bool(review and review <= today and (first is None or first >= today)
                and not (done and done >= review))


def mark_done(folder, note: str = "", today: date | None = None) -> dict:
    """Record in the archived advice that its go/no-go was decided, so it leaves the list. `folder` is the
    advice's folder, or only its name in the archive (2026-09-10_reiziger_t)."""
    f = Path(folder) / "advies.json"
    if not f.exists() and (archive.ARCHIVE / str(folder) / "advies.json").exists():
        f = archive.ARCHIVE / str(folder) / "advies.json"
    r = json.loads(f.read_text(encoding="utf-8"))
    r["go_no_go"] = {"op": (today or date.today()).isoformat(), "notitie": note}
    f.write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return r


# ---------------------------------------------------------------- the trip as it was
def rebuild(r: dict) -> tuple[dict, list[str]]:
    """The itinerary of an archived advice: stops.yaml as confirmed (since F-017), or rebuilt from its
    summary for an older advice, whose overrules then cannot be applied again."""
    from . import trip as trip_mod
    folder = Path(r["dir"])
    if (folder / "stops.yaml").exists():
        return trip_mod.coerce(yaml.safe_load((folder / "stops.yaml").read_text(encoding="utf-8"))), []
    s = _summary(r)
    stops = [{"place": x.get("place"), "from": x.get("start"), "to": x.get("end"),
              **({"lodging": x["lodging"]} if x.get("lodging") else {}),
              **({"transit_only": True} if x.get("transit_only") else {})} for x in s.get("stops") or r["stops"]]
    notes = (["advies van voor F-017: de overrules zijn niet opnieuw toegepast; vergelijk op de regels"]
             if r.get("overrides") else [])
    trip = {"traveller": r.get("traveller"), "type": r.get("type"), "review_on": r.get("review_on") or None,
            "profile": {}, "stops": stops}
    return trip_mod.coerce(trip), notes


def _summary(r: dict) -> dict:
    p = Path(r["dir"]) / "summary.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def then_stops(summary: dict, oid: str) -> list[dict] | None:
    """The legs of the advice for one outbreak, or None when the advice was not assessed against it."""
    if summary.get("outbreaks"):
        o = summary["outbreaks"].get(oid)
        return o.get("stops") if o else None
    return summary.get("stops") if summary.get("outbreak") == oid else None


# ---------------------------------------------------------------- then versus now
def _sev(cat: str | None) -> int | None:
    return SEVERITY.index(cat) if cat and cat in SEVERITY else None


def compare(then: list[dict] | None, now: list, spec) -> tuple[list[dict], str]:
    """Per leg the advice next to the situation now, and the change for the trip:
    strenger, milder, nieuwe gevallen or ongewijzigd. Compared on the category by the rules."""
    legs, status = [], set()
    for i, r in enumerate(now):
        t = then[i] if then and i < len(then) and then[i].get("place") == r.place else None
        t_rule = (t.get("rule_category") or t.get("category")) if t else None
        n_rule = r.rule_category or r.category
        change = ""
        if t is None:                                   # an outbreak that did not apply to the advice
            change = "nieuw" if spec.level(n_rule) != "geen_bezwaar" else ""
        elif _sev(n_rule) is not None and _sev(t_rule) is not None and _sev(n_rule) < _sev(t_rule):
            change = "strenger"
        elif _sev(n_rule) is not None and _sev(t_rule) is not None and _sev(n_rule) > _sev(t_rule):
            change = "milder"
        elif (r.cases or 0) > (t.get("cases") or 0):
            change = "nieuwe gevallen"
        fod_worse = t is not None and r.fod == "formeel_afgeraden" and t.get("fod") != "formeel_afgeraden"
        cdc_worse = t is not None and (r.cdc or 0) > (t.get("cdc") or 0)
        if fod_worse or cdc_worse:
            change = "strenger"
        status.add("strenger" if change in ("strenger", "nieuw") else change)
        legs.append({"place": r.place, "zone": r.zone, "province": r.province, "country": r.country,
                     "then": t_rule, "now": n_rule, "override": r.override_reason or (t or {}).get("override_reason"),
                     "now_level": spec.level(n_rule), "label_now": spec.label(n_rule),
                     "cases_then": (t or {}).get("cases"), "cases_now": r.cases, "new_now": r.new14,
                     "days_now": r.days_since_last, "fod_then": (t or {}).get("fod"), "fod_now": r.fod,
                     "cdc_then": (t or {}).get("cdc"), "cdc_now": r.cdc, "change": change})
    for s in ("strenger", "nieuwe gevallen", "milder"):
        if s in status:
            return legs, s
    return legs, "ongewijzigd"


def _load(spec, cache: dict, refresh: bool, asof: str | None):
    """The figures of one outbreak, once per check; (figures, note)."""
    from . import data
    if spec.id not in cache:
        try:
            cache[spec.id] = (data.load(refresh=refresh, asof=asof, spec=spec) if spec.has_data else None, None)
        except data.TableEmpty as e:
            cache[spec.id] = (None, f"geen cijfers voor {spec.name}: {e}")
    return cache[spec.id]


def check(r: dict, today: date, cache: dict, refresh: bool = False, asof: str | None = None) -> dict:
    """One archived advice against the figures of today."""
    from . import risk, route
    first, last, open_end = _span(r)
    res = {"dir": r["dir"], "traveller": r.get("traveller"), "type": r.get("type"), "advised_on": r.get("advised_on"),
           "overall_then": r.get("overall"), "review_on": r.get("review_on"), "first": str(first or ""),
           "last": "open" if open_end else str(last or ""), "places": r.get("places") or [],
           "due": due(r, today), "abroad": bool(first and first <= today), "notes": [], "parts": [],
           "status": "onbekend", "dossier": str(Path(r["dir"]) / "dossier.html")}
    try:
        trip, notes = rebuild(r)
    except (KeyError, ValueError, TypeError) as e:
        res["notes"].append(f"reisschema niet opnieuw te lezen: {e}")
        return res
    res["notes"] += notes
    summary = _summary(r)
    then_ids = list(r.get("outbreaks") or [])
    try:
        now_ids = [sp.id for sp in route.outbreaks_for({**trip, "outbreaks": None})]
    except (KeyError, ValueError) as e:
        res["notes"].append(f"routering niet gelukt: {e}")
        now_ids = []
    statuses = []
    for oid in dict.fromkeys(then_ids + now_ids):
        try:
            spec = outbreak.load(oid)
        except outbreak.ProfileError:
            res["notes"].append(f"profiel {oid} bestaat niet meer")
            continue
        ob, note = _load(spec, cache, refresh, asof)
        if note:
            res["notes"].append(note)
        try:
            rs = risk.assess(trip, ob, spec)
        except KeyError as e:                            # a place the registry no longer knows
            res["notes"].append(str(e).strip("'\""))
            continue
        legs, status = compare(then_stops(summary, oid), rs, spec)
        new = oid not in then_ids
        if new and oid != outbreak.NONE:
            res["notes"].append(f"{spec.name} geldt nu voor deze reis en gold niet bij het advies")
        part = {"id": oid, "name": spec.name, "new": new, "legs": legs, "status": status,
                "asof": str(ob.asof.date()) if ob is not None else None,
                "rule_now": risk.rule_overall(rs) if ob is not None or not spec.has_data else None}
        if spec.adapter.get("type") == "table" and ob is not None:
            last_date = ob.checks.get("table_last_date")
            if last_date and (today - date.fromisoformat(last_date)).days > spec.adapter["stale_days"]:
                res["notes"].append(f"de tabel van {spec.name} is ouder dan {spec.adapter['stale_days']} dagen "
                                    f"(laatste datum {last_date}): A en B zijn niet betrouwbaar")
        res["parts"].append(part)
        statuses.append(status)
    res["status"] = next((s for s in ORDER if s in statuses), "onbekend")
    res["trip"] = trip
    return res


# ---------------------------------------------------------------- one check of everything
def run(today: date | None = None, horizon: int = HORIZON, term: str = "", asof: str | None = None,
        refresh: bool = False, figures: bool = True, root: Path | None = None, archive_root: Path | None = None) -> dict:
    """Check every advice to follow; write the report page and its data. Returns the report."""
    from . import pipeline
    today = today or date.today()
    out = Path(root or ROOT) / today.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    results = [check(r, today, cache, refresh, asof) for r in candidates(today, horizon, term, archive_root)]
    for res in results:
        if figures and "trip" in res and (res["due"] or res["status"] == "strenger"):
            folder = out / archive._slug(res["traveller"] or Path(res["dir"]).name)
            try:                                       # map and curve on today's figures, for the decision
                specs = [outbreak.load(p["id"]) for p in res["parts"]]
                s = pipeline.analyse(res["trip"], folder, refresh=refresh, asof=asof, specs=specs or None)
                res["figures"] = [str(x) for x in s.get("attachments") or []]
            except Exception as e:                     # the facts stand without the figures
                res["notes"].append(f"kaart en curve niet getekend: {e}")
    report = {"checked_on": today.isoformat(), "created": datetime.now().isoformat(timespec="seconds"),
              "horizon": horizon, "term": term, "results": [{k: v for k, v in x.items() if k != "trip"} for x in results]}
    (out / "opvolging.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    page = out / "opvolging.html"
    page.write_text(render(report), encoding="utf-8")
    report["page"] = str(page)
    return report


def signature(report: dict) -> list:
    """What a quiet run compares with the previous one: per advice its status and the categories now."""
    return sorted([x["dir"], x["status"], x["due"], [[leg["now"] for leg in p["legs"]] for p in x["parts"]]]
                  for x in report["results"])


def news_since_last(report: dict, root: Path | None = None) -> bool:
    """Whether this check differs from the previous one in something worth opening the page for."""
    state = Path(root or ROOT) / "laatste.json"
    sig = signature(report)
    try:
        before = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        before = None
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(sig, ensure_ascii=False, default=str), encoding="utf-8")
    worth = any(x["due"] or x["status"] in ("strenger", "nieuwe gevallen", "milder") for x in report["results"])
    return worth and sig != before


# ---------------------------------------------------------------- a schedule the user sets
def plan_commands(schedule: str, hour: str = "08:00", exe: str | None = None) -> list[list[str]]:
    """The schtasks command(s) for a schedule: weekdagen, dagelijks, wekelijks, or uit to remove it."""
    if schedule == "uit":
        return [["schtasks", "/Delete", "/F", "/TN", TASK]]
    if schedule not in SCHEDULES:
        raise ValueError(f"onbekende planning '{schedule}' (kies uit {', '.join(SCHEDULES)} of uit)")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hour):
        raise ValueError(f"uur '{hour}': schrijf UU:MM, bv. 08:00")
    exe = exe or _command()
    return [["schtasks", "/Create", "/F", "/TN", TASK, "/TR", f"{exe} opvolging --stil", *SCHEDULES[schedule],
             "/ST", hour]]


def _command() -> str:
    """How the Task Scheduler starts this program: the dienstreis.exe next to this Python, or python -m."""
    exe = Path(sys.executable).with_name("dienstreis.exe")
    if exe.exists():
        return f'"{exe}"'
    found = shutil.which("dienstreis")
    return f'"{found}"' if found else f'"{sys.executable}" -m dienstreis.cli'


# ---------------------------------------------------------------- the page
def render(report: dict) -> str:
    """The report in the dossier's layout: go/no-go first, then what changed, then the rest."""
    from . import dossier as d
    res = report["results"]
    due_now = [x for x in res if x["due"]]
    changed = sorted([x for x in res if not x["due"] and x["status"] in ("strenger", "nieuwe gevallen", "milder")],
                     key=lambda x: ORDER.index(x["status"]))
    same = [x for x in res if not x["due"] and x["status"] == "ongewijzigd"]
    unknown = [x for x in res if not x["due"] and x["status"] == "onbekend"]

    def count(*statuses) -> int:                 # over every advice followed, the go/no-go ones included
        return len([x for x in res if x["status"] in statuses])
    head = (f'<div class="eyebrow">Opvolging · {d._e(d._date(report["checked_on"]))} · intern, niet voor An</div>'
            f"<h1>Go/no-go en reizigers ter plaatse</h1>"
            f'<p class="muted" style="margin:0">{len(res)} advies(en) gevolgd: ter plaatse, of vertrek binnen '
            f'{report["horizon"]} dagen{(" · zoekterm " + d._e(report["term"])) if report.get("term") else ""}. '
            f"Enkel feiten: het advies van toen naast de toestand nu, op de regels.</p>"
            f'<div class="badges">'
            + "".join(f'<span class="badge {cls if n else ""}">{n} {d._e(txt)}</span>' for n, (cls, txt) in (
                (len(due_now), ("stop", "go/no-go")), (count("strenger"), STATUS["strenger"]),
                (count("nieuwe gevallen", "milder"), ("cond", "andere wijziging")),
                (count("ongewijzigd"), ("", "ongewijzigd")))) + "</div>")
    blocks = [f'<div class="panel">{head}</div>']
    for key, title, items in (("gonogo", "Go/no-go: de beslissing valt nu", due_now),
                              ("veranderd", "Veranderd sinds het advies", changed),
                              ("onbekend", "Niet te beoordelen", unknown)):
        if items:
            blocks.append(f'<section id="{key}"><div class="panel"><h2>{d._e(title)}</h2>'
                          + "".join(_card(x) for x in items) + "</div></section>")
    if same:
        blocks.append('<section id="ongewijzigd"><div class="panel"><h2>Ongewijzigd</h2>' + d._table(
            ["Reiziger", "Plaatsen", "Van", "Tot", "Advies", "Oordeel toen", "Cijfers tot"],
            [[x["traveller"], ", ".join(map(str, x["places"])), d._date(x["first"]),
              x["last"] if x["last"] == "open" else d._date(x["last"]), d._date(x["advised_on"]), x["overall_then"],
              ", ".join(d._date(p["asof"]) for p in x["parts"] if p.get("asof"))] for x in same]) + "</div></section>")
    if not res:
        blocks.append('<section><div class="panel"><p class="muted">Geen reizigers ter plaatse en geen vertrek '
                      f'binnen {report["horizon"]} dagen in het archief.</p></div></section>')
    return ("<!DOCTYPE html>\n<html lang=\"nl\"><head><meta charset=\"UTF-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
            f"<title>Opvolging {d._e(report['checked_on'])}</title><style>{d.CSS}</style></head><body>"
            f'<header class="topbar"><div class="brand">{d.MARK}<span>dienstreis</span><span class="tag">opvolging</span></div>'
            '<span class="wordmark">Sc<span class="ai">AI</span><span class="dev">dev</span></span></header>'
            f"<main>{''.join(blocks)}</main></body></html>\n")


def _card(x: dict) -> str:
    from . import dossier as d
    cls, txt = STATUS[x["status"]]
    page = Path(x["dossier"])
    link = d._link(page.resolve().as_uri(), "dossier van het advies") if page.exists() else d._e(x["dir"])
    places = ", ".join(dict.fromkeys(map(str, x["places"])))
    meta = [("Advies", d._date(x["advised_on"])), ("Vertrek", d._date(x["first"])),
            ("Tot", x["last"] if x["last"] == "open" else d._date(x["last"])),
            ("Go/no-go", d._date(x["review_on"]) if x.get("review_on") else "")]
    out = (f'<div class="part"><h3>{d._e(x["traveller"])} · {d._e(places)}</h3>'
           f'<div class="badges"><span class="badge {cls}">{d._e(txt)}</span>'
           + ('<span class="badge stop">go/no-go</span>' if x["due"] else "")
           + ('<span class="badge">ter plaatse</span>' if x["abroad"] else "")
           + f'<span class="badge">{d._e(x["type"] or "reisadvies")}</span></div>'
           + '<div class="meta">' + "".join(f"<span>{d._e(k)} <b>{d._e(v)}</b></span>" for k, v in meta if v)
           + f"<span>{link}</span></div>"
           + f'<p>Oordeel in het advies: {d._e(x["overall_then"])}</p>')
    for p in x["parts"]:
        rows = []
        for leg in p["legs"]:
            arrow = f"{leg['then'] or '-'} → {leg['now']}" if leg["then"] != leg["now"] else leg["now"]
            rows.append([leg["place"], leg["zone"] or leg["country"] or "",
                         ("html", f"<b>{d._e(arrow)}</b>" if leg["change"] in ("strenger", "nieuw") else d._e(arrow)),
                         leg["label_now"], f"{d._n(leg['cases_then'])} → {d._n(leg['cases_now'])}"
                         if leg["cases_then"] is not None else d._n(leg["cases_now"]),
                         d._n(leg["new_now"]), "" if leg["days_now"] is None else f"{leg['days_now']:.0f}",
                         _pair(leg["fod_then"], leg["fod_now"]), _pair(leg["cdc_then"], leg["cdc_now"]),
                         leg["change"] + (f" (overrule: {leg['override']})" if leg.get("override") else "")])
        spec_recent = _recent(p["id"])
        out += (f"<h4>{d._e(p['name'])}" + (" · nieuw van toepassing" if p["new"] else "")
                + (f" · cijfers tot {d._e(d._date(p['asof']))}" if p.get("asof") else "") + "</h4>"
                + (f'<p class="muted">Volgens de regels nu: {d._e(p["rule_now"])}</p>' if p.get("rule_now") else "")
                + d._table(["Halte", "Zone", "Categorie", "Betekenis nu", "Gevallen", f"Nieuw ({spec_recent} d)",
                            "Dagen sinds laatste", "FOD", "CDC", "Wijziging"], rows, {4, 5, 6}))
    out += "".join(d._alert(n, "soft") for n in x["notes"])
    figs = [d._figure(d._img(Path(f).parent, f), Path(f).name) for f in x.get("figures") or []]
    if any(figs):
        out += f'<div class="figs">{"".join(figs)}</div>'
    if x["due"]:
        out += (f'<p class="muted">Beslist? Noteer het: <code>dienstreis opvolging --klaar {d._e(Path(x["dir"]).name)} '
                f'--notitie "..."</code>. Een nieuw advies maak je met <code>dienstreis advies</code>.</p>')
    return out + "</div>"


def _pair(then, now) -> str:
    if then == now or then is None:
        return "" if now is None else str(now)
    return f"{then} → {now if now is not None else '-'}"


def _recent(oid: str) -> int:
    try:
        return outbreak.load(oid).recent
    except outbreak.ProfileError:
        return 14
