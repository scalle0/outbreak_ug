"""Overruling a rule: allowed, but only on the record.

The categories classify a health zone; they do not know the dossier. A clinician must be able to
depart from them, and every later reader (the mail, the archive, the next advice) must be able to
see that it happened and why.
"""
from datetime import date

import pytest

from dienstreis import risk, trip as T

KNOWN = ["Kinshasa", "Kisangani"]
REASON = "reiziger verblijft in een gesloten compound, geen contact met de gemeenschap"


def _trip(override=None, trip_override=None):
    stop = {"place": "Kisangani", "from": "2026-11-28", "to": "2026-12-05"}
    if override is not None:
        stop["override"] = override
    t = {"traveller": "T", "stops": [stop]}
    if trip_override is not None:
        t["override"] = trip_override
    return t


def check(t):
    return T.validate(T.coerce(t), known_places=KNOWN, today=date(2026, 9, 22))


def test_override_needs_a_reason():
    issues = check(_trip({"category": "C"}))
    assert any("reden" in i for i in issues)


def test_reason_must_say_something():
    assert any("reden" in i for i in check(_trip({"category": "C", "reason": "ok"})))


def test_override_needs_a_category():
    assert any("category" in i for i in check(_trip({"reason": REASON})))


def test_unknown_category_is_refused():
    assert any("onbekende categorie" in i for i in check(_trip({"category": "Z", "reason": REASON})))


def test_unknown_key_is_refused():
    assert any("onbekende sleutel" in i for i in
               check(_trip({"category": "C", "reason": REASON, "verdct": "typo"})))


def test_valid_override_passes():
    assert check(_trip({"category": "C", "reason": REASON})) == []


def test_trip_level_override_needs_a_verdict():
    assert any("verdict" in i for i in check(_trip(trip_override={"reason": REASON})))


def test_trip_level_override_passes():
    assert check(_trip(trip_override={"verdict": "goedkeuren mits compound", "reason": REASON})) == []


def test_category_is_upper_cased():
    assert T.coerce(_trip({"category": "c", "reason": REASON}))["stops"][0]["override"]["category"] == "C"


# ---------------------------------------------------------------- applying it
def _risk(cat="A"):
    r = risk.StopRisk(place="Kisangani", start=None, end=None, nights=None, lodging=None,
                      transit_only=False, lat=0.0, lon=25.0, country="COD")
    r.category = cat
    return r


def test_apply_override_keeps_what_the_rules_said():
    r = risk._apply_override(_risk("A"), {"category": "C", "reason": REASON})
    assert r.category == "C" and r.rule_category == "A" and r.overridden
    assert r.verdict == risk.VERDICT["C"]
    assert any("overrule" in f and REASON in f for f in r.flags)


def test_no_override_leaves_the_rule_alone():
    r = risk._apply_override(_risk("A"), None)
    assert r.category == "A" and r.rule_category is None and not r.overridden


def test_override_to_the_same_category_is_not_a_change():
    r = risk._apply_override(_risk("A"), {"category": "A", "reason": REASON})
    assert not r.overridden and r.flags == []


def test_overall_can_be_overruled_and_the_rule_stays_visible():
    rs = [_risk("A")]
    assert risk.rule_overall(rs).startswith("niet goedkeuren")
    t = {"override": {"verdict": "goedkeuren mits compound", "reason": REASON}}
    assert risk.overall(rs, t) == "goedkeuren mits compound"
    assert risk.rule_overall(rs).startswith("niet goedkeuren")


def test_overrides_are_listed_for_the_record():
    rs = [risk._apply_override(_risk("A"), {"category": "C", "reason": REASON})]
    ov = risk.overrides(rs, {"override": {"verdict": "toch goedkeuren", "reason": REASON}})
    assert len(ov) == 2
    per_stop = next(o for o in ov if o["scope"] == "Kisangani")
    assert per_stop["rule_category"] == "A" and per_stop["category"] == "C"
    assert any(o["scope"] == "eindoordeel" for o in ov)
    assert all(o["reason"] for o in ov)


def test_a_stricter_override_is_allowed():
    """Departing from the rules may go either way; F is the harmless category, A the serious one."""
    r = risk._apply_override(_risk("F"), {"category": "B", "reason": REASON})
    assert r.category == "B" and r.rule_category == "F"


def test_skeleton_tells_the_writer_a_rule_was_set_aside():
    from dienstreis import mail
    rs = [risk._apply_override(_risk("A"), {"category": "C", "reason": REASON})]
    hint = mail._override_hint(rs, {})
    assert "bewust af van de regel" in hint and REASON in hint


def test_custom_verdict_is_not_matched_against_the_rule_words():
    """A verdict the clinician wrote cannot be checked for afraden/voorwaardelijk/geen bezwaar."""
    from dienstreis import mail
    assert mail.verdict_note("Wat dan ook.", "goedkeuren mits compound") is None


def test_rule_overall_reports_what_the_rules_said_not_the_override():
    """The bug this guards: recomputing from the overridden categories loses the rule verdict."""
    rs = [risk._apply_override(_risk("A"), {"category": "F", "reason": REASON})]
    assert risk.rule_overall(rs).startswith("niet goedkeuren")
    assert risk.overall(rs) == "geen ebola-gerelateerd bezwaar"
    assert risk.overrides(rs)[0]["rule_category"] == "A"
