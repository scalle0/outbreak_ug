"""Regression tests: the package must reproduce the manual advices of August-September 2026.

Frozen with --asof so they stay valid while the outbreak data keep moving.
Run: pytest -q   (needs network once to fetch the INRB repository into the cache)
"""
from pathlib import Path

import pytest
import yaml

from dienstreis import data, mail, risk

EX = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def ob_0822():
    return data.load(asof="2026-08-22")


@pytest.fixture(scope="module")
def ob_0919():
    return data.load(asof="2026-09-19")


def cats(ob, name):
    return "".join(r.category for r in risk.assess(yaml.safe_load(open(EX / f"{name}.yaml")), ob))


def test_zone_sum_matches_national(ob_0822, ob_0919):
    assert ob_0822.checks["zone_sum"] == ob_0822.checks["national_at_asof"] == 5514
    assert ob_0919.checks["zone_sum"] == ob_0919.checks["national_at_asof"] == 7672
    assert not ob_0919.unmatched


def test_report_figures_0822(ob_0822):
    # original report of 26 Aug: Tshopo 15 cases in 7 zones, 13 in Kisangani city, 57 zones, 6 provinces
    z = ob_0822.zones
    t = z[(z.PROVINCE == "Tshopo") & (z.cases > 0)]
    assert int(t.cases.sum()) == 15 and len(t) == 7
    city = ["Makiso Kisangani", "Kabondo", "Mangobo", "Lubunga (Tshopo)", "Tshopo"]
    assert int(t[t.Nom.isin(city)].cases.sum()) == 13
    assert ob_0822.checks["zones_with_cases"] == 57 and ob_0822.checks["provinces_with_cases"] == 6


def test_kisangani_short_stay_0822(ob_0822):
    assert cats(ob_0822, "voorbeeld_kisangani_kortverblijf") == "XXXFAF"


def test_hautkatanga_no_objection(ob_0919):
    rs = risk.assess(yaml.safe_load(open(EX / "voorbeeld_hautkatanga.yaml")), ob_0919)
    assert "".join(r.category for r in rs) == "XFF"
    assert risk.overall(rs).startswith("geen")
    assert min(r.nearest_active["km"] for r in rs if r.nearest_active) > 1000


def test_yangambi_via_kisangani(ob_0919):
    rs = risk.assess(yaml.safe_load(open(EX / "voorbeeld_yangambi_via_kisangani.yaml")), ob_0919)
    assert "".join(r.category for r in rs) == "XFFFAEAF"
    yang = [r for r in rs if r.place == "Yangambi"][0]
    assert yang.zone == "Isangi"          # Yangambi lies in health zone Isangi, not a zone of its own
    assert "formeel" in (yang.fod or "")


def test_family_stay_hautuele(ob_0919):
    rs = risk.assess(yaml.safe_load(open(EX / "voorbeeld_familieverblijf_hautuele.yaml")), ob_0919)
    assert "".join(r.category for r in rs) == "FAAD"
    durba = rs[-1]
    assert durba.zone == "Watsa"
    assert {"Mongbwalu", "Damas", "Mambasa"} <= {n["zone"] for n in durba.neighbours_active}
    assert any("familie" in f for f in durba.flags)


def test_text_checks():
    assert mail.check_text("Beste An,\n\nalles goed.") == []
    assert "em-dash aanwezig" in mail.check_text("a \u2014 b")
    assert any("CLAUDE" in i for i in mail.check_text("[[CLAUDE: x]]"))
