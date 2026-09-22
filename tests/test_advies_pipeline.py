"""End-to-end test of `dienstreis advies` with a fake LLM: no model calls, frozen data date.

Checks that the deterministic steps run around the LLM steps, that the prompts carry the
right inputs, that the text checks trigger one repair round, and that the outputs exist.
"""
import json
from pathlib import Path

import pytest

from dienstreis import advies, llm, log, risk

REQ = """Beste Steven,

Nieuwe aanvraag:
28/11 - 5/12 Kinshasa
6/12-13/12 Kisangani - Tshopo

Graag jouw advies. Geldt de 21-dagen regel?

An

Van: Iemand
REISINFO
Bestemming: Kisangani
Accommodatie: hotel
"""

STOPS = {"traveller": "Reiziger T", "note": "veldwerk", "profile": {"lodging": "hotel", "healthcare_work": False},
         "review_on": "2026-11-20",
         "stops": [{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-05"},
                   {"place": "Kisangani", "from": "2026-12-06", "to": "2026-12-13"}],
         "questions_from_an": ["Geldt de 21-dagenregel?"], "contradictions": [], "missing_info": ["vervoer"]}

GOOD = ("Beste An,\n\nKinshasa kan, Kisangani raad ik momenteel af.\n\n1. Kinshasa: geen bezwaar.\n"
        "2. Kisangani: af te raden.\n\nMet vriendelijke groet,\nSteven Callens")
BAD = GOOD.replace("Kinshasa kan,", "Kinshasa kan — cruciaal punt —")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(advies, "CONTEXT", tmp_path / "context.md")
    monkeypatch.setattr(log, "LOG", tmp_path / "log.csv")
    monkeypatch.setattr(risk, "LOCAL_ADVISORIES", tmp_path / "advisories.yaml")
    (tmp_path / "context.md").write_text("- 2026-09-10: Kisangani-luik Hubeau afgeraden\n", encoding="utf-8")
    req = tmp_path / "aanvraag.txt"
    req.write_text(REQ, encoding="utf-8")
    return tmp_path, req


def test_pipeline_with_repair(env, monkeypatch):
    tmp, req = env
    replies = iter([{"reply": BAD, "suggestions": ["x"]},
                    {"reply": GOOD, "suggestions": ["commitment: go/no-go 20/11"], "review_on": "2026-11-20",
                     "context_update": "2026-09-22: Reiziger T, Kisangani afgeraden"}])
    fake = llm.Fake({"stops": STOPS, "reply": lambda p: json.dumps(next(replies), ensure_ascii=False)})
    res = advies.run_advies(str(req), out=str(tmp / "out"), yes=True, asof="2026-09-19",
                            open_browser=False, llm_backend=fake)
    out = Path(res["out"])
    # deterministic categories unchanged by the LLM
    assert "".join(s["category"] for s in res["summary"]["stops"]) == "FA"
    # the reply prompt carried the skeleton, the risk table, An's question and the context
    p = fake.prompts["reply"][0]
    assert "<skelet>" in p and "Makiso Kisangani" in p and "21-dagenregel" in p and "Hubeau" in p
    # first answer failed the text checks -> exactly one repair round with the problems listed
    assert len(fake.prompts["reply"]) == 2 and "em-dash" in fake.prompts["reply"][1]
    assert (out / "reply.txt").read_text(encoding="utf-8").startswith("Beste An,")
    assert "—" not in (out / "reply.txt").read_text(encoding="utf-8")
    assert list(out.glob("reply_*.html")) and list(out.glob("kaart_*.png")) and (out / "stops.yaml").exists()
    assert "Reiziger T" in (tmp / "context.md").read_text(encoding="utf-8")
    assert "Reiziger T" in (tmp / "log.csv").read_text(encoding="utf-8")


INVENTED = GOOD.replace("2. Kisangani: af te raden.",
                        "2. Kisangani: af te raden, met 8 421 bevestigde gevallen.")


def test_invented_number_triggers_a_repair_round(env):
    """A case count that is in no calculated figure must not reach the widget."""
    tmp, req = env
    replies = iter([{"reply": INVENTED, "suggestions": []},
                    {"reply": GOOD, "suggestions": []}])
    fake = llm.Fake({"stops": STOPS, "reply": lambda p: json.dumps(next(replies), ensure_ascii=False)})
    res = advies.run_advies(str(req), out=str(tmp / "out"), yes=True, asof="2026-09-19",
                            open_browser=False, llm_backend=fake)
    assert len(fake.prompts["reply"]) == 2 and "8421" in fake.prompts["reply"][1]
    assert res["issues"] == [] and "8 421" not in (Path(res["out"]) / "reply.txt").read_text(encoding="utf-8")


def test_widget_is_not_built_when_checks_still_fail(env):
    """The widget is the copy-to-Outlook page: never built around text that failed the checks."""
    tmp, req = env
    fake = llm.Fake({"stops": STOPS, "reply": {"reply": INVENTED, "suggestions": []}})
    res = advies.run_advies(str(req), out=str(tmp / "out"), yes=True, asof="2026-09-19",
                            open_browser=False, llm_backend=fake)
    out = Path(res["out"])
    assert res["widget"] is None and not list(out.glob("reply_*.html"))
    assert any("8421" in i for i in res["issues"])
    assert (out / "reply.txt").exists()            # the text is kept so it can be corrected by hand
    assert "8421" in (out / "sugg.txt").read_text(encoding="utf-8")


def test_bad_itinerary_stops_before_the_analysis(env):
    """An unusable itinerary must not be analysed: it would give a wrong table, not an error."""
    tmp, req = env
    broken = {**STOPS, "stops": [{"place": "Doruma", "from": "2026-11-28", "to": "2026-12-05"}]}
    fake = llm.Fake({"stops": broken})
    with pytest.raises(SystemExit) as e:
        advies.run_advies(str(req), out=str(tmp / "out"), yes=True, asof="2026-09-19",
                          open_browser=False, llm_backend=fake)
    assert "niet bruikbaar" in str(e.value)
    assert "reply" not in fake.prompts


def test_non_iso_dates_from_the_model_are_accepted(env):
    """The model returned 28/11/2026 in a live test; that must not crash or drop the nights flag."""
    tmp, req = env
    belgian = {**STOPS, "stops": [{"place": "Kinshasa", "from": "28/11/2026", "to": "05/12/2026"},
                                  {"place": "Kisangani", "from": "06/12/2026", "to": "13/12/2026"}]}
    fake = llm.Fake({"stops": belgian, "reply": {"reply": GOOD, "suggestions": []}})
    res = advies.run_advies(str(req), out=str(tmp / "out"), yes=True, asof="2026-09-19",
                            open_browser=False, llm_backend=fake)
    assert [s["nights"] for s in res["summary"]["stops"]] == [7, 7]
    assert "".join(s["category"] for s in res["summary"]["stops"]) == "FA"


def test_extract_json_variants():
    assert llm.extract_json('tekst ```json\n{"a": 1}\n``` meer') == {"a": 1}
    assert llm.extract_json('voor {"a": "x}y", "b": {"c": 2}} na') == {"a": "x}y", "b": {"c": 2}}
    with pytest.raises(llm.LLMError):
        llm.extract_json("geen json")


def test_ask_json_retries_once():
    answers = iter(["onzin", '{"traveller": "X", "stops": []}'])
    fake = llm.Fake({"stops": lambda p: next(answers)})
    d = llm.ask_json(fake, "stops", {"aanvraag": "..."}, required=["traveller", "stops"])
    assert d["traveller"] == "X" and len(fake.prompts["stops"]) == 2
