"""The hand-kept case table: an outbreak without a curated feed still gets categories, on the zone
outlines of another profile. No network, no model, no drawing: the outlines are two boxes."""
import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import yaml
from shapely.geometry import box

from dienstreis import advies, data, figures, outbreak, pipeline

KIN, TSH = box(15.0, -4.6, 15.6, -4.0), box(24.5, 0.0, 26.0, 1.2)
HEAD = ",".join(data.TABLE_COLUMNS)


@pytest.fixture()
def table_profile(tmp_path, monkeypatch):
    """`tab_cod`: the Ebola profile's texts on a table of confirmed cases per province."""
    root = tmp_path / "outbreaks"
    shutil.copytree(outbreak.ROOT, root)
    prof = root / "tab_cod"
    shutil.copytree(root / "ebola_cod_2026", prof)
    cfg = yaml.safe_load((prof / "outbreak.yaml").read_text(encoding="utf-8"))
    cfg.update(id="tab_cod", name_nl="Tabelziekte", match_terms=["tabelziekte"],
               adapter={"type": "table", "cases": "cases.csv", "level": "admin1", "case_def": "bevestigd",
                        "boundaries": {"from": "ebola_cod_2026"}, "stale_days": 14})
    (prof / "outbreak.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    (prof / "zone_overrides.csv").unlink()
    monkeypatch.setattr(outbreak, "ROOT", root)
    monkeypatch.setattr(data, "LOCAL_OUTBREAKS", tmp_path / "lokaal")
    monkeypatch.setattr(data, "boundaries", lambda spec: gpd.GeoDataFrame(
        {"Nom": ["Kinshasa", "Tshopo"], "PROVINCE": ["Kinshasa", "Tshopo"]}, geometry=[KIN, TSH], crs="EPSG:4326"))
    outbreak.load.cache_clear()
    yield prof
    outbreak.load.cache_clear()


def _write(path, rows):
    path.write_text(HEAD + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


ROWS = ["2026-09-01,Kinshasa,,2,0,bevestigd,https://example.org/a",
        "2026-09-01,Tshopo,,1,0,bevestigd,https://example.org/a",
        "2026-09-01,NATIONAAL,,3,0,bevestigd,https://example.org/a",
        "2026-09-15,Kinshasa,,2,0,bevestigd,https://example.org/b",
        "2026-09-15,Tshopo,,4,1,bevestigd,https://example.org/b",
        "2026-09-15,NATIONAAL,,6,1,bevestigd,https://example.org/b"]


def test_the_table_gives_the_same_fields_as_any_adapter(table_profile):
    _write(table_profile / "cases.csv", ROWS)
    ob = data.load(spec=outbreak.load("tab_cod"))
    z = ob.zones.set_index("Nom")
    assert (z.loc["Tshopo", "cases"], z.loc["Tshopo", "deaths"], z.loc["Tshopo", "days_since_last"]) == (4, 1, 0)
    assert z.loc["Kinshasa", "days_since_last"] == 14          # its only increase was the first report
    assert ob.checks["zone_sum_matches_national"] and ob.checks["table_last_date"] == "2026-09-15"


def test_without_national_rows_the_units_are_summed(table_profile):
    _write(table_profile / "cases.csv", [r for r in ROWS if "NATIONAAL" not in r])
    assert int(data.load(spec=outbreak.load("tab_cod")).national.cases.iloc[-1]) == 6


def test_a_name_the_outlines_do_not_know_is_reported(table_profile):
    _write(table_profile / "cases.csv", ROWS + ["2026-09-15,Sankuruu,,5,0,bevestigd,https://example.org/b"])
    assert data.load(spec=outbreak.load("tab_cod")).unmatched == ["Sankuruu"]


def test_a_local_table_wins_once_it_reaches_the_same_date(table_profile):
    spec = outbreak.load("tab_cod")
    _write(table_profile / "cases.csv", ROWS)
    loc = data.LOCAL_OUTBREAKS / "tab_cod" / "cases.csv"
    loc.parent.mkdir(parents=True)
    _write(loc, ROWS[:3])
    assert data.table_path(spec) == table_profile / "cases.csv"     # older: the package copy
    _write(loc, ROWS + ["2026-09-22,Tshopo,,7,1,bevestigd,https://example.org/c"])
    assert data.table_path(spec) == loc


def test_confirmed_rows_go_to_the_local_table(table_profile):
    spec = outbreak.load("tab_cod")
    _write(table_profile / "cases.csv", ROWS)
    row = {"outbreak": "tab_cod", "date": "2026-09-22", "admin1": "Tshopo", "admin2": "", "cases_cum": 7,
           "deaths_cum": 1, "case_def": "bevestigd", "source_url": "https://example.org/c"}
    advies.maybe_apply_web({"case_updates": [row, {**row, "outbreak": "onbekend"}]}, apply_web=True,
                           outbreak_id="tab_cod", specs=[spec])
    t = data.read_table(data.table_path(spec))
    assert data.table_path(spec).parent.name == "tab_cod" and len(t) == len(ROWS) + 1
    assert t.iloc[-1]["cases_cum"] == 7


def test_the_web_step_gets_the_last_figures(table_profile):
    _write(table_profile / "cases.csv", ROWS)
    t = advies._tables_for_web([outbreak.load("tab_cod"), outbreak.default()])
    assert list(t) == ["tab_cod"] and t["tab_cod"]["laatste_datum"] == "2026-09-15"
    assert {r["admin1"] for r in t["tab_cod"]["laatste_cijfers"]} == {"Kinshasa", "Tshopo", "NATIONAAL"}


@pytest.fixture()
def no_drawing(monkeypatch):
    def fake_map(rs, ob, title, subtitle, out, annotate_neighbours=True):
        Path(out).write_bytes(b"png")
        return {"path": out, "label_overlaps": 0, "labels_clipped": 0, "far_stops_in_inset": []}
    monkeypatch.setattr(figures, "itinerary_map", fake_map)


TRIP = {"traveller": "Reiziger T", "outbreaks": ["tab_cod"],
        "stops": [{"place": "Kisangani", "from": pd.Timestamp("2026-10-06").date(), "to": pd.Timestamp("2026-10-10").date()}]}


def test_an_old_table_is_flagged(table_profile, no_drawing, tmp_path):
    _write(table_profile / "cases.csv", ROWS)
    s = pipeline.analyse(TRIP, tmp_path / "out", asof="2026-10-05")
    q = s["qa"]
    assert (q["table_last_date"], q["table_days_old"], q["table_stale"]) == ("2026-09-15", 20, True)
    assert "20 dagen oud" in advies._table_notes(s)[0]


def test_a_single_report_date_gives_no_curve(table_profile, no_drawing, tmp_path):
    _write(table_profile / "cases.csv", ROWS[3:])
    s = pipeline.analyse(TRIP, tmp_path / "out", asof="2026-09-20")
    assert s["epi"]["weekly_cases_last4_full_weeks"] == {} and s["epicurve"] is None
    assert len(s["attachments"]) == 1                             # the map only
    skel = (tmp_path / "out" / "reply_skeleton.txt").read_text(encoding="utf-8")
    assert "6 bevestigde gevallen" in skel and "per volledige week" not in skel
    assert "In bijlage de kaart met het reisschema." in skel          # no curve promised


def test_an_empty_table_does_not_stop_the_advice(table_profile, no_drawing, tmp_path):
    _write(table_profile / "cases.csv", [])
    s = pipeline.analyse(TRIP, tmp_path / "out", asof="2026-10-05")
    assert s["qa"]["table_empty"] and s["stops"][0]["category"] == "X"
    assert any("de tabel is leeg" in f for f in s["stops"][0]["flags"])
    assert "is leeg" in advies._table_notes(s)[0]
    assert s["overall"].startswith("geen cijfers voor Tabelziekte") and s["overall_level"] is None
