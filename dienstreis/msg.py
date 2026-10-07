"""Request mails -> dict (subject, sender, recipients, body, attachments). Uses olefile for .msg.

A request is one mail (.msg, .eml, .txt) or a folder with every mail of one request in it.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import olefile

from . import outbreak

GENERIC_TERMS = ["outbreak", "uitbraak", "épidémie"]
# an address ends on a domain label, never on the full stop that ends the sentence around it
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# words that point to health data about a person in the mail: ask before it goes to a model
HEALTH_WORDS = re.compile(r"\b(quarantaine|quarantine|isolatie|isolement|isolation|gehospitaliseerd|"
                          r"hospitalis\w*|positief getest|test\w* positief|tested positive|besmet\w*|"
                          r"symptomen|symptômes|symptoms|diagnose|diagnostic|ziek|malade|ill)\b", re.I)


def _outbreak_words() -> re.Pattern:
    """Words that mean the traveller wrote about an outbreak: generic ones and every active profile's."""
    terms = [t for s in outbreak.active() for t in s.match_terms] + GENERIC_TERMS
    return re.compile("|".join(re.escape(t) for t in terms), re.I)


def health_signals(req: dict) -> list[str]:
    """Words in the mail or its attachments that suggest health data about a person, lower case, once each."""
    text = (req.get("body") or "") + " " + " ".join(a.get("text") or "" for a in req.get("attachments", []))
    return sorted({m.group(1).lower() for m in HEALTH_WORDS.finditer(text)})


def _get(ole, stream: str):
    for suf, enc in (("001F", "utf-16-le"), ("001E", "cp1252")):
        if ole.exists(stream + suf):
            return ole.openstream(stream + suf).read().decode(enc, errors="replace").rstrip("\x00")
    return None


# PR_CLIENT_SUBMIT_TIME, then PR_MESSAGE_DELIVERY_TIME; both PT_SYSTIME (a FILETIME, UTC)
_SENT_TAGS = (0x00390040, 0x0E060040)


def _filetime(props: bytes) -> datetime | None:
    """When a .msg was sent (or else delivered), from its top-level property stream.

    The stream has a 32-byte header, then 16-byte entries: tag, flags, an 8-byte value.
    """
    found = {}
    for i in range(32, len(props) - 15, 16):
        tag = int.from_bytes(props[i:i + 4], "little")
        if tag in _SENT_TAGS:
            ft = int.from_bytes(props[i + 8:i + 16], "little")
            if ft:
                found[tag] = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ft // 10)
    return next((found[t] for t in _SENT_TAGS if t in found), None)


def parse_msg(path: str | Path, attach_dir: str | Path | None = None) -> dict:
    path = Path(path)
    ole = olefile.OleFileIO(str(path))
    top = {e[0] for e in ole.listdir()}
    recips = []
    for r in sorted(x for x in top if x.startswith("__recip")):
        recips.append({"name": _get(ole, r + "/__substg1.0_3001"),
                       "email": _get(ole, r + "/__substg1.0_39FE") or _get(ole, r + "/__substg1.0_3003")})
    atts = []
    out = Path(attach_dir) if attach_dir else path.parent / (path.stem + "_attachments")
    for a in sorted(x for x in top if x.startswith("__attach")):
        name = _get(ole, a + "/__substg1.0_3707") or _get(ole, a + "/__substg1.0_3704")
        item = {"name": name, "path": None, "text": None}
        if name and ole.exists(a + "/__substg1.0_37010102"):
            out.mkdir(parents=True, exist_ok=True)
            p = out / name
            p.write_bytes(ole.openstream(a + "/__substg1.0_37010102").read())
            item["path"] = str(p)
            if p.suffix.lower() in (".docx", ".pdf", ".xlsx"):
                item["text"] = _extract_text(p)
        atts.append(item)
    body = _get(ole, "__substg1.0_1000") or ""
    emails = [r["email"] for r in recips if r["email"]] + _EMAIL.findall(body)
    props = "__properties_version1.0"
    sent = _filetime(ole.openstream(props).read()) if ole.exists(props) else None
    return {
        "subject": _get(ole, "__substg1.0_0037"),
        "sent": sent.isoformat() if sent else None,
        "sender": _get(ole, "__substg1.0_0C1A"),
        "sender_email": _get(ole, "__substg1.0_0C1F"),
        "to": _get(ole, "__substg1.0_0E04"),
        "cc": _get(ole, "__substg1.0_0E03"),
        "recipients": recips,
        # reply-mail rule: consolidate replies on uzgent.be when the thread used the ugent.be address
        "sent_to_ugent_address": any(e and e.lower().startswith("steven.callens@ugent.be") for e in
                                     [r["email"] for r in recips]),
        "body": body,
        "attachments": atts,
        # only the traveller's own request counts, not the forwarding note of Team Actueel
        "traveller_mentions_outbreak": bool(_outbreak_words().search(
            _original_request(body) + " ".join(a["text"] or "" for a in atts))),
        "emails_in_thread": sorted(set(e.lower() for e in emails if e)),
    }


def _original_request(body: str) -> str:
    """Text below the first forwarded-message header (the traveller's form), or the body if none."""
    m = re.search(r"\n\s*(Van|From|De)\s*:.*?\n", body)
    return body[m.start():] if m else body


def _extract_text(p: Path) -> str | None:
    """Pure-Python first (works on Windows), external tools as fallback."""
    try:
        if p.suffix.lower() == ".docx":
            import docx
            d = docx.Document(str(p))
            rows = [" | ".join(c.text for c in r.cells) for t in d.tables for r in t.rows]
            return "\n".join([x.text for x in d.paragraphs] + rows)
        if p.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            return "\n".join(pg.extract_text() or "" for pg in PdfReader(str(p)).pages)
    except Exception:
        pass
    for cmd in (["extract-text", str(p)], ["pandoc", str(p), "-t", "plain"]):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True).stdout
        except Exception:
            continue
    return None


def parse_request(path: str | Path) -> dict:
    """A folder of mails; .msg via olefile; .eml via the email package; anything else as pasted mail text."""
    path = Path(path)
    if path.is_dir():
        return parse_folder(path)
    if path.suffix.lower() == ".msg":
        return parse_msg(path)
    if path.suffix.lower() == ".eml":
        import email
        from email import policy
        m = email.message_from_bytes(path.read_bytes(), policy=policy.default)
        part = m.get_body(preferencelist=("plain", "html"))
        body = part.get_content() if part else ""
        rec = [{"name": None, "email": a} for a in _EMAIL.findall(f"{m['to']} {m['cc']}")]
        try:
            sent = parsedate_to_datetime(m["date"]).isoformat() if m["date"] else None
        except (TypeError, ValueError):
            sent = None
    else:
        body = path.read_text(encoding="utf-8", errors="replace")
        m, rec, sent = {}, [], None
    return {"subject": (m.get("subject") if m else None) or path.stem, "sender": m.get("from") if m else None,
            "sent": sent,
            "recipients": rec, "body": body, "attachments": [],
            "sent_to_ugent_address": any(r["email"].lower().startswith("steven.callens@ugent.be") for r in rec),
            "traveller_mentions_outbreak": bool(_outbreak_words().search(_original_request(body))),
            "emails_in_thread": sorted(set(e.lower() for e in _EMAIL.findall(body)))}


MAILS = (".msg", ".eml", ".txt")
DOCUMENTS = (".docx", ".pdf", ".xlsx")


def _sent(req: dict, path: Path) -> tuple[datetime, bool]:
    """When a mail was sent, in UTC, and whether that came from the file date instead of the mail."""
    if req.get("sent"):
        t = datetime.fromisoformat(req["sent"])
        return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc), False
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc), True


def parse_folder(folder: str | Path) -> dict:
    """Every mail of one request, in one folder, read as one request, oldest first.

    A request rarely arrives in one piece: a first mail, a correction an hour later, the answer to a
    question. Each .msg, .eml and .txt is read on its own and put in order by the date in the mail
    itself (the file date only when the mail has none, and then the header says so), so the model
    reads the thread as it happened and can let a later mail correct an earlier one. Loose .docx,
    .pdf and .xlsx files in the folder count as attachments. The reply answers the last mail, so
    subject, sender and recipients are the last mail's.
    """
    folder = Path(folder)
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in MAILS)
    if not files:
        raise ValueError(f"geen mails ({', '.join(MAILS)}) in {folder}")
    mails = sorted(((parse_request(p), p) for p in files), key=lambda x: _sent(*x)[0])
    n, last = len(mails), mails[-1][0]
    parts, atts, seen, index = [], [], set(), []
    for i, (m, p) in enumerate(mails, start=1):
        when, from_file = _sent(m, p)
        stamp = f"{when.astimezone():%d/%m/%Y %H:%M}" + (" (bestandsdatum)" if from_file else "")
        parts.append(f"===== Mail {i} van {n}: {stamp} | {m.get('sender') or '?'} | "
                     f"{m.get('subject') or p.stem} =====\n{m.get('body') or ''}")
        index.append({"file": p.name, "sent": when.isoformat(), "sender": m.get("sender"),
                      "subject": m.get("subject")})
        for a in m.get("attachments", []):
            if a.get("name") not in seen:
                seen.add(a.get("name"))
                atts.append(a)
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in DOCUMENTS and p.name not in seen:
            seen.add(p.name)
            atts.append({"name": p.name, "path": str(p), "text": _extract_text(p)})
    reqs = [m for m, _ in mails]
    return {**{k: last.get(k) for k in ("subject", "sender", "sender_email", "to", "cc", "recipients")},
            "sent": index[-1]["sent"], "body": "\n\n".join(parts), "attachments": atts,
            "sent_to_ugent_address": any(r.get("sent_to_ugent_address") for r in reqs),
            "traveller_mentions_outbreak": any(r.get("traveller_mentions_outbreak") for r in reqs),
            "emails_in_thread": sorted({e for r in reqs for e in r.get("emails_in_thread", [])}),
            "mails": index, "mail_count": n}


if __name__ == "__main__":
    import sys
    print(json.dumps(parse_msg(sys.argv[1]), ensure_ascii=False, indent=2)[:20000])
