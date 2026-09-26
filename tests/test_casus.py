"""Case questions: a traveller already abroad, ill, exposed or in quarantine, or a general question.

The 25/09 mpox mail went through the tool as an Ebola trip with a go/no-go three months back. These
tests pin the road it takes now. Invented fixture (tests/fixtures/casus_mpox.txt); fake model.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from dienstreis import advies, archive, llm, log, msg
from dienstreis import trip as trip_mod

FIX = Path(__file__).parent / "fixtures" / "casus_mpox.txt"
TRIPMAIL = Path(__file__).parent / "fixtures" / "aanvraag_testpersoon.eml"
TODAY = date(2026, 9, 25)


def _check(t):
    return trip_mod.validate(trip_mod.coerce(t), known_places=trip_mod.known_places(), today=TODAY)


def test_a_trip_with_a_go_no_go_in_the_past_asks_whether_it_is_a_case():
    t = {"traveller": "X", "review_on": "2026-06-23",
         "stops": [{"place": "Kinshasa", "from": "2026-06-30", "to": "2026-10-02"}]}
    assert any("is dit een casus" in i for i in _check(t))
    assert not any("casus" in i for i in _check({**t, "type": "casus", "review_on": None}))


def test_a_case_may_leave_the_end_of_a_stay_open_and_a_trip_may_not():
    """Live run 2026-09-25: the model left `to` empty for a stay whose return was postponed."""
    stop = {"place": "Kinshasa", "from": "2026-06-30", "to": ""}
    assert _check({"type": "casus", "traveller": "X", "stops": [stop]}) == []
    assert any("'to' onleesbaar" in i for i in _check({"traveller": "X", "stops": [stop]}))
    from dienstreis import mail, risk
    r = risk.StopRisk(place="Kinshasa", start=date(2026, 6, 30), end=None, nights=None, lodging=None,
                      transit_only=False, lat=-4.3, lon=15.3, country="COD", category="X")
    assert mail.leg_paragraph(1, r).startswith("1. Kinshasa (sinds 30 juni):")


def test_a_case_or_question_needs_no_place_and_a_question_no_traveller():
    assert _check({"type": "casus", "traveller": "X", "stops": []}) == []
    assert _check({"type": "vraag", "stops": []}) == []
    assert any("onbekend type" in i for i in _check({"type": "klacht", "traveller": "X", "stops": []}))


def test_health_data_in_a_mail_is_recognised():
    assert "quarantaine" in msg.health_signals(msg.parse_request(FIX))
    assert msg.health_signals(msg.parse_request(TRIPMAIL)) == []


CASE = {"type": "casus", "traveller": "Doctoraatsstudent", "note": "doctoraat, verblijf in Kinshasa",
        "situation": "In quarantaine met mpox in Kinshasa; terugreis van 2/10 uitgesteld; woont in een UGent-home.",
        "profile": {"lodging": "hotel", "healthcare_work": False},
        "stops": [{"place": "Kinshasa", "from": "2026-06-30", "to": "2026-10-02"}],
        "diseases_mentioned": ["mpox"],
        "questions_from_an": ["Wat is jouw visie?", "Zijn er aanvullende richtlijnen, ook over de zorg daar?"]}
WEB = {"guidance": [{"topic": "terugreis", "text": "Reizen na vrijgave door de behandelende arts.",
                     "source": "https://example.org/richtlijn", "date": "2026-09-01"}],
       "advisories": [], "news": [], "who": {}}
REPLY = ("Beste An,\n\nTerugkeer pas na vrijgave door de behandelende arts ter plaatse.\n\n"
         "Met vriendelijke groet,\nSteven Callens")


@pytest.fixture()
def env(tmp_path):
    return tmp_path


def test_nothing_leaves_without_consent_under_yes(env):
    fake = llm.Fake({"stops": CASE})
    with pytest.raises(SystemExit) as e:
        advies.run_advies(str(FIX), out=str(env / "out"), yes=True, open_browser=False, llm_backend=fake,
                          asof="2026-09-19")
    assert "gezondheidsgegevens" in str(e.value) and fake.prompts == {}


def test_nothing_leaves_when_the_user_says_no(env, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    fake = llm.Fake({"stops": CASE})
    with pytest.raises(SystemExit) as e:
        advies.run_advies(str(FIX), out=str(env / "out"), open_browser=False, llm_backend=fake, asof="2026-09-19")
    assert "niets verstuurd" in str(e.value) and fake.prompts == {}


def test_a_case_the_heuristic_missed_is_asked_about_before_the_next_steps(env):
    """The mail has no health words, but the model reads a case: ask before web and reply."""
    fake = llm.Fake({"stops": CASE})
    with pytest.raises(SystemExit):
        advies.run_advies(str(TRIPMAIL), out=str(env / "out"), yes=True, open_browser=False, llm_backend=fake,
                          asof="2026-09-19")
    assert list(fake.prompts) == ["stops"]


def test_a_case_takes_its_own_road(env):
    fake = llm.Fake({"stops": CASE, "web_consult": WEB, "consult": {"reply": REPLY, "suggestions": []}})
    res = advies.run_advies(str(FIX), out=str(env / "out"), yes=True, open_browser=False, llm_backend=fake,
                            asof="2026-09-19", health_ok=True, uitbraken=["mpox_cod_2026"])
    out = Path(res["out"])
    assert set(fake.prompts) == {"stops", "web_consult", "consult"}
    # map and curve are drawn for the dossier, and none of them goes with the letter
    assert list(out.glob("*.png")) and res["summary"]["attachments"]
    assert json.loads((out / "dossier.json").read_text(encoding="utf-8"))["attachments_sent"] == []
    assert "data:image/png;base64," in (out / "dossier.html").read_text(encoding="utf-8")
    p = fake.prompts["consult"][0]
    assert "<feiten>" in p and "Feiten uit de cijfers" in p and "UGent-home" in p and "<skelet>" not in p
    assert "vermoede en bevestigde gevallen" in p                    # the mpox figures for Kinshasa
    assert "<guidance>" not in p and "example.org/richtlijn" in p
    rec = json.loads((Path(res["advice_dir"]) / "advies.json").read_text(encoding="utf-8"))
    assert rec["type"] == "casus" and rec["outbreaks"] == ["mpox_cod_2026"] and rec["situation"]
    assert log.LOG.read_text(encoding="utf-8").splitlines()[-1].endswith(",casus")


def test_a_question_without_a_place_goes_to_the_outbreak_it_names():
    assert advies._routed({"stops": []}, ["mpox"]) == ["mpox_cod_2026"]
    assert advies._routed({"stops": []}, ["cholera"]) == ["geen"]


def test_an_archived_advice_can_be_relabelled_on_the_record(tmp_path):
    d = tmp_path / "2026-09-25_student"
    d.mkdir()
    (d / "advies.json").write_text(json.dumps({"advised_on": "2026-09-25", "traveller": "Student",
                                               "reply": "de brief"}), encoding="utf-8")
    logfile = tmp_path / "log.csv"
    log.append({"advised_on": "2026-09-25", "traveller": "Student", "advice_dir": str(d)}, path=logfile)
    r = archive.relabel(d, kind="casus", outbreaks=["mpox_cod_2026"], reason="mpox-casus, als ebolareis bewaard",
                        today=TODAY)
    assert (r["type"], r["outbreaks"], r["reply"]) == ("casus", ["mpox_cod_2026"], "de brief")
    assert r["herlabeld"][0]["was"] == {"type": "reisadvies", "outbreaks": ["ebola_cod_2026"]}
    assert log.relabel(str(d), {"type": "casus", "outbreaks": "mpox_cod_2026"}, path=logfile)
    assert logfile.read_text(encoding="utf-8").splitlines()[-1].endswith(",mpox_cod_2026,casus")
