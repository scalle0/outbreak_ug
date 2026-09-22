"""Checks on the itinerary before it reaches the deterministic core.

The model writes the itinerary; everything after it is arithmetic on those dates and places. Two
mistakes would otherwise surface as a traceback halfway through the run, after the user has already
confirmed the schedule:

  dates   a non-ISO date ends up as a str. `date.fromisoformat` raises on "28/11/2026", and a date
          that stays a str makes `isinstance(s, date)` false in risk.assess_stop, so `nights` becomes
          None and the "overnachting(en) in getroffen gebied" flag never fires: a missing risk flag
          with no error anywhere.
  places  geo.locate raises KeyError for a place that is not in places.csv and has no lat/lon.

`coerce` repairs what can be repaired, `validate` reports the rest in Dutch, all issues at once, so
the user sees them next to the itinerary and can fix them with the editor that confirm_trip offers.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

PLACES = Path(__file__).parent / "config" / "places.csv"
LODGING = {"hotel", "family", "guesthouse", "camp", "compound", "unknown"}
# the DRC and its neighbours, wide enough for a stopover in Europe or southern Africa
LAT_RANGE, LON_RANGE = (-35.0, 60.0), (-25.0, 60.0)
MAX_SPAN_DAYS = 400
DATE_KEYS = ("from", "to")


def known_places() -> list[str]:
    """Place names from config/places.csv, without the comment lines and the header row.

    Same list that goes into the prompt as `bekende_plaatsen` and that validate() checks against,
    so the model is asked for exactly what the analysis can resolve. Read here rather than through
    geo.places() so that validating an itinerary does not pull in geopandas.
    """
    rows = [l.split(",")[0].strip() for l in PLACES.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]
    return [r for r in rows[1:] if r]


def parse_date(v, *, today: date | None = None):
    """date/datetime/ISO/Belgian dd-mm-yyyy -> date. Returns None if it cannot be read.

    Day first, never month first: the requests are Belgian, so 03/04/2026 is 3 April. A two-digit
    year is read as 20xx (the forms write "3/1/27").
    """
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip()
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})", s)
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    y += 2000 if y < 100 else 0
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _as_bool(v):
    return v if isinstance(v, bool) else str(v).strip().lower() in ("true", "ja", "yes", "1")


def coerce(trip: dict) -> dict:
    """Types the deterministic core expects. Unreadable values are left alone for validate to report."""
    t = dict(trip)
    if t.get("review_on") is not None:
        t["review_on"] = parse_date(t["review_on"]) or t["review_on"]
    prof = dict(t.get("profile") or {})
    if "healthcare_work" in prof:
        prof["healthcare_work"] = _as_bool(prof["healthcare_work"])
    t["profile"] = prof
    stops = []
    for s in t.get("stops") or []:
        s = dict(s)
        for k in DATE_KEYS:
            if s.get(k) is not None:
                s[k] = parse_date(s[k]) or s[k]
        if "transit_only" in s:
            s["transit_only"] = _as_bool(s["transit_only"])
        for k in ("lat", "lon"):
            if s.get(k) is not None:
                try:
                    s[k] = float(s[k])
                except (TypeError, ValueError):
                    pass
        if isinstance(s.get("place"), str):
            s["place"] = s["place"].strip()
        stops.append(s)
    t["stops"] = stops
    return t


def validate(trip: dict, *, known_places, today: date | None = None) -> list[str]:
    """Every problem with the itinerary, in Dutch. Empty list means it can go into the analysis."""
    today = today or date.today()
    known = {str(p).lower() for p in known_places}
    issues: list[str] = []

    if not str(trip.get("traveller") or "").strip():
        issues.append("geen reiziger in de aanvraag herkend")
    stops = trip.get("stops") or []
    if not stops:
        issues.append("geen enkele halte herkend")
        return issues
    lodging = (trip.get("profile") or {}).get("lodging")
    if lodging is not None and str(lodging).lower() not in LODGING:
        issues.append(f"profiel: onbekende verblijfsvorm '{lodging}' (kies uit {', '.join(sorted(LODGING))})")

    prev_end, prev_place = None, None
    for i, s in enumerate(stops, start=1):
        place = str(s.get("place") or "").strip()
        tag = f"halte {i}" + (f" '{place}'" if place else "")
        if not place:
            issues.append(f"{tag}: geen plaatsnaam")

        start, end = s.get("from"), s.get("to")
        for k, v in (("from", start), ("to", end)):
            if not isinstance(v, date):
                issues.append(f"{tag}: datum '{k}' onleesbaar ({v!r}); verwacht JJJJ-MM-DD")
        if isinstance(start, date) and isinstance(end, date):
            if end < start:
                issues.append(f"{tag}: 'to' ({end}) ligt voor 'from' ({start})")
            if prev_end and start < prev_end:
                issues.append(f"{tag}: begint ({start}) voor het einde van halte {i - 1} "
                              f"'{prev_place}' ({prev_end})")
            prev_end, prev_place = end, place

        if place and place.lower() not in known:
            if not (isinstance(s.get("lat"), float) and isinstance(s.get("lon"), float)):
                issues.append(f"{tag}: onbekende plaats en geen lat/lon; voeg ze toe aan de halte "
                              f"of zet de plaats in dienstreis/config/places.csv")
        for k, (lo, hi) in (("lat", LAT_RANGE), ("lon", LON_RANGE)):
            v = s.get(k)
            if isinstance(v, float) and not lo <= v <= hi:
                issues.append(f"{tag}: {k} {v} ligt buiten het verwachte gebied ({lo} tot {hi})")

        if s.get("transit_only") and isinstance(start, date) and isinstance(end, date) and start != end:
            issues.append(f"{tag}: transit_only maar loopt van {start} tot {end}; "
                          f"zet transit_only op false of maak er een dag van")
        sl = s.get("lodging")
        if sl is not None and str(sl).lower() not in LODGING:
            issues.append(f"{tag}: onbekende verblijfsvorm '{sl}'")

    # the year is the classic failure: a trip from December into March crosses into the next year
    dates = [d for s in stops for d in (s.get("from"), s.get("to")) if isinstance(d, date)]
    if dates:
        first, last = min(dates), max(dates)
        if (last - first).days > MAX_SPAN_DAYS:
            issues.append(f"reis beslaat {(last - first).days} dagen ({first} tot {last}); "
                          f"controleer de jaartallen")
        if first < today.replace(year=today.year - 1):
            issues.append(f"eerste datum {first} ligt meer dan een jaar in het verleden; "
                          f"controleer de jaartallen")
        if last > today.replace(year=today.year + 3):
            issues.append(f"laatste datum {last} ligt meer dan drie jaar in de toekomst; "
                          f"controleer de jaartallen")
    rv = trip.get("review_on")
    if rv is not None and not isinstance(rv, date) and str(rv).strip():
        issues.append(f"go/no-go-datum onleesbaar ({rv!r})")
    return issues
