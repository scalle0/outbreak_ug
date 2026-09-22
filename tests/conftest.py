"""Every test writes its log, context and local advisories to a temporary folder, never to the user's files."""
import pytest

from dienstreis import advies, log, risk


@pytest.fixture(autouse=True)
def _isolate_user_files(tmp_path, monkeypatch):
    monkeypatch.setattr(log, "LOG", tmp_path / "advice_log.csv")
    monkeypatch.setattr(advies, "CONTEXT", tmp_path / "context.md")
    monkeypatch.setattr(risk, "LOCAL_ADVISORIES", tmp_path / "advisories.yaml")
