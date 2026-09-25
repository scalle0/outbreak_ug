"""Risk classification per stop. Deterministic rules; the wording of the advice stays with Claude.

Categories (zone level, relative to the data date). The windows come from the outbreak profile
(`windows.active`, `windows.clear`); for Ebola they are 21 and 42 days:
  A  getroffen zone, geval binnen `active` dagen
  B  getroffen zone, laatste geval tussen `active` en `clear` dagen geleden
  C  getroffen zone, langer dan `clear` dagen zonder nieuw geval
  D  zone vrij, maar grenst aan een zone met een geval binnen `active` dagen
  E  zone vrij, provincie heeft een geval binnen `active` dagen
  F  niet getroffen, geen actieve zone in de provincie
  X  buiten het gebied van de cijfers -> grensmaatregelen van dat land uit het register
The verdict per category, and how it weighs in the verdict for the whole trip, are in the profile
too (`categories`, `overall`): they are clinical judgements, not code. FOD and CDC levels come
from the country registry (countries.py), per province where it has one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import countries, geo, outbreak, route

# the default profile's verdicts and labels, under the names the rest of the package and the tests use
VERDICT = {c: outbreak.default().verdict(c) for c in outbreak.CATEGORIES}
LABEL = {c: outbreak.default().label(c) for c in outbreak.CATEGORIES}


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
    spec: object = field(default=None, repr=False, compare=False)   # the outbreak this stop was assessed against

    @property
    def outbreak_spec(self) -> outbreak.OutbreakSpec:
        return self.spec or outbreak.default()

    @property
    def verdict(self) -> str:
        return self.outbreak_spec.verdict(self.category)

    @property
    def overridden(self) -> bool:
        return self.rule_category is not None and self.rule_category != self.category


def _norm_prov(p: str | None) -> str | None:
    return None if p is None else p.replace("é", "e").replace("É", "E")


def _country_flags(r: StopRisk) -> None:
    if r.fod == "formeel_afgeraden":
        r.flags.append(f"FOD raadt provincie formeel af ({r.fod_reason})" if r.province
                       else f"FOD raadt het land formeel af ({r.fod_reason})")
    if r.cdc and r.cdc >= 3:
        r.flags.append(f"CDC niveau {r.cdc}")


def assess_stop(stop: dict, zones, profile: dict, spec=None) -> StopRisk:
    spec = spec or outbreak.default()
    active, clear = spec.windows.get("active"), spec.windows.get("clear")     # none without figures
    fl = spec.flags
    loc = geo.locate(stop["place"], stop.get("lat"), stop.get("lon"))
    s, e = stop.get("from"), stop.get("to")
    nights = (e - s).days if isinstance(s, date) and isinstance(e, date) else None
    r = StopRisk(place=stop["place"], start=s, end=e, nights=nights, lodging=stop.get("lodging"),
                 transit_only=bool(stop.get("transit_only", False)), lat=loc["lat"], lon=loc["lon"],
                 country=loc["country"], spec=spec)
    z = geo.zone_of(zones, r.lat, r.lon, metric=spec.metric_epsg) if zones is not None else None
    if r.country is None:                          # a stop given by lat/lon: the map knows its country
        r.country = route.country_of(stop)
    if z is not None and r.country is None and len(spec.countries) == 1:
        r.country = spec.countries[0]              # inside the figures but on no land outline (a lake)
    land = countries.load(r.country)
    if z is None:
        r.category = "X"
        ms = countries.measures(land, spec.id)
        r.flags.append("; ".join(m["text"] for m in ms) if ms else spec.outside_note)
        if zones is not None:
            r.nearest_active = geo.nearest_active(zones, r.lat, r.lon, max_days=active, metric=spec.metric_epsg)
        r.fod, r.fod_reason = countries.fod(land)
        r.cdc = countries.cdc(land, spec.id)
        _country_flags(r)
        return r
    r.zone, r.province = z.Nom, _norm_prov(z.PROVINCE)
    r.cases, r.deaths, r.new14 = int(z.cases), int(z.deaths), int(z.new14)
    r.days_since_last = None if pd.isna(z.days_since_last) else float(z.days_since_last)
    prov = zones[zones.PROVINCE == z.PROVINCE]
    r.province_cases = int(prov.cases.sum())
    act = prov.days_since_last.notna() & (prov.days_since_last <= active)
    r.province_active_zones = int(act.sum())
    nb = geo.neighbours(zones, z.Nom)
    nba = nb[nb.days_since_last.notna() & (nb.days_since_last <= active)]
    r.neighbours_active = [{"zone": n.Nom, "province": _norm_prov(n.PROVINCE), "cases": int(n.cases),
                            "new14": int(n.new14), "days_since_last": int(n.days_since_last)}
                           for n in nba.sort_values("cases", ascending=False).itertuples()]
    r.nearest_active = geo.nearest_active(zones, r.lat, r.lon, max_days=active, metric=spec.metric_epsg)

    if r.cases > 0 and r.days_since_last is not None and r.days_since_last <= active:
        r.category = "A"
    elif r.cases > 0 and r.days_since_last is not None and r.days_since_last <= clear:
        r.category = "B"
    elif r.cases > 0:
        r.category = "C"
    elif r.neighbours_active:
        r.category = "D"
    elif r.province_active_zones > 0:
        r.category = "E"
    else:
        r.category = "F"

    r.fod, r.fod_reason = countries.fod(land, r.province)
    r.cdc = countries.cdc(land, spec.id, r.province)

    # flags: facts that Claude must weigh, never automatic verdict changes
    _country_flags(r)
    if r.category in "ABDE" and (r.lodging or profile.get("lodging")) == "family":
        r.flags.append(fl["family"])
    if r.category in "ABDE" and profile.get("healthcare_work"):
        r.flags.append("zorg- of labowerk")
    if r.category in "ABE" and not r.transit_only and (nights or 0) >= 1:
        r.flags.append(f"overnachting(en) in getroffen gebied: {nights}")
    if r.category in "DE" and (nights or 0) >= fl["long_stay_nights"]:
        r.flags.append(f"lang verblijf (>= {fl['long_stay_nights']} nachten) in risicogebied")
    rising = fl.get("rising_recent", fl.get("rising_new14"))
    if rising is not None and r.new14 >= rising:
        r.flags.append(f"stijgend in de zone: {r.new14} nieuwe gevallen in {spec.recent} dagen")
    return _apply_override(r, override_for(stop.get("override"), spec.id))


def override_for(o, outbreak_id: str) -> dict | None:
    """The overrule of a stop that applies to this outbreak.

    A stop carries one overrule, or a list of them, each naming its outbreak. An overrule without
    `outbreak` applies when it is the only one; trip.validate refuses it when several outbreaks apply.
    """
    items = [x for x in (o if isinstance(o, list) else [o]) if isinstance(x, dict)]
    mine = [x for x in items if x.get("outbreak") == outbreak_id]
    general = [x for x in items if not x.get("outbreak")]
    return (mine or general or [None])[0]


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
        r.flags.append(f"overrule: {r.outbreak_spec.label(r.rule_category)} ({r.rule_category}) naar {r.category}; "
                       f"{r.override_reason}")
    return r


def assess(trip: dict, ob=None, spec=None) -> list[StopRisk]:
    """Every stop against one outbreak: its figures `ob`, or none for a profile without figures."""
    spec = spec or getattr(ob, "spec", None) or outbreak.default()
    zones = ob.zones if ob is not None else None
    return [assess_stop(s, zones, trip.get("profile", {}), spec) for s in trip["stops"]]


def spec_of(rs: list[StopRisk]) -> outbreak.OutbreakSpec:
    return next((r.spec for r in rs if r.spec is not None), None) or outbreak.default()


def _verdict_for(cats: set[str], spec: outbreak.OutbreakSpec) -> str:
    """The strictest level among the categories decides; its text is in the profile."""
    levels = {spec.level(c) for c in cats}
    return spec.overall[next((lv for lv in outbreak.LEVELS if lv in levels), "geen_bezwaar")]


def rule_overall(rs: list[StopRisk]) -> str:
    """What the rules alone conclude, before any override."""
    return _verdict_for({r.rule_category or r.category for r in rs}, spec_of(rs))


def effective_overall(rs: list[StopRisk]) -> str:
    """The verdict over the categories as they stand, per-stop overrides included."""
    return _verdict_for({r.category for r in rs}, spec_of(rs))


def overall(rs: list[StopRisk], trip: dict | None = None) -> str:
    """The advice as it stands: the categories after any override, or the verdict the clinician wrote."""
    o = (trip or {}).get("override") or {}
    return str(o["verdict"]) if o.get("verdict") else effective_overall(rs)


def overrides(rs: list[StopRisk], trip: dict | None = None) -> list[dict]:
    """Every rule set aside in this advice, for the table, the archive and the mail prompt."""
    out = [{"scope": r.place, "van": r.outbreak_spec.label(r.rule_category),
            "naar": r.outbreak_spec.label(r.category),
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
                     "oordeel": r.verdict, "gevallen": r.cases, f"nieuw{r.outbreak_spec.recent}d": r.new14,
                     "dagen_sinds_laatste": None if r.days_since_last is None else int(r.days_since_last),
                     "actieve_buren": ", ".join(f"{n['zone']} ({n['cases']})" for n in r.neighbours_active[:4]) or "-",
                     "dichtstbij_actief": (f"{r.nearest_active['zone']} {r.nearest_active['km']} km"
                                           if r.nearest_active else "-"),
                     "FOD": r.fod or "-", "CDC": r.cdc or "-",
                     "regel_cat": r.rule_category or "-", "signalen": "; ".join(r.flags)})
    return pd.DataFrame(rows)
