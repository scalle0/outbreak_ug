"""The mpox profile for the DRC on its seeded table (WHO mpox dashboard, data to 2026-08-16).

Needs the INRB zone shapefile in the data cache, like the regression tests; no network otherwise.
The table in the package is frozen in git, and the conftest keeps a local copy out of the test.
"""
import yaml
from pathlib import Path

import pytest

from dienstreis import data, mail, outbreak, risk

EX = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def mpox():
    spec = outbreak.load("mpox_cod_2026")
    return spec, data.load(spec=spec, asof="2026-08-16")


def test_the_profile_is_confirmed_and_counts_all_cases():
    s = outbreak.load("mpox_cod_2026")
    assert s.active and s.adapter["level"] == "admin2" and s.adapter["stale_days"] == 60
    assert s.case_words["cases"] == "vermoede en bevestigde gevallen" and s.recent == 42
    assert s.level("A") == "voorwaardelijk" and all(s.level(c) == "geen_bezwaar" for c in "BCDEF")


def test_the_seeded_table_matches_the_who_export(mpox):
    spec, ob = mpox
    assert ob.unmatched == ["Dingila"]                  # no zone of its own in the INRB shapefile
    assert ob.checks["zones_with_cases"] == 199 and ob.checks["zone_sum_matches_national"] is None
    z = ob.zones.set_index("Nom")
    assert (z.loc["Makiso Kisangani", "cases"], z.loc["Makiso Kisangani", "new14"]) == (857, 8)
    assert int((ob.zones.days_since_last <= 21).sum()) == 148


def test_the_example_trips_under_mpox(mpox):
    spec, ob = mpox
    for name, cats in (("voorbeeld_familieverblijf_hautuele", "DADA"), ("voorbeeld_kisangani_kortverblijf", "XXXDAD")):
        rs = risk.assess(yaml.safe_load(open(EX / f"{name}.yaml", encoding="utf-8")), ob, spec)
        assert "".join(r.category for r in rs) == cats
        assert risk.overall(rs).startswith("voorwaardelijk")


def test_the_letter_says_what_the_figures_count(mpox):
    spec, ob = mpox
    rs = risk.assess(yaml.safe_load(open(EX / "voorbeeld_familieverblijf_hautuele.yaml", encoding="utf-8")), ob, spec)
    kis = mail.leg_paragraph(2, rs[1])
    assert "voorwaardelijk. Gezondheidszone Makiso Kisangani telt 857 vermoede en bevestigde gevallen" in kis
    assert "in de laatste 42 dagen" in kis and "bevestigde gevallen (" not in kis.replace("vermoede en bevestigde", "")
    assert mail.leg_paragraph(1, rs[0]).startswith("1. Kinshasa (28 november tot 6 december): geen bezwaar.")
