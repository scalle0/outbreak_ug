"""Reading the request mail: the deterministic facts the model is never asked for.

The fixture is an invented request (tests/fixtures/), so no colleague's travel details live in the
repo. It exercises the .eml path and the two rules that must not depend on the model:
whether the thread used the ugent.be address, and whether the traveller mentioned the outbreak.
"""
from pathlib import Path

import pytest

from dienstreis import msg

FIX = Path(__file__).parent / "fixtures" / "aanvraag_testpersoon.eml"


@pytest.fixture()
def req():
    return msg.parse_request(FIX)


def test_subject_and_body(req):
    assert "REISINFO" in req["subject"]
    assert "Aankomst Kinshasa: 28/11/2026" in req["body"]


def test_ugent_address_is_read_from_the_mail_not_the_model(req):
    """It drives the redirect line in the reply, so it is a fact about the thread."""
    assert req["sent_to_ugent_address"] is True


def test_traveller_did_not_mention_the_outbreak(req):
    """An's covering note mentions the 21-day rule; the traveller's own form does not."""
    assert req["traveller_mentions_outbreak"] is False


def test_original_request_starts_at_the_forward_header(req):
    """Only the traveller's own form counts, not Team Actueel's covering note."""
    original = msg._original_request(req["body"])
    assert "REISINFO" in original and "Graag jouw advies" not in original


def test_traveller_mentioning_the_outbreak_is_detected():
    body = "Beste Steven,\n\nVan: Iemand\nIk las over de ebola-uitbraak, is dit veilig?\n"
    assert "ebola" in msg._original_request(body).lower()


def test_txt_request_falls_back_to_the_filename(tmp_path):
    p = tmp_path / "losse_aanvraag.txt"
    p.write_text("Beste Steven,\n\nKinshasa 28/11/2026 tot 06/12/2026.\n", encoding="utf-8")
    r = msg.parse_request(p)
    assert r["subject"] == "losse_aanvraag" and "Kinshasa" in r["body"]
    assert r["sent_to_ugent_address"] is False


def test_emails_in_thread_are_collected(req):
    assert "actueel@ugent.be" in req["emails_in_thread"]
