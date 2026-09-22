"""Checks on the written reply: style, invented numbers, and the rule verdict.

The model rewrites the whole letter, so the case counts pass through it. These are the checks that
stand between a rewritten sentence and a figure that was never calculated.
"""
import pytest

from dienstreis import mail

FACTS = ("Watsa telt 5 514 bevestigde gevallen (57 overlijdens), waarvan 13 in de laatste 14 dagen. "
         "Data tot 19-09-2026.")


def test_numbers_from_the_facts_pass():
    txt = "Watsa telt 5 514 gevallen en 57 overlijdens, 13 in de laatste 14 dagen."
    assert mail.unknown_numbers(txt, [FACTS]) == []


def test_invented_number_is_caught():
    txt = "Watsa telt 5 842 gevallen."
    issues = mail.unknown_numbers(txt, [FACTS])
    assert len(issues) == 1 and "5842" in issues[0]


def test_thousands_separator_does_not_matter():
    """The house style writes 7 672; the summary JSON writes 7672."""
    for written in ("5 514", "5.514", "5514"):
        assert mail.unknown_numbers(f"Er zijn {written} gevallen.", ['{"cases": 5514}']) == []


def test_day_numbers_and_rule_windows_are_always_allowed():
    txt = "Temperatuur opvolgen tot 21 dagen na terugkeer; 42 dagen zonder geval; punt 3 van de voorwaarden."
    assert mail.unknown_numbers(txt, ["geen enkel getal hier"]) == []


def test_dates_in_the_reply_pass():
    txt = "Vertrek op 28/11 en terugkeer op 13/12."
    assert mail.unknown_numbers(txt, ["geen getallen"]) == []


def test_check_reply_combines_style_and_numbers():
    txt = "Dit is cruciaal: er zijn 9 999 gevallen."
    issues = mail.check_reply(txt, [FACTS])
    assert any("verboden versterkers" in i for i in issues)
    assert any("9999" in i for i in issues)


def test_number_check_can_be_switched_off():
    txt = "Er zijn 9 999 gevallen."
    assert mail.check_reply(txt, [FACTS], numbers=False) == []


AFRADEN = "niet goedkeuren in huidige vorm (minstens een luik af te raden)"


def test_softened_verdict_is_noticed():
    assert mail.verdict_note("Beste An,\n\nIk zie geen bezwaar tegen deze reis.\n", AFRADEN)


@pytest.mark.parametrize("txt", [
    "Ik moet dit luik afraden.",
    "2. Kisangani: af te raden.",
    "Kinshasa kan, Kisangani raad ik momenteel af.",
    "Dit luik wordt afgeraden.",
    "Ik kan deze reis niet goedkeuren in deze vorm.",
])
def test_the_ways_dutch_writes_afraden(txt):
    """Phrasing varies; the check must not fire on a letter that does say it."""
    assert mail.verdict_note(txt, AFRADEN) is None


def test_verdict_conditional_and_no_objection():
    assert mail.verdict_note("Dit luik kan voorwaardelijk doorgaan.",
                             "voorwaardelijk, met go/no-go dichter bij vertrek") is None
    assert mail.verdict_note("Hier is geen ebolagerelateerd bezwaar.",
                             "geen ebola-gerelateerd bezwaar") is None


def test_verdict_note_is_not_blocking():
    """A phrasing mismatch warns, it never stops a reply whose numbers are right."""
    soft = "Beste An,\n\nIk zie hier niets problematisch.\n"
    assert mail.check_reply(soft, [FACTS]) == []
