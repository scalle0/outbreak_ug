"""Country source registry: what is the same about a country whatever the disease.

    countries/<ISO3>.yaml          FOD pages and advisory, CDC level per outbreak, the pretravel
                                   line, trusted government sources and news outlets, the land
                                   neighbours, and measures at the borders tied to an outbreak
    countries/_international.yaml  bodies that apply to every country (WHO, ECDC, CDC, ...)

So a new disease in a known country, or a known disease in a new country, does not start the
search for sources again. The web step reads the registry, checks it against the live pages and
offers changes and new sources; what you accept is written to a local copy
(~/.config/dienstreis/countries/<ISO3>.yaml), which wins while it is verified more recently than
the file in the package. `verified: null` means nobody has checked that country yet.

The advisories table of 0.2 (~/.config/dienstreis/advisories.yaml, DRC provinces only) is still
read while it is newer than the registry: its FOD and CDC levels for the DRC, and its country
notes as measures tied to the Ebola outbreak.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import yaml

from . import outbreak

ROOT = Path(__file__).parent / "countries"
LOCAL = Path(os.environ.get("DIENSTREIS_COUNTRIES", Path.home() / ".config" / "dienstreis" / "countries"))
LEGACY = Path(os.environ.get("DIENSTREIS_ADVISORIES", Path.home() / ".config" / "dienstreis" / "advisories.yaml"))
LEGACY_OUTBREAK = "ebola_cod_2026"      # the only outbreak the 0.2 table knew
STALE_DAYS = 14
FOD_LEVELS = ("formeel_afgeraden", "niet_essentieel_afgeraden")
KEYS = ("iso3", "name_nl", "name_en", "letter_nl", "neighbours", "verified", "fod", "cdc", "pretravel",
        "government", "news", "measures")


def _read(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _newer(a: dict, b: dict) -> bool:
    return str(a.get("verified") or "") > str(b.get("verified") or "")


def load(iso3: str | None) -> dict | None:
    """The registry entry for a country, or None if the registry does not know it."""
    if not iso3:
        return None
    pkg, loc = ROOT / f"{iso3}.yaml", LOCAL / f"{iso3}.yaml"
    c, source = (_read(pkg), "package") if pkg.exists() else (None, None)
    if loc.exists():
        mine = _read(loc)
        if c is None or _newer(mine, c):
            c, source = mine, str(loc)
    if c is None:
        return None
    return _legacy(iso3, {**c, "_source": source})


def _legacy(iso3: str, c: dict) -> dict:
    """Apply the 0.2 advisories table where it is newer than the registry entry."""
    if not LEGACY.exists():
        return c
    old = _read(LEGACY)
    if not _newer(old, c):
        return c
    c = dict(c)
    if iso3 == "COD":
        d, prov = old.get("default") or {}, old.get("provinces") or {}
        c["fod"] = {**(c.get("fod") or {}),
                    "default": {"level": d.get("fod"), "reason": d.get("fod_reason")},
                    "regions": {p: {"level": v.get("fod"), "reason": v.get("fod_reason")} for p, v in prov.items()}}
        c["cdc"] = {**(c.get("cdc") or {}),
                    LEGACY_OUTBREAK: {"default": d.get("cdc"), "regions": {p: v.get("cdc") for p, v in prov.items()}}}
        c["verified"], c["_source"] = old.get("verified"), str(LEGACY)
    note = ((old.get("countries") or {}).get(iso3) or {}).get("note")
    if note:
        c["measures"] = [m for m in c.get("measures") or [] if m.get("outbreak") != LEGACY_OUTBREAK] + [
            {"outbreak": LEGACY_OUTBREAK, "text": note, "verified": old.get("verified"), "source": str(LEGACY)}]
    return c


def international() -> dict:
    return _read(ROOT / "_international.yaml")


def excluded(url: str | None) -> bool:
    """A source the clinician does not want used (`excluded` in _international.yaml), by domain."""
    from urllib.parse import urlparse
    host = (urlparse(url or "").hostname or "").lower()
    return any(host == x["domain"] or host.endswith("." + x["domain"])
               for x in international().get("excluded") or [])


def ids() -> list[str]:
    return sorted(p.stem for p in ROOT.glob("*.yaml") if not p.stem.startswith("_"))


# ---------------------------------------------------------------- reading an entry
def fod(c: dict | None, region: str | None = None) -> tuple[str | None, str | None]:
    """FOD level and reason for a region (province), or for the whole country."""
    f = (c or {}).get("fod") or {}
    d = ((f.get("regions") or {}).get(region) if region else None) or f.get("default")
    return (d.get("level"), d.get("reason")) if d else (None, None)


def cdc(c: dict | None, outbreak_id: str, region: str | None = None) -> int | None:
    x = ((c or {}).get("cdc") or {}).get(outbreak_id) or {}
    return ((x.get("regions") or {}).get(region) if region else None) or x.get("default")


def measures(c: dict | None, outbreak_id: str) -> list[dict]:
    return [m for m in (c or {}).get("measures") or [] if m.get("outbreak") == outbreak_id]


def neighbours(iso3: str | None) -> list[str]:
    return list((load(iso3) or {}).get("neighbours") or [])


def letter(iso3: str | None) -> str:
    """How a letter names the country: 'de DRC'; the code itself when the registry does not know it."""
    return (load(iso3) or {}).get("letter_nl") or (iso3 or "")


def age_days(c: dict | None, today: date | None = None) -> int | None:
    """Days since the entry was verified; None when it never was."""
    v = (c or {}).get("verified")
    if not v:
        return None
    v = v if isinstance(v, date) else date.fromisoformat(str(v))
    return ((today or date.today()) - v).days


def for_prompt(c: dict) -> dict:
    """What the web step needs to check an entry against the live pages."""
    return {k: c.get(k) for k in ("iso3", "name_nl", "verified", "fod", "cdc", "government", "news", "measures")}


# ---------------------------------------------------------------- checking and writing
def check(c: dict, iso3: str) -> list[str]:
    """Problems with a registry entry, all at once."""
    miss = [k for k in KEYS if k not in c]
    if miss:
        return [f"{iso3}: ontbrekende sleutel(s): {', '.join(miss)}"]
    issues = []
    if c["iso3"] != iso3:
        issues.append(f"{iso3}: iso3 '{c['iso3']}' verschilt van de bestandsnaam")
    f = c["fod"] or {}
    for where, d in [("default", f.get("default"))] + list((f.get("regions") or {}).items()):
        if d and d.get("level") not in FOD_LEVELS:
            issues.append(f"{iso3}: fod {where}: onbekend niveau '{d.get('level')}' (kies uit {', '.join(FOD_LEVELS)})")
    for ob, x in (c["cdc"] or {}).items():
        for where, lv in [("default", (x or {}).get("default"))] + list(((x or {}).get("regions") or {}).items()):
            if lv is not None and lv not in (1, 2, 3, 4):
                issues.append(f"{iso3}: cdc {ob} {where}: niveau {lv} (1 tot 4)")
    for m in c["measures"] or []:
        if not (m.get("outbreak") and m.get("text")):
            issues.append(f"{iso3}: een maatregel vraagt outbreak en text")
    return issues


def blank(iso3: str) -> dict:
    """A new entry for a country the registry does not know yet: names and land neighbours from the map.

    The neighbours matter: without them an outbreak in this country would never reach a trip next door.
    """
    try:
        from . import route
        known = route.describe(iso3)
    except Exception:                    # no map in the cache and no network: the code will do
        known = {}
    name = known.get("name_nl") or iso3
    return {"iso3": iso3, "name_nl": name, "name_en": known.get("name_en") or iso3, "letter_nl": name,
            "neighbours": known.get("neighbours") or [], "verified": None,
            "fod": {"pages": [], "default": None, "regions": {}}, "cdc": {}, "pretravel": None,
            "government": [], "news": [], "measures": []}


def save_local(c: dict) -> Path:
    """Write an entry to the local registry; it wins over the package while it is verified more recently."""
    LOCAL.mkdir(parents=True, exist_ok=True)
    p = LOCAL / f"{c['iso3']}.yaml"
    p.write_text(yaml.safe_dump({k: v for k, v in c.items() if not k.startswith("_")},
                                allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def apply_web(webd: dict, outbreak_id: str, today: date | None = None) -> dict[str, dict]:
    """The registry entries as they would be with the web step's findings: advisories, measures, sources.

    Every country whose advisories the web step checked gets today's date as `verified`; a country
    it only found a measure or a source for keeps its date. Nothing is written here.
    """
    today = today or date.today()
    out: dict[str, dict] = {}
    ids = set(outbreak.ids())

    def which(x: dict) -> str:
        """The profile a finding belongs to: a known id, else the outbreak of this run."""
        return x["outbreak"] if x.get("outbreak") in ids else outbreak_id

    def entry(iso3: str) -> dict:
        if iso3 not in out:
            c = load(iso3) or blank(iso3)
            out[iso3] = {k: v for k, v in c.items() if not k.startswith("_")}
        return out[iso3]

    for a in webd.get("advisories", []):
        if not a.get("country"):
            continue
        c, region = entry(a["country"]), a.get("region")
        f = c.setdefault("fod", {})
        f.setdefault("regions", {})
        if a.get("fod"):
            level = {"level": a["fod"], "reason": a.get("fod_reason")}
            if region:
                f["regions"][region] = level
            else:
                f["default"] = level
        if a.get("cdc") is not None:
            x = c.setdefault("cdc", {}).setdefault(which(a), {"default": None, "regions": {}})
            if region:
                x.setdefault("regions", {})[region] = a["cdc"]
            else:
                x["default"] = a["cdc"]
        c["verified"] = today
    found: dict[tuple[str, str], list[dict]] = {}
    for m in webd.get("measures", []):
        if m.get("country") and m.get("text"):
            found.setdefault((m["country"], which(m)), []).append(m)
    for (iso3, ob), ms in found.items():
        if not any(m.get("changed") for m in ms):
            continue
        c = entry(iso3)
        c["measures"] = [m for m in c.get("measures") or [] if m.get("outbreak") != ob] + [
            {"outbreak": ob, "text": m["text"], "verified": m.get("date") or today, "source": m.get("source"),
             **({"about": m.get("about") or m.get("outbreak")} if (m.get("about") or m.get("outbreak")) not in (None, ob)
                else {})}
            for m in ms]
    for s in webd.get("sources", []):
        if not (s.get("country") and s.get("url")) or excluded(s["url"]):
            continue
        c = entry(s["country"])
        if s.get("kind") == "fod":
            pages = c.setdefault("fod", {}).setdefault("pages", [])
            if s["url"] not in {p[1] for p in pages}:
                pages.append([s.get("name") or "FOD Buitenlandse Zaken", s["url"]])
        else:
            key = "government" if s.get("kind") == "overheid" else "news"
            lst = c.setdefault(key, [])
            if s["url"] not in {x.get("url") for x in lst}:
                lst.append({"name": s.get("name"), "url": s["url"], **({"what": s["why"]} if s.get("why") else {})})
    return out
