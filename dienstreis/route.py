"""Which outbreaks apply to a trip, and which country each stop is in. No judgements.

An outbreak applies when a stop lies in one of its countries, or in a country that borders one:
borders with an outbreak country are closed or screened, so those countries have to be checked
(decision 2026-09-25, instead of a distance radius). When no active profile applies, the advice
is written at country level with the profile `geen`.

A stop's country comes from config/places.csv, or for a stop given by lat/lon from the Natural
Earth country outlines already in the data cache. Natural Earth marks some countries -99 in
ISO_A3 (France, Norway): their code is taken from ADM0_A3 then. The other way round would be
wrong too: South Sudan is SSD in ISO_A3 but SDS in ADM0_A3.
"""
from __future__ import annotations

from functools import lru_cache

from . import countries, outbreak
from . import trip as trip_mod


def _places() -> dict[str, str]:
    rows = [l.split(",") for l in trip_mod.PLACES.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]
    return {r[0].strip().lower(): r[3].strip() for r in rows[1:] if len(r) >= 4}


@lru_cache(maxsize=1)
def _outlines():
    """Full-resolution country outlines with both codes; the map's simplified copy keeps only ISO_A3."""
    import geopandas as gpd
    from . import data
    data.fetch_countries(tolerance=0)                  # downloads the file once if it is missing
    c = gpd.read_file(data.CACHE / "ne_50m_admin_0_countries.geojson")[["ISO_A3", "ADM0_A3", "ADMIN", "NAME_NL",
                                                                          "geometry"]]
    c["iso"] = [a if i == "-99" else i for i, a in zip(c.ISO_A3, c.ADM0_A3)]
    return c


def country_at(lat: float, lon: float) -> str | None:
    """ISO3 of the country a point lies in (Natural Earth, cached); None at sea or on no land."""
    from shapely.geometry import Point
    c = _outlines()
    hit = c[c.geometry.contains(Point(lon, lat))]
    if hit.empty:
        return None
    iso, adm = hit.iloc[0]["ISO_A3"], hit.iloc[0]["ADM0_A3"]
    return adm if iso == "-99" else iso


def describe(iso3: str) -> dict:
    """Names and land neighbours of a country from Natural Earth, for a registry entry it does not have yet."""
    c = _outlines()
    row = c[c.iso == iso3]
    if row.empty:
        return {}
    g = row.geometry.iloc[0]
    nb = c[c.geometry.intersects(g.buffer(0.01)) & (c.iso != iso3)]
    return {"name_nl": row.NAME_NL.iloc[0] or row.ADMIN.iloc[0], "name_en": row.ADMIN.iloc[0],
            "neighbours": sorted(nb.iso)}


def country_of(stop: dict) -> str | None:
    """The country of a stop: places.csv for a known place, the map for a stop given by lat/lon."""
    known = _places().get(str(stop.get("place") or "").strip().lower())
    if known:
        return known
    if isinstance(stop.get("lat"), (int, float)) and isinstance(stop.get("lon"), (int, float)):
        return country_at(float(stop["lat"]), float(stop["lon"]))
    return None


def trip_countries(trip: dict) -> list[str]:
    return list(dict.fromkeys(c for c in (country_of(s) for s in trip.get("stops") or []) if c))


def reach(spec: outbreak.OutbreakSpec) -> set[str]:
    """The countries of an outbreak and their neighbours."""
    return set(spec.countries) | {n for c in spec.countries for n in countries.neighbours(c)}


def applicable(trip: dict) -> list[outbreak.OutbreakSpec]:
    """Every active outbreak whose countries or neighbouring countries the trip passes through."""
    here = set(trip_countries(trip))
    return [s for s in outbreak.active() if here & reach(s)]


def outbreaks_for(trip: dict) -> list[outbreak.OutbreakSpec]:
    """The outbreaks to assess the trip against: those the trip names (`outbreaks:` in stops.yaml,
    set by routing and confirmed or edited by the user), else routing; `geen` when none applies."""
    if trip.get("outbreaks"):
        return [outbreak.load(i) for i in trip["outbreaks"]]
    return applicable(trip) or [outbreak.none()]


def unmatched_diseases(mentioned: list[str], specs: list[outbreak.OutbreakSpec]) -> list[str]:
    """Diseases the request names that no applied profile covers: they must be looked for, not assumed away."""
    terms = [t.lower() for s in specs for t in s.match_terms]
    return [d for d in mentioned or [] if d and not any(t in d.lower() or d.lower() in t for t in terms)]
