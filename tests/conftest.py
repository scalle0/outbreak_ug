"""Every test writes its log, context and local country registry to a temporary folder, never to the user's files."""
import pytest

from dienstreis import advies, archive, countries, log


@pytest.fixture(autouse=True)
def _isolate_user_files(tmp_path, monkeypatch):
    monkeypatch.setattr(log, "LOG", tmp_path / "advice_log.csv")
    monkeypatch.setattr(advies, "CONTEXT", tmp_path / "context.md")
    monkeypatch.setattr(countries, "LOCAL", tmp_path / "countries")
    monkeypatch.setattr(countries, "LEGACY", tmp_path / "advisories.yaml")
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path / "adviezen")
