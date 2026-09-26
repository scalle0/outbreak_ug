"""Taking a test run out of the archive, the log and context.md, and putting it back (F-018)."""
import json
from datetime import date
from pathlib import Path

import pytest

from dienstreis import advies, archive, cli, log


def _advice(traveller="Student", day=date(2026, 9, 25), line=""):
    d = archive.save({"traveller": traveller, "type": "casus"},
                     {"outbreak": "mpox_cod_2026", "stops": [{"place": "Kinshasa", "start": "2026-06-30"}]},
                     "Beste An, ...", advised_on=day, context_line=line)
    log.append({"advised_on": day.isoformat(), "traveller": traveller, "stops": "Kinshasa", "advice_dir": str(d)})
    return d


@pytest.fixture()
def context():
    advies.CONTEXT.write_text("# Context\n\n- 2026-09-10: Reiziger T, Kisangani afgeraden\n"
                              "- 2026-09-25: Student Kinshasa, mpox-casus, criteria voor terugkeer\n", encoding="utf-8")
    return advies.CONTEXT


def test_an_advice_goes_to_the_trash_with_its_log_row_and_context_line(context, capsys):
    d = _advice(line="2026-09-25: Student Kinshasa, mpox-casus, criteria voor terugkeer")
    keep = _advice("Reiziger T", date(2026, 9, 10))
    cli.main(["verwijder", Path(d).name, "--ja"])
    assert not Path(d).exists() and (archive.trash_dir() / Path(d).name / "advies.json").exists()
    assert [r["traveller"] for r in log.history("Kinshasa")] == ["Reiziger T"]
    assert "mpox-casus" not in context.read_text(encoding="utf-8") and "Kisangani afgeraden" in context.read_text(encoding="utf-8")
    assert Path(keep).exists() and [r["traveller"] for r in archive.all_advices()] == ["Reiziger T"]
    assert "--herstel" in capsys.readouterr().out


def test_it_comes_back_whole(context):
    d = _advice(line="2026-09-25: Student Kinshasa, mpox-casus, criteria voor terugkeer")
    before_log, before_ctx = log.LOG.read_text(encoding="utf-8"), context.read_text(encoding="utf-8")
    cli.main(["verwijder", str(d), "--ja"])
    cli.main(["verwijder", "--herstel", Path(d).name])
    assert (Path(d) / "advies.json").exists() and not (Path(d) / "verwijderd.json").exists()
    assert log.LOG.read_text(encoding="utf-8") == before_log
    assert sorted(context.read_text(encoding="utf-8").splitlines()) == sorted(before_ctx.splitlines())


def test_an_older_advice_asks_about_each_line_of_its_day(context, monkeypatch):
    """Before F-018 an advice did not keep its context line: the lines of its date are asked one by one."""
    d = _advice()                                                      # no context_line on the record
    answers = iter(["j", "j"])                                         # remove the advice, and that line
    monkeypatch.setattr("builtins.input", lambda *a: next(answers))
    cli.main(["verwijder", Path(d).name])
    assert "mpox-casus" not in context.read_text(encoding="utf-8")
    info = json.loads((archive.trash_dir() / Path(d).name / "verwijderd.json").read_text(encoding="utf-8"))
    assert info["context_lines"] == ["- 2026-09-25: Student Kinshasa, mpox-casus, criteria voor terugkeer"]


def test_under_ja_an_uncertain_line_stays(context):
    d = _advice()
    cli.main(["verwijder", Path(d).name, "--ja"])
    assert "mpox-casus" in context.read_text(encoding="utf-8")


def test_nothing_happens_without_a_yes(context, monkeypatch):
    d = _advice(line="2026-09-25: Student Kinshasa, mpox-casus, criteria voor terugkeer")
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    cli.main(["verwijder", Path(d).name])
    assert Path(d).exists() and "mpox-casus" in context.read_text(encoding="utf-8") and log.history("Student")


def test_three_runs_of_one_mail_can_go_at_once(context):
    runs = [_advice(line=f"2026-09-25: run {i}") for i in range(3)]
    archive.add_context_lines(context, ["- 2026-09-25: run 0", "- 2026-09-25: run 1", "- 2026-09-25: run 2"])
    cli.main(["verwijder", *[Path(x).name for x in runs], "--ja"])
    assert archive.all_advices() == [] and "run " not in context.read_text(encoding="utf-8")
    assert len(list(archive.trash_dir().iterdir())) == 3


def test_an_unknown_advice_is_refused():
    with pytest.raises(FileNotFoundError):
        cli.main(["verwijder", "2026-01-01_niemand", "--ja"])
