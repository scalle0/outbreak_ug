"""Golden files: the deterministic output of the Ebola analysis, pinned before it became a profile.

Taken on c022d2e, before Ebola moved into `dienstreis/outbreaks/` (F-010), so that refactor can
show it changed nothing: the risk table, the reply skeleton, the sources, the summary and the
prompts of the three model steps must come out as they did. Data dates are frozen (asof), the
advisories table is frozen (tests/golden/advisories.yaml) and the data cache is not refreshed
during the run, so the files stay valid while the outbreak and the live advisories keep moving.

Line endings are normalised (git turns LF into CRLF on Windows checkouts); nothing else is.
What depends on the day the test runs (`vandaag`, the age of the advisories table) or on the
machine (output paths) is taken out before comparing. So are the two label counts of the map
(`map_label_overlaps`, `map_labels_clipped`): label placement differs slightly between two runs of
the same code on the same data (seen 2026-09-25, before and after the refactor alike), so they are
checked as counts, not pinned.

Regenerate only on purpose, after reading the diff:
    DIENSTREIS_GOLDEN_WRITE=1 pytest tests/test_golden.py
"""
import difflib
import json
import os
import re
from pathlib import Path

import pytest
import yaml

from dienstreis import advies, archive, countries, data, llm, log, outbreak, pipeline

HERE = Path(__file__).parent
GOLDEN = HERE / "golden"
EX = HERE.parent / "examples"
WRITE = os.environ.get("DIENSTREIS_GOLDEN_WRITE") == "1"

# the same data dates as test_regression.py: the original advices of August and September 2026
EXAMPLES = {"voorbeeld_kisangani_kortverblijf": "2026-08-22",
            "voorbeeld_hautkatanga": "2026-09-19",
            "voorbeeld_yangambi_via_kisangani": "2026-09-19",
            "voorbeeld_familieverblijf_hautuele": "2026-09-19"}
FILES = ["risk.csv", "reply_skeleton.txt", "sources.txt", "summary.json"]
LABEL_COUNTS = ("map_label_overlaps", "map_labels_clipped")


def _text(b: bytes | str) -> str:
    s = b.decode("utf-8") if isinstance(b, bytes) else b
    return s.replace("\r\n", "\n")


def _check(name: str, got: str) -> None:
    p = GOLDEN / name
    if WRITE:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(got, encoding="utf-8", newline="\n")
        return
    assert p.exists(), f"{p} ontbreekt; maak de goldens met DIENSTREIS_GOLDEN_WRITE=1"
    want = _text(p.read_bytes())
    if got != want:
        diff = difflib.unified_diff(want.splitlines(), got.splitlines(), "golden", "nu", lineterm="", n=1)
        pytest.fail(f"{name} wijkt af van de golden:\n" + "\n".join(list(diff)[:60]), pytrace=False)


def _norm_summary(raw: str) -> str:
    s = json.loads(raw)
    s.pop("files", None)                               # absolute paths of this run's folder
    for k in ("map", "epicurve"):
        s[k] = Path(s[k]).name
    s["epi"]["path"] = Path(s["epi"]["path"]).name
    s["attachments"] = [Path(a).name for a in s.get("attachments", [])]
    for k in ("advisories_verified_days_ago", "advisories_stale", "advisories_source"):
        s["qa"].pop(k, None)                           # depend on the day the test runs
    for k in LABEL_COUNTS:                             # depend on where the labels land
        assert isinstance(s["qa"].pop(k), int)
    return json.dumps(s, ensure_ascii=False, indent=1) + "\n"


def _norm_prompt(p: str) -> str:
    p = _text(p)
    p = re.sub(r"<vandaag>\n[^\n]*\n</vandaag>", "<vandaag>\nVANDAAG\n</vandaag>", p)
    p = re.sub(r'"advisories_verified_days_ago": [^,\n]*', '"advisories_verified_days_ago": X', p)
    p = re.sub(r'"advisories_source": ("[^"]*"|\{[^}]*\})', '"advisories_source": "X"', p)
    p = re.sub(r'"path": "[^"]*?([^"\\/]+)"', r'"path": "\1"', p)     # the run's temp folder
    for k in LABEL_COUNTS:
        p = re.sub(rf'"{k}": \d+', f'"{k}": X', p)
    return p


@pytest.fixture(scope="module")
def frozen():
    """Frozen advisories and a data cache that is read, never refreshed, for the whole module.

    The advisories are frozen through the 0.2 table (tests/golden/advisories.yaml, verified 2099), so
    this also keeps reading that old local file working; no local country registry is used.
    """
    with pytest.MonkeyPatch.context() as mp:
        # the goldens pin the Ebola output: routing is tested elsewhere (test_route, test_multi)
        mp.setattr(outbreak, "active", lambda: [outbreak.default()])
        mp.setattr(countries, "LEGACY", GOLDEN / "advisories.yaml")
        mp.setattr(countries, "LOCAL", GOLDEN / "geen_lokaal_register")
        mp.setattr(data, "_stale", lambda *a, **k: False)
        yield mp


@pytest.fixture(scope="module")
def analysed(frozen, tmp_path_factory):
    out = {}
    for name, asof in EXAMPLES.items():
        trip = yaml.safe_load(open(EX / f"{name}.yaml", encoding="utf-8"))
        d = tmp_path_factory.mktemp(name)
        pipeline.analyse(trip, d, asof=asof)
        out[name] = d
    return out


@pytest.mark.parametrize("name", list(EXAMPLES))
@pytest.mark.parametrize("fname", FILES)
def test_analysis_output_unchanged(analysed, name, fname):
    got = _text((analysed[name] / fname).read_bytes())
    if fname == "summary.json":
        got = _norm_summary(got)
    _check(f"{name}/{fname}", got)


@pytest.mark.parametrize("step", ["stops", "web", "reply"])
def test_step_instructions_unchanged(step):
    _check(f"prompts/{step}.md", _text(llm.build_prompt(step, {})))


REQ = """Beste Steven,

Nieuwe aanvraag:
28/11 - 5/12 Kinshasa
6/12-13/12 Kisangani - Tshopo

Graag jouw advies. Geldt de 21-dagen regel?

An

Van: Iemand
REISINFO
Bestemming: Kisangani
Accommodatie: hotel
"""
STOPS = {"traveller": "Reiziger T", "note": "veldwerk", "profile": {"lodging": "hotel", "healthcare_work": False},
         "review_on": "2026-11-20",
         "stops": [{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-05"},
                   {"place": "Kisangani", "from": "2026-12-06", "to": "2026-12-13"}],
         "questions_from_an": ["Geldt de 21-dagenregel?"], "contradictions": [], "missing_info": ["vervoer"]}
WEB = {"advisories": [], "news": [{"date": "2026-09-18", "item": "nieuws", "url": "https://example.org"}],
       "who": {"latest_don": "2026-09-10"}}
REPLY = ("Beste An,\n\nKinshasa kan, Kisangani raad ik momenteel af.\n\n1. Kinshasa: geen bezwaar.\n"
         "2. Kisangani: af te raden.\n\nMet vriendelijke groet,\nSteven Callens")


@pytest.fixture(scope="module")
def advice_run(frozen, tmp_path_factory):
    """One whole `advies` run with a fake model: what each step was actually given."""
    tmp = tmp_path_factory.mktemp("advies")
    frozen.setattr(advies, "CONTEXT", tmp / "context.md")
    frozen.setattr(log, "LOG", tmp / "log.csv")
    frozen.setattr(archive, "ARCHIVE", tmp / "adviezen")
    (tmp / "context.md").write_text("- 2026-09-10: Kisangani-luik Hubeau afgeraden\n", encoding="utf-8")
    req = tmp / "aanvraag.txt"
    req.write_text(REQ, encoding="utf-8")
    fake = llm.Fake({"stops": STOPS, "web": WEB, "reply": {"reply": REPLY, "suggestions": []}})
    advies.run_advies(str(req), out=str(tmp / "out"), yes=True, asof="2026-09-19",
                      open_browser=False, llm_backend=fake)
    return fake.prompts


@pytest.mark.parametrize("step", ["stops", "web", "reply"])
def test_step_inputs_unchanged(advice_run, step):
    assert len(advice_run[step]) == 1
    _check(f"run/prompt_{step}.md", _norm_prompt(advice_run[step][0]))
