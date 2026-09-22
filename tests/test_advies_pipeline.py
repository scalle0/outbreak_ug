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
