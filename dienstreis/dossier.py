"""The internal dossier: one self-contained HTML page per advice, for Steven, not for An.

The letter to An is short (F-015); everything behind it is here: the request and An's questions with
the answer each got, the verdict per outbreak, the epidemiology with curve, map and tables, the risks
for this traveller from the country registry, the guidance and sources, the model's assessment, what
the web step found, and the earlier advices for the same places or person.

The page is rendered from what the run left in its folder (summary.json, stops.yaml, feiten.txt,
reply.txt, web.json, sources.txt, the figures) and from dossier.json, which holds what no other file
keeps: the request, the model's assessment and the results of the checks. So `dienstreis dossier
<folder>` can rebuild it after a hand edit of reply.txt. Only the assessment comes from the model.

The copy button stays disabled while a blocking check fails, as the old widget was never built
around such a text. Figures are embedded, scaled down, so the archived page opens anywhere; the
full-size PNGs stay for Outlook. Layout: the ScAIdev design system (tokens v2, copied below); the
colours of the map and the curve are data colours and stay as they are.
"""
from __future__ import annotations

import base64
import html
import io
import json
import re
from datetime import date, datetime
from pathlib import Path

import yaml

from . import countries, fiche, mail, outbreak, risk

DATA = "dossier.json"
PAGE = "dossier.html"
IMG_WIDTH = 1600            # the figures are drawn at 300 dpi for Outlook; a screen needs a fraction of that
KIND = {"reisadvies": "Reisadvies", "casus": "Casus", "vraag": "Vraag"}
LEVEL = {"afraden": ("stop", "afraden"), "voorwaardelijk": ("cond", "voorwaardelijk"),
         "geen_bezwaar": ("ok", "geen bezwaar")}
SECTIONS = (("antwoord", "Antwoord"), ("aanvraag", "Aanvraag"), ("oordeel", "Oordeel"),
            ("epidemiologie", "Epidemiologie"), ("risico", "Risico"), ("fiche", "Ziektefiche"),
            ("richtlijnen", "Richtlijnen"), ("beoordeling", "Beoordeling"), ("web", "Web"),
            ("eerder", "Eerder"), ("bronnen", "Bronnen"))
PROFILE = {"lodging": "verblijf", "healthcare_work": "zorg- of labowerk", "family": "bij familie",
           "long_stay": "lang verblijf", "work": "werk"}
MODEL_FIELDS = (("beoordeling", "Beoordeling"), ("weggelaten", "Uit de mail gelaten"),
                ("na_te_kijken", "Na te kijken voor verzending"), ("toezeggingen", "Toezeggingen in de mail"),
                ("vragen_aan_behandelaar", "Vragen aan de behandelende arts"))

# Lucide line icons (ISC licence), inline so the page needs nothing from the network
ICONS = {
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "printer": '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
               '<path d="M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6"/><rect x="6" y="14" width="12" height="8" rx="1"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
             '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "link": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3"/>',
}
MARK = ('<svg class="mark" viewBox="0 0 64 64" aria-hidden="true"><g stroke="#3D8FC4" stroke-width="1.1" fill="none" '
        'opacity="0.85" stroke-linecap="round"><line x1="14" y1="20" x2="28" y2="30"/><line x1="14" y1="46" x2="28" '
        'y2="30"/><line x1="28" y1="30" x2="44" y2="18"/><line x1="28" y1="30" x2="48" y2="34"/><line x1="28" y1="30" '
        'x2="38" y2="46"/><line x1="48" y1="34" x2="44" y2="18"/><line x1="48" y1="34" x2="38" y2="46"/></g><g '
        'fill="#3D8FC4"><circle cx="14" cy="20" r="2.6"/><circle cx="14" cy="46" r="2.6"/><circle cx="44" cy="18" '
        'r="2.6"/><circle cx="48" cy="34" r="2.6"/><circle cx="38" cy="46" r="2.6"/></g><circle cx="44" cy="18" '
        'r="1.1" fill="#C8A96A"/><circle cx="28" cy="30" r="9" fill="#4FAE6A" opacity="0.18"/><circle cx="28" '
        'cy="30" r="5" fill="#4FAE6A"/><circle cx="26.5" cy="28.5" r="1.8" fill="#AEE0B6" opacity="0.7"/></svg>')

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
:root {
  --ink-900: #0B1418; --ink-800: #152127; --paper-50: #F5F7F4; --paper-100: #EAEEE8; --paper-300: #B0BBAB;
  --green-600: #2D8452; --green-500: #4FAE6A; --green-300: #AEE0B6;
  --blue-700: #246D9A; --blue-500: #3D8FC4; --sand-500: #C8A96A;
  --font-display: 'Space Grotesk', system-ui, sans-serif; --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
  --panel: #FFFFFF; --line: rgba(11, 20, 24, 0.10); --line-strong: rgba(11, 20, 24, 0.22);
  --muted: rgba(11, 20, 24, 0.66); --ok-bg: rgba(79, 174, 106, 0.12); --soft-bg: rgba(61, 143, 196, 0.10);
  --hard-bg: rgba(200, 169, 106, 0.14); --hard-ink: #7A6232;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 76px; }
body { margin: 0; font: 15px/1.5 var(--font-body); color: var(--ink-900); background: var(--paper-50); }
a { color: var(--blue-700); } a:hover { color: var(--blue-500); }
:focus-visible { outline: 2px solid var(--blue-500); outline-offset: 3px; }
.icon { width: 18px; height: 18px; flex: none; stroke: currentColor; stroke-width: 1.5; fill: none;
        stroke-linecap: round; stroke-linejoin: round; vertical-align: -4px; }
.mono, code { font-family: var(--font-mono); font-size: 0.92em; }
.muted { color: var(--muted); }
.topbar { position: sticky; top: 0; z-index: 10; display: flex; flex-wrap: wrap; align-items: center;
          gap: 8px 24px; padding: 10px 24px; background: var(--ink-900); color: var(--paper-100);
          border-bottom: 1px solid rgba(255, 255, 255, 0.10); }
.brand { display: flex; align-items: center; gap: 10px; font: 600 18px var(--font-display); letter-spacing: -0.02em; color: #fff; }
.mark { width: 30px; height: 30px; }
.tag { font: 500 11px var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase; color: rgba(234, 238, 232, 0.5); }
.toc { display: flex; flex-wrap: wrap; gap: 2px 14px; font: 600 13px var(--font-display); }
.toc a { color: var(--paper-300); text-decoration: none; padding: 4px 0; border-bottom: 2px solid transparent; }
.toc a:hover { color: #fff; border-bottom-color: var(--green-500); }
.wordmark { margin-left: auto; font: 700 13px var(--font-display); color: var(--paper-100); }
.wordmark .ai { color: var(--green-500); } .wordmark .dev { color: #7A857E; font-weight: 500; }
main { max-width: 1120px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font: 700 28px/1.2 var(--font-display); letter-spacing: -0.02em; margin: 0 0 8px; }
h2 { font: 600 20px/1.2 var(--font-display); letter-spacing: -0.02em; margin: 0 0 14px; }
h3 { font: 600 16px/1.25 var(--font-display); letter-spacing: -0.01em; margin: 22px 0 8px; }
h3:first-child { margin-top: 0; }
h4 { font: 600 14px/1.3 var(--font-display); margin: 16px 0 4px; }
.fiche p { margin: 4px 0 8px; } .fiche ul { margin: 4px 0 8px; padding-left: 20px; }
.ref { font-family: var(--font-mono); font-size: 0.85em; text-decoration: none; }
.eyebrow { font: 500 11px var(--font-mono); letter-spacing: 0.18em; text-transform: uppercase; color: var(--green-600); margin-bottom: 6px; }
section { margin-top: 28px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 20px 24px;
         box-shadow: 0 4px 24px -8px rgba(6, 11, 14, 0.12); }
.meta { display: flex; flex-wrap: wrap; gap: 4px 20px; font-size: 13px; color: var(--muted); margin-top: 10px; }
.meta b { font: 500 13px var(--font-mono); color: var(--ink-900); }
.badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px;
         font: 500 12px var(--font-mono); border: 1px solid var(--line); background: rgba(11, 20, 24, 0.04); color: var(--muted); }
.badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.badge.ok { background: var(--ok-bg); color: var(--green-600); border-color: rgba(79, 174, 106, 0.4); }
.badge.cond { background: var(--soft-bg); color: var(--blue-700); border-color: rgba(61, 143, 196, 0.4); }
.badge.stop { background: var(--hard-bg); color: var(--hard-ink); border-color: rgba(200, 169, 106, 0.6); }
.alert { display: flex; gap: 8px; align-items: flex-start; padding: 10px 12px; border-radius: 4px; margin: 8px 0;
         border: 1px solid var(--line); background: rgba(11, 20, 24, 0.03); }
.alert .icon { margin-top: 2px; }
.alert.hard { background: var(--hard-bg); border-color: rgba(200, 169, 106, 0.6); }
.alert.hard .icon { color: var(--hard-ink); }
.alert.soft { background: var(--soft-bg); border-color: rgba(61, 143, 196, 0.35); }
.alert.soft .icon { color: var(--blue-700); }
.alert.ok { background: var(--ok-bg); border-color: rgba(79, 174, 106, 0.4); }
.alert.ok .icon { color: var(--green-600); }
.row { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }
.btn { display: inline-flex; align-items: center; gap: 6px; font: 600 14px var(--font-display); cursor: pointer;
       border: 1px solid var(--line-strong); background: transparent; color: var(--ink-900); padding: 8px 14px; border-radius: 4px; }
.btn:hover { border-color: var(--blue-500); color: var(--blue-700); }
.btn.primary { background: var(--green-500); border-color: var(--green-500); color: var(--ink-900); }
.btn.primary:hover { filter: brightness(1.05); box-shadow: 0 0 0 1px rgba(61, 143, 196, 0.5); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
pre.letter { white-space: pre-wrap; word-break: break-word; font: 15px/1.55 var(--font-body); margin: 14px 0 0;
             background: var(--paper-50); border: 1px solid var(--line); border-radius: 4px; padding: 16px 18px; }
.tablewrap { overflow-x: auto; margin: 6px 0 4px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { text-align: left; font: 500 11px var(--font-mono); letter-spacing: 0.06em; text-transform: uppercase;
     color: var(--muted); border-bottom: 1px solid var(--line-strong); padding: 6px 8px; white-space: nowrap; }
td { border-bottom: 1px solid var(--line); padding: 6px 8px; vertical-align: top; }
td.n { font-family: var(--font-mono); text-align: right; white-space: nowrap; } th.n { text-align: right; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 8px 0 14px; }
.tile { border: 1px solid var(--line); border-radius: 4px; padding: 10px 12px; background: var(--paper-50); }
.tile .v { font: 700 22px/1.2 var(--font-display); letter-spacing: -0.02em; }
.tile .l { font-size: 12px; color: var(--muted); }
.figs { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
figure { margin: 12px 0; break-inside: avoid; }
figure img { width: 100%; height: auto; border: 1px solid var(--line); border-radius: 4px; background: #fff; }
figcaption { font-size: 12px; color: var(--muted); margin-top: 4px; }
dl.kv { display: grid; grid-template-columns: max-content 1fr; gap: 4px 18px; margin: 0; }
dl.kv dt { color: var(--muted); font-size: 13px; padding-top: 1px; } dl.kv dd { margin: 0; }
ul.items { margin: 4px 0; padding-left: 20px; } ul.items li { margin: 3px 0; }
details { margin-top: 12px; } details summary { cursor: pointer; color: var(--blue-700); font-size: 13px; }
details pre { white-space: pre-wrap; word-break: break-word; font: 12.5px/1.5 var(--font-mono); background: var(--paper-50);
              padding: 12px; border: 1px solid var(--line); border-radius: 4px; max-height: 480px; overflow: auto; }
.part + .part { margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--line); }
@media (max-width: 900px) { .figs { grid-template-columns: 1fr; } .toc { display: none; } }
@media (max-width: 640px) { .topbar { padding: 8px 16px; } .panel { padding: 16px; } dl.kv { grid-template-columns: 1fr; } }
@media print {
  .topbar, .noprint { display: none !important; }
  body { background: #fff; font-size: 12px; } main { max-width: none; padding: 0; }
  .panel { box-shadow: none; border-color: #ccc; } a { color: inherit; } section { margin-top: 16px; }
}
"""

JS = """
function kopieer() {
  const t = document.getElementById('t'), b = document.getElementById('kopieer');
  const label = b.innerHTML;
  const done = (msg) => { b.textContent = msg; setTimeout(() => { b.innerHTML = label; }, 1600); };
  const select = () => { const r = document.createRange(); r.selectNodeContents(t);
    const s = getSelection(); s.removeAllRanges(); s.addRange(r); done('Geselecteerd: Ctrl+C'); };
  if (navigator.clipboard) { navigator.clipboard.writeText(t.innerText).then(() => done('Gekopieerd'), select); }
  else { select(); }
}
"""


# ---------------------------------------------------------------- small pieces
def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _icon(name: str) -> str:
    return f'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def _alert(text: str, kind: str = "soft", raw: bool = False) -> str:
    icon = {"hard": "alert", "soft": "info", "ok": "check"}.get(kind, "info")
    return f'<div class="alert {kind}">{_icon(icon)}<div>{text if raw else _e(text)}</div></div>'


def _items(xs, raw: bool = False) -> str:
    xs = [x for x in xs if str(x).strip()]
    if not xs:
        return ""
    return '<ul class="items">' + "".join(f"<li>{x if raw else _e(x)}</li>" for x in xs) + "</ul>"


def _table(head: list[str], rows: list[list], numeric: set[int] = frozenset()) -> str:
    """A table; cells are escaped unless they are already markup (tuple ('html', text))."""
    if not rows:
        return ""
    def cell(i, v):
        v = v[1] if isinstance(v, tuple) and v and v[0] == "html" else _e("" if v is None else v)
        return f'<td class="n">{v}</td>' if i in numeric else f"<td>{v}</td>"
    body = "".join("<tr>" + "".join(cell(i, v) for i, v in enumerate(r)) + "</tr>" for r in rows)
    return ('<div class="tablewrap"><table><thead><tr>'
            + "".join(f'<th class="n">{_e(h)}</th>' if i in numeric else f"<th>{_e(h)}</th>" for i, h in enumerate(head))
            + f"</tr></thead><tbody>{body}</tbody></table></div>")


def _kv(pairs) -> str:
    rows = [(k, v) for k, v in pairs if v not in (None, "", [], {})]
    if not rows:
        return ""
    return '<dl class="kv">' + "".join(
        f"<dt>{_e(k)}</dt><dd>{v[1] if isinstance(v, tuple) and v[0] == 'html' else _e(v)}</dd>"
        for k, v in rows) + "</dl>"


def _link(url: str | None, text: str | None = None) -> str:
    if not url:
        return _e(text or "")
    if not re.match(r"^(https?|file):", str(url)):
        return _e(text or url)
    return f'<a href="{_e(url)}" target="_blank" rel="noopener">{_e(text or url)}</a>'


def _n(x) -> str:
    return "" if x is None else mail.n(x) if isinstance(x, int) else str(x)


def _date(x) -> str:
    """A date the way the letters write it: 22-08-2026."""
    try:
        return date.fromisoformat(str(x)[:10]).strftime("%d-%m-%Y")
    except ValueError:
        return str(x or "")


def _level_badge(level: str | None, text: str) -> str:
    cls = LEVEL.get(level or "", ("", ""))[0]
    return f'<span class="badge {cls}">{_e(text)}</span>'


def _level_of(verdict: str | None) -> str | None:
    """The level of a verdict as the rules write it; a verdict the clinician wrote gets none."""
    v = str(verdict or "")
    if "niet goedkeuren" in v or "afraden" in v:
        return "afraden"
    if "voorwaardelijk" in v:
        return "voorwaardelijk"
    if "geen" in v and "bezwaar" in v:
        return "geen_bezwaar"
    return None


def _section(key: str, title: str, body: str) -> str:
    n = [k for k, _ in SECTIONS].index(key) + 1
    return (f'<section id="{key}"><div class="eyebrow">{n:02d}</div><div class="panel">'
            f"<h2>{_e(title)}</h2>{body}</div></section>")


def _img(out: Path, p: str | None) -> str | None:
    """A figure of the run as a data URI, scaled down to IMG_WIDTH; None when it was not drawn."""
    if not p:
        return None
    f = out / Path(p).name
    if not f.exists():
        return None
    from PIL import Image
    try:
        with Image.open(f) as im:
            im.load()
            if im.width > IMG_WIDTH:
                im = im.resize((IMG_WIDTH, round(im.height * IMG_WIDTH / im.width)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
    except OSError:                          # not an image after all: the page renders without it
        return None
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _figure(uri: str | None, caption: str) -> str:
    return (f'<figure><img src="{uri}" alt="{_e(caption)}"><figcaption>{_e(caption)}</figcaption></figure>'
            if uri else "")


# ---------------------------------------------------------------- the run
def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_run(out) -> dict:
    """Everything the page is rendered from, read from the run's folder."""
    out = Path(out)
    def txt(name):
        p = out / name
        return p.read_text(encoding="utf-8") if p.exists() else ""
    return {"out": out, "summary": _read_json(out / "summary.json", {}),
            "trip": yaml.safe_load(txt("stops.yaml")) or {}, "web": _read_json(out / "web.json", {}),
            "reply": txt("reply.txt"), "feiten": txt("feiten.txt"), "sources": txt("sources.txt"),
            "data": _read_json(out / DATA, {})}


def _spec(oid: str | None):
    try:
        return outbreak.load(oid) if oid else None
    except (outbreak.ProfileError, OSError, KeyError):    # a profile removed since: the page still renders
        return None


def _ids(s: dict) -> list[str]:
    return list(s.get("outbreaks") or []) or ([s["outbreak"]] if s.get("outbreak") else [])


def _parts(s: dict) -> dict[str, dict]:
    """Every outbreak of the advice in one shape, strictest first; a single one from the top of the summary."""
    if s.get("outbreaks"):
        return s["outbreaks"]
    oid = s.get("outbreak")
    if not oid:
        return {}
    sp = _spec(oid)
    return {oid: {"name": sp.name if sp else oid, "asof": s.get("asof"), "overall": s.get("overall"),
                  "rule_overall": s.get("rule_overall"), "level": s.get("overall_level"),
                  "overrides": s.get("overrides") or [], "epi": s.get("epi"), "stops": s.get("stops") or [],
                  "qa": s.get("qa") or {}, "who": s.get("who"), "map": s.get("map"), "epicurve": s.get("epicurve")}}


def recheck(out) -> dict:
    """The checks on reply.txt as it is now, with the same limits as the run: after a hand edit, the
    page must say what the text still fails, and keep the copy button off while a blocking check does."""
    from . import advies
    run = load_run(out)
    s, d = run["summary"], run["data"]
    specs = [sp for sp in (_spec(i) for i in _ids(s)) if sp]
    kind = d.get("type") or s.get("type") or "reisadvies"
    sources = [run["feiten"], json.dumps(s, ensure_ascii=False, default=str),
               json.dumps(run["web"], ensure_ascii=False, default=str) if run["web"] else "",
               (d.get("aanvraag") or {}).get("body") or "",
               *[t for t in (fiche.confirmed_text(sp) for sp in specs) if t]]      # as in the run
    reply = run["reply"]
    issues = mail.check_reply(reply, sources, numbers=d.get("numbers", True), specs=specs or None)
    questions = (d.get("aanvraag") or {}).get("questions_from_an") or []
    notes = advies._soft_notes({"reply": reply, "dossier": d.get("model")},
                               s.get("overall") if kind == "reisadvies" else None, specs,
                               coverage=kind == "reisadvies", questions=questions)
    return {"issues": issues, "notes": notes}


# ---------------------------------------------------------------- sections
def _hero(run: dict) -> str:
    s, t, d = run["summary"], run["trip"], run["data"]
    kind = d.get("type") or s.get("type") or t.get("type") or "reisadvies"
    places = [x.get("place") for x in s.get("stops") or [] if x.get("place")]
    title = t.get("traveller") or (d.get("aanvraag") or {}).get("subject") or "Advies"
    sub = t.get("situation") if kind != "reisadvies" else t.get("note")
    badges = []
    if kind == "reisadvies":
        for oid, p in _parts(s).items():
            badges.append(_level_badge(p.get("level") or _level_of(p.get("overall")), f"{p.get('name', oid)}: {p.get('overall')}"))
        final = (t.get("override") or {}).get("verdict")
        if final:
            badges.append(_level_badge(_level_of(final), f"eindoordeel: {final}"))
    else:
        badges.append('<span class="badge">geen reisoordeel: een casus of vraag</span>')
        badges += [f'<span class="badge">{_e(p.get("name", oid))}</span>' for oid, p in _parts(s).items()]
    review = d.get("review_on") or t.get("review_on")
    meta = [("Go/no-go", _date(review) if review else ""), ("Cijfers tot", _date(s.get("asof")) if s.get("asof") else ""),
            ("Gemaakt", d.get("created", "")[:16].replace("T", " ")), ("Opnieuw opgebouwd", d.get("rebuilt", "")[:16].replace("T", " "))]
    meta_html = "".join(f"<span>{_e(k)} <b>{_e(v)}</b></span>" for k, v in meta if v)
    if d.get("proef"):
        badges.insert(0, '<span class="badge stop">proefrun</span>')
    return (f'<div class="eyebrow">{_e(KIND.get(kind, kind))} · intern dossier, niet voor An</div>'
            f"<h1>{_e(title)}{(' · ' + _e(', '.join(dict.fromkeys(places)))) if places else ''}</h1>"
            + (f'<p class="muted" style="margin:0">{_e(sub)}</p>' if sub else "")
            + f'<div class="badges">{"".join(badges)}</div><div class="meta">{meta_html}</div>')


def _attention(run: dict) -> str:
    d = run["data"]
    checks = d.get("checks") or {}
    out = [_alert("Proefrun: niet in het archief, geen logregel, geen contextregel, niets overgenomen. "
                  "Enkel de map van deze run.", "hard")] if d.get("proef") else []
    out += [_alert("Blokkerende controle: " + x, "hard") for x in checks.get("issues") or []]
    out += [_alert(x, "soft") for x in d.get("warnings") or []]
    return f'<div style="margin-top:16px">{"".join(out)}</div>' if out else ""


def _answer(run: dict) -> str:
    d, s = run["data"], run["summary"]
    checks = d.get("checks") or {}
    kind = d.get("type") or s.get("type") or "reisadvies"
    n_out = max(1, len(_ids(s)))
    limit = mail.MAX_WORDS + 50 * (n_out - 1) if kind == "reisadvies" else mail.MAX_WORDS
    words = mail.word_count(run["reply"])
    blocked = bool(checks.get("issues"))
    cmd = f"dienstreis dossier \"{run['out']}\""
    body = ('<div class="row noprint">'
            f'<button id="kopieer" class="btn primary" onclick="kopieer()"{" disabled" if blocked else ""}>'
            f'{_icon("copy")} Kopieer de mail</button>'
            f'<button class="btn" onclick="window.print()">{_icon("printer")} Afdrukken of PDF</button>'
            f'<span class="muted mono">{words} woorden · richtlijn {mail.TARGET_WORDS}, maximum {limit}</span></div>')
    if blocked:
        body += _alert("Kopiëren staat uit: " + _e("; ".join(checks["issues"])) + f". Pas reply.txt aan en draai "
                       f"<code>{_e(cmd)}</code>.", "hard", raw=True)
    body += f'<pre id="t" class="letter">{_e(run["reply"].rstrip())}</pre>'
    sent = d.get("attachments_sent")
    if sent:
        body += f'<p class="muted">Bijlagen bij de mail: {_e(", ".join(sent))}.</p>'
    elif kind != "reisadvies":
        body += '<p class="muted">Geen bijlagen: bij een casus of vraag blijven kaart en curve in dit dossier.</p>'
    body += "".join(_alert(x, "soft") for x in checks.get("notes") or [])
    return _section("antwoord", "Antwoord aan An", body)


def _request(run: dict) -> str:
    d, t, s = run["data"], run["trip"], run["summary"]
    a = d.get("aanvraag") or {}
    kind = d.get("type") or s.get("type") or "reisadvies"
    prof = t.get("profile") or {}
    prof_txt = "; ".join(f"{PROFILE.get(k, k)}: {'ja' if v is True else 'nee' if v is False else v}"
                         for k, v in prof.items() if v not in (None, ""))
    body = _kv([("Onderwerp", a.get("subject")), ("Van", a.get("sender")),
                ("Mails", a.get("mail_count") if (a.get("mail_count") or 1) > 1 else ""),
                ("Bijlagen", ", ".join(a.get("attachments") or [])), ("Type", KIND.get(kind, kind)),
                ("Reiziger", t.get("traveller")), ("Opmerking", t.get("note")),
                ("Toestand", t.get("situation")), ("Nationaliteit", a.get("nationality")),
                ("Aard van het werk", a.get("work_nature")), ("Vervoer", a.get("transport")),
                ("Profiel", prof_txt)])
    qs = a.get("questions_from_an") or []
    pairs = [p for p in ((d.get("model") or {}).get("vragen") or []) if isinstance(p, dict)]
    rows = []
    for i in range(max(len(qs), len(pairs))):
        q = qs[i] if i < len(qs) else (pairs[i].get("vraag") if i < len(pairs) else "")
        ans = pairs[i].get("antwoord") if i < len(pairs) else ""
        rows.append([q, ans or ("html", '<span class="muted">geen antwoord gekoppeld</span>')])
    if rows:
        body += "<h3>Vragen van An en het antwoord in de mail</h3>" + _table(["Vraag", "Antwoord in de mail"], rows)
    for key, label in (("missing_info", "Ontbreekt"), ("contradictions", "Tegenstrijdig")):
        if a.get(key):
            body += f"<h3>{label}</h3>" + _items(a[key])
    if d.get("unmatched"):
        body += "<h3>Genoemd, zonder actief uitbraakprofiel</h3>" + _items(d["unmatched"])
    stops = t.get("stops") or []
    if stops:
        body += "<h3>Reisschema</h3>" + _table(
            ["Van", "Tot", "Plaats", "Verblijf"],
            [[_date(x.get("from")), _date(x.get("to")) if x.get("to") else "open", x.get("place"),
              "transit" if x.get("transit_only") else (x.get("lodging") or "")] for x in stops])
    if a.get("body"):
        body += f"<details><summary>De aanvraag zoals ze binnenkwam</summary><pre>{_e(a['body'])}</pre></details>"
    return _section("aanvraag", "Aanvraag", body)


def _verdict(run: dict) -> str:
    s, t, d = run["summary"], run["trip"], run["data"]
    kind = d.get("type") or s.get("type") or "reisadvies"
    parts = _parts(s)
    if kind != "reisadvies":
        body = "<p>Geen oordeel volgens de regels: een casus of vraag krijgt een antwoord, geen reisoordeel.</p>"
    else:
        body = _table(["Uitbraak", "Volgens de regels", "Oordeel", "Niveau"],
                      [[p.get("name", oid), p.get("rule_overall"), p.get("overall"),
                        ("html", _level_badge(p.get("level"), LEVEL.get(p.get("level") or "", ("", "-"))[1]))]
                       for oid, p in parts.items()])
        if (t.get("override") or {}).get("verdict"):
            body += _alert(f"Eindoordeel voor de hele reis: {t['override']['verdict']} "
                           f"({t['override'].get('reason') or 'zonder reden'})", "soft")
    ov = s.get("overrides") or []
    if ov:
        body += "<h3>Bewust afgeweken van de regels</h3>" + _table(
            ["Waar", "Uitbraak", "Van", "Naar", "Reden"],
            [[o.get("scope"), o.get("outbreak", ""), o.get("van"), o.get("naar"), o.get("reason")] for o in ov])
    for oid, p in parts.items():
        rows = [[x.get("place"), x.get("zone") or x.get("country") or "", x.get("category"), x.get("label"),
                 x.get("verdict"), x.get("override_reason") or ""] for x in p.get("stops") or []]
        if rows:
            body += f"<h3>Per halte: {_e(p.get('name', oid))}</h3>" + _table(
                ["Halte", "Zone", "Cat", "Betekenis", "Regel", "Overrule"], rows)
    body += _categories(parts)
    review = d.get("review_on") or t.get("review_on")
    if review:
        body += f'<p>Go/no-go: <b class="mono">{_e(_date(review))}</b>, een week voor vertrek uit België.</p>'
    return _section("oordeel", "Oordeel", body)


def _categories(parts: dict) -> str:
    """What the categories mean, per outbreak: the rule, the verdict per stop and its weight for the trip.
    The categories of this advice (by the rules and after an overrule) are in bold; a profile without
    figures has only X and needs no legend."""
    out = ""
    for oid, p in parts.items():
        sp = _spec(oid)
        if not sp or not sp.windows.get("active"):
            continue
        seen = {x.get(k) for x in p.get("stops") or [] for k in ("category", "rule_category")}
        rows = []
        for c in outbreak.CATEGORIES:
            if c not in sp.categories:
                continue
            lvl = sp.level(c)
            cell = (lambda v: ("html", f"<b>{_e(v)}</b>")) if c in seen else (lambda v: v)
            rows.append([cell(c), cell(risk.definition(c, sp)), cell(sp.verdict(c)),
                         ("html", _level_badge(lvl, LEVEL.get(lvl, ("", lvl))[1]))])
        out += (f"<h3>Wat de categorieën betekenen: {_e(sp.name)}</h3>"
                + _table(["Cat", "Wanneer", "Oordeel per halte", "Weegt voor de reis als"], rows)
                + f'<p class="muted">Dagen geteld vanaf de laatste datum in de cijfers. De strengste halte bepaalt '
                  f"het oordeel voor de reis: afraden gaat voor voorwaardelijk, voorwaardelijk voor geen bezwaar. "
                  f"FOD, CDC, verblijf bij familie of een lang verblijf veranderen de categorie niet; ze staan bij "
                  f"de halte als aandachtspunt. Vetgedrukt: de categorieën in dit advies.</p>")
    return out


def _weeks(epi: dict) -> str:
    rows = epi.get("weeks_last8") or []
    if rows:
        return _table(["Week tot (zondag)", "Nieuwe gevallen", "Nieuwe overlijdens"],
                      [[_date(r.get("week")), _n(r.get("cases")), _n(r.get("deaths"))] for r in rows], {1, 2})
    w = epi.get("weekly_cases_last4_full_weeks") or {}
    return _table(["Week tot (zondag)", "Nieuwe gevallen"], [[k, _n(v)] for k, v in w.items()], {1}) if w else ""


def _qa_items(q: dict) -> list[str]:
    out = []
    def mark(ok, text):
        out.append(f'{_icon("check" if ok else "alert")} {_e(text)}')
    if q.get("zone_sum_matches_national") is not None:
        mark(q["zone_sum_matches_national"], "som van de zones klopt met het nationale totaal"
             if q["zone_sum_matches_national"] else "som van de zones wijkt af van het nationale totaal")
    e = q.get("ecdc") or {}
    if e.get("check"):
        mark(e["check"]["matches"] is not False, e["check"]["text"])
    elif q.get("ecdc_matches") is not None:
        mark(q["ecdc_matches"], f"ECDC-controle: {_n(e.get('cases'))} gevallen, data tot {mail.nl_months(str(e.get('data_until')))}"
             + ("" if q["ecdc_matches"] else " (wijkt af)"))
    w = q.get("who") or {}
    if w.get("ok"):
        mark(not w.get("from_cache"), f"WHO: {w.get('item')} ({_date(w.get('date'))}, {w.get('days_old')} dagen oud)"
             + (f"; WHO niet bereikbaar, laatst gelezen op {_date(w.get('read_on'))}" if w.get("from_cache") else ""))
    if q.get("table_last_date") or q.get("table_empty"):
        mark(not q.get("table_stale"), f"tabel: laatste datum {_date(q.get('table_last_date'))}, "
             f"{q.get('table_days_old')} dagen oud" + (" (te oud)" if q.get("table_stale") else ""))
    if q.get("unmatched_zone_names"):
        mark(False, "zonenamen zonder vorm op de kaart: " + ", ".join(map(str, q["unmatched_zone_names"])))
    for k in q.get("sources_unreachable") or []:
        mark(False, f"{k.upper()} niet bereikbaar tijdens de run ({(q.get(k) or {}).get('reason')})")
    if q.get("map_label_overlaps") or q.get("map_labels_clipped"):
        mark(False, f"kaartlabels: {q.get('map_label_overlaps')} overlappen, {q.get('map_labels_clipped')} vallen weg")
    return out


def _epidemiology(run: dict) -> str:
    s, out = run["summary"], run["out"]
    blocks = []
    for oid, p in _parts(s).items():
        sp = _spec(oid)
        epi, q = p.get("epi"), p.get("qa") or {}
        head = f"<h3>{_e(p.get('name', oid))}" + (f" · cijfers tot {_e(_date(p.get('asof')))}" if p.get("asof") else "") + "</h3>"
        if not epi:
            why = ("de cijfertabel is leeg" if q.get("table_empty") else
                   "geen uitbraakprofiel: het advies staat op landniveau" if oid == outbreak.NONE else "geen cijfers")
            blocks.append(f'<div class="part">{head}<p class="muted">Geen epidemiologie: {_e(why)}.</p></div>')
            continue
        words = sp.case_words if sp else {"cases": "gevallen", "deaths": "overlijdens"}
        nat = (sp.sources.get("national") if sp else None) or "nationale cijfers"
        tiles = [(mail.n(epi["last_total"]), f"{words['cases']} ({nat})"),
                 (mail.n(epi["last_deaths"]), words.get("deaths", "overlijdens")),
                 (f"{epi.get('cfr', 0):.1f} %", "ruwe CFR")]
        e = q.get("ecdc") or {}
        if e.get("ok"):
            tiles.append((mail.n(e["cases"]), f"ECDC, data tot {mail.nl_months(str(e.get('data_until')))}"))
        tiles_html = '<div class="tiles">' + "".join(
            f'<div class="tile"><div class="v">{_e(v)}</div><div class="l">{_e(l)}</div></div>' for v, l in tiles) + "</div>"
        figs = [_figure(_img(out, p.get("epicurve")), f"Epidemiecurve {p.get('name', oid)}"),
                _figure(_img(out, p.get("map")), f"Kaart met het reisschema, {p.get('name', oid)}")]
        figs_html = f'<div class="figs">{"".join(figs)}</div>' if any(figs) else ""
        recent = sp.recent if sp else 14
        zones = _table(["Halte", "Zone (provincie)", "Cat", "Gevallen", f"Nieuw ({recent} d)", "Dagen sinds laatste",
                        "Actieve buurzones", "Dichtstbijzijnde actieve zone"],
                       [[x.get("place"), f"{x.get('zone') or '-'}" + (f" ({x['province']})" if x.get("province") else ""),
                         x.get("category"), _n(x.get("cases")), _n(x.get("new14")),
                         "" if x.get("days_since_last") is None else f"{x['days_since_last']:.0f}",
                         ", ".join(f"{z.get('zone')} ({z.get('cases')})" for z in x.get("neighbours_active") or []),
                         (lambda a: f"{a.get('zone')}, {a.get('km')} km, {a.get('days_since_last')} d geleden" if a else "")(
                             x.get("nearest_active"))]
                        for x in p.get("stops") or []], {3, 4, 5})
        qa = _items(_qa_items(q), raw=True)
        blocks.append(f'<div class="part">{head}{tiles_html}'
                      + ("<h3>Per volle week</h3>" + _weeks(epi) if _weeks(epi) else "")
                      + figs_html + ("<h3>De zones van het reisschema</h3>" + zones if zones else "")
                      + ("<h3>Controles op de cijfers</h3>" + qa if qa else "") + "</div>")
    body = "".join(blocks) or '<p class="muted">Geen uitbraak van toepassing.</p>'
    return _section("epidemiologie", "Epidemiologie", body)


def _risk(run: dict) -> str:
    s, t = run["summary"], run["trip"]
    stops = s.get("stops") or []
    body = ""
    rows = [[x.get("place"), x.get("country") or "",
             f"{x.get('fod')}" + (f" ({x['fod_reason']})" if x.get("fod_reason") else "") if x.get("fod") else "",
             x.get("cdc") if x.get("cdc") is not None else "", ("html", _items(x.get("flags") or []) or "")]
            for x in stops]
    if rows:
        body += "<h3>Per halte</h3>" + _table(["Halte", "Land", "FOD", "CDC", "Signalen"], rows, {3})
    ids = _ids(s)
    for iso in dict.fromkeys(x.get("country") for x in stops if x.get("country")):
        c = countries.load(iso)
        if not c:
            body += f"<h3>{_e(iso)}</h3><p class=\"muted\">Niet in het landenregister.</p>"
            continue
        age = countries.age_days(c)
        verified = (f"{_date(c.get('verified'))} ({age} dagen geleden)" if age is not None else "nooit nagekeken")
        provs = sorted({x.get("province") for x in stops if x.get("country") == iso and x.get("province")})
        # the country, then only the provinces of the trip with an entry of their own (the rest follow the country)
        lv, rs = countries.fod(c)
        fod_rows = [f"heel het land: {lv}" + (f" ({rs})" if rs else "")] if lv else []
        own = ((c.get("fod") or {}).get("regions") or {})
        fod_rows += [f"{pv}: {own[pv].get('level')}" + (f" ({own[pv]['reason']})" if own[pv].get("reason") else "")
                     for pv in provs if pv in own]
        cdc_rows = []
        for oid in ids:
            if countries.cdc(c, oid) is None:
                continue
            own_cdc = (((c.get("cdc") or {}).get(oid) or {}).get("regions") or {})
            cdc_rows.append(f"{oid}: niveau {countries.cdc(c, oid)}"
                            + "".join(f"; {pv}: {own_cdc[pv]}" for pv in provs if pv in own_cdc))
        meas = [f"{m.get('text')} ({_date(m.get('date'))})" for oid in ids for m in countries.measures(c, oid)]
        pages = [_link(u, lbl) for lbl, u in (c.get("fod") or {}).get("pages") or []]
        body += (f"<h3>{_e(c.get('name_nl') or iso)}</h3>"
                 + _kv([("Nagekeken", verified), ("FOD", ("html", _items(fod_rows))),
                        ("CDC", ("html", _items(cdc_rows)) if cdc_rows else ""),
                        ("Grensmaatregelen", ("html", _items(meas)) if meas else ""),
                        ("Pretravel", c.get("pretravel")), ("FOD-pagina's", ("html", _items(pages, raw=True)) if pages else "")]))
    prof = t.get("profile") or {}
    if prof:
        body = "<h3>Profiel van de reiziger</h3>" + _kv(
            [(PROFILE.get(k, k), "ja" if v is True else "nee" if v is False else v) for k, v in prof.items()]) + body
    return _section("risico", "Risico voor deze reiziger", body or '<p class="muted">Geen reisschema.</p>')


def _md(text: str, known: set[str]) -> str:
    """Markdown of the fiche as HTML: raw HTML is shown as text, links go to the web or within the page,
    and a reference [document-id] links to that document under Richtlijnen."""
    import markdown
    h = markdown.markdown(str(text).replace("<", "&lt;"), extensions=["sane_lists", "tables"])
    h = re.sub(r'href="(?!https?:|#)[^"]*"', 'href="#"', h)
    return fiche._REF.sub(lambda m: (f'<a class="ref" href="#doc-{_e(m.group(1))}">[{_e(m.group(1))}]</a>'
                                     if m.group(1) in known else m.group(0)), h)


def _doc_ids(sp) -> set[str]:
    return {x.get("id") for docs in fiche.documents(sp)["levels"].values() for x in docs if x.get("id")}


def _fiche(run: dict) -> str:
    flags = [f for f in (run["web"] or {}).get("fiche_flags") or [] if isinstance(f, dict)]
    blocks = []
    for oid, p in _parts(run["summary"]).items():
        sp = _spec(oid)
        if oid == outbreak.NONE or sp is None:
            continue
        f = fiche.load(sp)
        head = f"<h3>{_e(p.get('name', oid))}</h3>"
        if not f:
            blocks.append(f'<div class="part">{head}<p class="muted">Nog geen fiche. Maak een concept met '
                          f"<code>dienstreis fiche {_e(oid)} --opstellen</code>.</p></div>")
            continue
        if f["confirmed"]:
            state = _alert(f"Bevestigd door {f.get('bevestigd_door') or '?'} op {_date(f.get('bevestigd_op'))}; "
                           f"bronnen nagekeken op {_date(f.get('verified'))}.", "ok")
        else:
            state = _alert(f"Concept, nog niet bevestigd: de mail steunt er niet op. Nagelezen? Zet "
                           f"<code>status: bevestigd</code>, <code>bevestigd_door</code> en <code>bevestigd_op</code> "
                           f"in {_e(f['path'])}.", "hard", raw=True)
        state += "".join(_alert(
            f"Mogelijk verouderd, {_e(x.get('section'))}: &ldquo;{_e(x.get('statement'))}&rdquo;. Nieuwer: "
            f"{_e(x.get('newer'))} ({_link(x.get('source'), 'bron')}, {_e(_date(x.get('date')))}).", "soft", raw=True)
            for x in flags if x.get("outbreak") == oid)
        known = _doc_ids(sp)
        order = list(fiche.SECTIONS) + [k for k in f["sections"] if k not in fiche.SECTIONS]
        secs = "".join(f"<h4>{_e(k)}</h4>{_md(f['sections'][k], known)}" for k in order if f["sections"].get(k))
        issues = _items(f["issues"] + [f"verwijzing zonder document: [{r}]" for r in f["refs"] if r not in known])
        blocks.append(f'<div class="part">{head}{state}<div class="fiche">{secs}</div>'
                      + (f'<p class="muted">Bij de fiche:</p>{issues}' if issues else "") + "</div>")
    body = "".join(blocks) or '<p class="muted">Geen uitbraakprofiel, dus geen fiche.</p>'
    return _section("fiche", "Ziektefiche", body)


def _sources_list(txt: str) -> list[tuple[str, str]]:
    """sources.txt as (label, url): a label line ending in a colon, the url on the next."""
    rows, lines = [], [x.strip() for x in txt.splitlines()]
    for i, line in enumerate(lines[:-1]):
        if line.endswith(":") and lines[i + 1].startswith("http"):
            rows.append((line[:-1], lines[i + 1]))
    return rows


def _documents(run: dict) -> str:
    """The key documents per outbreak and level, what the web step proposed, and the countries' own."""
    body = ""
    for oid, p in _parts(run["summary"]).items():
        sp = _spec(oid)
        if oid == outbreak.NONE or sp is None:
            continue
        d = fiche.documents(sp)
        rows_by_level = [(fiche.LEVELS[lv], docs) for lv, docs in d["levels"].items() if docs]
        if not rows_by_level:
            body += (f"<h3>{_e(p.get('name', oid))}</h3><p class=\"muted\">Nog geen documentenlijst: "
                     f"<code>dienstreis fiche {_e(oid)} --opstellen</code>.</p>")
            continue
        body += (f"<h3>{_e(p.get('name', oid))}</h3>"
                 + (f'<p class="muted">Nagekeken op {_e(_date(d["verified"]))}.</p>' if d["verified"] else ""))
        for label, docs in rows_by_level:
            body += f"<h4>{_e(label)}</h4>" + _table(
                ["Document", "Organisatie", "Datum", "Kernboodschap"],
                [[("html", f'<span id="doc-{_e(x.get("id"))}"></span>{_link(x.get("url"), x.get("title"))}'),
                  x.get("org"), _date(x.get("date")), x.get("key")] for x in docs])
    ups = [u for u in (run["web"] or {}).get("document_updates") or [] if isinstance(u, dict)]
    if ups:
        acc = run["data"].get("web_accepted")
        body += "<h3>Voorgesteld door de webstap</h3>" + _table(
            ["Uitbraak", "Niveau", "Wat", "Document", "Datum", "Kernboodschap"],
            [[u.get("outbreak"), fiche.LEVELS.get(u.get("level"), u.get("level")),
              f"vervangt {u.get('replaces')}" if u.get("action") == "nieuwere_versie" else "nieuw",
              ("html", _link(u.get("url"), u.get("title"))), _date(u.get("date")), u.get("key")] for u in ups])
        body += (_alert("Overgenomen in de lokale documentenlijst.", "ok") if acc is True else
                 _alert("Niet overgenomen.", "soft") if acc is False else "")
    for iso in dict.fromkeys(x.get("country") for x in run["summary"].get("stops") or [] if x.get("country")):
        docs = [x for x in (countries.load(iso) or {}).get("documents") or [] if isinstance(x, dict)]
        if docs:
            body += f"<h3>{_e(iso)}: documenten van het land</h3>" + _table(
                ["Document", "Organisatie", "Datum", "Kernboodschap"],
                [[("html", _link(x.get("url"), x.get("title"))), x.get("org"), _date(x.get("date")), x.get("key")]
                 for x in docs])
    return body


def _guidance(run: dict) -> str:
    g = [x for x in (run["web"] or {}).get("guidance") or [] if isinstance(x, dict)]
    body = _documents(run)
    if g:
        body += "<h3>Wat de webstap aan richtlijnen vond</h3>" + _table(
            ["Onderwerp", "Wat", "Bron", "Datum"],
            [[x.get("topic"), x.get("text"), ("html", _link(x.get("source"), "bron")), _date(x.get("date"))] for x in g])
    src = _sources_list(run["sources"])
    if src:
        body += "<h3>Bronnen van dit advies</h3>" + _items([_link(u, lbl) for lbl, u in src], raw=True)
    return _section("richtlijnen", "Richtlijnen en documenten", body or '<p class="muted">Geen richtlijnen of bronnen.</p>')


def _assessment(run: dict) -> str:
    d = run["data"]
    m = d.get("model") or {}
    body = ""
    for key, label in MODEL_FIELDS:
        v = m.get(key) or []
        v = v if isinstance(v, list) else [v]
        if any(str(x).strip() for x in v):
            body += f"<h3>{label}</h3>" + _items(v)
    if d.get("suggestions"):
        body += "<h3>Notities</h3>" + _items(d["suggestions"])
    return _section("beoordeling", "Beoordeling (model)",
                    body or '<p class="muted">Het model gaf geen beoordeling terug.</p>')


def _web(run: dict) -> str:
    w, d = run["web"] or {}, run["data"]
    if not w:
        why = (f"De webstap faalde ({_e(d['web_failed'])}): niets is live nagekeken." if d.get("web_failed")
               else "De webstap draaide niet (--no-web).")
        return _section("web", "Nieuws en webbevindingen", f'<p class="muted">{why}</p>')
    body = ""
    who = w.get("who") or {}
    if who:
        body += "<h3>WHO</h3>" + _kv([("Laatste DON", _date(who.get("latest_don"))),
                                      ("Nieuwer dan de invoer", "ja" if who.get("newer_than_input") else ""),
                                      ("Risico-inschatting", who.get("risk_assessment")),
                                      ("Reisbeperkingen aangeraden", "ja" if who.get("travel_restrictions_advised") else ""),
                                      ("Bron", ("html", _link(who.get("url"))) if who.get("url") else "")])
    adv = [a for a in w.get("advisories") or [] if isinstance(a, dict)]
    if adv:
        body += "<h3>Reisadviezen</h3>" + _table(
            ["Land", "Regio", "FOD", "CDC", "Gewijzigd", "Bron"],
            [[a.get("country"), a.get("region") or "heel het land",
              f"{a.get('fod')}" + (f" ({a['fod_reason']})" if a.get("fod_reason") else ""), a.get("cdc"),
              "ja" if a.get("changed") else "", ("html", _link(a.get("source"), a.get("checked_how") or "bron"))] for a in adv])
    meas = [m for m in w.get("measures") or [] if isinstance(m, dict)]
    if meas:
        body += "<h3>Grensmaatregelen</h3>" + _table(
            ["Land", "Maatregel", "Datum", "Gewijzigd", "Bron"],
            [[m.get("country"), m.get("text"), _date(m.get("date")), "ja" if m.get("changed") else "",
              ("html", _link(m.get("source"), "bron"))] for m in meas])
    news = [n for n in w.get("news") or [] if isinstance(n, dict)]
    if news:
        body += "<h3>Nieuws</h3>" + _items([f"{_e(_date(n.get('date')))}: {_e(n.get('item'))} "
                                            f"{_link(n.get('url'), '(bron)') if n.get('url') else ''}" for n in news], raw=True)
    cu = [r for r in w.get("case_updates") or [] if isinstance(r, dict)]
    if cu:
        body += "<h3>Voorgestelde cijfers</h3>" + _table(
            ["Uitbraak", "Datum", "Gebied", "Gevallen", "Overlijdens", "Definitie", "Bron"],
            [[r.get("outbreak"), _date(r.get("date")), " / ".join(x for x in (r.get("admin1"), r.get("admin2")) if x),
              _n(r.get("cases_cum")), _n(r.get("deaths_cum")), r.get("case_def"), ("html", _link(r.get("source_url"), "bron"))]
             for r in cu], {3, 4})
    src = [x for x in w.get("sources") or [] if isinstance(x, dict)]
    if src:
        body += "<h3>Voorgestelde bronnen</h3>" + _items(
            [f"{_e(x.get('country'))} ({_e(x.get('kind'))}): {_link(x.get('url'), x.get('name'))}"
             + (f" <span class='muted'>{_e(x.get('why'))}</span>" if x.get("why") else "") for x in src], raw=True)
    if w.get("notes"):
        body += "<h3>Notities van de webstap</h3>" + _items(w["notes"])
    acc = d.get("web_accepted")
    body += (_alert("Wat de webstap voorstelde, is overgenomen in het lokale landenregister.", "ok") if acc is True else
             _alert("Wat de webstap voorstelde, is niet overgenomen.", "soft") if acc is False else "")
    return _section("web", "Nieuws en webbevindingen", body or '<p class="muted">De webstap vond niets.</p>')


def _earlier(run: dict) -> str:
    d = run["data"]
    body = ""
    rows = []
    for r in d.get("earlier") or []:
        page = Path(r["dir"]) / PAGE if r.get("dir") else None
        link = (_link(page.resolve().as_uri(), "dossier") if page and page.exists() else
                _e(r.get("dir") or ""))
        rows.append([_date(r.get("advised_on")), r.get("traveller"), KIND.get(r.get("type"), r.get("type") or ""),
                     ", ".join(map(str, r.get("places") or [])), r.get("overall"), _date(r.get("review_on")) if r.get("review_on") else "",
                     ("html", link)])
    if rows:
        body += "<h3>Adviezen voor dezelfde plaatsen of persoon</h3>" + _table(
            ["Datum", "Reiziger", "Type", "Plaatsen", "Oordeel", "Go/no-go", ""], rows)
    hist = d.get("history") or []
    if hist:
        body += "<h3>Logregels</h3>" + _table(
            ["Datum", "Reiziger", "Haltes", "Cat", "Oordeel", "Go/no-go"],
            [[_date(h.get("advised_on")), h.get("traveller"), h.get("stops"), h.get("categories"), h.get("overall"),
              _date(h.get("review_on")) if h.get("review_on") else ""] for h in hist])
    if d.get("context_lines"):
        body += "<h3>Uit context.md</h3>" + _items(d["context_lines"])
    return _section("eerder", "Eerdere adviezen", body or '<p class="muted">Geen eerdere adviezen voor deze plaatsen of persoon.</p>')


def _trace(run: dict) -> str:
    s, d, out = run["summary"], run["data"], run["out"]
    rows = []
    for oid, p in _parts(s).items():
        q = p.get("qa") or {}
        w, e = q.get("who") or {}, q.get("ecdc") or {}
        sp = _spec(oid)
        rows.append([p.get("name", oid), _date(p.get("asof")) if p.get("asof") else "",
                     f"{_date(w.get('date'))} ({w.get('days_old')} d)" if w.get("ok") else "niet gevonden",
                     mail.nl_months(str(e.get("data_until"))) if e.get("ok") else "",
                     _date(q.get("table_last_date")) if q.get("table_last_date") else "",
                     ("html", _link(sp.dir.resolve().as_uri(), sp.id)) if sp else oid])
    body = _table(["Uitbraak", "Cijfers tot", "WHO DON", "ECDC tot", "Tabel tot", "Profiel"], rows)
    files = [("Map van deze run", ("html", _link(out.resolve().as_uri(), str(out.resolve())))),
             ("Archief", ("html", _link(Path(d["advice_dir"]).resolve().as_uri(), d["advice_dir"])) if d.get("advice_dir") else ""),
             ("Modelspoor", "llm_trace.json" if (out / "llm_trace.json").exists() else ""),
             ("Webstap", "web.json" if (out / "web.json").exists() else ""),
             ("Versie", d.get("version")), ("Gemaakt", (d.get("created") or "")[:19].replace("T", " "))]
    body += "<h3>Bestanden</h3>" + _kv(files)
    if run["feiten"]:
        body += f"<details><summary>feiten.txt: de berekende feiten waaruit de mail geschreven is</summary><pre>{_e(run['feiten'])}</pre></details>"
    return _section("bronnen", "Bronnen en traceerbaarheid", body)


# ---------------------------------------------------------------- the page
def render(run: dict) -> str:
    s, t, d = run["summary"], run["trip"], run["data"]
    title = f"Dossier {t.get('traveller') or (d.get('aanvraag') or {}).get('subject') or ''}".strip()
    toc = "".join(f'<a href="#{k}">{_e(v)}</a>' for k, v in SECTIONS)
    parts = [_answer(run), _request(run), _verdict(run), _epidemiology(run), _risk(run), _fiche(run),
             _guidance(run), _assessment(run), _web(run), _earlier(run), _trace(run)]
    return ("<!DOCTYPE html>\n<html lang=\"nl\"><head><meta charset=\"UTF-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
            f"<title>{_e(title)}</title><style>{CSS}</style></head><body>"
            f'<header class="topbar"><div class="brand">{MARK}<span>dienstreis</span><span class="tag">intern dossier</span></div>'
            f'<nav class="toc" aria-label="Inhoud">{toc}</nav>'
            '<span class="wordmark">Sc<span class="ai">AI</span><span class="dev">dev</span></span></header>'
            f"<main><div class=\"panel\">{_hero(run)}{_attention(run)}</div>{''.join(parts)}</main>"
            f"<script>{JS}</script></body></html>\n")


def build(out, rebuilt: bool = False) -> Path:
    """Write dossier.html in the run's folder from what the run left there, and return its path.

    `rebuilt` re-runs the checks on reply.txt first, for a letter edited by hand after the run.
    """
    out = Path(out)
    if rebuilt:
        data = _read_json(out / DATA, {})
        data["checks"] = recheck(out)
        data["rebuilt"] = datetime.now().isoformat(timespec="seconds")
        (out / DATA).write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    page = out / PAGE
    page.write_text(render(load_run(out)), encoding="utf-8")
    return page
