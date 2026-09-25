"""Which outbreaks apply to a trip, and which country a stop is in. No network: the country outlines
are replaced by a few boxes, including the two ways Natural Earth codes can mislead."""
import geopandas as gpd
import pytest
from shapely.geometry import box

from dienstreis import outbreak, route
from dienstreis import trip as trip_mod


@pytest.fixture(autouse=True)
def outlines(monkeypatch):
    fake = gpd.GeoDataFrame({"ISO_A3": ["-99", "SSD", "KEN"], "ADM0_A3": ["FRA", "SDS", "KEN"]},
                            geometry=[box(0, 45, 5, 50), box(28, 5, 33, 9), box(35, -3, 40, 3)], crs="EPSG:4326")
    monkeypatch.setattr(route, "_outlines", lambda: fake)


def _trip(*stops, **kw):
    return {"traveller": "Reiziger R", "stops": list(stops), **kw}


def test_a_known_place_takes_its_country_from_places_csv():
    assert route.country_of({"place": "Kinshasa"}) == "COD" and route.country_of({"place": "Kampala"}) == "UGA"


def test_a_point_takes_its_country_from_the_map():
    assert route.country_of({"place": "Parijs", "lat": 48.8, "lon": 2.3}) == "FRA"     # ISO_A3 -99
    assert route.country_of({"place": "Juba-west", "lat": 7.0, "lon": 30.0}) == "SSD"  # not SDS
    assert route.country_of({"place": "op zee", "lat": -30.0, "lon": -20.0}) is None


DRC = ["ebola_cod_2026", "mpox_cod_2026"]


def test_a_stop_in_the_outbreak_country_applies_it():
    assert [s.id for s in route.applicable(_trip({"place": "Kinshasa"}))] == DRC


def test_a_stop_in_a_neighbouring_country_applies_it_too():
    """Borders with an outbreak country are closed or screened: those countries are checked."""
    assert [s.id for s in route.applicable(_trip({"place": "Kampala"}))] == DRC


def test_a_trip_far_from_any_outbreak_goes_to_country_level():
    t = _trip({"place": "Nairobi", "lat": -1.3, "lon": 36.8})
    assert route.applicable(t) == [] and [s.id for s in route.outbreaks_for(t)] == [outbreak.NONE]
    assert [s.id for s in route.outbreaks_for(_trip({"place": "Addis Ababa"}))] == [outbreak.NONE]


def test_the_outbreaks_a_trip_names_win_over_routing():
    t = _trip({"place": "Addis Ababa"}, outbreaks=["ebola_cod_2026"])
    assert [s.id for s in route.outbreaks_for(t)] == ["ebola_cod_2026"]


def test_a_profile_in_concept_is_offered_where_it_reaches(monkeypatch):
    monkeypatch.setattr(outbreak.load("mpox_cod_2026"), "active", False)
    assert route.inactive_for("mpox", _trip({"place": "Kinshasa"})) == ["mpox_cod_2026"]
    assert route.inactive_for("mpox", _trip({"place": "Addis Ababa"})) == []
    assert route.inactive_for("cholera", _trip({"place": "Kinshasa"})) == []


def test_a_disease_without_a_profile_is_named():
    ebola = outbreak.default()
    assert route.unmatched_diseases(["mpox", "Ebola", "ebola-uitbraak"], [ebola]) == ["mpox"]
    assert route.unmatched_diseases(["mpox"], [outbreak.none()]) == ["mpox"]


# ---------------------------------------------------------------- stops.yaml with outbreaks
REASON = "verblijf in een gesloten compound, geen contact met de gemeenschap"


def _check(trip):
    return trip_mod.validate(trip_mod.coerce(trip), known_places=trip_mod.known_places())


def _stop(**override):
    return {"place": "Kisangani", "from": "2026-12-06", "to": "2026-12-13", **override}


def test_an_unknown_outbreak_is_refused():
    assert any("onbekende uitbraak 'pest'" in i for i in _check(_trip(_stop(), outbreaks=["pest"])))


def test_one_outbreak_needs_no_name_on_an_override():
    t = _trip(_stop(override={"category": "C", "reason": REASON}), outbreaks=["ebola_cod_2026"])
    assert _check(t) == []


def test_several_outbreaks_need_the_override_to_name_one():
    t = _trip(_stop(override={"category": "C", "reason": REASON}), outbreaks=["ebola_cod_2026", "geen"])
    assert any("welke ze opzij zet" in i for i in _check(t))
    t = _trip(_stop(override={"category": "C", "reason": REASON, "outbreak": "ebola_cod_2026"}),
              outbreaks=["ebola_cod_2026", "geen"])
    assert _check(t) == []


def test_an_override_for_an_outbreak_that_does_not_apply_is_refused():
    t = _trip(_stop(override={"category": "C", "reason": REASON, "outbreak": "geen"}), outbreaks=["ebola_cod_2026"])
    assert any("geldt niet voor deze reis" in i for i in _check(t))


def test_a_list_of_overrides_one_per_outbreak():
    t = _trip(_stop(override=[{"category": "C", "reason": REASON, "outbreak": "ebola_cod_2026"},
                              {"category": "X", "reason": REASON, "outbreak": "geen"}]),
              outbreaks=["ebola_cod_2026", "geen"])
    assert _check(t) == []
    t["stops"][0]["override"][1]["outbreak"] = "ebola_cod_2026"
    assert any("dezelfde uitbraak" in i for i in _check(t))
