"""The follow-up after the advice (F-017): which advices are followed, when a go/no-go has come, the
advice next to today's figures per leg, the report, a quiet scheduled run, and a schedule the user
sets. Facts only: no model anywhere. The integration tests use the cached data on a frozen date."""
import json
from datetime import date
from pathlib import Path

import pytest

from dienstreis import archive, cli, opvolging, outbreak, risk

TODAY = date(2026, 11, 20)


def _advice(traveller, stops, advised_on=date(2026, 9, 20), review_on="", kind="reisadvies",
            outbreaks=("ebola_cod_2026",), overrides=()):
    """An archived advice without an analysis behind it: the stops as the summary keeps them."""
    trip = {"traveller": traveller, "type": kind, "review_on": review_on or None,
            "stops": [{"place": p, "from": s, "to": e} for p, s, e, *_ in stops]}
    summary = {"outbreak": outbreaks[0], "overall": "geen ebola-gerelateerd bezwaar", "overrides": list(overrides),
               "stops": [{"place": p, "start": s, "end": e, "category": (rest or ["F"])[0], "cases": 0,
                          "fod": "niet_essentieel_afgeraden", "cdc": 2} for p, s, e, *rest in stops]}
    if len(outbreaks) > 1:
        summary["outbreaks"] = {o: {"stops": summary["stops"]} for o in outbreaks}
    return archive.save({**trip, "review_on": review_on or ""}, summary, "Beste An, ...", advised_on=advised_on)


# ---------------------------------------------------------------- which advices, and when a go/no-go comes
def test_abroad_now_and_leaving_within_the_horizon_are_followed():
    _advice("Nu ter plaatse", [("Kinshasa", "2026-11-10", "2026-11-30")])
    _advice("Binnen 20 dagen", [("Kinshasa", "2026-12-10", "2026-12-20")])
    _advice("Binnen 40 dagen", [("Kinshasa", "2026-12-30", "2027-01-10")])
    _advice("Terug", [("Kinshasa", "2026-10-01", "2026-10-10")])
    _advice("Een vraag", [("Kinshasa", "2026-11-10", "2026-11-30")], kind="vraag")
    _advice("Student", [("Kinshasa", "2026-06-30", "")], kind="casus")          # a case with no return date yet
    names = [r["traveller"] for r in opvolging.candidates(TODAY)]
    assert sorted(names) == ["Binnen 20 dagen", "Nu ter plaatse", "Student"]
    assert [r["traveller"] for r in opvolging.candidates(TODAY, term="binnen 40")] == ["Binnen 40 dagen"]


def test_a_newer_advice_for_the_same_traveller_replaces_the_older():
    _advice("Reiziger T", [("Kinshasa", "2026-11-28", "2026-12-05")], advised_on=date(2026, 9, 1))
    new = _advice("Reiziger T", [("Kinshasa", "2026-11-28", "2026-12-12")], advised_on=date(2026, 10, 1))
    assert [r["dir"] for r in opvolging.candidates(TODAY)] == [str(new)]


def test_a_go_no_go_is_due_until_it_is_marked_or_the_traveller_has_left():
    d = _advice("Reiziger T", [("Kinshasa", "2026-11-28", "2026-12-05")], review_on="2026-11-20")
    r = opvolging.candidates(TODAY)[0]
    assert opvolging.due(r, TODAY) and not opvolging.due(r, date(2026, 11, 19))
    assert not opvolging.due(r, date(2026, 11, 29))                             # left: the field watch goes on
    opvolging.mark_done(d, "Kisangani geschrapt", today=TODAY)
    r = opvolging.candidates(TODAY)[0]
    assert not opvolging.due(r, TODAY) and r["go_no_go"]["notitie"] == "Kisangani geschrapt"


# ---------------------------------------------------------------- then versus now, per leg
def _now(place, cat, cases=0, fod=None, cdc=None, rule=None, reason=None):
    return risk.StopRisk(place=place, start=None, end=None, nights=None, lodging=None, transit_only=False,
                         lat=0, lon=0, country="COD", zone=place, category=cat, cases=cases, fod=fod, cdc=cdc,
                         rule_category=rule, override_reason=reason, spec=outbreak.default())


def test_the_change_of_a_leg_is_read_on_the_rules():
    spec = outbreak.default()
    then = [{"place": "Kinshasa", "category": "F", "cases": 0}, {"place": "Kisangani", "category": "B", "cases": 5}]
    legs, status = opvolging.compare(then, [_now("Kinshasa", "D"), _now("Kisangani", "B", 5)], spec)
    assert status == "strenger" and [x["change"] for x in legs] == ["strenger", ""]
    assert opvolging.compare(then, [_now("Kinshasa", "F"), _now("Kisangani", "C", 5)], spec)[1] == "milder"
    assert opvolging.compare(then, [_now("Kinshasa", "F"), _now("Kisangani", "B", 7)], spec)[1] == "nieuwe gevallen"
    assert opvolging.compare(then, [_now("Kinshasa", "F"), _now("Kisangani", "B", 5)], spec)[1] == "ongewijzigd"


def test_an_overrule_stays_but_the_rule_under_it_is_compared():
    spec = outbreak.default()
    then = [{"place": "Kisangani", "category": "C", "rule_category": "A", "override_reason": "compound", "cases": 9}]
    legs, status = opvolging.compare(then, [_now("Kisangani", "C", 9, rule="B", reason="compound")], spec)
    assert status == "milder" and legs[0]["then"] == "A" and legs[0]["now"] == "B" and legs[0]["override"] == "compound"


def test_a_stricter_fod_or_cdc_level_counts_as_stricter():
    spec = outbreak.default()
    then = [{"place": "Kinshasa", "category": "F", "cases": 0, "fod": "niet_essentieel_afgeraden", "cdc": 2}]
    assert opvolging.compare(then, [_now("Kinshasa", "F", fod="formeel_afgeraden", cdc=2)], spec)[1] == "strenger"
    assert opvolging.compare(then, [_now("Kinshasa", "F", fod="niet_essentieel_afgeraden", cdc=3)], spec)[1] == "strenger"


def test_an_outbreak_that_did_not_apply_then_is_new():
    legs, status = opvolging.compare(None, [_now("Kisangani", "A", 20)], outbreak.default())
    assert status == "strenger" and legs[0]["change"] == "nieuw"


# ---------------------------------------------------------------- on the real (cached) figures
@pytest.fixture()
def ebola_only(monkeypatch):
    monkeypatch.setattr(outbreak, "active", lambda: [outbreak.default()])


def test_an_advice_is_checked_against_todays_figures(ebola_only):
    """Advised when Kisangani was unaffected (F); on the figures of 19/09 it has a recent case (A)."""
    _advice("Reiziger T", [("Kinshasa", "2026-11-28", "2026-12-05", "F"), ("Kisangani", "2026-12-06", "2026-12-13", "F")],
            review_on="2026-11-20")
    rep = opvolging.run(today=TODAY, asof="2026-09-19", figures=False)
    x = rep["results"][0]
    assert x["due"] and x["status"] == "strenger"
    legs = {leg["place"]: leg for leg in x["parts"][0]["legs"]}
    assert legs["Kisangani"]["then"] == "F" and legs["Kisangani"]["now"] == "A" and legs["Kisangani"]["change"] == "strenger"
    assert legs["Kinshasa"]["now"] == "F" and x["parts"][0]["asof"] == "2026-09-19"
    page = Path(rep["page"]).read_text(encoding="utf-8")
    assert "Go/no-go: de beslissing valt nu" in page and "F → A" in page and "dienstreis opvolging --klaar" in page
    assert '<span class="badge stop">1 strenger dan in het advies</span>' in page       # counted, go/no-go or not
    assert json.loads((Path(rep["page"]).parent / "opvolging.json").read_text(encoding="utf-8"))["results"][0]["status"] == "strenger"


def test_an_advice_from_before_f017_is_rebuilt_from_its_summary(ebola_only):
    d = _advice("Reiziger O", [("Kisangani", "2026-11-28", "2026-12-05", "A")],
                overrides=[{"scope": "stop Kisangani", "van": "A", "naar": "C", "reason": "compound"}])
    (Path(d) / "stops.yaml").unlink()
    x = opvolging.run(today=TODAY, asof="2026-09-19", figures=False)["results"][0]
    leg = x["parts"][0]["legs"][0]
    assert (leg["place"], leg["then"], leg["now"]) == ("Kisangani", "A", "A")
    assert any("overrules zijn niet opnieuw toegepast" in n for n in x["notes"])
    # the synthetic advice had FOD 'niet essentieel' and CDC 2; Tshopo is formally advised against now
    assert leg["fod_now"] == "formeel_afgeraden" and x["status"] == "strenger"


def test_an_outbreak_that_applies_now_is_named(monkeypatch):
    monkeypatch.setattr(outbreak, "active", lambda: [outbreak.default(), outbreak.load("mpox_cod_2026")])
    _advice("Reiziger M", [("Kinshasa", "2026-11-28", "2026-12-05", "F")])
    x = opvolging.run(today=TODAY, asof="2026-09-19", figures=False)["results"][0]
    assert [p["id"] for p in x["parts"]] == ["ebola_cod_2026", "mpox_cod_2026"] and x["parts"][1]["new"]
    assert any("Mpox (clade I) geldt nu voor deze reis" in n for n in x["notes"])


def test_a_trip_that_got_stricter_gets_its_map_and_curve(ebola_only):
    _advice("Reiziger T", [("Kisangani", "2026-12-06", "2026-12-13", "F")])
    x = opvolging.run(today=TODAY, asof="2026-09-19")["results"][0]
    assert x["status"] == "strenger" and any(Path(f).name.startswith("kaart_") for f in x["figures"])
    page = Path(opvolging.ROOT / TODAY.isoformat() / "opvolging.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," in page


# ---------------------------------------------------------------- a quiet run, and a schedule
def test_a_quiet_run_opens_the_page_only_for_something_new():
    rep = {"results": [{"dir": "a", "status": "strenger", "due": False, "parts": [{"legs": [{"now": "A"}]}]}]}
    assert opvolging.news_since_last(rep) is True
    assert opvolging.news_since_last(rep) is False                               # the same as last time
    calm = {"results": [{"dir": "a", "status": "ongewijzigd", "due": False, "parts": [{"legs": [{"now": "F"}]}]}]}
    assert opvolging.news_since_last(calm) is False                              # changed, but nothing to see


def test_the_schedule_is_the_users_own():
    cmd = opvolging.plan_commands("weekdagen", "07:30", exe='"C:\\x\\dienstreis.exe"')[0]
    assert cmd[:5] == ["schtasks", "/Create", "/F", "/TN", "dienstreis opvolging"]
    assert '"C:\\x\\dienstreis.exe" opvolging --stil' in cmd and "MON,TUE,WED,THU,FRI" in cmd and cmd[-1] == "07:30"
    assert opvolging.plan_commands("uit") == [["schtasks", "/Delete", "/F", "/TN", "dienstreis opvolging"]]
    with pytest.raises(ValueError):
        opvolging.plan_commands("dagelijks", "8u")


def test_the_command_marks_a_go_no_go_as_decided(capsys):
    d = _advice("Reiziger T", [("Kinshasa", "2026-11-28", "2026-12-05")], review_on="2026-11-20")
    cli.main(["opvolging", "--klaar", Path(d).name, "--notitie", "doorgaan zonder Kisangani"])   # the name will do
    rec = json.loads((Path(d) / "advies.json").read_text(encoding="utf-8"))
    assert rec["go_no_go"]["notitie"] == "doorgaan zonder Kisangani"
    assert "Go/no-go van Reiziger T genoteerd" in capsys.readouterr().out


def test_the_archive_keeps_the_itinerary_as_confirmed():
    d = _advice("Reiziger T", [("Kinshasa", "2026-11-28", "2026-12-05")])
    assert "Kinshasa" in (Path(d) / "stops.yaml").read_text(encoding="utf-8")
