"""Data layer: INRB-UMIE curated INSP situation reports, health-zone shapes, ECDC cross-check.

All numbers used downstream come from here, so every function returns data together with
the date it refers to. Nothing in this module makes judgements.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
from datetime import date
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

INRB_REPO = "https://github.com/INRB-UMIE/Ebola_DRC_2026.git"
ECDC_URL = "https://www.ecdc.europa.eu/en/ebola-outbreak-democratic-republic-congo-and-uganda"
WHO_DON_URL = "https://www.who.int/emergencies/disease-outbreak-news"
WHO_DON_API = "https://www.who.int/api/news/diseaseoutbreaknews"
UA = "Mozilla/5.0 (compatible; dienstreis-advies)"
NE_COUNTRIES = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
                "geojson/ne_50m_admin_0_countries.geojson")
CACHE = Path(os.environ.get("DIENSTREIS_CACHE", Path.home() / ".cache" / "dienstreis"))
CONFIG = Path(__file__).parent / "config"

# What the analysis reads, split by how often it actually changes. The INSP figures are new every
# day; the health-zone boundaries are not, and the shapefile is 66 MB. Refreshing both on the same
# six-hour clock meant re-fetching the geometry several times a day for nothing.
DAILY = [
    "data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_cases__daily.csv",
    "data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_deaths__daily.csv",
    "data/insp_sitrep/processed/insp_sitrep__national_cumulative_confirmed_cases__daily.csv",
    "data/insp_sitrep/processed/insp_sitrep__national_cumulative_confirmed_deaths__daily.csv",
    "data/aliases.csv",
]
SHAPES = [f"data/shapefiles/DRC_Health_zones.{e}" for e in ("shp", "shx", "dbf", "prj", "cpg")]
NEEDED = DAILY + SHAPES

# Drawing tolerance in degrees. The map is 12.5 inch at 300 dpi, about 3 750 pixels for a country
# 2 000 km wide: roughly 500 m per pixel. Detail finer than half a pixel cannot appear on the page.
DISPLAY_TOLERANCE = 0.0025


DAILY_MAX_AGE_H = 6.0
SHAPES_MAX_AGE_H = 30 * 24.0

INRB_RAW = "https://raw.githubusercontent.com/INRB-UMIE/Ebola_DRC_2026/main/"
HTTP_CACHE = "http_cache.json"


def _http_cache() -> dict:
    p = CACHE / HTTP_CACHE
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _download_needed(repo: Path, files: list[str]) -> None:
    """Fetch the given files, asking the server whether they changed since last time.

    Without git this is the only way in, so a 66 MB shapefile would otherwise come down again on
    every refresh. GitHub answers 304 for an unchanged file and sends no body.
    """
    meta = _http_cache()
    for f in files:
        p = repo / f
        head = {}
        m = meta.get(f) or {}
        if p.exists():
            if m.get("etag"):
                head["If-None-Match"] = m["etag"]
            if m.get("last_modified"):
                head["If-Modified-Since"] = m["last_modified"]
        r = requests.get(INRB_RAW + f, timeout=300, headers=head)
        if r.status_code == 304 and p.exists():
            continue
        r.raise_for_status()
        if r.content.startswith(b"version https://git-lfs"):
            raise RuntimeError(f"{f} is a Git LFS pointer; install git to fetch the INRB data")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(r.content)
        meta[f] = {"etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified")}
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / HTTP_CACHE).write_text(json.dumps(meta, indent=1), encoding="utf-8")


def _git(*args, cwd: Path | None = None):
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"}   # raw sitrep PDFs live in LFS; we do not need them
    return subprocess.run(list(args), check=True, env=env, capture_output=True, text=True, cwd=cwd)


def _sparse_clone(repo: Path) -> None:
    """Clone only the files the analysis reads.

    A plain --depth 1 clone of this repository is about 330 MB: mobility matrices, situation-report
    PDFs, health-site shapefiles, an archived copy of the zone shapefile. The analysis uses roughly
    70 MB of that, so blobs are fetched on demand and the checkout is limited to NEEDED.
    """
    if repo.exists():
        shutil.rmtree(repo)
    _git("git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "-q", INRB_REPO, str(repo))
    _git("git", "-C", str(repo), "sparse-checkout", "set", "--no-cone", *NEEDED)


def _stale(stamp: Path, max_age_h: float) -> bool:
    return not stamp.exists() or (time.time() - stamp.stat().st_mtime) >= max_age_h * 3600


# ---------------------------------------------------------------- fetching
def fetch_inrb(refresh: bool = False, max_age_h: float = DAILY_MAX_AGE_H,
               shapes_max_age_h: float = SHAPES_MAX_AGE_H) -> Path:
    """Make sure the cache holds the files the analysis reads, and that they are recent enough.

    The daily figures and the zone geometry age on separate clocks; only what is stale is fetched.
    """
    repo = CACHE / "inrb"
    stamps = {"daily": repo / ".dienstreis_fetched", "shapes": repo / ".dienstreis_shapes"}
    want = []
    if refresh or _stale(stamps["daily"], max_age_h) or not all((repo / f).exists() for f in DAILY):
        want += DAILY
    if refresh or _stale(stamps["shapes"], shapes_max_age_h) or not all((repo / f).exists() for f in SHAPES):
        want += SHAPES
    if not want:
        return repo

    CACHE.mkdir(parents=True, exist_ok=True)
    if shutil.which("git"):
        if not (repo / ".git").exists():
            _sparse_clone(repo)                       # includes a download without git left behind
        else:
            _git("git", "-C", str(repo), "fetch", "--depth", "1", "-q", "origin", "main")
            _git("git", "-C", str(repo), "reset", "--hard", "-q", "origin/main")
        # a shallow clone sometimes leaves tracked files unmaterialised: check them out explicitly
        _git("git", "-C", str(repo), "checkout", "--", *NEEDED)
    else:
        _download_needed(repo, want)   # no git (typical Windows PC): only the stale files

    missing = [f for f in NEEDED if not (repo / f).exists()]
    if missing:
        raise RuntimeError(f"INRB files missing after fetch: {missing}")
    for key, group in (("daily", DAILY), ("shapes", SHAPES)):
        if any(f in want for f in group):
            stamps[key].touch()
    return repo


def cache_size_mb(path: Path | None = None) -> float:
    p = path or CACHE
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6 if p.exists() else 0.0


def reset_cache() -> float:
    """Delete the data cache. The next run makes a lean sparse clone (see `dienstreis data --reset-cache`)."""
    size = cache_size_mb()
    if CACHE.exists():
        shutil.rmtree(CACHE)
    return size


def fetch_countries(tolerance: float = DISPLAY_TOLERANCE) -> gpd.GeoDataFrame:
    """Country borders for the map background. Downloaded once; national borders do not move.

    Drawn twice per map (behind the zones and again in the locator inset), so it is simplified to
    the same drawing tolerance and kept that way in the cache.
    """
    p = CACHE / "ne_50m_admin_0_countries.geojson"
    if not p.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        r = requests.get(NE_COUNTRIES, timeout=60)
        r.raise_for_status()
        p.write_bytes(r.content)
    if not tolerance:
        return gpd.read_file(p)[["ADMIN", "ISO_A3", "geometry"]]
    simple = CACHE / f"ne_50m_countries_{tolerance:g}.geojson"
    if not simple.exists():
        c = gpd.read_file(p)[["ADMIN", "ISO_A3", "geometry"]]
        c["geometry"] = c.geometry.simplify(tolerance)
        c.to_file(simple, driver="GeoJSON")
    return gpd.read_file(simple)


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


def _shape_stamp(repo: Path) -> str:
    """Identity of the health-zone shapefile, so cached outlines follow a refreshed shapefile."""
    f = repo / "data/shapefiles/DRC_Health_zones.shp"
    st = f.stat()
    return f"{int(st.st_mtime)}_{st.st_size}"


def display_geometry(zones: gpd.GeoDataFrame, repo: Path | None = None,
                     tolerance: float = DISPLAY_TOLERANCE) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Zone and province outlines for drawing: simplified, computed once, cached on disk.

    Two costs sat in every single advice. Merging the health zones into 26 province outlines takes
    about 50 seconds, and drawing a few thousand full-resolution polygons at 300 dpi another 25;
    both depend only on the shapefile, which is refreshed at most monthly. So they are computed on
    the first run after a shapefile change and read from the cache afterwards.

    Only what is drawn is simplified. `geo` decides which health zone a place falls in, which zones
    border it and how far the nearest active zone is, and those answers must come from the exact
    boundaries: `zones` itself is never touched here.
    """
    repo = Path(repo or (CACHE / "inrb"))
    tag = f"{tolerance:g}_{_shape_stamp(repo)}"
    fz, fp = CACHE / f"display_zones_{tag}.geojson", CACHE / f"display_prov_{tag}.geojson"

    if fz.exists() and fp.exists():
        geo_z, prov = gpd.read_file(fz), gpd.read_file(fp)
    else:
        # dissolve at full resolution first: simplifying the zones first would leave gaps and
        # spikes along the province borders, which are the one line on the map that must be right
        prov = zones.dissolve(by="PROVINCE").reset_index()[["PROVINCE", "geometry"]]
        if tolerance:
            prov["geometry"] = prov.geometry.simplify(tolerance)
        geo_z = zones[["Nom", "geometry"]].copy()
        if tolerance:
            geo_z["geometry"] = geo_z.geometry.simplify(tolerance)
        CACHE.mkdir(parents=True, exist_ok=True)
        for f in CACHE.glob("display_*.geojson"):      # drop outlines of an older shapefile
            f.unlink(missing_ok=True)
        geo_z.to_file(fz, driver="GeoJSON")
        prov.to_file(fp, driver="GeoJSON")

    out = zones.copy()
    out["geometry"] = out.Nom.map(dict(zip(geo_z.Nom, geo_z.geometry)))
    out = out.set_geometry("geometry")
    missing = out.geometry.isna()
    if missing.any():                                   # a zone the cache does not know: keep its own
        out.loc[missing, "geometry"] = zones.loc[missing, "geometry"]
    return out, prov


def who_snapshot(timeout: int = 40, top: int = 20) -> dict:
    """Most recent WHO Disease Outbreak News item about Ebola in the DRC.

    Read from the DON JSON API, not the page: the page is rendered client-side and a regex over its
    HTML finds nothing. A headline and a date, not figures; the counts that carry the advice come
    from INSP. Fails soft like the ECDC check, because a source being unreachable must make itself
    visible in the QA block, never stop an advice.
    """
    try:
        r = requests.get(WHO_DON_API, timeout=timeout, headers={"User-Agent": UA},
                         params={"$orderby": "PublicationDateAndTime desc", "$top": str(top)})
        r.raise_for_status()
        items = r.json().get("value", [])
        for it in items:
            title = str(it.get("Title") or "")
            if re.search(r"ebola", title, re.I) and re.search(r"congo|DRC", title, re.I):
                day = str(it.get("PublicationDateAndTime") or "")[:10]
                link = str(it.get("ItemDefaultUrl") or "").strip("/")
                return {"ok": True, "date": day or None, "item": title,
                        "url": f"https://www.who.int/emergencies/disease-outbreak-news/item/{link}"
                               if link else WHO_DON_URL,
                        "days_old": (date.today() - date.fromisoformat(day)).days if day else None}
        return {"ok": False, "reason": f"no DRC Ebola item in the last {len(items)} DON entries",
                "url": WHO_DON_URL}
    except Exception as e:   # network, API change or unparseable payload
        return {"ok": False, "reason": repr(e), "url": WHO_DON_URL}


def sources_snapshot(asof: str | None = None) -> dict:
    """The sources checked on every run, next to the INSP figures.

    ECDC and WHO are read here; FOD and CDC are prose pages that resist parsing, so they are checked
    in the web step (prompts/web.md) and recorded in advisories.yaml with the date they were verified.
    """
    if asof:
        return {"ecdc": {"ok": False, "reason": "asof run"}, "who": {"ok": False, "reason": "asof run"}}
    return {"ecdc": ecdc_snapshot(), "who": who_snapshot()}
