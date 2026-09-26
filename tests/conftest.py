"""Every test writes its log, context, local country registry, case tables, documents and fiches to a temporary
folder, never to the user's files, and never reads the user's local copies either."""
import pytest

from dienstreis import advies, archive, countries, data, fiche, log


@pytest.fixture(autouse=True)
def _isolate_user_files(tmp_path, monkeypatch):
    monkeypatch.setattr(log, "LOG", tmp_path / "advice_log.csv")
    monkeypatch.setattr(advies, "CONTEXT", tmp_path / "context.md")
    monkeypatch.setattr(countries, "LOCAL", tmp_path / "countries")
    monkeypatch.setattr(countries, "LEGACY", tmp_path / "advisories.yaml")
    monkeypatch.setattr(data, "LOCAL_OUTBREAKS", tmp_path / "outbreaks")
    monkeypatch.setattr(fiche, "LOCAL", tmp_path / "outbreaks")
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path / "adviezen")
