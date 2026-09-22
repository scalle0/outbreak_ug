"""The advice archive: kept whole, dated, searchable, and fed back into the next advice."""
from datetime import date

import pytest

from dienstreis import archive

SUMMARY = {
    "asof": "2026-09-19", "departure": "2026-11-28",
    "overall": "niet goedkeuren in huidige vorm (minstens een luik af te raden)",
    "rule_overall": "niet goedkeuren in huidige vorm (minstens een luik af te raden)",
    "overrides": [],
    "stops": [{"place": "Kinshasa", "zone": "Barumbu", "province": "Kinshasa", "category": "F",
               "verdict": "geen bezwaar", "start": "2026-11-28", "end": "2026-12-05", "nights": 7},
              {"place": "Kisangani", "zone": "Makiso Kisangani", "province": "Tshopo", "category": "A",
               "verdict": "afraden", "start": "2026-12-06", "end": "2026-12-13", "nights": 7}],
}
TRIP = {"traveller": "Reiziger T", "note": "veldwerk", "review_on": "2026-11-20"}
REPLY = "Beste An,\n\nKisangani raad ik af.\n\nMet vriendelijke groet,\nSteven Callens\n"


@pytest.fixture()
def root(tmp_path):
    return tmp_path / "adviezen"


def test_save_writes_a_dated_folder(root):
    d = archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 22), root=root)
    assert d.name == "2026-09-22_reiziger_t"
    assert (d / "advies.json").exists() and (d / "reply.txt").exists() and (d / "summary.json").exists()
    assert (d / "reply.txt").read_text(encoding="utf-8") == REPLY


def test_two_advices_on_one_day_do_not_overwrite(root):
    a = archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 22), root=root)
    b = archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 22), root=root)
    assert a != b and b.name.endswith("_2")


def test_the_record_is_searchable_on_what_matters(root):
    archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 22), root=root)
    for term in ("Kisangani", "Makiso", "Tshopo", "Reiziger T", "veldwerk"):
        assert archive.search(term, root=root), term
    assert not archive.search("Lubumbashi", root=root)


def test_search_filters(root):
    archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 20), root=root)
    archive.save({**TRIP, "traveller": "Reiziger B"},
                 {**SUMMARY, "overall": "geen ebola-gerelateerd bezwaar",
                  "overrides": [{"scope": "Kisangani", "van": "A", "naar": "C", "reason": "compound"}]},
                 REPLY, advised_on=date(2026, 9, 22), root=root)
    assert len(archive.search(root=root)) == 2
    assert len(archive.search(verdict="geen ebola", root=root)) == 1
    assert len(archive.search(since=date(2026, 9, 21), root=root)) == 1
    assert len(archive.search(until=date(2026, 9, 21), root=root)) == 1
    assert archive.search(overruled=True, root=root)[0]["traveller"] == "Reiziger B"
    assert archive.search(overruled=False, root=root)[0]["traveller"] == "Reiziger T"


def test_newest_first(root):
    archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 8, 1), root=root)
    archive.save({**TRIP, "traveller": "Later"}, SUMMARY, REPLY, advised_on=date(2026, 9, 22), root=root)
    assert archive.search(root=root)[0]["traveller"] == "Later"


def test_previous_advice_for_the_same_destination_comes_back_in_full(root):
    """A one-line log row cannot show a contradiction; the reply text can."""
    archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 10), root=root)
    hits = archive.for_trip({}, SUMMARY, root=root)
    assert len(hits) == 1 and hits[0]["reply"] == REPLY
    assert hits[0]["overall"].startswith("niet goedkeuren")


def test_an_unrelated_destination_is_not_fed_back(root):
    archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 10), root=root)
    other = {"stops": [{"place": "Lubumbashi", "zone": "Kenya", "province": "Haut-Katanga"}]}
    assert archive.for_trip({}, other, root=root) == []


def test_matching_on_zone_alone_is_enough(root):
    """Durba is in zone Watsa: a later trip to another place in that zone must still find it."""
    archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 10), root=root)
    same_zone = {"stops": [{"place": "Ergens anders", "zone": "Makiso Kisangani", "province": "Tshopo"}]}
    assert len(archive.for_trip({}, same_zone, root=root)) == 1


def test_overrides_travel_with_the_record(root):
    s = {**SUMMARY, "overrides": [{"scope": "Kisangani", "van": "A", "naar": "C", "reason": "compound"}]}
    archive.save(TRIP, s, REPLY, advised_on=date(2026, 9, 22), root=root)
    assert archive.for_trip({}, s, root=root)[0]["overrides"][0]["reason"] == "compound"


def test_empty_archive_is_not_an_error(root):
    assert archive.search("Kinshasa", root=root) == [] and archive.all_advices(root) == []


def test_a_broken_record_is_skipped(root):
    d = archive.save(TRIP, SUMMARY, REPLY, advised_on=date(2026, 9, 22), root=root)
    (root / "2026-09-23_kapot").mkdir(parents=True)
    (root / "2026-09-23_kapot" / "advies.json").write_text("{ niet", encoding="utf-8")
    assert len(archive.all_advices(root)) == 1
