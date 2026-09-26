"""The fixed fiche per disease and its key documents: written once from sources, confirmed by Steven.

    outbreaks/<id>/fiche.md         front matter (status concept | bevestigd, verified, bevestigd_door,
                                    bevestigd_op), then fixed sections (SECTIONS); a statement cites its
                                    document as [document-id]
    outbreaks/<id>/documents.yaml   the key documents per level (be, eu, who, us): id, org, title,
                                    date, url, key (the key message in one sentence)

The clinical background of an advice (clinical picture, treatment, vaccination, isolation, return
to Belgium) is not looked up again on every run: the web step finds what it happens to find, and a
letter about isolation should rest on text a clinician has read. So the fiche is drafted once
(`dienstreis fiche <id> --opstellen`, prompts/fiche.md) and stays a concept until Steven sets
`status: bevestigd`. Only a confirmed fiche reaches the letter step; the dossier shows either,
a concept under a banner.

The web step checks every run for newer guidance (prompts/web.md, web_consult.md). A newer or new
document is proposed and, after a yes, kept in a local copy
(~/.config/dienstreis/outbreaks/<id>/documents.yaml), which wins while it is verified more recently
than the one in the package, as for the country registry. A statement of the fiche that newer
guidance contradicts is only shown (`fiche_flags`): prose about treatment is changed by Steven, never
by the code. A local fiche.md wins the same way, for a fiche confirmed before it reaches the repo.
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

import yaml

# the same folder as data.LOCAL_OUTBREAKS: per outbreak its local case table, documents and fiche
LOCAL = Path(os.environ.get("DIENSTREIS_OUTBREAKS", Path.home() / ".config" / "dienstreis" / "outbreaks"))
FICHE, DOCUMENTS, CONCEPT = "fiche.md", "documents.yaml", "fiche_concept.md"
SECTIONS = ("Verwekker", "Overdracht", "Incubatie", "Klinisch beeld", "Ernst en letaliteit", "Diagnose",
            "Behandeling", "Vaccinatie en PEP", "Preventie voor reizigers", "Isolatie en vrijgave",
            "Terugkeer naar België")
LEVELS = {"be": "België", "eu": "Europa", "who": "WHO", "us": "Verenigde Staten"}
STATUS = ("concept", "bevestigd")
_REF = re.compile(r"\[([a-z0-9][a-z0-9-]*)\]")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:60] or "document"


def _verified(meta: dict) -> str:
    return str(meta.get("verified") or "")


# ---------------------------------------------------------------- the fiche
def parse(text: str) -> tuple[dict, str]:
    """fiche.md -> (front matter, body)."""
    text = text.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            return yaml.safe_load(text[4:end]) or {}, text[end + 5:].lstrip("\n")
    return {}, text


def sections(body: str) -> dict[str, str]:
    """The body's `## ` sections, in order: {title: text}."""
    parts = re.split(r"^## +(.+?)\s*$", body, flags=re.M)
    return {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts), 2)}


def _pick(spec, name: str, verified) -> tuple[Path | None, str]:
    """The package's file or the local copy, whichever was verified last."""
    pkg, loc = spec.dir / name, LOCAL / spec.id / name
    if loc.exists() and (not pkg.exists() or verified(loc) > verified(pkg)):
        return loc, "lokaal"
    return (pkg, "pakket") if pkg.exists() else (None, "")


def load(spec) -> dict | None:
    """The fiche of an outbreak, or None when it has none yet."""
    path, source = _pick(spec, FICHE, lambda p: _verified(parse(p.read_text(encoding="utf-8"))[0]))
    if path is None:
        return None
    meta, body = parse(path.read_text(encoding="utf-8"))
    secs = sections(body)
    status = meta.get("status") if meta.get("status") in STATUS else "concept"
    issues = [f"status '{meta.get('status')}' onbekend; gelezen als concept"] if meta.get("status") not in STATUS else []
    issues += [f"sectie ontbreekt: {s}" for s in SECTIONS if s not in secs]
    return {"outbreak": spec.id, "status": status, "confirmed": status == "bevestigd",
            "verified": _verified(meta), "bevestigd_door": meta.get("bevestigd_door"),
            "bevestigd_op": str(meta.get("bevestigd_op") or ""), "body": body, "sections": secs,
            "refs": sorted(set(_REF.findall(body))), "path": str(path), "source": source, "issues": issues}


def confirmed_text(spec) -> str | None:
    """The fiche as the letter step gets it: only once Steven confirmed it."""
    f = load(spec)
    return f["body"] if f and f["confirmed"] else None


# ---------------------------------------------------------------- the documents
def _read_docs(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def documents(spec) -> dict:
    """{"verified", "levels": {be|eu|who|us: [doc]}, "path", "source"}; empty levels when there is no list yet."""
    path, source = _pick(spec, DOCUMENTS, lambda p: _verified(_read_docs(p)))
    d = _read_docs(path) if path else {}
    return {"verified": _verified(d), "path": str(path or ""), "source": source,
            "levels": {lv: [x for x in d.get(lv) or [] if isinstance(x, dict)] for lv in LEVELS}}


def check_documents(d: dict) -> list[str]:
    """Problems with a documents list: every entry needs an id, org, title and url; ids are unique."""
    issues, seen = [], set()
    for lv, docs in d["levels"].items():
        for x in docs:
            miss = [k for k in ("id", "org", "title", "url") if not x.get(k)]
            if miss:
                issues.append(f"{lv}: {x.get('title') or x.get('id') or '?'} mist {', '.join(miss)}")
            if x.get("id") in seen:
                issues.append(f"{lv}: id '{x['id']}' komt twee keer voor")
            seen.add(x.get("id"))
    return issues


def for_prompt(spec) -> dict:
    """What the web step needs to look for newer guidance: the documents, and the fiche's text and date."""
    f, d = load(spec), documents(spec)
    return {"documenten": {lv: [{k: x.get(k) for k in ("id", "org", "title", "date", "url")} for x in docs]
                           for lv, docs in d["levels"].items()},
            "documenten_nagekeken": d["verified"] or None,
            "fiche": ({"status": f["status"], "nagekeken": f["verified"], "tekst": f["body"][:8000]} if f else None)}


def apply_updates(spec, updates: list[dict], today: date | None = None) -> dict:
    """The documents list as it would be with the web step's proposals; nothing is written here.

    `nieuw` adds a document to its level; `nieuwere_versie` replaces the one it names in `replaces`,
    keeping that id so the fiche's references still hold. The list gets today's date as verified.
    """
    from . import countries
    d = documents(spec)
    levels = {lv: [dict(x) for x in docs] for lv, docs in d["levels"].items()}
    ids = {x.get("id") for docs in levels.values() for x in docs}
    for u in updates:
        lv = u.get("level")
        if lv not in LEVELS or not u.get("url") or countries.excluded(u["url"]):
            continue
        doc = {k: u.get(k) for k in ("org", "title", "date", "url", "key") if u.get(k)}
        old = u.get("replaces")
        if u.get("action") == "nieuwere_versie" and old in ids:
            for docs in levels.values():
                for i, x in enumerate(docs):
                    if x.get("id") == old:
                        docs[i] = {"id": old, **doc, "verified": str(today or date.today())}
            continue
        new_id = _slug(f"{u.get('org', '')}-{u.get('title', '')}")
        while new_id in ids:
            new_id += "-2"
        ids.add(new_id)
        levels[lv].append({"id": new_id, **doc, "verified": str(today or date.today())})
    return {"verified": str(today or date.today()), **levels}


def save_local_documents(spec, docs: dict) -> Path:
    p = LOCAL / spec.id / DOCUMENTS
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(docs, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


# ---------------------------------------------------------------- a draft from the model
def render_draft(spec, answer: dict, today: date | None = None) -> tuple[str, dict]:
    """The model's draft (prompts/fiche.md) as fiche.md text and a documents list, always a concept."""
    today = str(today or date.today())
    secs = answer.get("secties") or {}
    head = {"outbreak": spec.id, "status": "concept", "verified": today, "bevestigd_door": None, "bevestigd_op": None}
    body = [f"# {spec.name}: ziektefiche", ""]
    for s in SECTIONS:
        body += [f"## {s}", "", str(secs.get(s) or "(niet gevonden in de bronnen; aan te vullen)").strip(), ""]
    text = ("---\n" + yaml.safe_dump(head, allow_unicode=True, sort_keys=False)
            + "# concept: nog niet bevestigd; zet status op bevestigd, met bevestigd_door en bevestigd_op\n---\n\n"
            + "\n".join(body).rstrip() + "\n")
    from . import countries
    docs = {"verified": today}
    for lv in LEVELS:
        docs[lv] = [{"id": x.get("id") or _slug(f"{x.get('org', '')}-{x.get('title', '')}"),
                     **{k: x.get(k) for k in ("org", "title", "date", "url", "key") if x.get(k)}}
                    for x in (answer.get("documenten") or {}).get(lv) or []
                    if isinstance(x, dict) and x.get("url") and not countries.excluded(x["url"])]
    return text, docs


def write_draft(spec, answer: dict, dest: Path, today: date | None = None) -> list[Path]:
    """Write the draft into `dest`. A confirmed fiche there is never overwritten: the draft goes next to
    it as fiche_concept.md, to compare by hand."""
    dest.mkdir(parents=True, exist_ok=True)
    text, docs = render_draft(spec, answer, today)
    current = dest / FICHE
    confirmed = current.exists() and parse(current.read_text(encoding="utf-8"))[0].get("status") == "bevestigd"
    fp = dest / (CONCEPT if confirmed else FICHE)
    fp.write_text(text, encoding="utf-8")
    dp = dest / (DOCUMENTS if not confirmed else "documents_concept.yaml")
    dp.write_text(yaml.safe_dump(docs, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return [fp, dp]
