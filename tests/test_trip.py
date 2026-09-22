"""Itinerary checks: the boundary between what the model wrote and what the analysis calculates.

No network, no model. Every case here is a way a wrong itinerary used to reach `risk.assess`.
"""
from datetime import date

import pytest

from dienstreis import trip as T

KNOWN = ["Kinshasa", "Kisangani", "Yangambi"]


def _trip(**kw):
    base = {"traveller": "Reiziger T", "profile": {"lodging": "hotel"},
            "stops": [{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-05"},
                      {"place": "Kisangani", "from": "2026-12-06", "to": "2026-12-13"}]}
    base.update(kw)
    return base


def check(t):
    return T.validate(T.coerce(t), known_places=KNOWN, today=date(2026, 9, 22))


def test_clean_trip_has_no_issues():
    assert check(_trip()) == []


@pytest.mark.parametrize("raw, expected", [
    ("2026-11-28", date(2026, 11, 28)),
    ("28/11/2026", date(2026, 11, 28)),     # Belgian day-first, the format seen from the model
    ("28-11-2026", date(2026, 11, 28)),
    ("3/1/27", date(2027, 1, 3)),           # two digit year, as the travel forms write it
    ("2026-11-28T00:00:00", date(2026, 11, 28)),
    (date(2026, 11, 28), date(2026, 11, 28)),
    ("onzin", None),
    ("32/11/2026", None),
])
def test_parse_date(raw, expected):
    assert T.parse_date(raw) == expected


def test_day_first_never_month_first():
    """03/04/2026 is 3 April in a Belgian request, not 4 March."""
    assert T.parse_date("03/04/2026") == date(2026, 4, 3)


def test_coerce_gives_real_dates():
    """risk.assess_stop tests `isinstance(s, date)`; a str silently drops the nights flag."""
    t = T.coerce(_trip(stops=[{"place": "Kinshasa", "from": "28/11/2026", "to": "05/12/2026"}]))
    s = t["stops"][0]
    assert isinstance(s["from"], date) and isinstance(s["to"], date)
    assert (s["to"] - s["from"]).days == 7


def test_unreadable_date_is_reported_not_raised():
    issues = check(_trip(stops=[{"place": "Kinshasa", "from": "ooit", "to": "2026-12-05"}]))
    assert any("onleesbaar" in i for i in issues)


def test_unknown_place_without_coordinates():
    issues = check(_trip(stops=[{"place": "Doruma", "from": "2026-11-28", "to": "2026-12-05"}]))
    assert any("onbekende plaats" in i and "places.csv" in i for i in issues)


def test_unknown_place_with_coordinates_is_fine():
    assert check(_trip(stops=[{"place": "Doruma", "lat": 4.73, "lon": 27.69,
                               "from": "2026-11-28", "to": "2026-12-05"}])) == []


def test_reversed_dates():
    issues = check(_trip(stops=[{"place": "Kinshasa", "from": "2026-12-22", "to": "2026-12-01"}]))
    assert any("ligt voor" in i for i in issues)


def test_stops_out_of_order():
    issues = check(_trip(stops=[{"place": "Kinshasa", "from": "2026-12-06", "to": "2026-12-13"},
                                {"place": "Kisangani", "from": "2026-11-28", "to": "2026-12-05"}]))
    assert any("begint" in i for i in issues)


def test_same_day_chaining_is_allowed():
    """The examples chain stops on one day: arrival and departure share a date."""
    assert check(_trip(stops=[{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-06"},
                              {"place": "Kisangani", "from": "2026-12-06", "to": "2026-12-14"}])) == []


def test_wrong_year_is_caught():
    """A December to March trip that loses the year rollover becomes a 400+ day trip."""
    issues = check(_trip(stops=[{"place": "Kinshasa", "from": "2026-12-22", "to": "2026-12-28"},
                                {"place": "Kisangani", "from": "2027-01-05", "to": "2025-03-01"}]))
    assert issues


def test_far_past_and_far_future():
    assert any("verleden" in i for i in
               check(_trip(stops=[{"place": "Kinshasa", "from": "2024-01-01", "to": "2024-01-08"}])))
    assert any("toekomst" in i for i in
               check(_trip(stops=[{"place": "Kinshasa", "from": "2031-01-01", "to": "2031-01-08"}])))


def test_transit_only_must_be_one_day():
    issues = check(_trip(stops=[{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-05",
                                 "transit_only": True}]))
    assert any("transit_only" in i for i in issues)


def test_unknown_lodging():
    assert any("verblijfsvorm" in i for i in check(_trip(profile={"lodging": "yurt"})))


def test_coordinates_outside_the_region():
    issues = check(_trip(stops=[{"place": "Ergens", "lat": 52.4, "lon": -120.0,
                                 "from": "2026-11-28", "to": "2026-12-05"}]))
    assert any("buiten het verwachte gebied" in i for i in issues)


def test_no_stops_and_no_traveller():
    issues = T.validate(T.coerce({"stops": []}), known_places=KNOWN, today=date(2026, 9, 22))
    assert any("reiziger" in i for i in issues) and any("halte" in i for i in issues)


def test_known_places_skips_comment_and_header():
    names = T.known_places()
    assert "Kinshasa" in names and "name" not in names and not any(n.startswith("#") for n in names)


def test_examples_all_validate():
    """Guard against the checks becoming stricter than the itineraries actually written."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    import yaml
    for p in sorted((root / "examples").glob("*.yaml")):
        t = T.coerce(yaml.safe_load(p.read_text(encoding="utf-8")))
        assert T.validate(t, known_places=T.known_places(), today=date(2026, 9, 22)) == [], p.name
