"""Several outbreaks in one advice, and an advice at country level when none applies.

No network, no model, no drawing: a second, synthetic outbreak ("Testziekte") lives in a temporary
copy of the profiles, both outbreaks get small in-memory zones, and the map and curve are replaced
by stubs. What is tested is how the outbreaks are combined, not how they are drawn.
"""
import json
import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import yaml
from shapely.geometry import box

from dienstreis import advies, archive, data, figures, llm, log, mail, outbreak, pipeline

KIN, KIS = box(15.0, -4.6, 15.6, -4.0), box(24.9, 0.3, 25.5, 0.8)     # around Kinshasa and Kisangani


@pytest.fixture()
def two_outbreaks(tmp_path, monkeypatch):
    """The real profiles plus `test_cod`, a milder second outbreak in the DRC."""
    root = tmp_path / "outbreaks"
    shutil.copytree(outbreak.ROOT, root)
    test = root / "test_cod"
    shutil.copytree(root / "ebola_cod_2026", test)
    cfg = yaml.safe_load((test / "outbreak.yaml").read_text(encoding="utf-8"))
    cfg.update(id="test_cod", name_nl="Testziekte", match_terms=["testziekte"],
               conditions=["Testvoorwaarde voor de testziekte.",
                           "[[CLAUDE: go/no-go-datum en criteria, of 'korte check een week voor vertrek']]"])
    cfg["categories"]["A"]["level"] = "voorwaardelijk"      # this one never makes a trip afraden
    cfg["overall"]["geen_bezwaar"] = "geen testziekte-gerelateerd bezwaar"
    (test / "outbreak.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(outbreak, "ROOT", root)
    outbreak.load.cache_clear()

    def fake_load(refresh=False, asof=None, spec=None):
        """Ebola: a recent case in Kisangani. Testziekte: a case in Kinshasa 30 days ago."""
        hz = gpd.GeoDataFrame({"Nom": ["Barumbu", "Makiso Kisangani"], "PROVINCE": ["Kinshasa", "Tshopo"]},
                              geometry=[KIN, KIS], crs="EPSG:4326")
        days = pd.date_range("2026-08-01", "2026-09-19")
        cw = pd.DataFrame(0.0, index=days, columns=hz.Nom)
        if spec.id == "test_cod":
            cw.loc["2026-08-20":, "Barumbu"] = 3
        else:
            cw.loc["2026-09-16":, "Makiso Kisangani"] = 5
        dw = cw * 0
        national = pd.DataFrame({"cases": cw.sum(axis=1), "deaths": dw.sum(axis=1)})
        return data.derive(hz, cw, dw, national, None, [], spec)

    def fake_map(rs, ob, title, subtitle, out, annotate_neighbours=True):
        Path(out).write_bytes(b"png")
        return {"path": out, "label_overlaps": 0, "labels_clipped": 0, "far_stops_in_inset": []}

    def fake_curve(ob, out, ecdc=None):
        Path(out).write_bytes(b"png")
        return {"path": out, "weekly_cases_last4_full_weeks": {"08-09": 0, "15-09": 5}, "last_total": 5,
                "last_deaths": 0, "cfr": 0.0}

    monkeypatch.setattr(data, "load", fake_load)
    monkeypatch.setattr(figures, "itinerary_map", fake_map)
    monkeypatch.setattr(figures, "epicurve", fake_curve)
    yield
    outbreak.load.cache_clear()


TRIP = {"traveller": "Reiziger M", "profile": {"lodging": "hotel"},
        "outbreaks": ["ebola_cod_2026", "test_cod"],
        "stops": [{"place": "Kinshasa", "from": pd.Timestamp("2026-11-28").date(), "to": pd.Timestamp("2026-12-06").date()},
                  {"place": "Kisangani", "from": pd.Timestamp("2026-12-06").date(), "to": pd.Timestamp("2026-12-13").date()}]}


def test_each_outbreak_is_assessed_and_the_strictest_leads(two_outbreaks, tmp_path):
    s = pipeline.analyse(TRIP, tmp_path / "out", asof="2026-09-19")
    assert s["outbreak"] == "ebola_cod_2026" and s["overall_level"] == "afraden"
    assert "".join(x["category"] for x in s["stops"]) == "FA"
    assert "".join(x["category"] for x in s["outbreaks"]["test_cod"]["stops"]) == "BF"
    assert s["overall"].startswith("Ebola (Bundibugyo-virus): niet goedkeuren") and "Testziekte: voorwaardelijk" in s["overall"]
    assert set(pd.read_csv(tmp_path / "out" / "risk.csv").uitbraak) == {"ebola_cod_2026", "test_cod"}


def test_each_outbreak_has_its_own_map_and_curve(two_outbreaks, tmp_path):
    s = pipeline.analyse(TRIP, tmp_path / "out", asof="2026-09-19")
    names = sorted(Path(a).name for a in s["attachments"])
    assert names == ["epicurve_ebola_cod_2026_20260919.png", "epicurve_test_cod_20260919.png",
                     "kaart_reiziger_m_ebola_cod_2026.png", "kaart_reiziger_m_test_cod.png"]


def test_the_skeleton_covers_every_outbreak(two_outbreaks, tmp_path):
    pipeline.analyse(TRIP, tmp_path / "out", asof="2026-09-19")
    skel = (tmp_path / "out" / "reply_skeleton.txt").read_text(encoding="utf-8")
    assert "Voor Testziekte:" in skel
    testblock = skel.split("Voor Testziekte:")[1].split("Stand van zaken")[0]
    assert "Kinshasa" in testblock and "Kisangani" not in testblock      # only where it weighs
    assert "Stand van zaken Ebola (Bundibugyo-virus)" in skel and "Stand van zaken Testziekte" in skel
    assert skel.count("go/no-go-datum en criteria") == 1                 # the same condition once
    assert "Testvoorwaarde voor de testziekte." in skel
    assert "de kaarten met het reisschema en de bijgewerkte epidemiecurves" in skel


def test_an_override_applies_to_the_outbreak_it_names(two_outbreaks, tmp_path):
    reason = "verblijf in een gesloten compound, geen contact met de gemeenschap"
    trip = {**TRIP, "stops": [{**TRIP["stops"][0], "override": {"category": "F", "reason": reason,
                                                                 "outbreak": "test_cod"}}, TRIP["stops"][1]]}
    s = pipeline.analyse(trip, tmp_path / "out", asof="2026-09-19")
    assert "".join(x["category"] for x in s["outbreaks"]["test_cod"]["stops"]) == "FF"
    assert "".join(x["category"] for x in s["stops"]) == "FA"            # ebola untouched
    assert [o["outbreak"] for o in s["overrides"]] == ["test_cod"]


def test_a_verdict_override_covers_the_whole_advice(two_outbreaks, tmp_path):
    reason = "de reiziger schrapt Kisangani; Kinshasa blijft"
    trip = {**TRIP, "override": {"verdict": "goedkeuren zonder Kisangani", "reason": reason}}
    s = pipeline.analyse(trip, tmp_path / "out", asof="2026-09-19")
    assert s["overall"] == "goedkeuren zonder Kisangani"
    assert s["overrides"][-1]["scope"] == "eindoordeel" and "Testziekte" in s["overrides"][-1]["van"]


def test_the_windows_of_every_outbreak_are_allowed_numbers(two_outbreaks):
    specs = [outbreak.load("ebola_cod_2026"), outbreak.load("test_cod")]
    assert mail.unknown_numbers("na 42 dagen", [], specs) == []


def test_a_reply_that_leaves_an_outbreak_out_gets_a_note(two_outbreaks):
    specs = [outbreak.load("ebola_cod_2026"), outbreak.load("test_cod")]
    assert "Testziekte" in mail.coverage_note("Over ebola: niet goedkeuren.", specs)
    assert mail.coverage_note("Ebola en de testziekte: niet goedkeuren.", specs) is None
    assert mail.coverage_note("Over ebola.", specs[:1]) is None


# ---------------------------------------------------------------- country level
ADDIS = {"traveller": "Reiziger N", "profile": {"lodging": "hotel"},
         "stops": [{"place": "Addis Ababa", "from": pd.Timestamp("2026-11-28").date(),
                    "to": pd.Timestamp("2026-12-06").date()}]}


def test_a_trip_no_outbreak_applies_to_is_written_at_country_level(tmp_path):
    s = pipeline.analyse(ADDIS, tmp_path / "out", asof="2026-09-19")
    assert s["outbreak"] == "geen" and s["overall_level"] is None and s["attachments"] == []
    assert s["epi"] is None and s["map"] is None and s["qa"]["zone_sum_matches_national"] is None
    skel = (tmp_path / "out" / "reply_skeleton.txt").read_text(encoding="utf-8")
    assert "geen uitbraakprofiel van toepassing" in skel
    assert "Stand van zaken" not in skel and "In bijlage" not in skel
    assert "Pretravel consult en registratie via Travellers Online." in skel


REPLY = ("Beste An,\n\nAddis Abeba: geen uitbraak bekend, geen bezwaar.\n\n"
         "Met vriendelijke groet,\nSteven Callens")


def test_country_level_advice_end_to_end(tmp_path, monkeypatch):
    """The whole `advies` for a trip no profile covers: the web step is told to look for an outbreak,
    and a disease the request names without a profile goes to the top of the notes."""
    req = tmp_path / "aanvraag.txt"
    req.write_text("Beste Steven,\n\nVan: Iemand\nAddis Abeba, 28/11 tot 6/12. Is er mpox?\n", encoding="utf-8")
    stops = {**{k: v for k, v in ADDIS.items() if k != "stops"},
             "stops": [{"place": "Addis Ababa", "from": "2026-11-28", "to": "2026-12-06"}],
             "diseases_mentioned": ["mpox"]}
    fake = llm.Fake({"stops": stops, "web": {"advisories": [], "news": [], "who": {}},
                     "reply": {"reply": REPLY, "suggestions": []}})
    res = advies.run_advies(str(req), out=str(tmp_path / "out"), yes=True, asof="2026-09-19",
                            open_browser=False, llm_backend=fake)
    assert res["trip"]["outbreaks"] == ["geen"]
    assert '"geen profiel" betekent niet "geen uitbraak"' in fake.prompts["web"][0].lower()
    assert "<ziekten_zonder_profiel>" in fake.prompts["web"][0] and "mpox" in fake.prompts["reply"][0]
    assert res["suggestions"][0].startswith("De aanvraag noemt mpox")
    assert "concept" not in res["suggestions"][0]          # the mpox concept profile does not reach Ethiopia
    rec = json.loads((Path(res["advice_dir"]) / "advies.json").read_text(encoding="utf-8"))
    assert rec["outbreaks"] == ["geen"] and rec["countries"] == ["ETH"]


# ---------------------------------------------------------------- log and archive
def test_an_old_log_gets_the_new_column_once(tmp_path):
    p = tmp_path / "advice_log.csv"
    old = [f for f in log.FIELDS if f != "outbreaks"]
    p.write_text(",".join(old) + "\n" + ",".join(["2026-09-22", "Reiziger O"] + [""] * (len(old) - 2)) + "\n",
                 encoding="utf-8")
    log.append({"advised_on": "2026-09-25", "traveller": "Reiziger P", "outbreaks": "geen"}, path=p)
    rows = p.read_text(encoding="utf-8").splitlines()
    assert rows[0] == ",".join(log.FIELDS)
    assert rows[1].endswith(",ebola_cod_2026,reisadvies") and rows[2].endswith(",geen,")


def test_an_old_archive_record_reads_as_ebola(tmp_path):
    d = tmp_path / "2026-09-22_reiziger_o"
    d.mkdir()
    (d / "advies.json").write_text(json.dumps({"advised_on": "2026-09-22", "traveller": "Reiziger O",
                                               "places": ["Kinshasa"], "reply": "x"}), encoding="utf-8")
    r = archive.all_advices(tmp_path)[0]
    assert r["outbreaks"] == ["ebola_cod_2026"] and archive.search("", outbreak="geen", root=tmp_path) == []
    assert archive.search("", outbreak="ebola_cod_2026", root=tmp_path)[0]["traveller"] == "Reiziger O"


def test_earlier_advices_on_the_same_outbreak_come_first(tmp_path):
    for day, ob in (("2026-09-24", ["geen"]), ("2026-09-20", ["ebola_cod_2026"])):
        d = tmp_path / f"{day}_x"
        d.mkdir()
        (d / "advies.json").write_text(json.dumps({"advised_on": day, "traveller": day, "places": ["Kinshasa"],
                                                   "outbreaks": ob, "reply": "x"}), encoding="utf-8")
    hits = archive.for_trip({}, {"outbreak": "ebola_cod_2026", "stops": [{"place": "Kinshasa"}]}, root=tmp_path)
    assert [h["advised_on"] for h in hits] == ["2026-09-20", "2026-09-24"]


def test_a_passage_inside_a_sentence_is_joined_with_en(two_outbreaks):
    specs = [outbreak.load("ebola_cod_2026"), outbreak.load("test_cod")]
    assert outbreak.fill("over {{uitbraak:opdracht}}.", specs).count("tijdens de ebola-uitbraak") == 1  # same text once
    specs[1].sections["opdracht"] = "tijdens de testziekte"
    assert outbreak.fill("over {{uitbraak:opdracht}}.", specs).endswith("(Bundibugyo-virus, 2026) en tijdens de testziekte.")
    assert "\n\n" in outbreak.fill("{{uitbraak:valkuilen}}", [outbreak.default(), outbreak.none()])
