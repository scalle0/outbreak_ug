"""The itinerary map for a trip that never enters a zone of the figures. Runs on the cached data of
2026-09-19, like the golden tests."""
from pathlib import Path

from dienstreis import data, outbreak, pipeline
from dienstreis import trip as trip_mod


def test_a_trip_outside_the_figures_still_gets_its_map(tmp_path, monkeypatch):
    """Proefrun 2026-10-07: a trip to Kampala and Kasese (Uganda) stopped while drawing the map."""
    monkeypatch.setattr(outbreak, "active", lambda: [outbreak.default()])
    monkeypatch.setattr(data, "_stale", lambda *a, **k: False)
    trip = {"type": "reisadvies", "traveller": "Reiziger U", "profile": {"lodging": "hotel"},
            "stops": [{"place": "Kampala", "from": "2026-11-30", "to": "2026-12-05"},
                      {"place": "Kasese", "lat": 0.1833, "lon": 30.0833, "from": "2026-12-05", "to": "2026-12-09"}]}
    s = pipeline.analyse(trip_mod.coerce(trip), tmp_path, asof="2026-09-19")
    assert {st["category"] for st in s["stops"]} == {"X"}
    assert s["map"] and Path(s["map"]).exists()
