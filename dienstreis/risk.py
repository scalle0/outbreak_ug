"""Risk classification per stop. Deterministic rules; the wording of the advice stays with Claude.

Categories (health zone level, relative to the data date):
  A  getroffen zone, geval in laatste 21 dagen          -> afraden
  B  getroffen zone, laatste geval 22-42 dagen geleden   -> voorwaardelijk (go/no-go vlak voor vertrek)
  C  getroffen zone, > 42 dagen zonder nieuw geval       -> voorwaardelijk, lichte voorwaarden
  D  zone vrij, maar grenst aan zone met geval <= 21 d   -> voorwaardelijk, herevaluatie dichter bij vertrek
  E  zone vrij, provincie heeft geval <= 21 d            -> voorwaardelijk
  F  niet getroffen, geen actieve zone in provincie      -> geen bezwaar
  X  buiten de DRC                                       -> land-notitie uit advisories.yaml
"""
from __future__ import annotations

import os

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from . import geo

CONFIG = Path(__file__).parent / "config"
VERDICT = {"A": "afraden", "B": "voorwaardelijk", "C": "voorwaardelijk", "D": "voorwaardelijk",
           "E": "voorwaardelijk", "F": "geen bezwaar", "X": "zie landnotitie"}
LABEL = {"A": "getroffen zone, recent geval (<= 21 d)", "B": "getroffen zone, laatste geval 22-42 d",
         "C": "getroffen zone, > 42 d zonder geval", "D": "vrije zone, grenst aan actieve zone",
         "E": "vrije zone in provincie met actieve transmissie", "F": "niet getroffen",
         "X": "buiten de DRC"}


LOCAL_ADVISORIES = Path(os.environ.get("DIENSTREIS_ADVISORIES",
                                     Path.home() / ".config" / "dienstreis" / "advisories.yaml"))


def advisories() -> dict:
    """Package table, or the local copy when that one was verified more recently (see `dienstreis advies --web`)."""
    pkg = yaml.safe_load(open(CONFIG / "advisories.yaml", encoding="utf-8"))
    pkg["_source"] = "package"
    if LOCAL_ADVISORIES.exists():
        loc = yaml.safe_load(open(LOCAL_ADVISORIES, encoding="utf-8"))
        if loc and str(loc.get("verified", "")) > str(pkg.get("verified", "")):
            loc["_source"] = str(LOCAL_ADVISORIES)
            return loc
    return pkg


@dataclass
class StopRisk:
    place: str
    start: date | None
    end: date | None
    nights: int | None
    lodging: str | None
    transit_only: bool
    lat: float
    lon: float
    country: str | None
    zone: str | None = None
    province: str | None = None
    cases: int = 0
    deaths: int = 0
    new14: int = 0
    days_since_last: float | None = None
    province_cases: int = 0
    province_active_zones: int = 0
    neighbours_active: list = field(default_factory=list)
    nearest_active: dict | None = None
    category: str = "F"
    rule_category: str | None = None      # what the rules said, when a clinician overrode it
    override_reason: str | None = None
    fod: str | None = None
    fod_reason: str | None = None
    cdc: int | None = None
    flags: list = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return VERDICT[self.category]

    @property
    def overridden(self) -> bool:
        return self.rule_category is not None and self.rule_category != self.category


def _norm_prov(p: str | None) -> str | None:
    return None if p is None else p.replace("é", "e").replace("É", "E")


def assess_stop(stop: dict, zones, adv: dict, profile: dict) -> StopRisk:
    loc = geo.locate(stop["place"], stop.get("lat"), stop.get("lon"))
    s, e = stop.get("from"), stop.get("to")
    nights = (e - s).days if isinstance(s, date) and isinstance(e, date) else None
    r = StopRisk(place=stop["place"], start=s, end=e, nights=nights, lodging=stop.get("lodging"),
                 transit_only=bool(stop.get("transit_only", False)), lat=loc["lat"], lon=loc["lon"],
                 country=loc["country"])
    z = geo.zone_of(zones, r.lat, r.lon)
    if z is None:
        r.category = "X"
        r.flags.append(adv.get("countries", {}).get(r.country or "", {}).get("note", "buiten DRC"))
        r.nearest_active = geo.nearest_active(zones, r.lat, r.lon)
        return r
    r.zone, r.province = z.Nom, _norm_prov(z.PROVINCE)
    r.cases, r.deaths, r.new14 = int(z.cases), int(z.deaths), int(z.new14)
    r.days_since_last = None if pd.isna(z.days_since_last) else float(z.days_since_last)
    prov = zones[zones.PROVINCE == z.PROVINCE]
    r.province_cases = int(prov.cases.sum())
    act = prov.days_since_last.notna() & (prov.days_since_last <= 21)
    r.province_active_zones = int(act.sum())
    nb = geo.neighbours(zones, z.Nom)
    nba = nb[nb.days_since_last.notna() & (nb.days_since_last <= 21)]
    r.neighbours_active = [{"zone": n.Nom, "province": _norm_prov(n.PROVINCE), "cases": int(n.cases),
                            "new14": int(n.new14), "days_since_last": int(n.days_since_last)}
                           for n in nba.sort_values("cases", ascending=False).itertuples()]
    r.nearest_active = geo.nearest_active(zones, r.lat, r.lon)

    if r.cases > 0 and r.days_since_last is not None and r.days_since_last <= 21:
        r.category = "A"
    elif r.cases > 0 and r.days_since_last is not None and r.days_since_last <= 42:
        r.category = "B"
    elif r.cases > 0:
        r.category = "C"
    elif r.neighbours_active:
        r.category = "D"
    elif r.province_active_zones > 0:
        r.category = "E"
    else:
        r.category = "F"

    pa = adv["provinces"].get(r.province, adv["default"])
    r.fod, r.fod_reason, r.cdc = pa["fod"], pa.get("fod_reason"), pa["cdc"]

    # flags: facts that Claude must weigh, never automatic verdict changes
    if r.fod == "formeel_afgeraden":
        r.flags.append(f"FOD raadt provincie formeel af ({r.fod_reason})")
    if r.cdc and r.cdc >= 3:
        r.flags.append(f"CDC niveau {r.cdc}")
    if r.category in "ABDE" and (r.lodging or profile.get("lodging")) == "family":
        r.flags.append("verblijf bij familie: blootstelling via zorg voor zieken en begrafenissen")
    if r.category in "ABDE" and profile.get("healthcare_work"):
        r.flags.append("zorg- of labowerk")
    if r.category in "ABE" and not r.transit_only and (nights or 0) >= 1:
        r.flags.append(f"overnachting(en) in getroffen gebied: {nights}")
    if r.category in "DE" and (nights or 0) >= 14:
        r.flags.append("lang verblijf (>= 14 nachten) in risicogebied")
    if r.new14 >= 5:
        r.flags.append(f"stijgend in de zone: {r.new14} nieuwe gevallen in 14 dagen")
    return _apply_override(r, stop.get("override"))


def _apply_override(r: StopRisk, o: dict | None) -> StopRisk:
    """Let the clinician set the category aside, on the record.

    The rules classify a health zone; they do not know the dossier. What the rules said is kept in
    `rule_category` and the reason travels with it, so the table, the archive and the mail all show
    that a judgement was made rather than a category silently changing.
    """
    if not o or not o.get("category"):
        return r
    r.rule_category = r.category
    r.category = o["category"]
    r.override_reason = o.get("reason")
    if r.overridden:
        r.flags.append(f"overrule: {LABEL[r.rule_category]} ({r.rule_category}) naar {r.category}; "
                       f"{r.override_reason}")
    return r


def assess(trip: dict, ob) -> list[StopRisk]:
    adv = advisories()
    return [assess_stop(s, ob.zones, adv, trip.get("profile", {})) for s in trip["stops"]]


def _verdict_for(cats: set[str]) -> str:
    if "A" in cats:
        return "niet goedkeuren in huidige vorm (minstens een luik af te raden)"
    if cats & set("BDE"):
        return "voorwaardelijk, met go/no-go dichter bij vertrek"
    return "geen ebola-gerelateerd bezwaar"


def rule_overall(rs: list[StopRisk]) -> str:
    """What the rules alone conclude, before any override."""
    return _verdict_for({r.rule_category or r.category for r in rs})


def effective_overall(rs: list[StopRisk]) -> str:
    """The verdict over the categories as they stand, per-stop overrides included."""
    return _verdict_for({r.category for r in rs})


def overall(rs: list[StopRisk], trip: dict | None = None) -> str:
    """The advice as it stands: the categories after any override, or the verdict the clinician wrote."""
    o = (trip or {}).get("override") or {}
    return str(o["verdict"]) if o.get("verdict") else effective_overall(rs)


def overrides(rs: list[StopRisk], trip: dict | None = None) -> list[dict]:
    """Every rule set aside in this advice, for the table, the archive and the mail prompt."""
    out = [{"scope": r.place, "van": LABEL[r.rule_category], "naar": LABEL[r.category],
            "category": r.category, "rule_category": r.rule_category, "reason": r.override_reason}
           for r in rs if r.overridden]
    o = (trip or {}).get("override") or {}
    if o.get("verdict"):
        out.append({"scope": "eindoordeel", "van": effective_overall(rs), "naar": o["verdict"],
                    "reason": o.get("reason")})
    return out


def table(rs: list[StopRisk]) -> pd.DataFrame:
    rows = []
    for r in rs:
        rows.append({"stop": r.place, "van": r.start, "tot": r.end, "nachten": r.nights,
                     "zone": r.zone or "-", "provincie": r.province or r.country, "cat": r.category,
                     "oordeel": r.verdict, "gevallen": r.cases, "nieuw14d": r.new14,
                     "dagen_sinds_laatste": None if r.days_since_last is None else int(r.days_since_last),
                     "actieve_buren": ", ".join(f"{n['zone']} ({n['cases']})" for n in r.neighbours_active[:4]) or "-",
                     "dichtstbij_actief": (f"{r.nearest_active['zone']} {r.nearest_active['km']} km"
                                           if r.nearest_active else "-"),
                     "FOD": r.fod or "-", "CDC": r.cdc or "-",
                     "regel_cat": r.rule_category or "-", "signalen": "; ".join(r.flags)})
    return pd.DataFrame(rows)
