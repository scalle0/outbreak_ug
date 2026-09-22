"""WHO and ECDC are read on every run. A source that is unreachable must be visible, never fatal."""
import json

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
