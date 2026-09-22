"""Fetching: what is downloaded, when, and what is left alone.

The zone shapefile is 66 MB and its boundaries do not change; the INSP figures change daily. These
tests pin that the two are fetched on separate clocks and that an unchanged file is not re-sent.
No network: git and requests are both replaced.
"""
import time

import pytest

from dienstreis import data


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "CACHE", tmp_path)
    monkeypatch.setattr(data.shutil, "which", lambda n: None)     # force the no-git path
    return tmp_path


class FakeResponse:
    def __init__(self, status=200, body=b"x", headers=None):
        self.status_code, self.content, self.headers = status, body, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def recorder(monkeypatch, responder=None):
    """Replace requests.get and record which paths were asked for, with which headers."""
    calls = []

    def get(url, timeout=None, headers=None):
        f = url.replace(data.INRB_RAW, "")
        calls.append((f, dict(headers or {})))
        return (responder or (lambda f, h: FakeResponse(headers={"ETag": f'"{f}"'})))(f, headers or {})

    monkeypatch.setattr(data.requests, "get", get)
    return calls


def test_first_run_fetches_everything(cache, monkeypatch):
    calls = recorder(monkeypatch)
    data.fetch_inrb()
    assert {f for f, _ in calls} == set(data.NEEDED)


def test_second_run_within_six_hours_fetches_nothing(cache, monkeypatch):
    recorder(monkeypatch)
    data.fetch_inrb()
    calls = recorder(monkeypatch)
    data.fetch_inrb()
    assert calls == []


def test_stale_figures_do_not_drag_the_shapefile_along(cache, monkeypatch):
    """The point of the split: after six hours only the daily figures are refetched."""
    recorder(monkeypatch)
    data.fetch_inrb()
    old = time.time() - 7 * 3600
    import os
    os.utime(cache / "inrb" / ".dienstreis_fetched", (old, old))

    calls = recorder(monkeypatch)
    data.fetch_inrb()
    asked = {f for f, _ in calls}
    assert asked == set(data.DAILY)
    assert not asked & set(data.SHAPES)


def test_shapefile_is_refetched_once_it_is_really_old(cache, monkeypatch):
    recorder(monkeypatch)
    data.fetch_inrb()
    old = time.time() - (data.SHAPES_MAX_AGE_H + 1) * 3600
    import os
    os.utime(cache / "inrb" / ".dienstreis_shapes", (old, old))

    calls = recorder(monkeypatch)
    data.fetch_inrb()
    assert set(data.SHAPES) <= {f for f, _ in calls}


def test_unchanged_file_is_not_downloaded_again(cache, monkeypatch):
    """A 304 keeps the cached bytes: the server sends no body for an unchanged shapefile."""
    recorder(monkeypatch)
    data.fetch_inrb()
    (cache / "inrb" / data.SHAPES[0]).write_bytes(b"cached bytes")

    seen = []

    def responder(f, headers):
        seen.append((f, headers.get("If-None-Match")))
        return FakeResponse(status=304, body=b"")

    calls = recorder(monkeypatch, responder)
    data.fetch_inrb(refresh=True)
    assert all(etag for _, etag in seen), "conditional request not sent"
    assert (cache / "inrb" / data.SHAPES[0]).read_bytes() == b"cached bytes"
    assert len(calls) == len(data.NEEDED)


def test_refresh_asks_for_everything(cache, monkeypatch):
    recorder(monkeypatch)
    data.fetch_inrb()
    calls = recorder(monkeypatch)
    data.fetch_inrb(refresh=True)
    assert {f for f, _ in calls} == set(data.NEEDED)


def test_missing_file_is_refetched_even_when_fresh(cache, monkeypatch):
    recorder(monkeypatch)
    data.fetch_inrb()
    (cache / "inrb" / data.DAILY[0]).unlink()
    calls = recorder(monkeypatch)
    data.fetch_inrb()
    assert data.DAILY[0] in {f for f, _ in calls}


def test_git_lfs_pointer_is_refused(cache, monkeypatch):
    recorder(monkeypatch, lambda f, h: FakeResponse(body=b"version https://git-lfs.github.com/spec/v1"))
    with pytest.raises(RuntimeError, match="LFS"):
        data.fetch_inrb()


def test_sparse_clone_limits_the_checkout(tmp_path, monkeypatch):
    """With git, only the needed blobs and paths are asked for; a full clone is ~330 MB."""
    monkeypatch.setattr(data, "CACHE", tmp_path)
    monkeypatch.setattr(data.shutil, "which", lambda n: "git")
    cmds = []

    def fake_git(*args, cwd=None):
        cmds.append(list(args))
        if args[1] == "clone":                       # materialise what the clone would produce
            repo = tmp_path / "inrb"
            for f in data.NEEDED:
                (repo / f).parent.mkdir(parents=True, exist_ok=True)
                (repo / f).write_bytes(b"x")
            (repo / ".git").mkdir(parents=True, exist_ok=True)
        return None

    monkeypatch.setattr(data, "_git", fake_git)
    data.fetch_inrb()
    clone = next(c for c in cmds if c[1] == "clone")
    assert "--filter=blob:none" in clone and "--sparse" in clone
    sparse = next(c for c in cmds if "sparse-checkout" in c)
    assert set(data.NEEDED) <= set(sparse)


def test_cache_size_and_reset(cache, monkeypatch):
    recorder(monkeypatch)
    data.fetch_inrb()
    assert data.cache_size_mb() > 0
    freed = data.reset_cache()
    assert freed > 0 and not cache.exists()
