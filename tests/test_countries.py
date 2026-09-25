"""The country registry: what is the same about a country whatever the disease.

No network, no model. Local copies and the 0.2 advisories table go to temporary folders (conftest).
"""
from datetime import date

import geopandas as gpd
import pytest
import yaml
from shapely.geometry import box

from dienstreis import advies, countries, mail, outbreak, risk


def test_every_registry_file_is_valid():
    assert "COD" in countries.ids()
    for iso3 in countries.ids():
        assert countries.check(countries.load(iso3), iso3) == [], iso3


def test_neighbours_agree_both_ways():
    known = set(countries.ids())
    for iso3 in known:
        for nb in set(countries.neighbours(iso3)) & known:
            assert iso3 in countries.neighbours(nb), f"{iso3} noemt {nb} als buur, maar niet omgekeerd"


def test_the_drc_and_its_nine_neighbours_are_in_the_registry():
    assert set(countries.neighbours("COD")) == {"AGO", "BDI", "CAF", "COG", "RWA", "SSD", "TZA", "UGA", "ZMB"}
    assert set(countries.neighbours("COD")) <= set(countries.ids())


def test_reading_an_entry():
    c = countries.load("COD")
    assert countries.fod(c, "Tshopo") == ("formeel_afgeraden", "veiligheidssituatie")
    assert countries.fod(c, "Kinshasa") == ("niet_essentieel_afgeraden", "algemene volatiliteit")
    assert countries.cdc(c, "ebola_cod_2026", "Ituri") == 4
    assert countries.cdc(c, "ebola_cod_2026", "Kinshasa") == 2 and countries.cdc(c, "andere_uitbraak") is None
    assert countries.letter("COD") == "de DRC" and countries.letter("XYZ") == "XYZ"
    assert countries.load("XYZ") is None


def test_a_newer_local_copy_wins_and_an_older_one_does_not():
    c = {k: v for k, v in countries.load("COD").items() if not k.startswith("_")}
    countries.save_local({**c, "verified": date(2099, 1, 1), "pretravel": "lokaal"})
    assert countries.load("COD")["pretravel"] == "lokaal"
    countries.save_local({**c, "verified": date(2000, 1, 1), "pretravel": "oud"})
    assert countries.load("COD")["pretravel"] != "oud"


def test_the_02_advisories_table_is_still_read_when_newer():
    countries.LEGACY.write_text(yaml.safe_dump({
        "verified": date(2099, 1, 1), "default": {"fod": "niet_essentieel_afgeraden", "fod_reason": "x", "cdc": 1},
        "provinces": {"Tshopo": {"fod": "niet_essentieel_afgeraden", "fod_reason": "y", "cdc": 2}},
        "countries": {"UGA": {"note": "grens open"}}}), encoding="utf-8")
    c = countries.load("COD")
    assert countries.fod(c, "Tshopo") == ("niet_essentieel_afgeraden", "y") and countries.cdc(c, "ebola_cod_2026") == 1
    assert c["pretravel"] and c["neighbours"]          # what the old table did not hold stays
    assert [m["text"] for m in countries.measures(countries.load("UGA"), "ebola_cod_2026")] == ["grens open"]


def test_an_older_02_table_is_ignored():
    countries.LEGACY.write_text(yaml.safe_dump({"verified": date(2000, 1, 1), "default": {"fod": "x", "cdc": 4},
                                                "provinces": {}}), encoding="utf-8")
    assert countries.cdc(countries.load("COD"), "ebola_cod_2026") == 2


WEB = {"advisories": [
           {"country": "COD", "region": "Tshopo", "fod": "formeel_afgeraden", "fod_reason": "gewapend conflict",
            "cdc": 4, "changed": True},
           {"country": "UGA", "region": None, "fod": "niet_essentieel_afgeraden", "fod_reason": "grens",
            "cdc": None, "changed": True}],
       "measures": [{"country": "UGA", "text": "screening aan de grens met de DRC", "date": "2026-09-24",
                     "source": "https://example.org/uga", "changed": True},
                    {"country": "ZMB", "text": "niets nieuws", "changed": False}],
       "sources": [{"country": "UGA", "kind": "overheid", "name": "Ministry of Health", "url": "https://example.org/moh"},
                   {"country": "UGA", "kind": "fod", "name": "FOD Oeganda", "url": "https://example.org/fod"}],
       "news": [], "who": {}}


def test_web_findings_are_merged_into_the_entries():
    out = countries.apply_web(WEB, "ebola_cod_2026", today=date(2026, 9, 25))
    cod, uga = out["COD"], out["UGA"]
    assert cod["fod"]["regions"]["Tshopo"]["reason"] == "gewapend conflict"
    assert cod["cdc"]["ebola_cod_2026"]["regions"]["Tshopo"] == 4 and cod["verified"] == date(2026, 9, 25)
    assert countries.fod(uga) == ("niet_essentieel_afgeraden", "grens") and uga["verified"] == date(2026, 9, 25)
    assert [m["text"] for m in countries.measures(uga, "ebola_cod_2026")] == ["screening aan de grens met de DRC"]
    assert uga["government"][0]["url"] == "https://example.org/moh"
    assert ["FOD Oeganda", "https://example.org/fod"] in uga["fod"]["pages"]
    assert "ZMB" not in out                           # an unchanged measure is not a change


def test_nothing_is_written_without_a_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    advies.maybe_apply_web(WEB, apply_web=False)
    assert not countries.LOCAL.exists()


def test_accepted_findings_go_to_the_local_registry():
    advies.maybe_apply_web(WEB, apply_web=True)
    assert countries.load("UGA")["_source"].endswith("UGA.yaml") and countries.age_days(countries.load("UGA")) == 0
    assert countries.fod(countries.load("COD"), "Tshopo")[1] == "gewapend conflict"


def test_a_country_checked_for_the_first_time_is_recorded_even_without_changes(monkeypatch):
    webd = {"advisories": [{"country": "ZMB", "region": None, "fod": "niet_essentieel_afgeraden",
                            "fod_reason": "z", "changed": False}], "news": [], "who": {}}
    advies.maybe_apply_web(webd, apply_web=True)
    assert countries.age_days(countries.load("ZMB")) == 0


def test_the_pretravel_line_comes_from_the_countries_of_the_trip():
    r = risk.StopRisk(place="Kinshasa", start=None, end=None, nights=None, lodging=None, transit_only=False,
                      lat=-4.3, lon=15.3, country="COD")
    assert mail.pretravel_line([r]) == ("Pretravel consult (gele koorts verplicht, malariaprofylaxe) "
                                        "en registratie via Travellers Online.")
    r.country = "ZMB"
    assert mail.pretravel_line([r]) == "Pretravel consult en registratie via Travellers Online."


def _zones():
    """One health zone around Kisangani with a recent case; nothing else."""
    return gpd.GeoDataFrame({"Nom": ["Makiso Kisangani"], "PROVINCE": ["Tshopo"], "cases": [5], "deaths": [1],
                             "new14": [2], "days_since_last": [3.0]},
                            geometry=[box(24.9, 0.3, 25.5, 0.8)], crs="EPSG:4326")


def test_a_stop_in_a_zone_takes_fod_and_cdc_from_the_registry():
    r = risk.assess_stop({"place": "Kisangani"}, _zones(), {}, outbreak.default())
    assert (r.category, r.fod, r.cdc) == ("A", "formeel_afgeraden", 3)
    assert "FOD raadt provincie formeel af (veiligheidssituatie)" in r.flags


def test_a_stop_in_a_neighbouring_country_carries_its_border_measures():
    r = risk.assess_stop({"place": "Kampala"}, _zones(), {}, outbreak.default())
    assert r.category == "X" and r.country == "UGA"
    assert r.flags[0].startswith("Uganda outbreak declared over")


def test_a_stop_in_a_country_without_measures_gets_the_profiles_note():
    r = risk.assess_stop({"place": "Addis Ababa"}, _zones(), {}, outbreak.default())
    assert r.category == "X" and r.flags == [outbreak.default().outside_note]


def test_a_new_country_gets_its_names_and_neighbours(monkeypatch):
    """Without neighbours an outbreak there would never reach a trip next door (live run, Kenya, 2026-09-25)."""
    from dienstreis import route
    monkeypatch.setattr(route, "describe", lambda iso3: {"name_nl": "Kenia", "name_en": "Kenya",
                                                         "neighbours": ["ETH", "SOM", "SSD", "TZA", "UGA"]})
    out = countries.apply_web({"advisories": [{"country": "KEN", "region": None, "fod": None, "cdc": 1}]}, "geen")
    ken = out["KEN"]
    assert (ken["name_nl"], ken["letter_nl"], ken["neighbours"]) == ("Kenia", "Kenia", ["ETH", "SOM", "SSD", "TZA", "UGA"])
    assert countries.check(ken, "KEN") == []


def test_a_finding_about_a_disease_without_a_profile_is_kept_under_the_run(monkeypatch):
    """The model keyed a measure to 'mpox en ebola'; no profile has that id, so no advice would ever find it."""
    webd = {"advisories": [{"country": "UGA", "region": None, "cdc": 2, "outbreak": "dengue (Level 1)"}],
            "measures": [{"country": "UGA", "outbreak": "mpox en ebola", "text": "screening", "changed": True}]}
    uga = countries.apply_web(webd, "ebola_cod_2026")["UGA"]
    assert uga["cdc"]["ebola_cod_2026"]["default"] == 2 and "dengue (Level 1)" not in uga["cdc"]
    m = countries.measures(uga, "ebola_cod_2026")
    assert [x["text"] for x in m] == ["screening"] and m[0]["about"] == "mpox en ebola"
