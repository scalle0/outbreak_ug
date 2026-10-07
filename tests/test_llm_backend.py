"""The claude-code backend (F-016): it runs on the subscription login even with an API key in the
environment, says why a call failed, and tries once more when the API is busy. `claude` itself is
replaced: no model, no network."""
import json
import subprocess

import pytest

from dienstreis import llm

WARNING = ("⚠ claude.ai connectors are disabled because ANTHROPIC_API_KEY or another auth source is set and "
           "takes precedence over your claude.ai login · Unset it to load your organization's connectors")


@pytest.fixture()
def claude(monkeypatch):
    """A fake `claude -p`: each call pops the next (returncode, stdout, stderr) and records its env."""
    calls, answers = [], []

    def run(cmd, **kw):
        calls.append(kw)
        code, out, err = answers.pop(0)
        return subprocess.CompletedProcess(cmd, code, out, err)

    monkeypatch.setenv("DIENSTREIS_CLAUDE", "claude")
    monkeypatch.setattr(llm.subprocess, "run", run)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    return calls, answers


def _ok(result):
    return 0, json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": result}), ""


def test_an_api_key_in_the_environment_does_not_reach_claude(claude, monkeypatch):
    calls, answers = claude
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "token")
    monkeypatch.setenv("PATH_TEST", "kept")
    answers.append(_ok('{"ok": true}'))
    assert llm.ClaudeCode().complete("p", step="stops") == '{"ok": true}'
    env = calls[0]["env"]
    assert "ANTHROPIC_API_KEY" not in env and "ANTHROPIC_AUTH_TOKEN" not in env and env["PATH_TEST"] == "kept"


def test_a_failure_names_claudes_reason_not_the_connectors_warning(claude):
    calls, answers = claude
    out = json.dumps({"type": "result", "subtype": "error_during_execution", "is_error": True,
                      "result": "Credit balance is too low"})
    answers.append((1, out, WARNING))
    with pytest.raises(llm.LLMError) as e:
        llm.ClaudeCode().complete("p", step="web", web=True)
    assert "Credit balance is too low" in str(e.value) and "connectors" not in str(e.value)
    assert len(calls) == 1                                        # not a busy API: no second try


def test_an_error_with_exit_code_zero_is_still_an_error(claude):
    _, answers = claude
    answers.append((0, json.dumps({"subtype": "error_max_turns", "is_error": True, "result": ""}), ""))
    with pytest.raises(llm.LLMError, match="error_max_turns"):
        llm.ClaudeCode().complete("p", step="fiche", web=True)


def test_a_busy_api_gets_one_more_try(claude):
    calls, answers = claude
    answers += [(1, json.dumps({"is_error": True, "result": "API Error: 529 Overloaded"}), WARNING), _ok("{}")]
    assert llm.ClaudeCode().complete("p", step="reply") == "{}"
    assert len(calls) == 2
    answers += [(1, json.dumps({"is_error": True, "result": "API Error: 529 Overloaded"}), "")] * 2
    with pytest.raises(llm.LLMError, match="Overloaded"):
        llm.ClaudeCode().complete("p", step="reply")


def test_an_advices_web_step_gets_room_for_all_its_checks(claude, monkeypatch):
    """2026-10-07: the web step ran out of its 25 turns once it also checked case figures and documents."""
    calls, answers = claude
    cmds = []
    run = llm.subprocess.run
    monkeypatch.setattr(llm.subprocess, "run", lambda cmd, **kw: (cmds.append(cmd), run(cmd, **kw))[1])
    for step in ("web", "web_consult", "reply"):
        answers.append(_ok("{}"))
        llm.ClaudeCode().complete("p", step=step, web=step != "reply")
    turns = [c[c.index("--max-turns") + 1] for c in cmds]
    assert turns == ["60", "60", "2"]
    assert [kw["timeout"] for kw in calls] == [1800, 1800, 900]


def test_no_answer_in_time_is_an_llm_error_and_not_retried(claude, monkeypatch):
    calls = []

    def slow(cmd, **kw):
        calls.append(kw)
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(llm.subprocess, "run", slow)
    with pytest.raises(llm.LLMError, match="geen antwoord binnen 1800 s"):
        llm.ClaudeCode().complete("p", step="web", web=True)
    assert len(calls) == 1
