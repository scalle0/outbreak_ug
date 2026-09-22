"""Outlook .msg -> dict (subject, sender, recipients, body, attachments). Uses olefile only."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import olefile


def _get(ole, stream: str):
    for suf, enc in (("001F", "utf-16-le"), ("001E", "cp1252")):
        if ole.exists(stream + suf):
            return ole.openstream(stream + suf).read().decode(enc, errors="replace").rstrip("\x00")
    return None


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
    emails = [r["email"] for r in recips if r["email"]] + re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", body)
    return {
        "subject": _get(ole, "__substg1.0_0037"),
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
        "traveller_mentions_outbreak": bool(re.search(r"ebola|bundibugyo|outbreak|uitbraak|épidémie",
                                                      _original_request(body) + " ".join(a["text"] or "" for a in atts),
                                                      re.I)),
        "emails_in_thread": sorted(set(e.lower() for e in emails if e)),
    }


def _original_request(body: str) -> str:
    """Text below the first forwarded-message header (the traveller's form), or the body if none."""
    m = re.search(r"\n\s*(Van|From|De)\s*:.*?\n", body)
    return body[m.start():] if m else body


def _extract_text(p: Path) -> str | None:
    for cmd in (["extract-text", str(p)], ["pandoc", str(p), "-t", "plain"]):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True).stdout
        except Exception:
            continue
    return None


if __name__ == "__main__":
    import sys
    print(json.dumps(parse_msg(sys.argv[1]), ensure_ascii=False, indent=2)[:20000])
