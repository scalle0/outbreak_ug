"""The facts a reply is written from, the checks on the reply, the HTML copy widget, and sources.

The facts file (`feiten.txt`) holds the rule verdict, the calculated facts per stop, the state of
the outbreak and the conditions. It is not a letter frame: An gets a short answer written by the
model (prompts/reply.md, prompts/consult.md), and the facts go to Steven's dossier. What is
about the disease (the zone unit, the conditions, the outbreak sources) comes from its profile;
what is about the country (FOD pages, the pretravel line) from the country registry.
"""
from __future__ import annotations

import html
import re

from . import countries, outbreak
from .risk import StopRisk, overrides, rule_overall, spec_of

MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
          "oktober", "november", "december"]
EN_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
             "october", "november", "december"]
FOD_TXT = {"formeel_afgeraden": "raadt de FOD alle reizen naar {p} formeel af ({r})",
           "niet_essentieel_afgeraden": "valt {p} onder het algemene FOD-advies (niet-essentiële reizen naar {land} afgeraden)"}


def d(x) -> str:
    return "" if x is None else f"{x.day} {MONTHS[x.month - 1]}"


def n(x: int) -> str:
    return f"{x:,}".replace(",", " ")


def cap(s: str) -> str:
    """First letter upper case, the rest as written: a zone name keeps its own capitals."""
    return s[:1].upper() + s[1:]


def nl_months(s: str) -> str:
    """English month names, as the ECDC page writes its dates, in Dutch: '19 September' -> '19 september'."""
    return re.sub(rf"\b({'|'.join(EN_MONTHS)})\b", lambda m: MONTHS[EN_MONTHS.index(m.group(1).lower())],
                  s, flags=re.I)


def leg_paragraph(i: int, r: StopRisk) -> str:
    spec = r.outbreak_spec
    when = (f" ({d(r.start)} tot {d(r.end)})" if r.start and r.end else f" (sinds {d(r.start)})" if r.start else "")
    head = f"{i}. {r.place}{when}: "
    if r.category == "X":
        extra = []                               # a formal FOD advisory and CDC >= 3 are flags already
        if r.fod == "niet_essentieel_afgeraden":
            land = countries.letter(r.country)
            extra.append(FOD_TXT[r.fod].format(p=land, r=r.fod_reason, land=land))
        if r.cdc == 2:
            extra.append("de CDC hanteert niveau 2")
        return head + "; ".join([spec.label("X")] + r.flags + extra) + "."
    parts = []
    zone_txt = f"{spec.unit} {r.zone}" if r.zone and r.zone.lower() != r.place.lower() else f"de {spec.unit}"
    cw = spec.case_words
    if r.category == "A":
        parts.append(f"{spec.verdict('A') if spec.verdict('A') != 'afraden' else 'af te raden'}. "
                     f"{cap(zone_txt)} telt {n(r.cases)} {cw['cases']} "
                     f"({n(r.deaths)} overlijdens), waarvan {r.new14} in de laatste {spec.recent} dagen")
    elif r.category in "BC":
        parts.append(f"{spec.verdict(r.category)}. {cap(zone_txt)} telt {n(r.cases)} gevallen, het laatste "
                     f"{int(r.days_since_last)} dagen geleden")
    elif r.category == "D":
        nb = ", ".join(f"{x['zone']} ({x['cases']})" for x in r.neighbours_active[:3])
        parts.append(f"{spec.verdict('D')}. {cap(zone_txt)} heeft geen {cw['none']}, maar grenst "
                     f"aan zones met actieve transmissie: {nb}")
    elif r.category == "E":
        parts.append(f"{spec.verdict('E')}. {cap(zone_txt)} heeft geen gevallen; de provincie {r.province} "
                     f"telt {n(r.province_cases)} gevallen in {r.province_active_zones} actieve zone(s)")
    else:
        na = r.nearest_active
        dist = f"; de dichtstbijzijnde zone met recente gevallen ({na['zone']}) ligt op circa {n(round(na['km'], -1))} km" if na else ""
        parts.append(f"{spec.verdict('F')}. Geen {cw['none']} in {zone_txt} of in de provincie {r.province}{dist}")
    if r.fod:
        parts.append(FOD_TXT[r.fod].format(p=r.province, r=r.fod_reason, land=countries.letter(r.country)))
    if r.cdc and r.cdc >= 2:
        parts.append(f"de CDC hanteert niveau {r.cdc}")
    return head + "; ".join(parts) + "."


def _override_hint(rs: list[StopRisk], trip: dict, ov: list[dict] | None = None) -> str:
    ov = overrides(rs, trip) if ov is None else ov
    if not ov:
        return ""
    parts = "; ".join(f"{o['scope']}: {o['van']} -> {o['naar']} ({o['reason']})" for o in ov)
    return (f" De arts week bewust af van de regel: {parts}. Schrijf het oordeel zoals het nu is, "
            f"en zeg kort waarom, zonder de regelcategorie te noemen.")


def _stand(rs: list[StopRisk], epi: dict, ecdc: dict, named: bool) -> str:
    """The national situation in one sentence: total with its date and source, and the full weeks."""
    spec = spec_of(rs)
    wk = list(epi["weekly_cases_last4_full_weeks"].values())
    tot = ecdc if ecdc.get("ok") else {"cases": epi["last_total"], "deaths": epi["last_deaths"], "data_until": None}
    bron = f"ECDC, data tot {nl_months(tot['data_until'])}" if tot.get("data_until") else spec.sources["national"]
    label = f"Stand van zaken {spec.name}" if named else "Stand van zaken"
    weeks = f" Nieuwe gevallen per volledige week, laatste vier weken: {', '.join(n(x) for x in wk)}." if wk else ""
    return (f"{label} ({bron}): "
            f"{n(tot['cases'])} {spec.case_words['cases']} en {n(tot['deaths'])} overlijdens (CFR {epi['cfr']:.0f} procent)."
            + weeks)


def facts(rs: list[StopRisk], epi: dict | None, ecdc: dict, others=()) -> str:
    """For a case or a question: the figures of the outbreaks at the place, without a trip's verdicts or conditions."""
    lines = ["Feiten uit de cijfers (achtergrond bij een casus of vraag, geen reisadvies):", ""]
    for x, e, c in [(rs, epi, ecdc)] + list(others):
        if x:
            lines += [f"{spec_of(x).name}:"] + [leg_paragraph(i + 1, r) for i, r in enumerate(x)] + [""]
    lines += [_stand(x, e, c, named=True) for x, e, c in [(rs, epi, ecdc)] + list(others) if e and x]
    return "\n".join(lines).rstrip() + "\n"


def feiten(trip: dict, rs: list[StopRisk], epi: dict | None, ecdc: dict, others=(),
           overrides: list[dict] | None = None, kind: str = "reisadvies") -> str:
    """The calculated facts the letter is written from, and that every number in it must trace to.

    `rs`, `epi`, `ecdc` are the strictest outbreak's; `others` holds (stops, epi, ecdc) for every
    further outbreak that applies; `epi` is None without figures. A case or a question gets the
    figures for its place only (`facts`).
    """
    if kind != "reisadvies":
        return facts(rs, epi, ecdc, others)
    spec = spec_of(rs)
    rule = rule_overall(rs) if not others else "; ".join(
        f"{spec_of(x).name}: {rule_overall(x)}" for x in [rs] + [o[0] for o in others])
    lines = [f"Regeloordeel: {rule}.{_override_hint(rs, trip, overrides)}", "", "Per luik:"]
    lines += [leg_paragraph(i + 1, r) for i, r in enumerate(rs)]
    for o_rs, _, _ in others:                    # a further outbreak: only the stops where it weighs
        legs = [leg_paragraph(i + 1, r) for i, r in enumerate(o_rs)
                if r.category != "X" and r.outbreak_spec.level(r.category) != "geen_bezwaar"]
        lines += ["", f"Voor {spec_of(o_rs).name}:"] + (legs or ["geen bezwaar op de haltes van dit reisschema."])
    stand = [_stand(x, e, c, named=bool(others)) for x, e, c in [(rs, epi, ecdc)] + list(others) if e]
    lines += [""] + (stand + [""] if stand else [])
    conds = [c for c in dict.fromkeys(spec.conditions + [c for o in others for c in spec_of(o[0]).conditions])
             if not c.startswith("[[")]           # a local profile may still carry a slot of the old letter frame
    lines += ["Voorwaarden uit profiel en land (voor de reiziger):"]
    lines += [f"- {c}" for c in [pretravel_line(rs)] + conds]
    return "\n".join(lines).rstrip() + "\n"


REDIRECT = "Voor verdere correspondentie kan u mij best bereiken via steven.callens@uzgent.be."


def with_redirect(reply: str, redirect: bool) -> str:
    """The uzgent.be line when the thread used the ugent.be address: added by the code, not left to the model."""
    if not redirect or "steven.callens@uzgent.be" in reply:
        return reply
    i = reply.find("Met vriendelijke groet")
    if i < 0:
        return reply.rstrip() + "\n\n" + REDIRECT + "\n"
    return reply[:i] + REDIRECT + "\n\n" + reply[i:].rstrip() + "\nsteven.callens@uzgent.be\n"


BANNED = ["cruciaal", "essentieel", "significant", "belangrijk", "substantieel", "aanzienlijk"]


def check_text(txt: str) -> list[str]:
    issues = []
    if "\u2014" in txt:
        issues.append("em-dash aanwezig")
    if "[[CLAUDE" in txt:
        issues.append(f"{txt.count('[[CLAUDE')} open [[CLAUDE]]-plaatshouder(s)")
    hits = [w for w in BANNED if re.search(rf"\b{w}\b", txt, re.I)]
    if hits:
        issues.append("verboden versterkers: " + ", ".join(hits))
    return issues


# numbers written out in the reply: "7 672" and "7.672" are the same number as "7672"
_NUMBER = re.compile(r"\d+(?:[ \u00a0.,]\d{3})*(?:,\d+)?")
# day numbers, 14 (the count of new cases), 100 (percentages) and the outbreak's own rule windows
# (for Ebola 21 and 42 days) are always allowed
_ALWAYS_OK = {str(n) for n in range(0, 32)} | {"100"}


def _always_ok(specs=None) -> set[str]:
    return _ALWAYS_OK | {str(w) for s in (specs or [outbreak.default()]) for w in s.windows.values()}


def _numbers(txt: str) -> set[str]:
    out = set()
    for m in _NUMBER.finditer(txt):
        s = re.sub(r"[ \u00a0.]", "", m.group(0)).split(",")[0]
        if s:
            out.add(s.lstrip("0") or "0")
    return out


def unknown_numbers(txt: str, sources: list[str], specs=None) -> list[str]:
    """Numbers in the reply that appear in none of the facts it was written from.

    The model rewrites the whole letter, so every case count, death count and interval passes
    through it. check_text catches style, not arithmetic: this is what stops an invented figure
    from going out in a signed medical advice. Reported, never silently corrected.
    """
    allowed = _always_ok(specs)
    for s in sources:
        allowed |= _numbers(s)
    bad = sorted(_numbers(txt) - allowed, key=lambda x: (-len(x), x))
    return [f"onbekend getal '{b}': komt niet voor in de berekende gegevens" for b in bad]


def check_reply(txt: str, sources: list[str], numbers: bool = True, specs=None) -> list[str]:
    """Blocking checks: style, and every number traceable to the calculated facts."""
    return check_text(txt) + (unknown_numbers(txt, sources, specs) if numbers else [])


# the same verdict written the way a letter writes it: "af te raden", "raad ik momenteel af"
_VERDICT = {
    "afraden": r"\bafrad|\baf\s+te\s+raden\b|\bafgeraden\b|\braad\b[^.]{0,40}\baf\b|niet\s+goed\s*(?:te\s+)?keuren",
    "voorwaardelijk": r"\bvoorwaardelijk\b|\bvoorwaarden?\b",
    "geen bezwaar": r"\bgeen\b[^.]{0,30}\bbezwaar\b",
}


TARGET_WORDS = 120      # An reads the answer, not the reasoning: that goes to the dossier
MAX_WORDS = 200


def word_count(txt: str) -> int:
    """Words in the reply, without the salutation and the signature block."""
    out, rows = [], txt.splitlines()
    if rows and rows[0].strip().startswith("Beste"):
        rows = rows[1:]
    for row in rows:
        if row.strip().startswith("Met vriendelijke groet"):
            break
        out.append(row)
    return len(" ".join(out).split())


def length_note(txt: str, limit: int = MAX_WORDS) -> str | None:
    """Warn when the reply has grown into a report.

    An reads this to decide about a trip, not to follow the reasoning; the reasoning belongs in the
    dossier. Raised in the repair round so the model gets one chance to cut, but never blocking: a
    long reply that is accurate can still be sent, and only the clinician can judge that.
    """
    n = word_count(txt)
    if n <= limit:
        return None
    return (f"de mail telt {n} woorden, dat is te lang (richtlijn {TARGET_WORDS}, maximum {limit}); "
            f"kort in: An krijgt het antwoord, de rest hoort in het dossier")


def questions_note(dossier: dict | None, questions: list[str]) -> str | None:
    """Every explicit question of An needs its answer in the letter; `dossier.vragen` says which sentence.

    Never blocking: the pairing comes from the model, so it can only show that an answer is missing.
    Without a dossier (a reply of before F-015) there is nothing to pair with.
    """
    if not questions or not isinstance(dossier, dict):
        return None
    answered = [q for q in dossier.get("vragen") or []
                if isinstance(q, dict) and str(q.get("antwoord") or "").strip()]
    if len(answered) >= len(questions):
        return None
    return (f"{len(questions) - len(answered)} van de {len(questions)} vragen van An zonder antwoord "
            f"(dossier.vragen); beantwoord elke vraag in een of twee zinnen")


def coverage_note(txt: str, specs) -> str | None:
    """With several outbreaks, warn when the reply does not name one of them. Never blocking."""
    if len(specs) < 2:
        return None
    missing = [sp.name for sp in specs if sp.match_terms
               and not any(re.search(rf"\b{re.escape(t)}", txt, re.I) for t in sp.match_terms)]
    return (f"de mail noemt {', '.join(missing)} niet, terwijl die uitbraak voor deze reis geldt; bedoeld of niet?"
            if missing else None)


def verdict_note(txt: str, overall: str | None) -> str | None:
    """Warn when the rule verdict does not come back in the letter at all.

    The model may argue against the rules, but not quietly drop them. Phrasing in Dutch varies too
    much to make this blocking: it is raised in the repair round and then carried into the notes,
    so a wrongly flagged wording never stops a correct reply from being sent.
    """
    if not overall:
        return None
    if "niet goedkeuren" in overall:
        want = "afraden"
    elif "voorwaardelijk" in overall:
        want = "voorwaardelijk"
    elif "geen" in overall and "bezwaar" in overall:
        want = "geen bezwaar"
    else:
        return None   # a verdict the clinician wrote themselves: nothing to match it against
    if re.search(_VERDICT[want], txt, re.I):
        return None
    return f"regeloordeel '{want}' komt niet terug in de mail (regels: {overall}); bedoeld of niet?"


def widget(mail_text: str, suggestions: list[str], title: str) -> str:
    sug = "\n".join(f"      <li>{html.escape(s)}</li>" for s in suggestions) or "      <li>No flags. Reply ready to send.</li>"
    return f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
:root {{ --bg:#fff; --fg:#1a1a1a; --box:#f5f5f5; --border:#ddd; --muted:#555; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#1e1e1e; --fg:#eaeaea; --box:#2a2a2a; --border:#444; --muted:#aaa; }} }}
:root[data-theme="dark"] {{ --bg:#1e1e1e; --fg:#eaeaea; --box:#2a2a2a; --border:#444; --muted:#aaa; }}
body {{ margin:16px; background:var(--bg); color:var(--fg); font-family:system-ui,sans-serif; }}
.w {{ max-width:760px; }} .box {{ background:var(--box); border:1px solid var(--border); border-radius:6px; padding:16px;
font-family:monospace; font-size:.85rem; white-space:pre-wrap; word-break:break-word; margin-top:8px; }}
button {{ padding:5px 12px; border:1px solid var(--border); border-radius:5px; background:var(--box); color:var(--fg); cursor:pointer; }}
hr {{ margin:20px 0; border:none; border-top:1px solid var(--border); }} .s {{ font-size:.85rem; color:var(--muted); }}
</style></head><body><div class="w">
  <button onclick="c()">Kopieer</button>
  <pre id="t" class="box">{html.escape(mail_text)}</pre>
  <hr><div class="s"><strong>SUGGESTIONS - NOT PART OF REPLY MAIL</strong><ul>
{sug}
  </ul></div></div>
<script>function c(){{navigator.clipboard.writeText(document.getElementById('t').innerText).then(()=>{{const b=document.querySelector('button');b.textContent='Gekopieerd!';setTimeout(()=>b.textContent='Kopieer',1500);}});}}</script>
</body></html>"""


def pretravel_line(rs: list[StopRisk]) -> str:
    """The pretravel condition, with what the countries of the trip ask for (yellow fever, malaria)."""
    notes = [p for p in dict.fromkeys((countries.load(r.country) or {}).get("pretravel") for r in rs) if p]
    consult = f"Pretravel consult ({'; '.join(notes)})" if notes else "Pretravel consult"
    return f"{consult} en registratie via Travellers Online."


def sources(spec=None, iso3s: list[str] | None = None, others=()) -> list[tuple[str, str]]:
    """The links for sources.txt: WHO, the outbreaks' own sources, CDC, and the FOD pages of the trip's countries."""
    spec = spec or outbreak.default()
    fod = [tuple(p) for i in (iso3s or spec.countries)
           for p in (((countries.load(i) or {}).get("fod") or {}).get("pages") or [])]
    own = [tuple(x) for sp in [spec, *others] for x in sp.sources.get("mail", [])]
    return list(dict.fromkeys([("WHO, Disease Outbreak News", "https://www.who.int/emergencies/disease-outbreak-news")]
                              + own + [("US CDC, Travel Health Notices", "https://wwwnc.cdc.gov/travel/notices")]
                              + fod))


def sources_block(spec=None, iso3s: list[str] | None = None, others=()) -> str:
    return "\n\n".join(f"{t}:\n{u}" for t, u in sources(spec, iso3s, others))
