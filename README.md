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
| 4 | LLM, optional (`--web`) | check FOD/CDC advisories and news not yet in the data; changes are offered for a local `advisories.yaml` |
| 5 | LLM | reply to An and notes for you, using `context.md` and the advice log for consistency |
| 6 | Python | text checks (em-dash, banned words, placeholders) with one repair round, widget in the browser, Outlook draft with map and epicurve (never sent), log line, context line |

LLM backends (`--llm`, or the environment variable `DIENSTREIS_LLM`):

- `claude-code` (default): runs `claude -p` from your Claude Code install, on your own subscription.
  Text steps run with all tools disabled; the web step only gets WebSearch and WebFetch.
  If `claude` is not on PATH: `setx DIENSTREIS_CLAUDE C:\Users\<you>\.local\bin\claude.exe`
- `api`: Anthropic API, needs `ANTHROPIC_API_KEY` and `pip install anthropic`; `--model` to choose.
- `manual`: no model access from the script; it writes `prompt_<step>.md`, you paste it in any Claude
  chat and save the JSON answer as `antwoord_<step>.json`.

The prompts live in `dienstreis/prompts/` (`stops.md`, `web.md`, `reply.md`): that is where the
clinical judgement rules, pitfalls and mail conventions are written down. Change them there, not in code.
The model never produces numbers: every figure in the reply comes from step 3.

Local files (never in the repo): `%USERPROFILE%\.config\dienstreis\context.md`, `advice_log.csv`,
optional `advisories.yaml` (used when verified more recently than the packaged table), and the
`out_<traveller>/` folders. Data cache: `%USERPROFILE%\.cache\dienstreis`. Git is used when present;
without git the needed INRB files are downloaded directly.

Useful options: `--yes` (no confirmation), `--web`, `--no-open`, `--out DIR`, `--asof YYYY-MM-DD`
(freeze the data date), `--refresh` (ignore the 6-hour cache).

## Install (other platforms, or inside a Claude session)

```bash
git clone https://github.com/scalle0/outbreak_ug.git && pip install -e outbreak_ug
```

Data are fetched on first use into `~/.cache/dienstreis` (override with `DIENSTREIS_CACHE`):
INRB-UMIE GitHub repository (INSP situation reports per health zone + health-zone shapefile),
Natural Earth country borders, and the ECDC landing page for a cross-check. Cached 6 hours.

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
- Advisories are a maintained table, not scraped: verify the live FOD and CDC pages each time.
- The internal DRC 21-day exit rule (Dutch advisory) is unverified and deliberately not encoded.

## Tests

`pytest -q` runs the whole `advies` pipeline with a fake LLM (no model calls; checks the repair round,
the prompt inputs and the outputs; never touches your log or context), and reproduces the manual
advices of August and September 2026 with frozen data dates
(one trip on 22 Aug data, three on 19 Sep data), including the published figures
of the original report (5 514 cases, 57 zones, Tshopo 15 cases of which 13 in Kisangani).
