"""Simplified outlines are for drawing only.

The map is the one place where full-resolution geometry buys nothing: half a pixel on the printed
page. But the same polygons decide which health zone a place falls in and which zones border it, so
the simplification must never reach them. That is what these tests pin.
"""
import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from dienstreis import data, geo


def _zones():
    """Two adjacent squares with a deliberately over-detailed shared edge."""
    wiggle = [(1.0, y / 1000.0) for y in range(0, 1001)]
    left = Polygon([(0, 0)] + wiggle + [(0, 1)])
    right = Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
    return gpd.GeoDataFrame({"Nom": ["Links", "Rechts"], "PROVINCE": ["P1", "P1"],
                             "cases": [5, 0], "new14": [1, 0]},
                            geometry=[left, right], crs="EPSG:4326")


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "CACHE", tmp_path)
    repo = tmp_path / "inrb" / "data" / "shapefiles"
    repo.mkdir(parents=True)
    (repo / "DRC_Health_zones.shp").write_bytes(b"x" * 10)     # only its mtime and size are read
    return tmp_path


def test_zones_passed_in_are_never_modified(cache):
    """geo.zone_of and geo.neighbours run on these polygons: they must stay exact."""
    z = _zones()
    before = [g.wkt for g in z.geometry]
    data.display_geometry(z, repo=cache / "inrb")
    assert [g.wkt for g in z.geometry] == before


def test_simplification_actually_removes_vertices(cache):
    z = _zones()
    disp, _ = data.display_geometry(z, repo=cache / "inrb", tolerance=0.01)
    def n(g):
        return len(g.exterior.coords)
    assert n(disp.geometry.iloc[0]) < n(z.geometry.iloc[0])


def test_columns_and_figures_survive(cache):
    z = _zones()
    disp, prov = data.display_geometry(z, repo=cache / "inrb")
    assert list(disp.Nom) == list(z.Nom) and list(disp.cases) == list(z.cases)
    assert len(prov) == 1 and set(prov.PROVINCE) == {"P1"}


def test_result_is_cached_and_reused(cache):
    z = _zones()
    data.display_geometry(z, repo=cache / "inrb")
    files = sorted(p.name for p in cache.glob("display_*.geojson"))
    assert len(files) == 2
    # a second call must not need the zone geometry at all: hand it a frame whose geometry differs
    other = _zones()
    other["geometry"] = other.geometry.translate(10, 10)   # obviously different geometry
    disp, _ = data.display_geometry(other, repo=cache / "inrb")
    assert disp.geometry.iloc[0].equals(
        gpd.read_file(cache / [f for f in files if "zones" in f][0]).geometry.iloc[0])


def test_a_new_shapefile_invalidates_the_cache(cache):
    z = _zones()
    data.display_geometry(z, repo=cache / "inrb")
    first = {p.name for p in cache.glob("display_*.geojson")}
    shp = cache / "inrb" / "data" / "shapefiles" / "DRC_Health_zones.shp"
    shp.write_bytes(b"y" * 99)                                  # different size -> different stamp
    data.display_geometry(z, repo=cache / "inrb")
    second = {p.name for p in cache.glob("display_*.geojson")}
    assert second and second != first
    assert len(second) == 2, "outlines of the old shapefile should be cleaned up"


def test_tolerance_zero_keeps_everything(cache):
    z = _zones()
    disp, _ = data.display_geometry(z, repo=cache / "inrb", tolerance=0)
    assert disp.geometry.iloc[0].equals(z.geometry.iloc[0])


def test_zone_lookup_is_unaffected_by_the_display_copy(cache):
    """The real risk: a place near a border resolving to a different zone after simplification."""
    z = _zones()
    pt = (0.5, 0.999)                                  # lat, lon close to the wiggly edge
    before = geo.zone_of(z, *pt)
    data.display_geometry(z, repo=cache / "inrb", tolerance=0.05)
    after = geo.zone_of(z, *pt)
    assert before is not None and after is not None and before.Nom == after.Nom
