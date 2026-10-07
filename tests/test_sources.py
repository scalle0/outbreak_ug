"""WHO and ECDC are read on every run. A source that is unreachable must be visible, never fatal."""
import json
from pathlib import Path

import pytest

from dienstreis import data


class R:
    def __init__(self, payload=None, status=200, text=""):
        self._p, self.status_code, self.text = payload, status, text

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


DON = {"value": [
    {"Title": "Cholera - Somewhere", "PublicationDateAndTime": "2026-09-15T00:00:00Z",
     "ItemDefaultUrl": "/2026-DON900"},
    {"Title": "Ebola disease caused by Bundibugyo virus - Democratic Republic of the Congo",
     "PublicationDateAndTime": "2026-09-10T00:00:00Z", "ItemDefaultUrl": "/2026-DON617"},
]}


def test_who_picks_the_drc_ebola_item_not_the_newest(monkeypatch):
    monkeypatch.setattr(data.requests, "get", lambda *a, **k: R(DON))
    d = data.who_snapshot()
    assert d["ok"] and d["date"] == "2026-09-10" and "Bundibugyo" in d["item"]
    assert d["url"].endswith("/2026-DON617") and "//2026" not in d["url"]


def test_who_reports_how_old_the_item_is(monkeypatch):
    monkeypatch.setattr(data.requests, "get", lambda *a, **k: R(DON))
    assert isinstance(data.who_snapshot()["days_old"], int)


def test_who_without_a_drc_item_fails_soft(monkeypatch):
    monkeypatch.setattr(data.requests, "get", lambda *a, **k: R({"value": [DON["value"][0]]}))
    d = data.who_snapshot()
    assert d["ok"] is False and "no DRC Ebola item" in d["reason"] and d["url"]


def test_who_network_failure_fails_soft(monkeypatch):
    def boom(*a, **k):
        raise OSError("geen netwerk")
    monkeypatch.setattr(data.requests, "get", boom)
    d = data.who_snapshot()
    assert d["ok"] is False and "geen netwerk" in d["reason"]



def test_who_asks_only_for_the_fields_it_reads(monkeypatch):
    """2026-10-07: with the full text of every item the answer was 600 kB and timed out."""
    seen = []
    monkeypatch.setattr(data.requests, "get", lambda url, **k: (seen.append(k), R(DON))[1])
    data.who_snapshot()
    assert seen[0]["params"]["$select"] == "Title,PublicationDateAndTime,ItemDefaultUrl"


def test_who_tries_again_after_a_timeout_or_a_busy_server(monkeypatch):
    answers = [data.requests.ReadTimeout("read timed out"), R(status=503), R(DON)]

    def get(*a, **k):
        x = answers.pop(0)
        if isinstance(x, Exception):
            raise x
        return x
    monkeypatch.setattr(data.requests, "get", get)
    assert data.who_snapshot()["ok"] and not answers


def test_a_client_error_is_not_tried_again(monkeypatch):
    calls = []
    monkeypatch.setattr(data.requests, "get", lambda *a, **k: (calls.append(1), R(status=404))[1])
    assert data.who_snapshot()["ok"] is False and len(calls) == 1


def test_unreachable_who_falls_back_on_the_last_item_read(monkeypatch):
    monkeypatch.setattr(data.requests, "get", lambda *a, **k: R(DON))
    live = data.who_snapshot()

    def timeout(*a, **k):
        raise data.requests.ReadTimeout("read timed out")
    monkeypatch.setattr(data.requests, "get", timeout)
    d = data.who_snapshot()
    assert d["ok"] and d["from_cache"] and d["item"] == live["item"] and d["date"] == "2026-09-10"
    assert d["read_on"] and "read timed out" in d["reason"]
    # never seen before: unreachable, as before
    monkeypatch.setattr(data, "WHO_LAST", data.WHO_LAST.with_name("leeg.json"))
    assert data.who_snapshot()["ok"] is False

def test_who_garbage_payload_fails_soft(monkeypatch):
    monkeypatch.setattr(data.requests, "get", lambda *a, **k: R({"unexpected": 1}))
    assert data.who_snapshot()["ok"] is False


def test_sources_snapshot_reads_both(monkeypatch):
    monkeypatch.setattr(data, "who_snapshot", lambda *a, **k: {"ok": True, "item": "x"})
    monkeypatch.setattr(data, "ecdc_snapshot", lambda *a, **k: {"ok": True, "cases": 1})
    s = data.sources_snapshot()
    assert set(s) == {"ecdc", "who"} and s["who"]["ok"] and s["ecdc"]["ok"]


def test_asof_run_skips_the_live_sources(monkeypatch):
    """A frozen-date run must not mix today's WHO page into last month's figures."""
    def boom(*a, **k):
        raise AssertionError("should not be called")
    monkeypatch.setattr(data, "who_snapshot", boom)
    monkeypatch.setattr(data, "ecdc_snapshot", boom)
    s = data.sources_snapshot("2026-09-19")
    assert all(v["reason"] == "asof run" for v in s.values())


def test_unreachable_source_reaches_the_notes(tmp_path, monkeypatch):
    """A source that could not be read must be visible in the advice, not only in the QA dict."""
    from dienstreis import advies, archive, llm
    import json as _json

    monkeypatch.setattr(archive, "ARCHIVE", tmp_path / "adviezen")
    monkeypatch.setattr(advies, "CONTEXT", tmp_path / "context.md")
    monkeypatch.setattr(data, "who_snapshot", lambda *a, **k: {"ok": False, "reason": "geen netwerk"})

    req = tmp_path / "aanvraag.txt"
    req.write_text("Beste Steven,\n\nVan: Iemand\nKinshasa 28/11/2026 tot 05/12/2026.\n", encoding="utf-8")
    stops = {"traveller": "Reiziger W", "profile": {"lodging": "hotel"},
             "stops": [{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-05"}]}
    reply = "Beste An,\n\nKinshasa geeft geen bezwaar.\n\nMet vriendelijke groet,\nSteven Callens"
    fake = llm.Fake({"stops": stops, "reply": {"reply": reply, "suggestions": []}})
    res = advies.run_advies(str(req), out=str(tmp_path / "out"), yes=True, open_browser=False,
                            llm_backend=fake, web=False)
    assert "who" in res["summary"]["qa"]["sources_unreachable"]
    assert any("WHO" in s and "niet bereikbaar" in s for s in res["suggestions"])



def test_a_who_item_from_the_last_read_reaches_the_notes(tmp_path, monkeypatch):
    """Not unreachable, but not live either: the advice says which item stood in and from when."""
    from dienstreis import advies, archive, llm

    monkeypatch.setattr(archive, "ARCHIVE", tmp_path / "adviezen")
    monkeypatch.setattr(data, "who_snapshot", lambda *a, **k: {
        "ok": True, "from_cache": True, "read_on": "2026-10-06", "date": "2026-09-10", "days_old": 27,
        "item": "Ebola disease caused by Bundibugyo virus - Democratic Republic of the Congo",
        "url": data.WHO_DON_URL, "reason": "ReadTimeout('read timed out')"})
    req = tmp_path / "aanvraag.txt"
    req.write_text("Beste Steven,\n\nVan: Iemand\nKinshasa 28/11/2026 tot 05/12/2026.\n", encoding="utf-8")
    stops = {"traveller": "Reiziger W", "profile": {"lodging": "hotel"},
             "stops": [{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-05"}]}
    reply = "Beste An,\n\nKinshasa geeft geen bezwaar.\n\nMet vriendelijke groet,\nSteven Callens"
    fake = llm.Fake({"stops": stops, "reply": {"reply": reply, "suggestions": []}})
    res = advies.run_advies(str(req), out=str(tmp_path / "out"), yes=True, open_browser=False,
                            llm_backend=fake, web=False)
    qa = res["summary"]["qa"]
    assert qa["sources_cached"] == ["who"] and "who" not in qa["sources_unreachable"]
    note = next(s for s in res["suggestions"] if s.startswith("WHO") and "was niet bereikbaar" in s)
    assert "gelezen op 2026-10-06" in note and "Kijk na of er een nieuwer is." in note
    assert "laatst gelezen op" in Path(res["dossier"]).read_text(encoding="utf-8")

def test_nothing_found_is_not_unreachable(monkeypatch, tmp_path):
    """A live run reported WHO 'niet bereikbaar' when it had only found no item about the outbreak."""
    from datetime import date as _date
    from dienstreis import pipeline
    monkeypatch.setattr(data.requests, "get", lambda *a, **k: R({"value": [DON["value"][0]]}))
    assert data.who_snapshot()["none_found"] is True
    monkeypatch.setattr(data, "who_snapshot", lambda *a, **k: {"ok": False, "reason": "no item", "none_found": True})
    trip = {"traveller": "R", "stops": [{"place": "Addis Ababa", "from": _date(2026, 11, 1), "to": _date(2026, 11, 5)}]}
    assert pipeline.analyse(trip, tmp_path / "out")["qa"]["sources_unreachable"] == []


# ---------------------------------------------------------------- ECDC next to the national figures
def _ecdc(cases, until):
    return {"ok": True, "cases": cases, "deaths": 1, "data_until": until}


def test_ecdc_a_few_days_ahead_is_a_lag_not_a_failure():
    """Proefrun 2026-10-07: ECDC 8 603 to 4/10 against INSP 8 442 to 2/10 was reported as 'QA faalde'."""
    import pandas as pd
    from dienstreis import mail
    c = mail.ecdc_check(_ecdc(8603, "4 October"), {"last_total": 8442}, pd.Timestamp("2026-10-02"))["check"]
    assert c["status"] == "ecdc_nieuwer" and c["matches"] is None and c["days_ahead"] == 2
    assert c["text"] == ("ECDC telt 8 603 gevallen tot 4 oktober, de nationale cijfers 8 442 tot 2 oktober: "
                         "de zonecijfers lopen 2 dagen achter op ECDC (+161 gevallen).")


def test_ecdc_on_the_same_day_must_agree():
    from datetime import date
    from dienstreis import mail
    same = mail.ecdc_check(_ecdc(8442, "2 October"), {"last_total": 8442}, date(2026, 10, 2))["check"]
    assert same["status"] == "gelijk" and same["matches"] is True
    off = mail.ecdc_check(_ecdc(8450, "2 October"), {"last_total": 8442}, date(2026, 10, 2))["check"]
    assert off["status"] == "wijkt_af" and off["matches"] is False and "verschil van 8" in off["text"]


def test_ecdc_behind_or_across_new_year_is_not_compared():
    from datetime import date
    from dienstreis import mail
    behind = mail.ecdc_check(_ecdc(8000, "28 September"), {"last_total": 8442}, date(2026, 10, 2))["check"]
    assert behind["status"] == "ecdc_ouder" and behind["matches"] is None
    newyear = mail.ecdc_check(_ecdc(9100, "2 January"), {"last_total": 9000}, date(2026, 12, 30))
    assert newyear["data_until_date"] == "2027-01-02" and newyear["check"]["days_ahead"] == 3


def test_an_unreadable_ecdc_date_falls_back_on_the_totals():
    from datetime import date
    from dienstreis import mail
    c = mail.ecdc_check(_ecdc(8603, "early October"), {"last_total": 8442}, date(2026, 10, 2))["check"]
    assert c["status"] == "wijkt_af" and c["matches"] is False


def test_the_notes_say_ecdc_runs_ahead_and_do_not_call_it_a_failure():
    from dienstreis import advies
    check = {"status": "ecdc_nieuwer", "matches": None, "days_ahead": 2, "text": "ECDC loopt 2 dagen voor."}
    s = {"outbreak": "ebola_cod_2026", "qa": {"zone_sum_matches_national": True, "ecdc_matches": None,
                                              "ecdc": {"ok": True, "check": check}}}
    assert advies._figure_checks(s) == ([], ["ECDC loopt 2 dagen voor."])
    s["qa"]["ecdc"]["check"] = {**check, "status": "wijkt_af", "matches": False, "text": "Verschil."}
    assert advies._figure_checks(s) == (["Verschil."], [])
