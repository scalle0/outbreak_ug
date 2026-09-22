"""Optional: put the reply as a draft in Outlook (Windows, `pip install pywin32`). Never sends."""
from __future__ import annotations

from pathlib import Path


def draft(req: dict, body: str, attachments: list[str], to: str = "actueel@ugent.be") -> None:
    import win32com.client  # noqa: import only on Windows with pywin32
    ol = win32com.client.Dispatch("Outlook.Application")
    m = ol.CreateItem(0)
    subj = req.get("subject") or "dienstreis"
    m.To = to
    m.Subject = subj if subj.lower().startswith(("re:", "antw:")) else f"RE: {subj}"
    m.Body = body
    for a in attachments:
        if a and Path(a).exists():
            m.Attachments.Add(str(Path(a).resolve()))
    m.Display(False)
