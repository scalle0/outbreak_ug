"""The reply skeleton writes names and dates the way a Dutch letter does. No network, no model."""
from datetime import date

from dienstreis import mail, risk

EPI = {"weekly_cases_last4_full_weeks": {"31-08": 569, "07-09": 586, "14-09": 586, "21-09": 572},
       "last_total": 7672, "last_deaths": 3699, "cfr": 48.2}


def _stop(**kw):
    base = dict(place="Kisangani", start=date(2026, 12, 6), end=date(2026, 12, 13), nights=7, lodging=None,
                transit_only=False, lat=0.5, lon=25.2, country="COD", zone="Makiso Kisangani",
                province="Tshopo", cases=20, deaths=9, new14=10, days_since_last=0.0, category="A")
    return risk.StopRisk(**{**base, **kw})


def test_a_zone_name_keeps_its_capitals():
    """'.capitalize()' lowercased everything after the first letter: 'Gezondheidszone makiso kisangani'."""
    txt = mail.leg_paragraph(1, _stop())
    assert "Gezondheidszone Makiso Kisangani telt 20" in txt


def test_every_category_sentence_keeps_the_capitals():
    for cat, extra in (("B", {"days_since_last": 30.0}), ("D", {"cases": 0, "neighbours_active": [
            {"zone": "Mangobo", "cases": 4}]}), ("E", {"cases": 0})):
        assert "Gezondheidszone Makiso Kisangani" in mail.leg_paragraph(1, _stop(category=cat, **extra))


def test_ecdc_month_is_written_in_dutch():
    ecdc = {"ok": True, "cases": 7773, "deaths": 3759, "data_until": "19 September"}
    txt = mail.skeleton({"traveller": "Reiziger T"}, [_stop()], EPI, ecdc, redirect=False)
    assert "ECDC, data tot 19 september" in txt and "September" not in txt


def test_nl_months_leaves_dutch_and_other_words_alone():
    assert mail.nl_months("21 September, 3 mei, May 4") == "21 september, 3 mei, mei 4"
    assert mail.nl_months("Mayombe") == "Mayombe"
