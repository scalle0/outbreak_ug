# dienstreis-advies

Reproducible outbreak travel-risk analysis for UGent Team Actueel dienstreizen, built on the
Ebola Bundibugyo (BVD) outbreak in the DRC, 2026. One command on your own PC turns a forwarded
request mail into a checked Dutch reply, an itinerary map and an epidemic curve. Everything
deterministic runs in Python; a language model is used only for the three steps that need
judgement (reading the itinerary, optional web check, writing the reply).

## Quick start on Windows (one command per advice)

```powershell
# once
git clone https://github.com/scalle0/outbreak_ug.git
cd outbreak_ug
py -m pip install -e ".[windows]"        # add ",api" for the Anthropic API backend
dienstreis context                        # opens context.md: earlier advices, open commitments

# per request: save the forwarded mail from Outlook as .msg, then
dienstreis advies "FW_ RRF Vertrek ....msg" --outlook
```

What happens:

| step | who | what |
|---|---|---|
| 1 | Python | read the .msg (attachments included) |
| 2 | LLM | itinerary from the mail -> `stops.yaml`; shown in the terminal, you confirm or edit it in Notepad |
| 3 | Python | INRB/INSP data, health zone per stop, category A-F, map, epicurve, ECDC cross-check, reply skeleton |
| 4 | LLM (`--no-web` to skip) | check FOD, CDC and WHO advisories and news not yet in the data; changes are offered for a local `advisories.yaml` |
| 5 | LLM | reply to An and notes for you, using `context.md` and the earlier advices for the same destinations |
| 6 | Python | checks (em-dash, banned words, placeholders, every number traceable to step 3) with one repair round, widget in the browser, Outlook draft with map and epicurve (never sent), log line, context line, archived advice, `llm_trace.json` |

### Which account pays

The default backend signs in as **you**, through the Claude Code you already have installed. No API
key, no `.env` file, nothing to configure: `claude auth status` shows `authMethod: claude.ai`, and
that is the account the advices run on. An `ANTHROPIC_API_KEY` in your environment does not change
that; it is only used when you ask for `--llm api` explicitly.

Do not put an API key in a `.env` file inside this repository: the project lives in a synced folder,
so the key would be uploaded with everything else. If you ever need one, set it as a Windows user
variable (`setx ANTHROPIC_API_KEY ...`), which is stored per user and outside the synced tree.

LLM backends (`--llm`, or the environment variable `DIENSTREIS_LLM`):

- `claude-code` (default): runs `claude -p` from your Claude Code install, on your own subscription.
  Text steps run with all tools disabled; the web step only gets WebSearch and WebFetch. The call
  runs in an empty temporary folder with settings, MCP servers, skills and CLAUDE.md discovery
  switched off, so nothing but the prompt reaches the model and the advice does not depend on the
  folder you ran the command from.
  If `claude` is not on PATH: `setx DIENSTREIS_CLAUDE C:\Users\<you>\.local\bin\claude.exe`
- `api`: Anthropic API, needs `ANTHROPIC_API_KEY` and `pip install anthropic`; `--model` to choose.
- `manual`: no model access from the script; it writes `prompt_<step>.md`, you paste it in any Claude
  chat and save the JSON answer as `antwoord_<step>.json`.

The prompts live in `dienstreis/prompts/` (`stops.md`, `web.md`, `reply.md`): that is where the
clinical judgement rules, pitfalls and mail conventions are written down. Change them there, not in code.

## What the model may and may not do

The model writes the itinerary and the letter; it never decides a category and never produces a
figure. Four checks hold that line, and each one names the problem instead of correcting it quietly:

| check | where | what happens when it fails |
|---|---|---|
| itinerary is usable: readable dates, known place or coordinates, stops in order, plausible years | `trip.py`, before any analysis | shown with the itinerary; `--yes` stops, otherwise you edit it in Notepad. A wrong itinerary would give a wrong risk table, not an error |
| every number in the reply appears in the calculated facts | `mail.unknown_numbers` | one repair round naming the number; if it survives, no widget and no Outlook draft |
| style: no em-dash, no banned intensifiers, no open placeholders | `mail.check_text` | same |
| the rule verdict (afraden / voorwaardelijk / geen bezwaar) still appears in the letter | `mail.verdict_note` | a note in `sugg.txt`. Only a warning: the model may argue against the rules, but you should see that it did |

`out_*/llm_trace.json` keeps every prompt, answer and retry of the run, so a sentence in a sent
advice can be traced back to what the model was given. `--no-number-check` switches the number
check off for the rare reply where a legitimate figure trips it.

## Sources checked every run

| source | how | when |
|---|---|---|
| INSP situation reports per health zone (INRB-UMIE) | the figures the whole advice rests on | every run |
| ECDC epidemiological update | page parsed, compared with the INSP national total | every run |
| WHO Disease Outbreak News | read from the WHO JSON API: latest DRC Ebola item, its date and age | every run |
| FOD Buitenlandse Zaken, US CDC | read in the web step; they are prose pages, and "formally advised against for security reasons" means something different from "for health reasons" | every run, `--no-web` to skip |

A source that cannot be reached never stops an advice: it fails soft and shows up in the QA block
under `sources_unreachable`, and in the notes. A run with `--asof` skips the live sources
altogether, because today's pages do not belong with last month's figures.

## Overruling a rule

The categories classify a health zone. They do not know the dossier, so you can set one aside, per
stop or for the whole trip, as long as you say why:

```yaml
stops:
  - place: Kisangani
    from: 2026-12-06
    to: 2026-12-13
    override: {category: C, reason: verblijf in een gesloten compound, geen contact met de gemeenschap}
override: {verdict: goedkeuren mits compound, reason: ...}   # optional, for the whole trip
```

A reason is required. What the rules said is kept next to what you decided: the risk table gains a
`regel_cat` column, `summary.json` keeps `rule_overall` and `overrides`, the log line and the
archived advice record it, and the step that writes the mail is told a rule was set aside and why,
so the letter argues the point instead of quietly reporting a different category. An override may be
stricter as well as milder. It applies to that one advice and is not carried into the next run:
an old judgement should not be laid silently over new figures.

## Earlier advices

Every advice is kept whole under `%USERPROFILE%\.config\dienstreis\adviezen\<date>_<traveller>\`:
the mail as written, the figures behind it, and the overrides. When a new request touches a place,
zone or province you have advised on before, those advices go to the step that writes the mail in
full, so a contradiction with what you said last time is visible while the letter is being written
rather than after it is sent.

```bash
dienstreis zoek Kisangani            # on place, zone, province, traveller or note
dienstreis zoek --overruled --vol    # advices where a rule was set aside, with the full text
dienstreis zoek --sinds 2026-08-01 --oordeel afraden
```

## Privacy

This tool is no longer fully local. With the `claude-code` and `api` backends, the subject and body
of the request mail, the text of its attachments, `context.md` (which names colleagues and earlier
advices), the matching rows of the advice log, **the full text of earlier advices for the same
destinations** and the calculated figures are sent to Anthropic under your own subscription or API key. Nothing is sent by `data`, `run`, `check`, `widget` or `due`, and
`--llm manual` keeps the machine offline: it writes the prompt to a file and waits for you to paste
an answer back. `--no-web` stops the model searching the open web. Decide deliberately what
goes into `context.md`; it is the richest personal data in the system and it goes out with every reply.

Local files (never in the repo): `%USERPROFILE%\.config\dienstreis\context.md`, `advice_log.csv`,
optional `advisories.yaml` (used when verified more recently than the packaged table), and the
`out_<traveller>/` folders. Data cache: `%USERPROFILE%\.cache\dienstreis` (`dienstreis data` shows
its size, `dienstreis data --reset-cache` empties it).

Useful options: `--yes` (no confirmation of a clean itinerary; still stops on an unusable one),
`--web`, `--apply-web` (take over advisory changes found online without asking), `--no-open`,
`--no-number-check`, `--out DIR`, `--asof YYYY-MM-DD` (freeze the data date), `--refresh` (ignore
the 6-hour cache).

## Install (other platforms, or inside a Claude session)

```bash
git clone https://github.com/scalle0/outbreak_ug.git && pip install -e outbreak_ug
```

With uv, keeping the environment out of a synced folder:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\venvs\outbreak_ug"
uv sync --extra test ; uv run pytest -q
```

Data are fetched on first use into `~/.cache/dienstreis` (override with `DIENSTREIS_CACHE`):
INRB-UMIE GitHub repository (INSP situation reports per health zone + health-zone shapefile),
Natural Earth country borders, and the ECDC landing page for a cross-check.

Only what is stale is fetched, because the two halves age very differently:

| | refreshed | why |
|---|---|---|
| INSP figures per zone, aliases | every 6 hours | new situation report most days |
| health-zone shapefile (66 MB) | every 30 days | zone boundaries almost never move |
| province outlines and simplified zone outlines for the map | when the shapefile changes | see below |
| Natural Earth country borders (3 MB) | once | national borders do not move |

With git, the clone is sparse (`--filter=blob:none --sparse`, checkout limited to the ten files the
analysis reads): 113 MB instead of the 330 MB a plain `--depth 1` clone of that repository costs.
Without git the files are downloaded directly, with the ETag of the previous copy, so an unchanged
shapefile comes back as `304 Not Modified` with no body. `--refresh` ignores both clocks.

If you already have a full clone in the cache from an earlier version, `dienstreis data --reset-cache`
drops it; the next run makes the lean one.

## Step by step (what `advies` does, for manual use)

```bash
dienstreis msg request.msg > request.json        # 1. read the forwarded Outlook message
# 2. write stops.yaml from the request (see examples/)
dienstreis run stops.yaml --out out_name --log     # 3. risk table, map, epicurve, skeleton, QA
# 4. complete the [[CLAUDE: ...]] paragraphs in out_name/reply_skeleton.txt -> reply.txt
dienstreis widget reply.txt --suggestions sugg.txt --out reply.html   # 5. refuses if checks fail
dienstreis due                                     # reviews that are due (go/no-go dates)
dienstreis data --zone Watsa                       # quick look at current figures
```

`stops.yaml`:

```yaml
traveller: Reiziger D
profile: {lodging: family, healthcare_work: false}
sent_to_ugent_address: false        # from `dienstreis msg`: adds the uzgent.be redirect line
review_on: 2026-11-01               # logged with --log, listed by `dienstreis due`
stops:
  - {place: Kinshasa,  from: 2026-11-28, to: 2026-12-06}
  - {place: Kisangani, from: 2026-12-06, to: 2026-12-14}
  - {place: Durba,     from: 2026-12-22, to: 2027-03-01, lodging: family}
  - {place: Somewhere, lat: 1.23, lon: 25.6, from: ..., to: ..., transit_only: true}
```

## Outputs (`out_name/`)

| file | content |
|---|---|
| `risk.csv`, `risk.md` | per stop: health zone, category A-F/X, rule verdict, cases, new in 14 d, days since last case, active neighbours, nearest active zone, FOD and CDC level, flags |
| `kaart_*.png` | health-zone choropleth, hatching for new cases (14 d), stop zones outlined, route, locator inset for far stops, label-overlap checked |
| `epicurve_*.png` | cumulative cases/deaths and weekly incidence from the national INSP series |
| `reply_skeleton.txt` | Dutch reply with fact-based paragraph per stop and `[[CLAUDE: ...]]` placeholders |
| `sources.txt` | URLs to paste into the mail |
| `summary.json` | everything above as data, plus QA |
| `stops.yaml` | the itinerary the model read from the mail, after your confirmation |
| `reply.txt`, `reply_*.html` | the reply, and the copy widget (only written when every check passed) |
| `sugg.txt` | notes for you, not part of the mail: commitments made, deviations, what to verify |
| `llm_trace.json` | every prompt, answer and retry of this run |
| `web.json` | what the web step found (FOD, CDC, WHO, news) |

## Why the map is fast

Drawing used to take about 105 of the 115 seconds an advice needed. Fifty of those went into
merging the health zones into 26 province outlines, and another twenty-five into drawing a few
thousand full-resolution polygons at 300 dpi, on every single run, for a shapefile that changes at
most once a month. Both are now computed once and cached (`data.display_geometry`), and the outlines
are simplified to about 250 m: the map is 12.5 inch at 300 dpi for a country 2 000 km wide, roughly
500 m per pixel, so finer detail cannot appear on the page. A map now takes about 20 seconds, an
advice about 30; the first run after a new shapefile pays the one-off cost of rebuilding the outlines.

**Only what is drawn is simplified.** Which health zone a place falls in, which zones border it and
how far the nearest active zone is are all decided on the exact boundaries. `display_geometry` works
on a copy and never touches `ob.zones`, and `test_display_geometry.py` pins that, including a point
sitting right on a zone border.

## Risk categories (health-zone level)

| cat | rule | default verdict |
|---|---|---|
| A | zone has a new case in the last 21 days | afraden |
| B | zone affected, last case 22-42 days ago | voorwaardelijk, go/no-go close to departure |
| C | zone affected, > 42 days without a case | voorwaardelijk, light conditions |
| D | zone free, borders a zone with a case in 21 days | voorwaardelijk, re-evaluate closer to departure |
| E | zone free, province has active zones | voorwaardelijk |
| F | not affected | geen bezwaar |
| X | outside the DRC | country note from `config/advisories.yaml` |

Flags never change the category; they list what must be weighed (FOD formal advisory and its
reason, CDC level, family stay, healthcare work, overnight stays, long stays, rising zone).

## QA built in

- zone sum must equal the national INSP total for the same date (INSP downward revisions are
  kept in levels; new-case detection uses the running maximum)
- ECDC headline parsed and compared (ok / mismatch / page changed)
- unmatched zone spellings reported (add them to `config/zone_overrides.csv`)
- advisories older than 14 days flagged (`config/advisories.yaml`, `verified:`)
- map label overlaps and labels clipped by the frame, inset or legend counted (inset and legend go to corners without stops); em-dash, banned intensifiers and open placeholders block the widget

## Known limits

- Zone-level deaths sum below the national total: INSP books some treatment-centre deaths as
  "à ventiler" (not yet assigned to a zone). Use national deaths for totals.
- Place coordinates are approximate; `config/places.csv` grows as places come up.
- Advisories are a maintained table, not scraped: verify the live FOD and CDC pages each time,
  or use `--web` and read what it found before accepting it.
- The checks catch invented figures, not a wrong judgement written in correct figures. You read and
  sign every advice; the checks narrow what can go wrong, they do not replace the reading.
- Two runs of the same request give two different letters. The figures are fixed, the wording is not.
- The internal DRC 21-day exit rule (Dutch advisory) is unverified and deliberately not encoded.

## Tests

`pytest -q` needs no model and, apart from the pipeline and regression tests, no network:

| file | what it pins |
|---|---|
| `test_advies_pipeline.py` | the whole `advies` run with a fake LLM: the repair round, the prompt inputs, overruling and archiving end to end, the web step on and off |
| `test_trip.py` | the itinerary checks: Belgian and ISO dates, unknown places, stop order, wrong years |
| `test_reply_checks.py` | style, invented numbers, and the ways Dutch writes "afraden" |
| `test_overrule.py` | a rule may be set aside, never silently: reason required, rule verdict preserved |
| `test_archive.py` | advices saved, searchable, and handed back to the next advice |
| `test_cache.py` | what is fetched and when, with git and requests replaced |
| `test_sources.py` | WHO and ECDC, including every way they can fail |
| `test_display_geometry.py` | the map's simplified outlines never reach the zone lookup |
| `test_request_parsing.py` | reading the request mail, against an invented fixture |
| `test_regression.py` | reproduces the manual advices of August and September 2026 on frozen data dates (one trip on 22 Aug, three on 19 Sep), including the published figures of the original report (5 514 cases, 57 zones, Tshopo 15 cases of which 13 in Kisangani) |

The pipeline and regression tests each do a full analysis against the cached data, so a complete
run takes minutes. `pytest -q --ignore=tests/test_advies_pipeline.py --ignore=tests/test_regression.py`
runs the rest in a couple of seconds while you work.
