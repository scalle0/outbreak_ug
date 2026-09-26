"""The fiche per disease and its documents (F-015): read with a local copy that wins when newer, proposals
from the web step kept only after a yes, a flagged statement shown and never applied, a confirmed fiche
never overwritten by a draft, and only a confirmed one in the letter. No network, no model."""
import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from dienstreis import advies, dossier, fiche, llm, outbreak

TODAY = date(2026, 9, 26)


def _fiche_text(status="concept", verified="2026-09-26", extra="", **meta):
    head = {"outbreak": "ebola_cod_2026", "status": status, "verified": verified, **meta}
    body = "\n".join(f"## {s}\n\nTekst over {s.lower()} [who-factsheet].\n" for s in fiche.SECTIONS)
    return "---\n" + yaml.safe_dump(head, allow_unicode=True) + "---\n\n# Ebola\n\n" + body + extra


DOCS = {"verified": "2026-09-26",
        "be": [{"id": "sciensano-procedure", "org": "Sciensano", "title": "Procedure ebola", "date": "2026-08-01",
                "url": "https://www.sciensano.be/ebola", "key": "Melding binnen 24 uur."}],
        "eu": [], "who": [{"id": "who-factsheet", "org": "WHO", "title": "Ebola factsheet", "date": "2025-04-20",
                           "url": "https://www.who.int/ebola", "key": "Incubatie 2 tot 21 dagen."}],
        "us": []}


@pytest.fixture()
def local(tmp_path, monkeypatch):
    """A local copy for the Ebola profile, verified far in the future so it wins over the package."""
    d = fiche.LOCAL / "ebola_cod_2026"
    d.mkdir(parents=True)
    return d


def test_the_front_matter_and_the_sections_are_read(local):
    (local / fiche.FICHE).write_text(_fiche_text(verified="2099-01-01"), encoding="utf-8")
    f = fiche.load(outbreak.load("ebola_cod_2026"))
    assert f["status"] == "concept" and not f["confirmed"] and f["source"] == "lokaal"
    assert list(f["sections"]) == list(fiche.SECTIONS) and f["issues"] == []
    assert f["refs"] == ["who-factsheet"]


def test_an_unknown_status_is_a_concept_and_a_missing_section_is_named(local):
    text = _fiche_text(status="klaar", verified="2099-01-01").replace("## Diagnose", "## Iets anders")
    (local / fiche.FICHE).write_text(text, encoding="utf-8")
    f = fiche.load(outbreak.load("ebola_cod_2026"))
    assert f["status"] == "concept" and any("klaar" in x for x in f["issues"])
    assert "sectie ontbreekt: Diagnose" in f["issues"]


def test_the_local_copy_wins_only_when_newer(local, tmp_path):
    from types import SimpleNamespace
    pkg = tmp_path / "pakket"                                       # a profile folder of its own, not the repo's
    pkg.mkdir()
    (pkg / fiche.DOCUMENTS).write_text(yaml.safe_dump({**DOCS, "verified": "2026-09-01", "be": []}), encoding="utf-8")
    sp = SimpleNamespace(id="ebola_cod_2026", dir=pkg)
    (local / fiche.DOCUMENTS).write_text(yaml.safe_dump({**DOCS, "verified": "2000-01-01"}), encoding="utf-8")
    assert fiche.documents(sp)["source"] == "pakket" and fiche.documents(sp)["levels"]["be"] == []
    (local / fiche.DOCUMENTS).write_text(yaml.safe_dump({**DOCS, "verified": "2099-01-01"}), encoding="utf-8")
    d = fiche.documents(sp)
    assert d["source"] == "lokaal" and d["levels"]["be"][0]["id"] == "sciensano-procedure"
    assert fiche.check_documents(d) == []


def test_only_a_confirmed_fiche_reaches_the_letter(local):
    sp = outbreak.load("ebola_cod_2026")
    (local / fiche.FICHE).write_text(_fiche_text(verified="2099-01-01"), encoding="utf-8")
    assert fiche.confirmed_text(sp) is None
    (local / fiche.FICHE).write_text(_fiche_text("bevestigd", "2099-01-01", bevestigd_door="Steven Callens",
                                                 bevestigd_op="2026-09-27"), encoding="utf-8")
    assert "Tekst over incubatie" in fiche.confirmed_text(sp)


def test_proposals_add_or_replace_and_keep_the_ids(local):
    sp = outbreak.load("ebola_cod_2026")
    (local / fiche.DOCUMENTS).write_text(yaml.safe_dump({**DOCS, "verified": "2099-01-01"}), encoding="utf-8")
    ups = [{"outbreak": sp.id, "level": "who", "action": "nieuwere_versie", "replaces": "who-factsheet",
            "org": "WHO", "title": "Ebola factsheet 2026", "date": "2026-09-01", "url": "https://www.who.int/ebola-2026",
            "key": "Incubatie 2 tot 21 dagen."},
           {"outbreak": sp.id, "level": "eu", "action": "nieuw", "org": "ECDC", "title": "Rapid risk assessment",
            "date": "2026-09-10", "url": "https://www.ecdc.europa.eu/rra", "key": "Laag risico voor de EU."},
           {"outbreak": sp.id, "level": "be", "action": "nieuw", "org": "Wanda", "title": "Iets",
            "url": "https://www.wanda.be/x"},                                  # excluded domain
           {"outbreak": sp.id, "level": "mars", "action": "nieuw", "url": "https://example.org"}]
    d = fiche.apply_updates(sp, ups, TODAY)
    assert d["verified"] == "2026-09-26"
    assert d["who"] == [{"id": "who-factsheet", "org": "WHO", "title": "Ebola factsheet 2026", "date": "2026-09-01",
                         "url": "https://www.who.int/ebola-2026", "key": "Incubatie 2 tot 21 dagen.",
                         "verified": "2026-09-26"}]                            # the fiche's reference still holds
    assert [x["id"] for x in d["eu"]] == ["ecdc-rapid-risk-assessment"]
    assert len(d["be"]) == 1                                                    # wanda.be is not proposed


WEB = {"document_updates": [{"outbreak": "ebola_cod_2026", "level": "eu", "action": "nieuw", "org": "ECDC",
                             "title": "Rapid risk assessment", "date": "2026-09-10",
                             "url": "https://www.ecdc.europa.eu/rra", "key": "Laag risico voor de EU."}],
       "fiche_flags": [{"outbreak": "ebola_cod_2026", "section": "Incubatie", "statement": "2 tot 21 dagen",
                        "newer": "2 tot 25 dagen", "source": "https://www.who.int/x", "date": "2026-09-20"}]}


def test_proposals_are_kept_only_after_a_yes_and_flags_never(local, monkeypatch, capsys):
    sp = outbreak.load("ebola_cod_2026")
    text = _fiche_text(verified="2099-01-01")
    (local / fiche.FICHE).write_text(text, encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    assert advies.maybe_apply_web(WEB, apply_web=False, outbreak_id=sp.id, specs=[sp]) is False
    assert not (local / fiche.DOCUMENTS).exists()
    out = capsys.readouterr().out
    assert "FICHE ebola_cod_2026, Incubatie" in out and "DOCUMENT ebola_cod_2026 (Europa, nieuw)" in out
    assert advies.maybe_apply_web(WEB, apply_web=True, outbreak_id=sp.id, specs=[sp]) is True
    assert [x["title"] for x in fiche.documents(sp)["levels"]["eu"]] == ["Rapid risk assessment"]
    assert (local / fiche.FICHE).read_text(encoding="utf-8") == text          # the flag changed nothing


def test_a_draft_is_a_concept_and_never_overwrites_a_confirmed_fiche(local):
    sp = outbreak.load("ebola_cod_2026")
    answer = {"secties": {"Verwekker": "Bundibugyo-virus [who-factsheet]."},
              "documenten": {"who": [DOCS["who"][0]], "be": [{"org": "Wanda", "title": "x", "url": "https://wanda.be/x"}]}}
    paths = fiche.write_draft(sp, answer, local, TODAY)
    meta, body = fiche.parse(paths[0].read_text(encoding="utf-8"))
    assert paths[0].name == fiche.FICHE and meta["status"] == "concept" and meta["verified"] == "2026-09-26"
    secs = fiche.sections(body)
    assert list(secs) == list(fiche.SECTIONS) and "niet gevonden in de bronnen" in secs["Diagnose"]
    docs = yaml.safe_load(paths[1].read_text(encoding="utf-8"))
    assert docs["who"][0]["id"] == "who-factsheet" and docs["be"] == []
    confirmed = _fiche_text("bevestigd", "2026-09-26", bevestigd_door="Steven Callens", bevestigd_op="2026-09-27")
    (local / fiche.FICHE).write_text(confirmed, encoding="utf-8")
    paths = fiche.write_draft(sp, answer, local, TODAY)
    assert paths[0].name == fiche.CONCEPT and (local / fiche.FICHE).read_text(encoding="utf-8") == confirmed


def test_the_command_drafts_with_the_model_and_keeps_its_trace(local, monkeypatch, capsys):
    from dienstreis import cli
    answer = {"secties": {s: f"{s} [who-factsheet]." for s in fiche.SECTIONS},
              "documenten": {"who": [DOCS["who"][0]]}, "notities": ["Twee bronnen spreken elkaar tegen."]}
    fake = llm.Fake({"fiche": answer})
    monkeypatch.setattr(llm, "get_backend", lambda *a, **k: fake)
    cli.main(["fiche", "ebola_cod_2026", "--opstellen"])
    assert "Ebola" in fake.prompts["fiche"][0] and "<secties>" in fake.prompts["fiche"][0]
    assert (local / fiche.FICHE).exists() and (local / "fiche_trace.json").exists()
    out = capsys.readouterr().out
    assert "Twee bronnen spreken elkaar tegen." in out and "status: bevestigd" in out


# ---------------------------------------------------------------- in the dossier
def _run(tmp_path) -> Path:
    from test_dossier import DATA, FEITEN, LETTER, SUMMARY, TRIP     # the synthetic run of test_dossier
    out = tmp_path / "out"
    out.mkdir()
    (out / "summary.json").write_text(json.dumps(SUMMARY), encoding="utf-8")
    (out / "stops.yaml").write_text(yaml.safe_dump(TRIP), encoding="utf-8")
    (out / "reply.txt").write_text(LETTER, encoding="utf-8")
    (out / "feiten.txt").write_text(FEITEN, encoding="utf-8")
    (out / dossier.DATA).write_text(json.dumps(DATA), encoding="utf-8")
    return out


def test_the_dossier_shows_the_fiche_under_its_banner_with_its_documents(local, tmp_path):
    extra = "\nEen <script>alert(1)</script> en [link](javascript:alert(1)).\n"
    (local / fiche.FICHE).write_text(_fiche_text(verified="2099-01-01", extra=extra), encoding="utf-8")
    (local / fiche.DOCUMENTS).write_text(yaml.safe_dump({**DOCS, "verified": "2099-01-01"}), encoding="utf-8")
    out = _run(tmp_path)
    (out / "web.json").write_text(json.dumps(WEB), encoding="utf-8")
    page = dossier.build(out).read_text(encoding="utf-8")
    fiche_part = page.split('id="fiche"')[1].split("</section>")[0]
    assert "Concept, nog niet bevestigd" in fiche_part and "Tekst over klinisch beeld" in fiche_part
    assert 'href="#doc-who-factsheet"' in fiche_part and 'id="doc-who-factsheet"' in page
    assert "Mogelijk verouderd, Incubatie" in fiche_part and "2 tot 25 dagen" in fiche_part
    assert "<script>alert" not in page and 'href="javascript:' not in page
    docs_part = page.split('id="richtlijnen"')[1].split("</section>")[0]
    assert "België" in docs_part and "Melding binnen 24 uur." in docs_part
    assert "Voorgesteld door de webstap" in docs_part and "Rapid risk assessment" in docs_part


def test_a_confirmed_fiche_says_who_confirmed_it(local, tmp_path):
    (local / fiche.FICHE).write_text(_fiche_text("bevestigd", "2099-01-01", bevestigd_door="Steven Callens",
                                                 bevestigd_op="2026-09-27"), encoding="utf-8")
    page = dossier.build(_run(tmp_path)).read_text(encoding="utf-8")
    assert "Bevestigd door Steven Callens op 27-09-2026" in page and "Concept, nog niet" not in page
