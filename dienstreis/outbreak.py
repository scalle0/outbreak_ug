"""Outbreak profiles: everything the code applies to one outbreak, read from outbreaks/<id>/.

The code knows how to place a stop in a zone, classify it against the zones with cases, draw a
map and check a letter. It does not know which disease it is looking at. That lives in the
profile: where the figures come from, the windows that set the categories, the verdict per
category, the flag and condition texts, the sources, the texts on the figures, and the passages
of the prompts that are about this disease. Those are clinical judgements. The code applies them
and invents none, so a new outbreak is a new folder, and a changed judgement is a changed line in
a file that can be read.

    outbreaks/<id>/outbreak.yaml       the profile (see ebola_cod_2026 for every key, with comments)
    outbreaks/<id>/prompt.md           prompt passages, spliced in where a prompt says {{uitbraak:<name>}}
    outbreaks/<id>/zone_overrides.csv  observed zone spellings -> shapefile names (inrb adapter)

Called `spec` in the code, because `profile` already means the traveller's profile.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).parent / "outbreaks"
DEFAULT = "ebola_cod_2026"
LEVELS = ("afraden", "voorwaardelijk", "geen_bezwaar")        # strictest first
CATEGORIES = tuple("ABCDEFX")
ADAPTERS = ("inrb",)
REQUIRED = ("id", "active", "name_nl", "countries", "match_terms", "unit", "windows", "metric_epsg",
            "adapter", "categories", "overall", "outside_note", "flags", "conditions", "sources", "figures")
_SECTION = re.compile(r"^<!-- uitbraak:(\w+) -->\n", re.M)
_SLOT = re.compile(r"\{\{uitbraak:(\w+)\}\}")


class ProfileError(ValueError):
    pass


def _check(cfg: dict, path: Path) -> list[str]:
    """Every problem with a profile, so a broken one is refused whole instead of failing mid-advice."""
    miss = [k for k in REQUIRED if k not in cfg]
    if miss:
        return [f"ontbrekende sleutel(s): {', '.join(miss)}"]
    issues = []
    if cfg["id"] != path.parent.name:
        issues.append(f"id '{cfg['id']}' verschilt van de mapnaam '{path.parent.name}'")
    cats = cfg["categories"] or {}
    for c in CATEGORIES:
        v = cats.get(c)
        if not isinstance(v, dict) or not all(v.get(k) for k in ("label", "verdict", "level")):
            issues.append(f"categorie {c}: geef label, verdict en level")
        elif v["level"] not in LEVELS:
            issues.append(f"categorie {c}: onbekend level '{v['level']}' (kies uit {', '.join(LEVELS)})")
    miss = [lv for lv in LEVELS if not (cfg["overall"] or {}).get(lv)]
    if miss:
        issues.append(f"overall: geef een tekst voor {', '.join(miss)}")
    w = cfg["windows"] or {}
    if not (isinstance(w.get("active"), int) and isinstance(w.get("clear"), int) and 0 < w["active"] < w["clear"]):
        issues.append("windows: active en clear zijn gehele dagen, active kleiner dan clear")
    if not (cfg["sources"] or {}).get("national"):
        issues.append("sources.national: hoe de nationale cijfers heten in de mail (bv. INSP)")
    if (cfg["adapter"] or {}).get("type") not in ADAPTERS:
        issues.append(f"adapter.type: kies uit {', '.join(ADAPTERS)}")
    if not isinstance(cfg["metric_epsg"], int):
        issues.append("metric_epsg: een EPSG-code met meters als eenheid")
    return issues


def _sections(path: Path) -> dict[str, str]:
    """prompt.md -> {name: text}. A section runs from its marker to the next; trailing blank lines go."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    parts = _SECTION.split(text)            # [preamble, name1, body1, name2, body2, ...]
    return {parts[i]: parts[i + 1].rstrip("\n") for i in range(1, len(parts), 2)}


class OutbreakSpec:
    """One outbreak profile, read and checked once."""

    def __init__(self, folder: Path):
        path = folder / "outbreak.yaml"
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        issues = _check(cfg, path)
        if issues:
            raise ProfileError(f"{path} is niet bruikbaar: " + "; ".join(issues))
        self.dir, self.cfg = folder, cfg
        self.id: str = cfg["id"]
        self.name: str = cfg["name_nl"]
        self.active: bool = bool(cfg["active"])
        self.countries: list[str] = list(cfg["countries"])
        self.match_terms: list[str] = list(cfg["match_terms"])
        self.unit: str = cfg["unit"]
        self.windows: dict[str, int] = dict(cfg["windows"])
        self.metric_epsg: int = cfg["metric_epsg"]
        self.adapter: dict = cfg["adapter"]
        self.categories: dict[str, dict] = cfg["categories"]
        self.overall: dict[str, str] = cfg["overall"]
        self.outside_note: str = cfg["outside_note"]
        self.flags: dict = cfg["flags"]
        self.conditions: list[str] = list(cfg["conditions"])
        self.sources: dict = cfg["sources"]
        self.figures: dict[str, str] = cfg["figures"]
        self.sections = _sections(folder / "prompt.md")

    def __repr__(self) -> str:
        return f"OutbreakSpec({self.id})"

    def verdict(self, cat: str) -> str:
        return self.categories[cat]["verdict"]

    def label(self, cat: str) -> str:
        return self.categories[cat]["label"]

    def level(self, cat: str) -> str:
        return self.categories[cat]["level"]

    def file(self, name: str) -> Path:
        return self.dir / name


def ids() -> list[str]:
    return sorted(p.parent.name for p in ROOT.glob("*/outbreak.yaml"))


@lru_cache(maxsize=None)
def load(id: str | None = None) -> OutbreakSpec:
    name = id or DEFAULT
    folder = ROOT / name
    if not (folder / "outbreak.yaml").exists():
        raise ProfileError(f"onbekende uitbraak '{name}' (bekend: {', '.join(ids()) or 'geen'})")
    return OutbreakSpec(folder)


def default() -> OutbreakSpec:
    return load(DEFAULT)


def active() -> list[OutbreakSpec]:
    return [s for s in (load(i) for i in ids()) if s.active]


def fill(text: str, specs: list[OutbreakSpec] | None = None) -> str:
    """Put each profile's passage where a prompt says {{uitbraak:<name>}}."""
    specs = specs or [default()]

    def one(m: re.Match) -> str:
        found = [s.sections[m.group(1)] for s in specs if m.group(1) in s.sections]
        if not found:
            raise ProfileError(f"geen passage '{m.group(1)}' in prompt.md van {', '.join(s.id for s in specs)}")
        return "\n\n".join(found)
    return _SLOT.sub(one, text)
