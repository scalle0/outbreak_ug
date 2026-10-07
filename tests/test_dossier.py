"""The internal dossier (F-015): built from a run's folder, every section present, the letter one click
from the clipboard only when it passed the checks. A synthetic run folder: no network, no model."""
import base64
import io
import json
import re
from pathlib import Path

import pytest
import yaml
from PIL import Image

from dienstreis import archive, cli, countries, dossier

LETTER = ("Beste An,\n\nKinshasa kan, Kisangani raad ik momenteel af: er is een geval van de laatste 21 dagen.\n\n"
          "Met vriendelijke groet,\nSteven Callens\n")
OVERALL = "niet goedkeuren in huidige vorm (minstens een luik af te raden)"
SUMMARY = {
    "asof": "2026-09-19", "outbreak": "ebola_cod_2026", "type": "reisadvies", "overall": OVERALL,
    "rule_overall": OVERALL, "overrides": [], "overall_level": "afraden",
    "epi": {"path": "epicurve_20260919.png", "weekly_cases_last4_full_weeks": {"07-09": 586, "14-09": 572},
            "weeks_last8": [{"week": "2026-09-07", "cases": 586, "deaths": 260},
                            {"week": "2026-09-14", "cases": 572, "deaths": 251}],
            "last_total": 7672, "last_deaths": 3699, "cfr": 48.2},
    "stops": [{"place": "Kinshasa", "country": "COD", "zone": "Barumbu", "province": "Kinshasa", "category": "F",
               "label": "niet getroffen", "verdict": "geen bezwaar", "cases": 0, "new14": 0, "days_since_last": None,
               "neighbours_active": [], "nearest_active": {"zone": "Makiso Kisangani", "km": 1220, "days_since_last": 3},
               "fod": "niet_essentieel_afgeraden", "fod_reason": "algemene volatiliteit", "cdc": 2, "flags": []},
              {"place": "Kisangani", "country": "COD", "zone": "Makiso Kisangani", "province": "Tshopo",
               "category": "A", "label": "geval in de laatste 21 dagen", "verdict": "afraden", "cases": 20,
               "new14": 10, "days_since_last": 0.0, "neighbours_active": [{"zone": "Mangobo", "cases": 4}],
               "nearest_active": None, "fod": "formeel_afgeraden", "fod_reason": "veiligheidssituatie", "cdc": 3,
               "flags": ["FOD formeel afgeraden (veiligheidssituatie)"]}],
    "qa": {"zone_sum_matches_national": True, "ecdc_matches": True,
           "ecdc": {"ok": True, "cases": 7672, "deaths": 3699, "data_until": "19 September"},
           "who": {"ok": True, "item": "Ebola, DRC", "date": "2026-09-10", "days_old": 9},
           "sources_unreachable": [], "unmatched_zone_names": [], "map_label_overlaps": 0},
    "map": "kaart_reiziger_t.png", "epicurve": "epicurve_20260919.png",
    "attachments": ["kaart_reiziger_t.png", "epicurve_20260919.png"],
}
TRIP = {"type": "reisadvies", "traveller": "Reiziger T", "note": "veldwerk", "review_on": "2026-11-20",
        "profile": {"lodging": "hotel", "healthcare_work": False},
        "stops": [{"place": "Kinshasa", "from": "2026-11-28", "to": "2026-12-05"},
                  {"place": "Kisangani", "from": "2026-12-06", "to": "2026-12-13"}]}
FEITEN = ("Regeloordeel: niet goedkeuren in huidige vorm (minstens een luik af te raden).\n\nPer luik:\n"
          "Kisangani: 20 bevestigde gevallen, 10 nieuw in 14 dagen; het laatste geval van 19-09.\n")
DATA = {"created": "2026-09-26T10:00:00", "version": "0.3.0", "type": "reisadvies",
        "aanvraag": {"subject": "Aanvraag dienstreis", "sender": "An", "mail_count": 1, "attachments": [],
                     "body": "Beste Steven, geldt de 21-dagen regel?", "questions_from_an": ["Geldt de 21-dagenregel?",
                                                                                          "Mag hij via Kisangani?"],
                     "missing_info": ["vervoer"], "contradictions": []},
        "unmatched": [], "numbers": True,
        "model": {"vragen": [{"vraag": "Geldt de 21-dagenregel?", "antwoord": "Ja, tot 21 dagen na terugkeer."}],
                  "beoordeling": ["Kisangani: categorie A, 10 nieuwe gevallen in 14 dagen."],
                  "weggelaten": ["de stand van zaken: staat in de curve"], "na_te_kijken": ["de 21-dagenregel"],
                  "toezeggingen": ["go/no-go op 20/11"], "vragen_aan_behandelaar": []},
        "checks": {"issues": [], "notes": []}, "warnings": [], "review_on": "2026-11-20",
        "attachments_sent": ["kaart_reiziger_t.png", "epicurve_20260919.png"], "web_accepted": None,
        "earlier": [], "history": [], "context_lines": ["2026-09-10: Kisangani-luik Hubeau afgeraden"]}


def _png(path: Path, size=(3200, 1000)) -> None:
    Image.new("RGB", size, (245, 247, 244)).save(path)


@pytest.fixture()
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(countries, "LOCAL", tmp_path / "geen_lokaal_register")   # the repo registry only
    out = tmp_path / "out_reiziger_t"
    out.mkdir()
    (out / "summary.json").write_text(json.dumps(SUMMARY), encoding="utf-8")
    (out / "stops.yaml").write_text(yaml.safe_dump(TRIP, allow_unicode=True), encoding="utf-8")
    (out / "reply.txt").write_text(LETTER, encoding="utf-8")
    (out / "feiten.txt").write_text(FEITEN, encoding="utf-8")
    (out / "sources.txt").write_text("WHO, Disease Outbreak News:\nhttps://www.who.int/emergencies/disease-outbreak-news\n",
                                     encoding="utf-8")
    (out / dossier.DATA).write_text(json.dumps(DATA), encoding="utf-8")
    _png(out / "kaart_reiziger_t.png")
    _png(out / "epicurve_20260919.png", (1200, 900))
    return out


def _page(out: Path) -> str:
    return dossier.build(out).read_text(encoding="utf-8")


def test_every_section_is_there(run):
    page = _page(run)
    for key, _ in dossier.SECTIONS:
        assert f'<section id="{key}">' in page and f'href="#{key}"' in page
    assert "<title>Dossier Reiziger T</title>" in page
    assert "Kisangani-luik Hubeau afgeraden" in page                      # the context line
    assert "Uit de mail gelaten" in page and "go/no-go op 20/11" in page  # the model's assessment


def test_the_categories_are_explained(run):
    """2026-10-07: the verdict showed categories A to F without saying what they mean."""
    html = _page(run).split('<section id="oordeel">')[1].split("</section>")[0]
    assert "Wat de categorieën betekenen: " in html
    assert "had een geval in de laatste 21 dagen" in html and "22 tot 42 dagen geleden" in html
    assert "grenst aan een gezondheidszone met een geval" in html and "Buiten het gebied van de cijfers" in html
    assert "<b>A</b>" in html and "<b>F</b>" in html and "<b>B</b>" not in html   # this advice: A and F
    assert "De strengste halte bepaalt het oordeel voor de reis" in html


def test_the_letter_is_there_to_copy(run):
    page = _page(run)
    m = re.search(r'<pre id="t" class="letter">(.*?)</pre>', page, re.S)
    assert m and "Kisangani raad ik momenteel af" in m.group(1)
    assert 'onclick="kopieer()">' in page                                 # enabled
    assert "navigator.clipboard.writeText(t.innerText)" in page
    assert "16 woorden" in page and "richtlijn 120, maximum 200" in page


def test_the_figures_are_embedded_and_scaled_down(run):
    page = _page(run)
    uris = re.findall(r'src="data:image/png;base64,([^"]+)"', page)
    assert len(uris) == 2
    widths = sorted(Image.open(io.BytesIO(base64.b64decode(u))).width for u in uris)
    assert widths == [1200, dossier.IMG_WIDTH]                            # 3200 scaled, 1200 left alone
    assert "kaart_reiziger_t.png" in page                                 # named as sent with the letter


def test_an_unreadable_figure_is_left_out(run):
    (run / "kaart_reiziger_t.png").write_bytes(b"png")
    page = _page(run)
    assert len(re.findall(r'src="data:image/png', page)) == 1


def test_each_question_shows_its_answer_or_its_absence(run):
    page = _page(run)
    assert "Ja, tot 21 dagen na terugkeer." in page
    assert "Mag hij via Kisangani?" in page and "geen antwoord gekoppeld" in page


def test_the_epidemiology_and_the_risks(run):
    page = _page(run)
    assert "7 672" in page and "48.2 %" in page and "ECDC, data tot 19 september" in page
    assert "07-09-2026" in page and "586" in page                         # the weeks, with deaths
    assert "Makiso Kisangani (Tshopo)" in page and "Mangobo (4)" in page
    assert "Democratische Republiek Congo" in page and "Tshopo: formeel_afgeraden" in page
    assert "Kinshasa: " not in page.split('id="risico"')[1].split("</section>")[0].split("FOD-pagina")[0].split(
        "heel het land")[1].split("</ul>")[0]                              # a province without its own entry


def test_copying_is_off_while_a_blocking_check_fails(run):
    d = {**DATA, "checks": {"issues": ["onbekend getal '8421'"], "notes": []}}
    (run / dossier.DATA).write_text(json.dumps(d), encoding="utf-8")
    page = _page(run)
    assert 'onclick="kopieer()" disabled' in page and "Kopiëren staat uit" in page
    assert f'dienstreis dossier &quot;{run}&quot;' in page


def test_a_hand_edit_is_checked_again(run):
    (run / "reply.txt").write_text(LETTER.replace("momenteel af:", "momenteel af — cruciaal:"), encoding="utf-8")
    page = dossier.build(run, rebuilt=True).read_text(encoding="utf-8")
    data = json.loads((run / dossier.DATA).read_text(encoding="utf-8"))
    assert any("em-dash" in x for x in data["checks"]["issues"]) and data["rebuilt"]
    assert 'onclick="kopieer()" disabled' in page
    (run / "reply.txt").write_text(LETTER, encoding="utf-8")
    page = dossier.build(run, rebuilt=True).read_text(encoding="utf-8")
    assert 'onclick="kopieer()">' in page


def test_the_command_rebuilds_and_fails_on_a_blocking_check(run):
    (run / "reply.txt").write_text(LETTER.replace("21 dagen", "8421 dagen"), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        cli.main(["dossier", str(run), "--no-open"])
    assert e.value.code == 1
    (run / "reply.txt").write_text(LETTER, encoding="utf-8")
    cli.main(["dossier", str(run), "--no-open"])                       # no exit: the checks pass


def test_a_case_has_no_trip_verdict_and_sends_no_figures(run):
    s = {**SUMMARY, "type": "casus"}
    (run / "summary.json").write_text(json.dumps(s), encoding="utf-8")
    (run / dossier.DATA).write_text(json.dumps({**DATA, "type": "casus", "attachments_sent": []}), encoding="utf-8")
    (run / "stops.yaml").write_text(yaml.safe_dump({**TRIP, "type": "casus", "situation": "In quarantaine in Kinshasa."}),
                                    encoding="utf-8")
    page = _page(run)
    assert "geen reisoordeel" in page and "Geen oordeel volgens de regels" in page
    assert "In quarantaine in Kinshasa." in page
    assert "blijven kaart en curve in dit dossier" in page
    assert len(re.findall(r'src="data:image/png', page)) == 2             # but shown here


def test_what_comes_from_a_mail_is_escaped(run):
    (run / "stops.yaml").write_text(yaml.safe_dump({**TRIP, "traveller": "<script>alert(1)</script>"}), encoding="utf-8")
    page = _page(run)
    assert "<script>alert(1)" not in page and "&lt;script&gt;alert(1)" in page


def test_web_findings_and_guidance(run):
    web = {"guidance": [{"topic": "isolatie", "text": "21 dagen opvolging", "source": "https://example.org/r",
                         "date": "2026-09-20"}],
           "news": [{"date": "2026-09-18", "item": "nieuwe zone", "url": "https://example.org/n"}],
           "who": {"latest_don": "2026-09-10", "risk_assessment": "hoog nationaal"},
           "advisories": [{"country": "COD", "region": "Tshopo", "fod": "formeel_afgeraden", "cdc": 3, "changed": True,
                           "source": "javascript:alert(1)"}]}
    (run / "web.json").write_text(json.dumps(web), encoding="utf-8")
    (run / dossier.DATA).write_text(json.dumps({**DATA, "web_accepted": True}), encoding="utf-8")
    page = _page(run)
    assert "21 dagen opvolging" in page and "nieuwe zone" in page and "hoog nationaal" in page
    assert "overgenomen in het lokale landenregister" in page
    assert 'href="javascript:' not in page                                # only http(s) and file links


def test_several_outbreaks_each_get_their_part(run):
    s = {**SUMMARY, "outbreaks": {
        "ebola_cod_2026": {"name": "Ebola (Bundibugyo-virus)", "asof": "2026-09-19", "overall": OVERALL,
                           "rule_overall": OVERALL, "level": "afraden", "epi": SUMMARY["epi"], "stops": SUMMARY["stops"],
                           "qa": SUMMARY["qa"], "map": SUMMARY["map"], "epicurve": SUMMARY["epicurve"]},
        "mpox_cod_2026": {"name": "Mpox (clade I)", "asof": "2026-09-15", "overall": "voorwaardelijk",
                          "rule_overall": "voorwaardelijk", "level": "voorwaardelijk", "epi": None,
                          "stops": [], "qa": {"table_empty": True}, "map": None, "epicurve": None}}}
    (run / "summary.json").write_text(json.dumps(s), encoding="utf-8")
    page = _page(run)
    assert "Ebola (Bundibugyo-virus)" in page and "Mpox (clade I)" in page
    assert "de cijfertabel is leeg" in page
    assert 'class="badge stop"' in page and 'class="badge cond"' in page


def test_the_model_never_gets_the_archive_folders(tmp_path):
    d = archive.save({"traveller": "Reiziger T"}, {"stops": [{"place": "Kisangani"}], "outbreak": "ebola_cod_2026"},
                     "de brief", root=tmp_path)
    trip, summary = {"traveller": "Iemand"}, {"stops": [{"place": "Kisangani"}]}
    assert "dir" not in archive.for_trip(trip, summary, root=tmp_path)[0]
    assert archive.for_trip(trip, summary, root=tmp_path, with_dir=True)[0]["dir"] == str(d)
