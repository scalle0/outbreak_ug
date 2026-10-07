"""Data layer: the figures of an outbreak per zone, the zone shapes, and the ECDC and WHO checks.

All numbers used downstream come from here, so every function returns data together with
the date it refers to. Nothing in this module makes judgements.

Where the figures come from is set by the outbreak profile (`adapter` in outbreak.yaml):

    inrb    a GitHub repository with INSP situation reports per health zone and the zone shapefile
            (INRB-UMIE, Ebola DRC 2026)
    table   a hand-kept case table in the profile folder (cases.csv), per province or health zone,
            on the zone outlines of another profile; the web step proposes new rows, you confirm
            them into a local copy (~/.config/dienstreis/outbreaks/<id>/cases.csv)

Every adapter hands its series to `derive`, so the fields the risk rules read are computed the
same way whatever the source.
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

from . import outbreak

WHO_DON_URL = "https://www.who.int/emergencies/disease-outbreak-news"
WHO_DON_API = "https://www.who.int/api/news/diseaseoutbreaknews"
UA = "Mozilla/5.0 (compatible; dienstreis-advies)"
NE_COUNTRIES = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
                "geojson/ne_50m_admin_0_countries.geojson")
CACHE = Path(os.environ.get("DIENSTREIS_CACHE", Path.home() / ".cache" / "dienstreis"))
WHO_LAST = CACHE / "who_last.json"      # the last WHO item read per outbreak, for a run when WHO is unreachable
RETRY_WAITS = (5, 15)                   # seconds before the second and third try of a source read every run

NOT_CONFIGURED = "not configured for this outbreak"   # a source the profile does not name: not a failure
LOCAL_OUTBREAKS = Path(os.environ.get("DIENSTREIS_OUTBREAKS", Path.home() / ".config" / "dienstreis" / "outbreaks"))
TABLE_COLUMNS = ["date", "admin1", "admin2", "cases_cum", "deaths_cum", "case_def", "source_url"]
NATIONAL = "NATIONAAL"                                 # admin1 of a row that holds the national total


class TableEmpty(ValueError):
    """A case table without figures per unit: the outbreak is assessed without figures, and says so."""


# What the analysis reads, split by how often it actually changes. The INSP figures are new every
# day; the health-zone boundaries are not, and the shapefile is 66 MB. Refreshing both on the same
# six-hour clock meant re-fetching the geometry several times a day for nothing.
def _daily(spec) -> list[str]:
    return list(spec.adapter["daily"].values())


def _shapes(spec) -> list[str]:
    return [f"{spec.adapter['shapes']}.{e}" for e in ("shp", "shx", "dbf", "prj", "cpg")]


# the default profile's files, under the names the rest of the package and the tests use
_DEFAULT = outbreak.default()
INRB_REPO = _DEFAULT.adapter["repo"]
INRB_RAW = _DEFAULT.adapter["raw"]
DAILY = _daily(_DEFAULT)
SHAPES = _shapes(_DEFAULT)
NEEDED = DAILY + SHAPES
ECDC_URL = _DEFAULT.sources["ecdc"]

# Drawing tolerance in degrees. The map is 12.5 inch at 300 dpi, about 3 750 pixels for a country
# 2 000 km wide: roughly 500 m per pixel. Detail finer than half a pixel cannot appear on the page.
DISPLAY_TOLERANCE = 0.0025


DAILY_MAX_AGE_H = 6.0
SHAPES_MAX_AGE_H = 30 * 24.0

HTTP_CACHE = "http_cache.json"


def _http_cache() -> dict:
    p = CACHE / HTTP_CACHE
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _download_needed(repo: Path, files: list[str], raw: str | None = None) -> None:
    """Fetch the given files, asking the server whether they changed since last time.

    Without git this is the only way in, so a 66 MB shapefile would otherwise come down again on
    every refresh. GitHub answers 304 for an unchanged file and sends no body.
    """
    raw = raw or INRB_RAW
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
        r = requests.get(raw + f, timeout=300, headers=head)
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


def _sparse_clone(repo: Path, url: str | None = None, needed: list[str] | None = None) -> None:
    """Clone only the files the analysis reads.

    A plain --depth 1 clone of this repository is about 330 MB: mobility matrices, situation-report
    PDFs, health-site shapefiles, an archived copy of the zone shapefile. The analysis uses roughly
    70 MB of that, so blobs are fetched on demand and the checkout is limited to NEEDED.
    """
    if repo.exists():
        shutil.rmtree(repo)
    _git("git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "-q", url or INRB_REPO, str(repo))
    _git("git", "-C", str(repo), "sparse-checkout", "set", "--no-cone", *(needed or NEEDED))


def _stale(stamp: Path, max_age_h: float) -> bool:
    return not stamp.exists() or (time.time() - stamp.stat().st_mtime) >= max_age_h * 3600


# ---------------------------------------------------------------- fetching
def fetch_inrb(refresh: bool = False, max_age_h: float = DAILY_MAX_AGE_H,
               shapes_max_age_h: float = SHAPES_MAX_AGE_H, spec=None) -> Path:
    """Make sure the cache holds the files the analysis reads, and that they are recent enough.

    The daily figures and the zone geometry age on separate clocks; only what is stale is fetched.
    """
    spec = spec or outbreak.default()
    a = spec.adapter
    daily, shapes = _daily(spec), _shapes(spec)
    needed = daily + shapes
    repo = CACHE / a["cache_dir"]
    stamps = {"daily": repo / ".dienstreis_fetched", "shapes": repo / ".dienstreis_shapes"}
    want = []
    if refresh or _stale(stamps["daily"], max_age_h) or not all((repo / f).exists() for f in daily):
        want += daily
    if refresh or _stale(stamps["shapes"], shapes_max_age_h) or not all((repo / f).exists() for f in shapes):
        want += shapes
    if not want:
        return repo

    CACHE.mkdir(parents=True, exist_ok=True)
    if shutil.which("git"):
        if not (repo / ".git").exists():
            _sparse_clone(repo, a["repo"], needed)    # includes a download without git left behind
        else:
            _git("git", "-C", str(repo), "fetch", "--depth", "1", "-q", "origin", "main")
            _git("git", "-C", str(repo), "reset", "--hard", "-q", "origin/main")
        # a shallow clone sometimes leaves tracked files unmaterialised: check them out explicitly
        _git("git", "-C", str(repo), "checkout", "--", *needed)
    else:
        _download_needed(repo, want, a["raw"])   # no git (typical Windows PC): only the stale files

    missing = [f for f in needed if not (repo / f).exists()]
    if missing:
        raise RuntimeError(f"INRB files missing after fetch: {missing}")
    for key, group in (("daily", daily), ("shapes", shapes)):
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


def _alias_map(repo: Path, shape_names: list[str], spec=None) -> dict[str, str]:
    """Map every observed INSP spelling to a shapefile health-zone name (Nom)."""
    spec = spec or outbreak.default()
    overrides = pd.read_csv(spec.file("zone_overrides.csv"), comment="#")
    ov = {norm(a): b for a, b in zip(overrides.observed, overrides.shapefile_nom)}
    inrb = pd.read_csv(repo / spec.adapter["daily"]["aliases"])
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
    spec: object = None              # the outbreak profile these figures belong to


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


def load(refresh: bool = False, asof: str | None = None, spec=None) -> Outbreak:
    """The figures of one outbreak (default: the default profile), up to `asof` if given."""
    spec = spec or outbreak.default()
    kind = spec.adapter["type"]
    if kind == "inrb":
        return _load_inrb(spec, refresh, asof)
    if kind == "table":
        return _load_table(spec, refresh, asof)
    raise ValueError(f"{spec.id}: onbekende adapter '{kind}'")


# ---------------------------------------------------------------- the hand-kept table
def read_table(path: Path) -> pd.DataFrame:
    """A case table: one row per date and unit, cumulative figures, the case definition and the source."""
    t = pd.read_csv(path, comment="#", dtype=str, keep_default_na=False)
    missing = [c for c in TABLE_COLUMNS if c not in t.columns]
    if missing:
        raise ValueError(f"{path}: kolommen ontbreken: {', '.join(missing)}")
    t["date"] = pd.to_datetime(t["date"], errors="coerce")
    for c in ("cases_cum", "deaths_cum"):
        t[c] = pd.to_numeric(t[c], errors="coerce")
    return t.dropna(subset=["date"])


def _last(path: Path) -> pd.Timestamp:
    t = read_table(path)
    return t["date"].max() if len(t) else pd.Timestamp.min


def table_path(spec) -> Path:
    """The case table: the package copy, or the local one as soon as it reaches the same date or later."""
    pkg = spec.file(spec.adapter["cases"])
    loc = LOCAL_OUTBREAKS / spec.id / spec.adapter["cases"]
    if loc.exists() and (not pkg.exists() or _last(loc) >= _last(pkg)):
        return loc
    return pkg


def append_local_table(spec, rows: list[dict]) -> Path:
    """Add confirmed rows to the local case table (a copy of the package table the first time)."""
    loc = LOCAL_OUTBREAKS / spec.id / spec.adapter["cases"]
    base = read_table(table_path(spec)) if table_path(spec).exists() else pd.DataFrame(columns=TABLE_COLUMNS)
    new = pd.DataFrame([{c: r.get(c, "") for c in TABLE_COLUMNS} for r in rows])
    new["date"] = pd.to_datetime(new["date"], errors="coerce")
    t = pd.concat([base, new], ignore_index=True).dropna(subset=["date"])
    t = t.drop_duplicates(subset=["date", "admin1", "admin2"], keep="last").sort_values(["date", "admin1", "admin2"])
    loc.parent.mkdir(parents=True, exist_ok=True)
    t.assign(date=t["date"].dt.strftime("%Y-%m-%d")).to_csv(loc, index=False, encoding="utf-8")
    return loc


def boundaries(spec) -> gpd.GeoDataFrame:
    """The unit outlines of a table outbreak (Nom, PROVINCE, geometry), taken from another profile's zones.

    At admin1 the zones are merged into provinces, once per shapefile, and kept in the cache: the
    merge takes about a minute, and these are the exact outlines the zone lookup runs on.
    """
    src = outbreak.load(spec.adapter["boundaries"]["from"])
    repo = fetch_inrb(spec=src)
    level = spec.adapter["level"]
    if level == "admin2":                 # the zones as they are: read in seconds, nothing to cache
        hz = gpd.read_file(repo / f"{src.adapter['shapes']}.shp")
        return hz.dissolve(by="Nom", aggfunc="first").reset_index()[["Nom", "PROVINCE", "geometry"]]
    cached = CACHE / f"units_{src.id}_{level}_{_shape_stamp(repo, src)}.geojson"
    if cached.exists():
        return gpd.read_file(cached)
    hz = gpd.read_file(repo / f"{src.adapter['shapes']}.shp")
    hz = hz.dissolve(by="Nom", aggfunc="first").reset_index()[["Nom", "PROVINCE", "geometry"]]
    if level == "admin1":
        hz = hz.dissolve(by="PROVINCE").reset_index()[["PROVINCE", "geometry"]]
        hz["Nom"] = hz["PROVINCE"]
        hz = hz[["Nom", "PROVINCE", "geometry"]]
    for f in CACHE.glob(f"units_{src.id}_{level}_*.geojson"):
        f.unlink(missing_ok=True)
    hz.to_file(cached, driver="GeoJSON")
    return hz


def _load_table(spec, refresh: bool, asof: str | None) -> Outbreak:
    path = table_path(spec)
    t = read_table(path) if path.exists() else pd.DataFrame(columns=TABLE_COLUMNS)
    national_rows = t[t["admin1"].str.upper() == NATIONAL]
    sub = t[(t["admin1"].str.upper() != NATIONAL) & (t["admin1"].str.len() > 0)]
    if sub.empty:
        raise TableEmpty(f"{spec.id}: geen cijfers per eenheid in {path}")
    hz = boundaries(spec)
    key = spec.adapter["level"]
    ov_path = spec.file("zone_overrides.csv")
    ov = {}
    if ov_path.exists():
        o = pd.read_csv(ov_path, comment="#")
        ov = {norm(a): b for a, b in zip(o.observed, o.shapefile_nom)}
    by_norm = {norm(n): n for n in hz.Nom}

    def resolve(obs: str) -> str | None:
        k = norm(obs)
        return ov.get(k) or by_norm.get(k)

    def long(col):
        return sub[[key, "date", col]].set_axis(["nom", "date", "v"], axis=1)
    cw, unmatched = _to_wide(long("cases_cum"), resolve)
    dw, _ = _to_wide(long("deaths_cum"), resolve)
    if len(national_rows):
        national = (national_rows.groupby("date")[["cases_cum", "deaths_cum"]].max()
                    .rename(columns={"cases_cum": "cases", "deaths_cum": "deaths"}).sort_index())
    else:
        national = pd.DataFrame({"cases": cw.sum(axis=1),
                                 "deaths": dw.reindex(cw.index).ffill().fillna(0).sum(axis=1)})
    ob = derive(hz, cw, dw, national, asof, unmatched, spec)
    if spec.adapter.get("national_check") is False:   # zone and national figures from different bases
        ob.checks["zone_sum_matches_national"] = None
    ob.checks["table"] = str(path)
    ob.checks["table_last_date"] = str(ob.asof.date())
    return ob


def _load_inrb(spec, refresh: bool, asof: str | None) -> Outbreak:
    """INRB-UMIE layout: INSP series per zone (long CSV), aliases.csv, a zone shapefile with Nom/PROVINCE."""
    a = spec.adapter
    repo = fetch_inrb(refresh=refresh, spec=spec)
    hz = gpd.read_file(repo / f"{a['shapes']}.shp")
    hz = hz.dissolve(by="Nom", aggfunc="first").reset_index()[["Nom", "PROVINCE", "geometry"]]
    resolve = _alias_map(repo, hz.Nom.tolist(), spec)
    d = a["daily"]
    cw, un1 = _to_wide(_read_long(repo / d["cases"]), resolve)
    dw, _ = _to_wide(_read_long(repo / d["deaths"]), resolve)
    nat_c = _read_long(repo / d["national_cases"])
    nat_d = _read_long(repo / d["national_deaths"])
    national = (nat_c.groupby("date").v.max().rename("cases").to_frame()
                .join(nat_d.groupby("date").v.max().rename("deaths"), how="outer").sort_index())
    return derive(hz, cw, dw, national, asof, un1, spec)


def derive(hz: gpd.GeoDataFrame, cw: pd.DataFrame, dw: pd.DataFrame, national: pd.DataFrame,
           asof: str | None, unmatched: list[str], spec) -> Outbreak:
    """The fields the risk rules read, from any adapter's series.

    hz        zones: Nom, PROVINCE, geometry
    cw, dw    date x Nom cumulative confirmed cases and deaths, forward filled
    national  date -> cases, deaths (national cumulative)
    """
    if asof:
        cw, dw, national = cw.loc[:asof], dw.loc[:asof], national.loc[:asof]
    t = cw.index.max()

    def lag(days):
        sub = cw.loc[:t - pd.Timedelta(days=days)]
        base = sub.iloc[-1] if len(sub) else cw.iloc[0] * 0
        return base.clip(upper=cw.loc[t])   # new cases are never negative

    last_inc = cw.cummax().diff().gt(0).apply(lambda s: s[s].index.max() if s.any() else pd.NaT)
    first_case = cw.gt(0).apply(lambda s: s[s].index.min() if s.any() else pd.NaT)
    fig = pd.DataFrame({
        "cases": cw.loc[t], "deaths": dw.reindex(columns=cw.columns).ffill().loc[:t].iloc[-1].fillna(0),
        "new14": cw.loc[t] - lag(getattr(spec, "recent", 14)),     # new cases over the profile's recent window
        "first_case": first_case, "last_increase": last_inc,
    })
    # a zone whose only report is its first case has no increase row: use first_case then
    fig["last_case"] = fig["last_increase"].fillna(fig["first_case"])
    fig["days_since_last"] = (t - fig["last_case"]).dt.days
    zones = hz.merge(fig, left_on="Nom", right_index=True, how="left")
    for c in ("cases", "deaths", "new14"):
        zones[c] = zones[c].fillna(0).astype(int)

    checks = {"zone_sum": int(zones.cases.sum()),
              "national_at_asof": _at(national.cases, t),
              "zones_with_cases": int((zones.cases > 0).sum()),
              "provinces_with_cases": int(zones.loc[zones.cases > 0, "PROVINCE"].nunique())}
    checks["zone_sum_matches_national"] = checks["zone_sum"] == checks["national_at_asof"]
    return Outbreak(zones, cw, national, t, unmatched, checks, spec)


def _at(s: pd.Series, t) -> int | None:
    s = s.dropna().loc[:t]
    return int(s.iloc[-1]) if len(s) else None


# ---------------------------------------------------------------- ECDC cross-check
_NUM = r"([\d][\d\s  ,]*)"


def ecdc_snapshot(timeout: int = 30, spec=None) -> dict:
    """Parse the ECDC landing page headline. Fragile by nature: returns {'ok': False} on failure."""
    url = (spec or outbreak.default()).sources.get("ecdc")
    if not url:
        return {"ok": False, "reason": NOT_CONFIGURED}
    try:
        import html as _html
        raw = _get(url, timeout=(10, timeout)).text
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
                "url": url}
    except Exception as e:  # network or layout change
        return {"ok": False, "reason": repr(e)}


def _shape_source(spec):
    """Where an outbreak's zone outlines live: its own shapefile, or that of the profile a table borrows from."""
    if spec.adapter["type"] == "table":
        src = outbreak.load(spec.adapter["boundaries"]["from"])
        return CACHE / src.adapter["cache_dir"], src
    return CACHE / spec.adapter["cache_dir"], spec


def _shape_stamp(repo: Path, spec=None) -> str:
    """Identity of the health-zone shapefile, so cached outlines follow a refreshed shapefile."""
    f = repo / f"{(spec or outbreak.default()).adapter['shapes']}.shp"
    st = f.stat()
    return f"{int(st.st_mtime)}_{st.st_size}"


def display_geometry(zones: gpd.GeoDataFrame, repo: Path | None = None, tolerance: float = DISPLAY_TOLERANCE,
                     spec=None) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Zone and province outlines for drawing: simplified, computed once, cached on disk.

    Two costs sat in every single advice. Merging the health zones into 26 province outlines takes
    about 50 seconds, and drawing a few thousand full-resolution polygons at 300 dpi another 25;
    both depend only on the shapefile, which is refreshed at most monthly. So they are computed on
    the first run after a shapefile change and read from the cache afterwards.

    Only what is drawn is simplified. `geo` decides which health zone a place falls in, which zones
    border it and how far the nearest active zone is, and those answers must come from the exact
    boundaries: `zones` itself is never touched here.

    The file names carry the outbreak id, so two outbreaks never clean up each other's outlines.
    """
    spec = spec or outbreak.default()
    own_repo, shp_spec = _shape_source(spec)
    repo = Path(repo or own_repo)
    tag = f"{spec.id}_{tolerance:g}_{_shape_stamp(repo, shp_spec)}"
    stale = re.compile(rf"display_(zones|prov)_({re.escape(spec.id)}_|\d)")   # \d: names from before 0.3
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
            if stale.match(f.name):
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


def _get(url: str, *, timeout=(10, 30), **kw) -> requests.Response:
    """GET that tries again after a timeout, a dropped connection or a busy server (429, 5xx).

    A source read on every run must not drop out of an advice for one slow answer (WHO, 2026-10-07:
    read timeout). A 4xx other than 429 is an answer, not a hiccup, and is not retried.
    """
    for wait in (*RETRY_WAITS, None):
        try:
            r = requests.get(url, timeout=timeout, **kw)
            if wait is None or not (r.status_code == 429 or r.status_code >= 500):
                return r
        except (requests.Timeout, requests.ConnectionError):
            if wait is None:
                raise
        time.sleep(wait)
    raise AssertionError("unreachable")


def _who_last(spec_id: str, item: dict | None = None) -> dict | None:
    """The last WHO item read for this outbreak: written after every live read, read when WHO is unreachable."""
    try:
        seen = json.loads(WHO_LAST.read_text(encoding="utf-8"))
    except Exception:
        seen = {}
    if item is None:
        return seen.get(spec_id)
    seen[spec_id] = {**item, "read_on": date.today().isoformat()}
    try:
        WHO_LAST.parent.mkdir(parents=True, exist_ok=True)
        WHO_LAST.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
    return None


def who_snapshot(timeout=(10, 30), top: int = 20, spec=None) -> dict:
    """Most recent WHO Disease Outbreak News item about this outbreak (title patterns in the profile).

    Read from the DON JSON API, not the page: the page is rendered client-side and a regex over its
    HTML finds nothing. Only the three fields used are asked for: with the full text of every item
    the answer was 600 kB and timed out (2026-10-07); now it is a few kB. A headline and a date, not
    figures; the counts that carry the advice come from INSP.

    Fails soft like the ECDC check, because a source being unreachable must make itself visible in
    the QA block, never stop an advice. When WHO cannot be reached, the item of the last live read is
    used, marked `from_cache` with the day it was read: the web step still looks for a newer one.
    """
    sp = spec or outbreak.default()
    who = sp.sources.get("who") or {}
    if not who.get("title"):
        return {"ok": False, "reason": NOT_CONFIGURED, "url": WHO_DON_URL}
    try:
        r = _get(WHO_DON_API, timeout=timeout, headers={"User-Agent": UA},
                 params={"$orderby": "PublicationDateAndTime desc", "$top": str(top),
                         "$select": "Title,PublicationDateAndTime,ItemDefaultUrl"})
        r.raise_for_status()
        items = r.json().get("value", [])
        for it in items:
            title = str(it.get("Title") or "")
            if all(re.search(p, title, re.I) for p in who["title"]):
                day = str(it.get("PublicationDateAndTime") or "")[:10]
                link = str(it.get("ItemDefaultUrl") or "").strip("/")
                found = {"ok": True, "date": day or None, "item": title,
                         "url": f"https://www.who.int/emergencies/disease-outbreak-news/item/{link}"
                                if link else WHO_DON_URL}
                _who_last(sp.id, found)
                return {**found, "days_old": _days_old(day)}
        # read fine, nothing about this outbreak: not the same as a source that could not be reached
        return {"ok": False, "reason": f"no {who.get('label', 'matching')} item in the last {len(items)} DON entries",
                "url": WHO_DON_URL, "none_found": True}
    except Exception as e:   # network, API change or unparseable payload
        last = _who_last(sp.id)
        if last and last.get("ok"):
            return {**last, "days_old": _days_old(last.get("date")), "from_cache": True, "reason": repr(e)}
        return {"ok": False, "reason": repr(e), "url": WHO_DON_URL}


def _days_old(day: str | None) -> int | None:
    return (date.today() - date.fromisoformat(day)).days if day else None


def sources_snapshot(asof: str | None = None, spec=None) -> dict:
    """The sources checked on every run, next to the INSP figures.

    ECDC and WHO are read here; FOD and CDC are prose pages that resist parsing, so they are checked
    in the web step (prompts/web.md) and kept in the country registry with the date they were verified.
    """
    if asof:
        return {"ecdc": {"ok": False, "reason": "asof run"}, "who": {"ok": False, "reason": "asof run"}}
    return {"ecdc": ecdc_snapshot(spec=spec), "who": who_snapshot(spec=spec)}
