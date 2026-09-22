"""LLM layer: the only place where the package calls a language model.

The model is used for three judgement steps and nothing else:
  stops  : turn the request mail into a structured itinerary (stops.yaml), for the user to confirm
  web    : optional check of FOD/CDC advisories and recent news that is not yet in the data
  reply  : write the Dutch reply from the skeleton, the risk table and the context

Backends
  claude-code : `claude -p` (Claude Code CLI, uses the user's own subscription); default
  api         : Anthropic API (needs ANTHROPIC_API_KEY and `pip install anthropic`)
  manual      : writes the prompt to a file; the user pastes the answer from any chat window
  fake        : canned answers for tests
Every step asks for JSON; `ask_json` extracts it, validates the required keys and retries once.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

PROMPTS = Path(__file__).parent / "prompts"
DEFAULT_API_MODEL = "claude-opus-5"


class LLMError(RuntimeError):
    pass


def load_prompt(step: str) -> str:
    return (PROMPTS / f"{step}.md").read_text(encoding="utf-8")


def build_prompt(step: str, inputs: dict) -> str:
    """Instruction file for the step followed by the inputs as clearly delimited JSON blocks."""
    parts = [load_prompt(step), "", "# Invoer", ""]
    for k, v in inputs.items():
        body = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=1, default=str)
        parts += [f"<{k}>", body, f"</{k}>", ""]
    return "\n".join(parts)


def extract_json(text: str) -> dict:
    """First JSON object in the answer, with or without ```json fences."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    cand = m.group(1) if m else None
    if cand is None:
        i = text.find("{")
        if i < 0:
            raise LLMError("geen JSON in het antwoord")
        depth, instr, esc = 0, False, False
        for j, ch in enumerate(text[i:], start=i):
            if instr:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    instr = False
                continue
            if ch == '"':
                instr = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cand = text[i:j + 1]
                    break
    if cand is None:
        raise LLMError("onvolledige JSON in het antwoord")
    return json.loads(cand)


class Backend:
    name = "base"

    def complete(self, prompt: str, *, step: str, web: bool = False) -> str:
        raise NotImplementedError


class ClaudeCode(Backend):
    """Headless Claude Code. The prompt goes in via stdin (no Windows command-line length limit)."""
    name = "claude-code"

    def __init__(self, model: str | None = None, workdir: Path | None = None, timeout: int = 900):
        self.bin = os.environ.get("DIENSTREIS_CLAUDE") or shutil.which("claude") or shutil.which("claude.exe")
        if not self.bin:
            raise LLMError("Claude Code niet gevonden; zet DIENSTREIS_CLAUDE op het pad van claude(.exe) "
                           "of gebruik --llm api / --llm manual")
        self.model, self.workdir, self.timeout = model, workdir, timeout

    def complete(self, prompt: str, *, step: str, web: bool = False) -> str:
        cmd = [self.bin, "-p", "Volg de instructies in de invoer. Antwoord uitsluitend met het gevraagde JSON-object.",
               "--output-format", "json"]
        if web:   # only web tools, pre-approved so that print mode never waits for a permission prompt
            cmd += ["--tools", "WebSearch,WebFetch", "--allowedTools", "WebSearch,WebFetch", "--max-turns", "25"]
        else:     # pure text step: no tools at all
            cmd += ["--tools", "", "--max-turns", "2"]
        if self.model:
            cmd += ["--model", self.model]
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                           timeout=self.timeout, cwd=self.workdir)
        if r.returncode != 0:
            raise LLMError(f"claude -p faalde ({r.returncode}): {r.stderr.strip()[:500]}")
        try:
            env = json.loads(r.stdout)
            return env.get("result", "") if isinstance(env, dict) else r.stdout
        except json.JSONDecodeError:
            return r.stdout


class Api(Backend):
    name = "api"

    def __init__(self, model: str | None = None):
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("pip install anthropic (of gebruik --llm claude-code)") from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY ontbreekt")
        self.client = anthropic.Anthropic()
        self.model = model or DEFAULT_API_MODEL

    def complete(self, prompt: str, *, step: str, web: bool = False) -> str:
        kw = {}
        if web:
            kw["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}]
        msg = self.client.messages.create(model=self.model, max_tokens=8000,
                                          messages=[{"role": "user", "content": prompt}], **kw)
        return "".join(getattr(b, "text", "") for b in msg.content)


class Manual(Backend):
    """No model access from the script: the user carries the prompt to a chat window and back."""
    name = "manual"

    def __init__(self, workdir: Path, reader: Callable[[str], str] = input):
        self.workdir, self.reader = Path(workdir), reader

    def complete(self, prompt: str, *, step: str, web: bool = False) -> str:
        self.workdir.mkdir(parents=True, exist_ok=True)
        p = self.workdir / f"prompt_{step}.md"
        a = self.workdir / f"antwoord_{step}.json"
        p.write_text(prompt, encoding="utf-8")
        print(f"\nPlak de inhoud van {p} in een Claude-chat{' met webzoeken' if web else ''} "
              f"en bewaar het JSON-antwoord in {a}.")
        self.reader("Druk op Enter als het antwoord bewaard is... ")
        if not a.exists():
            raise LLMError(f"{a} niet gevonden")
        return a.read_text(encoding="utf-8")


class Fake(Backend):
    """Tests: answers[step] is a dict, a string or a callable(prompt) -> str."""
    name = "fake"

    def __init__(self, answers: dict):
        self.answers, self.prompts = answers, {}

    def complete(self, prompt: str, *, step: str, web: bool = False) -> str:
        self.prompts.setdefault(step, []).append(prompt)
        a = self.answers[step]
        if callable(a):
            a = a(prompt)
        return a if isinstance(a, str) else json.dumps(a, ensure_ascii=False)


def get_backend(name: str, model: str | None = None, workdir: Path | None = None) -> Backend:
    if name == "claude-code":
        return ClaudeCode(model, workdir)
    if name == "api":
        return Api(model)
    if name == "manual":
        return Manual(workdir or Path.cwd())
    raise LLMError(f"onbekende backend {name}")


def ask_json(backend: Backend, step: str, inputs: dict, required: list[str], web: bool = False) -> dict:
    prompt = build_prompt(step, inputs)
    last = None
    for attempt in range(2):
        text = backend.complete(prompt, step=step, web=web)
        try:
            d = extract_json(text)
            miss = [k for k in required if k not in d]
            if not miss:
                return d
            last = f"ontbrekende velden: {miss}"
        except (LLMError, json.JSONDecodeError) as e:
            last = str(e)
        prompt = build_prompt(step, inputs) + f"\n\nJe vorige antwoord was onbruikbaar ({last}). " \
                                                "Geef enkel het JSON-object met alle gevraagde velden."
    raise LLMError(f"stap {step}: {last}")
