"""Data layer: INRB-UMIE curated INSP situation reports, health-zone shapes, ECDC cross-check.

All numbers used downstream come from here, so every function returns data together with
the date it refers to. Nothing in this module makes judgements.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

INRB_REPO = "https://github.com/INRB-UMIE/Ebola_DRC_2026.git"
ECDC_URL = "https://www.ecdc.europa.eu/en/ebola-outbreak-democratic-republic-congo-and-uganda"
NE_COUNTRIES = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
                "geojson/ne_50m_admin_0_countries.geojson")
CACHE = Path(os.environ.get("DIENSTREIS_CACHE", Path.home() / ".cache" / "dienstreis"))
CONFIG = Path(__file__).parent / "config"

NEEDED = [
    "data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_cases__daily.csv",
    "data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_deaths__daily.csv",
    "data/insp_sitrep/processed/insp_sitrep__national_cumulative_confirmed_cases__daily.csv",
    "data/insp_sitrep/processed/insp_sitrep__national_cumulative_confirmed_deaths__daily.csv",
    "data/aliases.csv",
] + [f"data/shapefiles/DRC_Health_zones.{e}" for e in ("shp", "shx", "dbf", "prj", "cpg")]


# ---------------------------------------------------------------- fetching
def fetch_inrb(refresh: bool = False, max_age_h: float = 6.0) -> Path:
    """Clone or update the INRB repo into the cache and make sure the needed files exist."""
    repo = CACHE / "inrb"
    stamp = repo / ".dienstreis_fetched"
    fresh = stamp.exists() and (time.time() - stamp.stat().st_mtime) < max_age_h * 3600
    if repo.exists() and fresh and not refresh and all((repo / f).exists() for f in NEEDED):
        return repo
    CACHE.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"}   # raw sitrep PDFs live in LFS; we do not need them
    run = lambda *a: subprocess.run(list(a), check=True, env=env, capture_output=True, text=True)
    if not (repo / ".git").exists():
        run("git", "clone", "--depth", "1", "-q", INRB_REPO, str(repo))
    else:
        run("git", "-C", str(repo), "fetch", "--depth", "1", "-q", "origin", "main")
        run("git", "-C", str(repo), "reset", "--hard", "-q", "origin/main")
    # a shallow clone sometimes leaves tracked files unmaterialised: check them out explicitly
    run("git", "-C", str(repo), "checkout", "--", *NEEDED)
    missing = [f for f in NEEDED if not (repo / f).exists()]
    if missing:
        raise RuntimeError(f"INRB files missing after fetch: {missing}")
    stamp.touch()
    return repo


def fetch_countries() -> gpd.GeoDataFrame:
    p = CACHE / "ne_50m_admin_0_countries.geojson"
    if not p.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        r = requests.get(NE_COUNTRIES, timeout=60)
        r.raise_for_status()
        p.write_bytes(r.content)
    return gpd.read_file(p)[["ADMIN", "ISO_A3", "geometry"]]


# ---------------------------------------------------------------- name handling
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"\(.*?\)", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _alias_map(repo: Path, shape_names: list[str]) -> dict[str, str]:
    """Map every observed INSP spelling to a shapefile health-zone name (Nom)."""
    overrides = pd.read_csv(CONFIG / "zone_overrides.csv", comment="#")
    ov = {norm(a): b for a, b in zip(overrides.observed, overrides.shapefile_nom)}
    inrb = pd.read_csv(repo / "data/aliases.csv")
    canon = {norm(a): b for a, b in zip(inrb.observed_name, inrb.canonical_nom)}
    by_norm: dict[str, list[str]] = {}
    for n in shape_names:
        by_norm.setdefault(norm(n), []).append(n)

    def resolve(obs: str) -> str | None:
        k = norm(obs)
        if k in ov:
            return ov[k]
        k2 = norm(canon.get(k, obs))
        if k2 in ov:
            return ov[k2]
        hits = by_norm.get(k2, [])
        return hits[0] if len(hits) == 1 else None
    return resolve  # type: ignore[return-value]


# ---------------------------------------------------------------- loading
@dataclass
class Outbreak:
    zones: gpd.GeoDataFrame          # one row per health zone, geometry + latest figures
    series: pd.DataFrame             # zone x date cumulative confirmed cases (forward filled)
    national: pd.DataFrame           # date, cases, deaths (national cumulative)
    asof: pd.Timestamp
    unmatched: list[str]
    checks: dict


def _read_long(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = ["nom", "date", "v"]
    return df.assign(date=pd.to_datetime(df["date"], errors="coerce"),
                     v=pd.to_numeric(df["v"], errors="coerce")).dropna(subset=["date"])


def _to_wide(df: pd.DataFrame, resolve) -> tuple[pd.DataFrame, list[str]]:
    df = df.assign(Nom=df["nom"].map(resolve))
    df = df.dropna(subset=["nom"])
    unmatched = sorted(df.loc[df.Nom.isna() & df.v.gt(0), "nom"].unique())
    df = df.dropna(subset=["Nom"])
    # aliases of one zone are combined per date by max, then carried forward
    wide = df.pivot_table(index="date", columns="Nom", values="v", aggfunc="max").sort_index()
    wide = wide.ffill().fillna(0)
    # levels keep INSP downward revisions (so zone sums match the national total);
    # new-case detection uses the running maximum, so a revision is never read as a new case
    return wide, unmatched


def load(refresh: bool = False, asof: str | None = None) -> Outbreak:
    repo = fetch_inrb(refresh=refresh)
    base = repo / "data/insp_sitrep/processed"
    hz = gpd.read_file(repo / "data/shapefiles/DRC_Health_zones.shp")
    hz = hz.dissolve(by="Nom", aggfunc="first").reset_index()[["Nom", "PROVINCE", "geometry"]]
    resolve = _alias_map(repo, hz.Nom.tolist())

    cw, un1 = _to_wide(_read_long(base / "insp_sitrep__cumulative_confirmed_cases__daily.csv"), resolve)
    dw, _ = _to_wide(_read_long(base / "insp_sitrep__cumulative_confirmed_deaths__daily.csv"), resolve)
    if asof:
        cw, dw = cw.loc[:asof], dw.loc[:asof]
    t = cw.index.max()

    def lag(days):
        sub = cw.loc[:t - pd.Timedelta(days=days)]
        base = sub.iloc[-1] if len(sub) else cw.iloc[0] * 0
        return base.clip(upper=cw.loc[t])   # new cases are never negative

    last_inc = cw.cummax().diff().gt(0).apply(lambda s: s[s].index.max() if s.any() else pd.NaT)
    first_case = cw.gt(0).apply(lambda s: s[s].index.min() if s.any() else pd.NaT)
    fig = pd.DataFrame({
        "cases": cw.loc[t], "deaths": dw.reindex(columns=cw.columns).ffill().loc[:t].iloc[-1].fillna(0),
        "new14": cw.loc[t] - lag(14), "new21": cw.loc[t] - lag(21),
        "first_case": first_case, "last_increase": last_inc,
    })
    # a zone whose only report is its first case has no increase row: use first_case then
    fig["last_case"] = fig["last_increase"].fillna(fig["first_case"])
    fig["days_since_last"] = (t - fig["last_case"]).dt.days
    zones = hz.merge(fig, left_on="Nom", right_index=True, how="left")
    for c in ("cases", "deaths", "new14", "new21"):
        zones[c] = zones[c].fillna(0).astype(int)

    nat_c = _read_long(base / "insp_sitrep__national_cumulative_confirmed_cases__daily.csv")
    nat_d = _read_long(base / "insp_sitrep__national_cumulative_confirmed_deaths__daily.csv")
    national = (nat_c.groupby("date").v.max().rename("cases").to_frame()
                .join(nat_d.groupby("date").v.max().rename("deaths"), how="outer").sort_index())
    if asof:
        national = national.loc[:asof]

    checks = {"zone_sum": int(zones.cases.sum()),
              "national_at_asof": _at(national.cases, t),
              "zones_with_cases": int((zones.cases > 0).sum()),
              "provinces_with_cases": int(zones.loc[zones.cases > 0, "PROVINCE"].nunique())}
    checks["zone_sum_matches_national"] = checks["zone_sum"] == checks["national_at_asof"]
    return Outbreak(zones, cw, national, t, un1, checks)


def _at(s: pd.Series, t) -> int | None:
    s = s.dropna().loc[:t]
    return int(s.iloc[-1]) if len(s) else None


# ---------------------------------------------------------------- ECDC cross-check
_NUM = r"([\d][\d\s  ,]*)"


def ecdc_snapshot(timeout: int = 30) -> dict:
    """Parse the ECDC landing page headline. Fragile by nature: returns {'ok': False} on failure."""
    try:
        import html as _html
        raw = requests.get(ECDC_URL, timeout=timeout).text
        text = _html.unescape(re.sub(r"<[^>]+>", " ", raw))
        text = re.sub(r"\s+", " ", text)
        m = re.search(r"total of " + _NUM + r" confirmed cases, including " + _NUM +
                      r" related deaths \(from data up until (\d{1,2} \w+)", text)
        upd = re.search(r"last updated on (\d{1,2} \w+) at", text)
        if not m:
            return {"ok": False, "reason": "headline pattern not found"}
        n = lambda s: int(re.sub(r"\D", "", s))
        return {"ok": True, "cases": n(m.group(1)), "deaths": n(m.group(2)),
                "data_until": m.group(3), "page_updated": upd.group(1) if upd else None,
                "url": ECDC_URL}
    except Exception as e:  # network or layout change
        return {"ok": False, "reason": repr(e)}
