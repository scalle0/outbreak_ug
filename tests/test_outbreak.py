"""Outbreak profiles: read and checked before any advice uses them, and applied where they belong.

No network, no model. The Ebola output itself is pinned by test_golden.py; these tests pin the
mechanism: a broken profile is refused whole, prompt passages land where the template asks, and
the code takes what differs per outbreak from the profile rather than from itself.
"""
import shutil

import pytest
import yaml

from dienstreis import data, mail, msg, outbreak


def test_every_profile_in_the_repo_loads():
    assert outbreak.DEFAULT in outbreak.ids()
    for i in outbreak.ids():
        s = outbreak.load(i)
        assert s.id == i and s.dir.name == i


def _copy_default(tmp_path, name="kopie", **changes):
    """A copy of the default profile in a temporary folder, with some keys changed or removed."""
    folder = tmp_path / name
    shutil.copytree(outbreak.default().dir, folder)
    cfg = yaml.safe_load((folder / "outbreak.yaml").read_text(encoding="utf-8"))
    cfg["id"] = name
    for k, v in changes.items():
        if v is None:
            cfg.pop(k, None)
        else:
            cfg[k] = v
    (folder / "outbreak.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return folder


def test_a_copy_of_the_default_profile_is_valid(tmp_path):
    s = outbreak.OutbreakSpec(_copy_default(tmp_path))
    assert s.windows == outbreak.default().windows and s.sections == outbreak.default().sections


def test_a_broken_profile_is_refused_with_every_problem(tmp_path):
    cats = dict(outbreak.default().categories)
    cats["C"] = {**cats["C"], "level": "misschien"}
    cats.pop("X")
    folder = _copy_default(tmp_path, categories=cats, windows={"active": 42, "clear": 21},
                           overall={"afraden": "x"})
    with pytest.raises(outbreak.ProfileError) as e:
        outbreak.OutbreakSpec(folder)
    msg_ = str(e.value)
    for part in ("categorie C", "categorie X", "windows", "voorwaardelijk, geen_bezwaar"):
        assert part in msg_


def test_missing_keys_are_named(tmp_path):
    with pytest.raises(outbreak.ProfileError, match="conditions"):
        outbreak.OutbreakSpec(_copy_default(tmp_path, conditions=None))


def test_folder_name_and_id_must_agree(tmp_path):
    folder = _copy_default(tmp_path)
    cfg = yaml.safe_load((folder / "outbreak.yaml").read_text(encoding="utf-8"))
    cfg["id"] = "iets_anders"
    (folder / "outbreak.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(outbreak.ProfileError, match="mapnaam"):
        outbreak.OutbreakSpec(folder)


def test_unknown_profile_names_the_known_ones():
    with pytest.raises(outbreak.ProfileError, match=outbreak.DEFAULT):
        outbreak.load("pest_2099")


def test_prompt_sections_keep_trailing_spaces_and_drop_trailing_blank_lines(tmp_path):
    p = tmp_path / "prompt.md"
    p.write_text("preamble\n<!-- uitbraak:a -->\neen regel \n\n\n<!-- uitbraak:b -->\ntwee\n", encoding="utf-8")
    assert outbreak._sections(p) == {"a": "een regel ", "b": "twee"}


def test_fill_puts_the_passage_where_the_template_asks():
    s = outbreak.default()
    out = outbreak.fill("voor {{uitbraak:opdracht}} na", [s])
    assert out == f"voor {s.sections['opdracht']} na"


def test_fill_refuses_a_passage_no_profile_has():
    with pytest.raises(outbreak.ProfileError, match="bestaat_niet"):
        outbreak.fill("{{uitbraak:bestaat_niet}}")


def test_rule_windows_of_the_profile_are_always_allowed_numbers():
    s = outbreak.default()
    assert {str(s.windows["active"]), str(s.windows["clear"])} <= mail._always_ok([s])
    assert mail.unknown_numbers(f"na {s.windows['clear']} dagen", [], [s]) == []


def test_outbreak_words_come_from_the_profiles(tmp_path):
    req = tmp_path / "aanvraag.txt"
    req.write_text("Van: Iemand\nIk reis naar een gebied met Bundibugyo.\n", encoding="utf-8")
    assert msg.parse_request(req)["traveller_mentions_outbreak"] is True
    req.write_text("Van: Iemand\nGewoon een congres.\n", encoding="utf-8")
    assert msg.parse_request(req)["traveller_mentions_outbreak"] is False


def test_a_source_the_profile_does_not_name_is_not_a_failure(tmp_path, monkeypatch):
    s = outbreak.OutbreakSpec(_copy_default(tmp_path, sources={"national": "X", "mail": []}))

    def boom(*a, **k):
        raise AssertionError("no request for a source the profile does not name")
    monkeypatch.setattr(data.requests, "get", boom)
    assert data.ecdc_snapshot(spec=s) == {"ok": False, "reason": data.NOT_CONFIGURED}
    assert data.who_snapshot(spec=s)["reason"] == data.NOT_CONFIGURED
