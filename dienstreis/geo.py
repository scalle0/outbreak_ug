"""Geography: place lookup, point-in-zone, neighbours and distances. No judgements."""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

CONFIG = Path(__file__).parent / "config"
METRIC = 32735  # UTM 35S: fine for distances across the DRC


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (la1, lo1), (la2, lo2) = [(radians(x), radians(y)) for x, y in (a, b)]
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def places() -> pd.DataFrame:
    return pd.read_csv(CONFIG / "places.csv", comment="#")


def locate(name: str, lat: float | None = None, lon: float | None = None) -> dict:
    """Coordinates for a place name (config) unless lat/lon are given."""
    if lat is not None and lon is not None:
        return {"name": name, "lat": float(lat), "lon": float(lon), "country": None, "source": "stops.yaml"}
    p = places()
    hit = p[p.name.str.lower() == name.lower()]
    if hit.empty:
        raise KeyError(f"Unknown place '{name}': add it to config/places.csv or give lat/lon in stops.yaml")
    r = hit.iloc[0]
    return {"name": r["name"], "lat": r.lat, "lon": r.lon, "country": r.country, "source": "places.csv"}


def zone_of(zones: gpd.GeoDataFrame, lat: float, lon: float) -> pd.Series | None:
    pt = Point(lon, lat)
    hit = zones[zones.geometry.contains(pt)]
    if hit.empty:  # points on a border or just outside (lakes, rivers): take nearest within 5 km
        ptm = gpd.GeoSeries([pt], crs=zones.crs).to_crs(METRIC).iloc[0]
        d = zones.to_crs(METRIC).geometry.distance(ptm)
        if d.min() < 5000:
            return zones.loc[d.idxmin()]
        return None
    return hit.iloc[0]


def neighbours(zones: gpd.GeoDataFrame, nom: str) -> gpd.GeoDataFrame:
    geom = zones.loc[zones.Nom == nom, "geometry"].iloc[0]
    nb = zones[zones.geometry.intersects(geom.buffer(0.01)) & (zones.Nom != nom)]
    return nb


def nearest_active(zones: gpd.GeoDataFrame, lat: float, lon: float, max_days: int = 21) -> dict | None:
    """Nearest zone with a new case in the last `max_days` days (edge distance, km)."""
    act = zones[zones.days_since_last.notna() & (zones.days_since_last <= max_days)]
    if act.empty:
        return None
    pt = gpd.GeoSeries([Point(lon, lat)], crs=zones.crs).to_crs(METRIC).iloc[0]
    d = act.to_crs(METRIC).geometry.distance(pt) / 1000
    i = d.idxmin()
    return {"zone": act.loc[i, "Nom"], "province": act.loc[i, "PROVINCE"], "km": round(float(d.loc[i])),
            "cases": int(act.loc[i, "cases"]), "days_since_last": int(act.loc[i, "days_since_last"])}
