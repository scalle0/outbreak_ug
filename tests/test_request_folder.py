"""A folder with every mail of one request is read as one request, in the order the mails were sent.

Requests arrive in pieces: a first mail, a correction an hour later, an answer to a question.
Invented mails only; no network, no model.
"""
import os
from datetime import datetime, timezone

import pytest

from dienstreis import advies, llm, msg


def _eml(path, subject, date, body, to="actueel@ugent.be"):
    path.write_text(f"Subject: {subject}\nFrom: Team Actueel <actueel@ugent.be>\nTo: {to}\nDate: {date}\n"
                    f"Content-Type: text/plain; charset=\"utf-8\"\nMIME-Version: 1.0\n\n{body}\n", encoding="utf-8")


@pytest.fixture()
def folder(tmp_path):
    d = tmp_path / "aanvraag_testpersoon"
    d.mkdir()
    # file names deliberately in the wrong order: the date in the mail decides
    _eml(d / "z_eerste.eml", "FW: REISINFO dienstreis DRC", "Tue, 10 Nov 2026 10:02:11 +0100",
         "Beste Steven,\n\nVan: Testpersoon Een <testpersoon.een@example.org>\nKinshasa 28/11/2026 tot 06/12/2026, terug 13/12/2026.",
         to="steven.callens@ugent.be")
    _eml(d / "a_correctie.eml", "RE: FW: REISINFO dienstreis DRC", "Tue, 10 Nov 2026 11:15:00 +0100",
         "Correctie van de reiziger: terugreis nu op 20/12/2026. Kopie aan collega@example.org.")
    import docx
    doc = docx.Document()
    doc.add_paragraph("Programma: veldwerk in Kisangani, verblijf in hotel.")
    doc.save(d / "programma.docx")
    (d / "kaartje.png").write_bytes(b"\x89PNG")        # neither a mail nor a document: ignored
    return d


def test_mails_are_read_in_the_order_they_were_sent(folder):
    r = msg.parse_request(folder)
    assert r["mail_count"] == 2 and [m["file"] for m in r["mails"]] == ["z_eerste.eml", "a_correctie.eml"]
    first, second = r["body"].index("===== Mail 1 van 2"), r["body"].index("===== Mail 2 van 2")
    assert first < r["body"].index("Kinshasa 28/11/2026") < second < r["body"].index("20/12/2026")


def test_the_reply_answers_the_last_mail(folder):
    assert msg.parse_request(folder)["subject"] == "RE: FW: REISINFO dienstreis DRC"


def test_facts_about_the_thread_hold_if_any_mail_has_them(folder):
    """The ugent.be address appears in the first mail only; it still drives the redirect line."""
    r = msg.parse_request(folder)
    assert r["sent_to_ugent_address"] is True
    assert {"testpersoon.een@example.org", "collega@example.org"} <= set(r["emails_in_thread"])


def test_loose_documents_are_attachments_and_other_files_are_ignored(folder):
    atts = {a["name"]: a for a in msg.parse_request(folder)["attachments"]}
    assert set(atts) == {"programma.docx"} and "veldwerk in Kisangani" in atts["programma.docx"]["text"]


def test_a_mail_without_a_date_takes_the_file_date_and_says_so(folder):
    note = folder / "notitie.txt"
    note.write_text("Van An: de reiziger heeft geen zorgcontact.\n", encoding="utf-8")
    between = datetime(2026, 11, 10, 9, 30, tzinfo=timezone.utc).timestamp()     # 10:30 Brussels
    os.utime(note, (between, between))
    r = msg.parse_request(folder)
    assert [m["file"] for m in r["mails"]] == ["z_eerste.eml", "notitie.txt", "a_correctie.eml"]
    assert "(bestandsdatum)" in r["body"].split("===== Mail 3")[0].split("===== Mail 2")[1]


def test_an_empty_folder_is_refused(tmp_path):
    with pytest.raises(ValueError, match="geen mails"):
        msg.parse_request(tmp_path)


def _ft(t: datetime) -> bytes:
    return int((t - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10_000_000).to_bytes(8, "little")


def test_msg_sent_time_is_read_from_the_property_stream():
    """Submit time wins over delivery time; entries are 16 bytes after a 32-byte header."""
    sent, delivered = datetime(2026, 11, 10, 9, 2, tzinfo=timezone.utc), datetime(2026, 11, 10, 9, 3, tzinfo=timezone.utc)
    entry = lambda tag, value: tag.to_bytes(4, "little") + b"\0" * 4 + value
    props = b"\0" * 32 + entry(0x0E060040, _ft(delivered)) + entry(0x0037001F, b"\0" * 8) + entry(0x00390040, _ft(sent))
    assert msg._filetime(props) == sent
    assert msg._filetime(b"\0" * 32 + entry(0x0E060040, _ft(delivered))) == delivered
    assert msg._filetime(b"\0" * 32) is None


def test_the_itinerary_step_reads_the_whole_thread(folder, tmp_path):
    """Stopped at the itinerary check, so no analysis runs: what matters is what the model was given."""
    fake = llm.Fake({"stops": {"traveller": "Testpersoon Een", "stops": []}})
    with pytest.raises(SystemExit):
        advies.run_advies(str(folder), out=str(tmp_path / "out"), yes=True, open_browser=False,
                          llm_backend=fake, web=False)
    p = fake.prompts["stops"][0]
    assert "===== Mail 1 van 2" in p and "===== Mail 2 van 2" in p and "terugreis nu op 20/12/2026" in p
    assert "programma.docx" in p and "latere mail verbetert" in p
