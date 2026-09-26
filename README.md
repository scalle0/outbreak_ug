# dienstreis-advies

Reproducible outbreak travel-risk analysis for UGent Team Actueel dienstreizen. One command on
your own PC turns a forwarded request mail into a checked Dutch reply, an itinerary map and an
epidemic curve. What belongs to one outbreak lives in its profile under `dienstreis/outbreaks/`
(see [Outbreak profiles](#outbreak-profiles)); the first, and so far only, profile is the Ebola
Bundibugyo (BVD) outbreak in the DRC, 2026. Everything
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

# a request that came in several mails: save them all (and any loose documents) in one folder
dienstreis advies "aanvraag Kisangani" --outlook
```

A folder is read as one request: every `.msg`, `.eml` and `.txt` in it, in the order they were sent
(the date in the mail, not the file name), each under its own header, so a correction an hour later
overrides the first mail and the difference shows up under `contradictions`. Loose `.docx`, `.pdf`
and `.xlsx` files count as attachments. The Outlook draft answers the last mail.

What happens:

| step | who | what |
|---|---|---|
| 1 | Python | read the .msg, or every mail in the request's folder in the order they were sent (attachments included) |
| 2 | LLM | itinerary from the mail -> `stops.yaml`; shown in the terminal, you confirm or edit it in Notepad |
| 3 | Python | per outbreak that applies (see [Which outbreaks apply](#which-outbreaks-apply)): its data, zone per stop, category A-F, map, epicurve, ECDC cross-check; then one facts file (`feiten.txt`) |
| 4 | LLM (`--no-web` to skip) | check FOD, CDC and WHO advisories, border measures of neighbouring countries and news not yet in the data; changes and new sources are offered for the local country registry |
| 5 | LLM | a short reply to An (the answer, one or two sentences per question of hers, at most three actions) and the dossier fields for you (assessment, what was left out of the mail, what to verify, commitments), using `context.md` and the earlier advices for the same destinations |
| 6 | Python | checks (em-dash, banned words, placeholders, every number traceable to step 3) with one repair round, the uzgent.be redirect line when the thread used the ugent.be address, the [internal dossier](#the-internal-dossier) in the browser, Outlook draft (never sent) with map and epicurve for a trip advice, log line, context line, archived advice, `llm_trace.json` |

### Which account pays

The default backend signs in as **you**, through the Claude Code you already have installed. No API
key, no `.env` file, nothing to configure: `claude auth status` shows `authMethod: claude.ai`, and
that is the account the advices run on. An `ANTHROPIC_API_KEY` in your environment does not change
that, but only because the code sees to it: with the key set, `claude` sends its calls with the key
and bills them to it, while `claude auth status` still shows your login (`apiKeySource:
ANTHROPIC_API_KEY`). So the default backend takes `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` out
of the environment of every call. The key is only used when you ask for `--llm api` explicitly.

When a call fails, the error names claude's own reason (a limit, a busy API, too many turns), not the
warning about claude.ai connectors that `claude` prints whenever a key is set. A busy or rate-limited
API gets one more try after 30 seconds.

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

The prompts live in `dienstreis/prompts/` (`stops.md`, `web.md`, `reply.md`, for a case `web_consult.md` and `consult.md`, and `fiche.md`): that is where the
judgement rules and mail conventions are written down. The passages about one disease (the category
table, its pitfalls, what the web step should look for) are in that outbreak's `prompt.md` and are
spliced in where a prompt says `{{uitbraak:<name>}}`. Change them there, not in code.

## What the model may and may not do

The model writes the itinerary and the letter; it never decides a category and never produces a
figure. Four checks hold that line, and each one names the problem instead of correcting it quietly:

| check | where | what happens when it fails |
|---|---|---|
| itinerary is usable: readable dates, known place or coordinates, stops in order, plausible years | `trip.py`, before any analysis | shown with the itinerary; `--yes` stops, otherwise you edit it in Notepad. A wrong itinerary would give a wrong risk table, not an error |
| every number in the reply appears in the calculated facts | `mail.unknown_numbers` | one repair round naming the number; if it survives, the dossier's copy button stays off and there is no Outlook draft |
| style: no em-dash, no banned intensifiers, no open placeholders | `mail.check_text` | same |
| the rule verdict (afraden / voorwaardelijk / geen bezwaar) still appears in the letter | `mail.verdict_note` | a note in `sugg.txt`. Only a warning: the model may argue against the rules, but you should see that it did |
| the reply is an answer, not a report (about 120 words, 200 at most, 50 more per further outbreak) | `mail.length_note` | one attempt to cut, then a note. Also only a warning: what falls out of the mail belongs in the dossier fields (`sugg.txt`), which is where the reasoning goes |
| every explicit question of An has an answer (`dossier.vragen` pairs each question with its sentence in the mail) | `mail.questions_note` | one repair round, then a note. Only a warning, and skipped when the model returns no dossier |

`out_*/llm_trace.json` keeps every prompt, answer and retry of the run, so a sentence in a sent
advice can be traced back to what the model was given. `--no-number-check` switches the number
check off for the rare reply where a legitimate figure trips it.

## Outbreak profiles

Everything that differs between outbreaks is in `dienstreis/outbreaks/<id>/`, not in the code:

| file | what |
|---|---|
| `outbreak.yaml` | where the figures come from (`adapter`), the countries they cover, the zone unit, the rule windows, the verdict per category and how it weighs in the trip verdict, flag texts and thresholds, the conditions for the traveller (in `feiten.txt`), ECDC and WHO sources, the texts on the map and the curve |
| `prompt.md` | the passages of the prompts that are about this disease, one `<!-- uitbraak:<name> -->` section each |
| `zone_overrides.csv` | observed zone spellings mapped to the shapefile (inrb adapter) |
| `fiche.md`, `documents.yaml` | the fixed fiche of the disease and its key documents, see [The fiche per disease](#the-fiche-per-disease) |

The windows, verdicts, conditions and flag texts are clinical judgements: the code applies them and
invents none. A profile is checked when it is read, and refused whole with every problem named
(`tests/test_outbreak.py`). `ebola_cod_2026/outbreak.yaml` documents every key.

Two adapters:

- `inrb`: a GitHub repository with INSP situation reports per health zone and the zone shapefile
  (the Ebola profile).
- `table`: a case table kept by hand in the profile folder (`cases.csv`), for an outbreak without a
  curated feed. One row per date and unit, cumulative, with the case definition and the source:

  ```csv
  date,admin1,admin2,cases_cum,deaths_cum,case_def,source_url
  2026-09-15,Tshopo,,4,1,bevestigd,https://...
  2026-09-15,NATIONAAL,,6,1,bevestigd,https://...
  ```

  `level` in the profile says whether the unit is the province (`admin1`) or the health zone
  (`admin2`); the outlines come from another profile (`boundaries: {from: ebola_cod_2026}`), merged
  into provinces once and cached. A row with `admin1: NATIONAAL` gives the national total; without
  one the units are summed. The web step gets the last figures and proposes newer official ones as
  `case_updates`; what you accept goes to `%USERPROFILE%\.config\dienstreis\outbreaks\<id>\cases.csv`,
  which wins as soon as it reaches the same date. A table older than `stale_days` is flagged at the
  top of the notes, because categories A and B rest on recent cases; an empty table gives an advice
  without figures for that outbreak, never one without objection.

`mpox_cod_2026` is mpox (clade I) in the DRC per health zone, on a table seeded from the WHO mpox
dashboard (data to 16 August 2026): suspected and confirmed cases since 2024, the date of the last
report per zone, and the national weekly series. It counts new cases over 42 days (WHO's six-week
window), writes "vermoede en bevestigde gevallen", makes a zone with a case in 21 days conditional
and nothing advised against, and counts as stale after 60 days. Being active, it is assessed next to
Ebola on every trip through the DRC or a neighbouring country. A profile can be kept in concept with
`active: false`: routing then skips it, a request naming its disease gets a note pointing to it, and
`--uitbraak <id>` uses it on purpose. `dienstreis uitbraken` lists the profiles with their state,
countries and neighbours.

## Case questions

Not every mail is a planned trip. The itinerary step says what a request is (`type` in `stops.yaml`,
shown on the itinerary screen, yours to correct):

| type | what | road |
|---|---|---|
| `reisadvies` | a trip that has not started | as above: rules, map, curve, verdict |
| `casus` | a traveller already abroad or just back, ill, exposed or in quarantine | the figures for the place as background, with map and curve in the dossier but none attached to the letter, no verdict; a web step that looks up official guidance first (isolation, return travel, what arrival in Belgium requires, contacts: ITG, Sciensano, Departement Zorg, Hoge Gezondheidsraad, WHO, ECDC); a letter written from the employer's side (the treating doctor decides, UGent advises, criteria rather than dates) |
| `vraag` | a general question | as a case; without a place it goes to the outbreaks its diseases name |

A trip whose go/no-go date already lies in the past is refused with the question whether it is a
case: that is how the mpox mail of 25/09 went wrong, filed as an Ebola trip with a go/no-go three
months back. The prompts are `prompts/web_consult.md` and `prompts/consult.md`; the itinerary step
adds `situation`, two or three sentences on the case as the mail describes it.

`dienstreis herlabel <advice folder> --type casus --uitbraak <id> --reden "..."` corrects what an
archived advice was filed as. The letter and the figures stay as they were; the record keeps the old
labels, the date and the reason, and the log row follows.

What a profile may set beyond the Ebola keys: `case_words` (how the letter names what the figures
count), `windows.recent` (days over which new cases are counted, default 14), `flags.rising_recent`,
and for a table `national_check: false` when zone and national figures come from different bases.

## The fiche per disease

What a clinician needs to know about the disease itself (agent, transmission, incubation, clinical
picture, severity, diagnosis, treatment, vaccination and PEP, prevention for travellers, isolation and
release, return to Belgium) is not looked up again for every mail. It is in a fixed fiche per
outbreak profile, written once from Belgian, European, WHO and US sources and confirmed by you:

| file | what |
|---|---|
| `outbreaks/<id>/fiche.md` | front matter (`status: concept` or `bevestigd`, `verified`, `bevestigd_door`, `bevestigd_op`), then one `##` section per topic. A statement cites its document as `[document-id]`, which the dossier links |
| `outbreaks/<id>/documents.yaml` | the key documents per level (`be`, `eu`, `who`, `us`): `id`, `org`, `title`, `date`, `url`, and `key`, the key message in one sentence |

```bash
dienstreis fiche mpox_cod_2026                        # status: sections, documents per level, references without a document
dienstreis fiche mpox_cod_2026 --opstellen --repo     # a concept drafted from sources (web search, a few minutes)
```

`--opstellen` writes a concept; without `--repo` it goes to the local folder
(`%USERPROFILE%\.config\dienstreis\outbreaks\<id>\`), with `--repo` into the profile's folder to
commit. A confirmed fiche is never overwritten: the draft then goes next to it as `fiche_concept.md`.
Read the concept, correct it where needed, and set `status: bevestigd`, `bevestigd_door` and
`bevestigd_op`. Until then the dossier shows it under a banner and the letter does not rest on it.

- **The letter** gets only a confirmed fiche (`fiche` in its inputs): answers about isolation,
  vaccination or release rest on text you have read, not on what the web step happened to find. Its
  numbers count as sources for the number check.
- **The web step** gets the documents and the fiche on every run. A newer version of a document, or
  a new key document, is proposed (`document_updates`) and kept after a yes in a local copy of
  `documents.yaml`, which wins while it is verified more recently, as for the country registry. A
  statement of the fiche that newer guidance contradicts is only shown (`fiche_flags`), in the
  terminal and in the dossier: the fiche is changed by you, never by the code.
- **A country's own documents** (a ministry's circular, a national guideline) go under `documents` in
  `countries/<ISO3>.yaml`, with the same fields (`org`, `title`, `date`, `url`, `key`); the dossier lists them per country.

## Which outbreaks apply

An outbreak applies to a trip when a stop lies in one of its countries or in a country that borders
one: borders with an outbreak country are closed or screened, so those countries are checked, and
their border measures come from the country registry. There is no distance radius. A stop's country
comes from `config/places.csv`, or for a stop given by lat/lon from the Natural Earth outlines.

The outcome is written into `stops.yaml` as `outbreaks: [ebola_cod_2026]` and shown on the itinerary
screen. After you edit the itinerary it is worked out again, unless you changed `outbreaks` yourself
or named them with `--uitbraak ID` (repeatable) on `advies` or `run`.

- **Several outbreaks**: each is assessed on its own figures, with its own map and curve (file names
  carry the outbreak id). The strictest leads the letter and the summary; the others follow in
  `feiten.txt` under "Voor <ziekte>:", listing only the stops where they matter, and reach the mail step
  as `andere_uitbraken`. `summary.json` keeps every outbreak under `outbreaks`. The length warning
  allows 50 words more per further outbreak, and a reply that does not name one of them gets a note.
- **None applies**: the advice is written at country level with the profile `geen`. There are no
  figures, map or curve; every stop carries its country's FOD and CDC advice and border measures, and
  the web step is told to look for an outbreak at the destination first, because "no profile" does
  not mean "no outbreak".
- **A disease the request names without a profile** (the itinerary step lists `diseases_mentioned`):
  it is flagged on the itinerary screen and at the top of the notes, and the web and mail steps are
  told to look for it and say that the figures do not cover it.

## Country source registry

What is the same about a country whatever the disease lives in `dienstreis/countries/<ISO3>.yaml`,
so a new outbreak in a known country, or a known outbreak reaching a new country, does not start
the search for sources again:

| key | what |
|---|---|
| `fod` | the FOD Buitenlandse Zaken pages, the advisory for the country and per province, with the reason (security or health) |
| `cdc` | the CDC Travel Health Notice level, per outbreak profile, for the country and per province |
| `pretravel` | what the pretravel condition of the letter names (yellow fever, malaria) |
| `government`, `news` | trusted national sources and the news outlets the web step may rely on |
| `neighbours` | land borders; a trip through a country bordering an outbreak country gets its border measures checked |
| `measures` | entry and exit measures tied to an outbreak (closed border, screening, quarantine), each with the date it was verified and its source |
| `verified` | when the advisories were last checked against the live pages; `null` means never |

`_international.yaml` lists the bodies that apply everywhere (WHO, WHO AFRO, ECDC, US CDC, Africa
CDC, ITG, Sciensano, Departement Zorg, Reuters, AP). The registry starts with the DRC and its nine
neighbours; for the neighbours only the name, the borders and the notes of the old advisories
table are filled in, and the web step looks up the rest.

The web step reads the registry, checks it against the live pages, and offers what differs: a
changed advisory, a border measure, a new FOD page or source. What you accept is written to
`%USERPROFILE%\.config\dienstreis\countries\<ISO3>.yaml`, which wins while it is verified more
recently than the file in the repo; accepting also records that the countries were checked today.
A country nobody has checked yet is named in the console and in `qa.advisories_unverified`. The
`advisories.yaml` of 0.2, if you still have one, is read while it is newer than the registry.

## Sources checked every run

| source | how | when |
|---|---|---|
| INSP situation reports per health zone (INRB-UMIE) | the figures the whole advice rests on | every run |
| ECDC epidemiological update | page parsed, compared with the INSP national total | every run |
| WHO Disease Outbreak News | read from the WHO JSON API: latest DRC Ebola item, its date and age | every run |
| FOD Buitenlandse Zaken, US CDC | read in the web step; they are prose pages, and "formally advised against for security reasons" means something different from "for health reasons" | every run, `--no-web` to skip |
| border measures of neighbouring countries | read in the web step for every country on the trip that borders an outbreak country: closed border, screening, quarantine or entry ban for travellers from the outbreak country | every run, `--no-web` to skip |

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

With several outbreaks, an override says which one it sets aside, and a stop can carry one per
outbreak:

```yaml
    override:
      - {outbreak: ebola_cod_2026, category: C, reason: ...}
      - {outbreak: mpox_cod_2026, category: F, reason: ...}
```

The verdict override for the whole trip stays one, over all outbreaks.

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
dienstreis zoek Kisangani            # on place, zone, province, country, outbreak, traveller or note
dienstreis zoek --uitbraak ebola_cod_2026   # only advices about that outbreak
dienstreis zoek --overruled --vol    # advices where a rule was set aside, with the full text
dienstreis zoek --sinds 2026-08-01 --oordeel afraden
```

Each hit shows its folder and, for an advice since F-015, a link to its dossier.

## The internal dossier

The letter to An is short: the answer, one or two sentences per question of hers, at most three
actions. Everything behind it is in `dossier.html`, one page per advice for you, never for An. It
opens in the browser at the end of `advies`, is copied into the archive, and prints to PDF.

| section | what |
|---|---|
| Antwoord aan An | the letter with a copy button, the word count against the limit, and the checks' notes. The button stays off while a blocking check fails (an invented number, an em-dash): correct `reply.txt` and run `dienstreis dossier <out folder>`, which checks the text again and rebuilds the page |
| Aanvraag | subject, sender, type, profile, An's questions each with the sentence that answers it (or "geen antwoord gekoppeld"), what is missing or contradicts, the itinerary, and the request as it came in |
| Oordeel | per outbreak the verdict by the rules and the final one, overrides with their reason, the verdict per stop, the go/no-go date |
| Epidemiologie | per outbreak the national total, deaths and CFR with source and date, the last eight full weeks, curve and map, the zones of the itinerary (cases, recent cases, days since the last one, active neighbouring zones, nearest active zone) and the checks on the figures |
| Risico | the traveller's profile, per stop the FOD and CDC level and the flags, per country when it was last verified, the provinces that differ, border measures and the FOD pages |
| Ziektefiche | the fiche per disease, under a banner while it is a concept, with the statements the web step flags as possibly outdated |
| Richtlijnen | the key documents per level (België, Europa, WHO, Verenigde Staten), what the web step proposes, the countries' own documents, the guidance it found for a case, and the sources of the advice |
| Beoordeling | the model's assessment: its reasoning, what it left out of the letter, what to verify, the commitments the letter makes, questions for the treating doctor |
| Web | WHO, advisories, border measures, news, proposed figures and sources, and whether you accepted them |
| Eerder | earlier advices for the same places or person (with a link to their dossier), log rows, the lines of `context.md` about them |
| Bronnen | data dates per outbreak, the profiles, the files of the run, and `feiten.txt` |

Everything on the page is rendered from the run's files; only the assessment comes from the model.
The figures are embedded, scaled down to 1600 pixels, so the archived page opens without the run's
folder; the full-size PNGs stay for Outlook. A case or a question gets its map and curve too, in the
dossier only. The layout follows the ScAIdev design system; the colours of the map and the curve are
data colours and stay as they are. The page contains the request and the case, like the archive
does: it stays on this machine.

## Privacy

This tool is no longer fully local. With the `claude-code` and `api` backends, the subject and body
of the request mail, the text of its attachments, `context.md` (which names colleagues and earlier
advices), the matching rows of the advice log, **the full text of earlier advices for the same
destinations** and the calculated figures are sent to Anthropic under your own subscription or API key. Nothing is sent by `data`, `run`, `check`, `dossier` or `due`, and
`--llm manual` keeps the machine offline: it writes the prompt to a file and waits for you to paste
an answer back. `--no-web` stops the model searching the open web. Decide deliberately what
goes into `context.md`; it is the richest personal data in the system and it goes out with every reply.

**Health data about a person.** A mail that looks like it carries health data about someone
(quarantaine, isolatie, ziek, besmet, symptomen, a positive test, ...) is shown as such before
anything is sent, and the program asks. `--yes` does not answer that question: confirming an
itinerary is not agreeing to send health data. `--gezondheidsgegevens-ok` does, for a run without a
keyboard; `--llm manual` sends nothing. When the words are missed but the model reads the mail as a
case, the question comes before the web and mail steps, and says the mail already went out once to
read the itinerary.

Local files (never in the repo): `%USERPROFILE%\.config\dienstreis\context.md`, `advice_log.csv`,
`countries\<ISO3>.yaml` for what you accepted from the web step (used when verified more recently than the
registry in the repo), `outbreaks\<id>\` for accepted case figures and documents and a local fiche, and the
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
dienstreis run stops.yaml --out out_name --log     # 3. risk table, map, epicurve, facts, QA
# 4. write the short reply to An from out_name/feiten.txt -> reply.txt
dienstreis dossier out_name                        # 5. rebuild the dossier after editing reply.txt
dienstreis due                                     # reviews that are due (go/no-go dates)
dienstreis data --zone Watsa                       # quick look at current figures
```

`stops.yaml`:

```yaml
traveller: Reiziger D
profile: {lodging: family, healthcare_work: false}
sent_to_ugent_address: false        # from `dienstreis msg`: adds the uzgent.be redirect line
review_on: 2026-11-01               # logged with --log, listed by `dienstreis due`
outbreaks: [ebola_cod_2026]         # optional: set by routing in `advies`; left out, `run` routes itself
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
| `kaart_*.png` | health-zone choropleth, hatching for new cases (14 d), stop zones outlined, route, locator inset for far stops, label-overlap checked; one per outbreak with figures, the id in the name when there are several |
| `epicurve_*.png` | cumulative cases/deaths and weekly incidence from the national series; one per outbreak with figures |
| `feiten.txt` | the calculated facts the letter is written from: the rule verdict, a paragraph per stop, the state of the outbreak, the conditions for the traveller. Every number in the reply must appear here or in `summary.json`. Not a letter frame (until F-015 it was one: `reply_skeleton.txt`) |
| `sources.txt` | URLs to paste into the mail |
| `summary.json` | everything above as data, plus QA |
| `stops.yaml` | the itinerary the model read from the mail, after your confirmation |
| `reply.txt` | the letter to An |
| `dossier.html` | the internal dossier, see [The internal dossier](#the-internal-dossier); a copy goes into the archive |
| `dossier.json` | what the dossier needs that no other file keeps: the request, the model's assessment, the checks |
| `sugg.txt` | notes for you, not part of the mail: the model's assessment, what it left out of the mail, what to verify, commitments made, questions for the treating doctor; failed checks on top |
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
The cached outlines carry the outbreak id in their name (since 0.3), so the first run after updating
to 0.3 rebuilds them once, and two outbreaks never clean up each other's.

**Only what is drawn is simplified.** Which health zone a place falls in, which zones border it and
how far the nearest active zone is are all decided on the exact boundaries. `display_geometry` works
on a copy and never touches `ob.zones`, and `test_display_geometry.py` pins that, including a point
sitting right on a zone border.

## Where everything lives

Four places, and only one of them is irreplaceable.

| | where | what | if you lose it |
|---|---|---|---|
| **Your state** | `%USERPROFILE%\.config\dienstreis\` | `context.md` (standing notes), `advice_log.csv` (one line per advice), `adviezen/<date>_<traveller>/` (each advice whole: `advies.json`, `reply.txt`, `summary.json`, `dossier.html`), `countries/<ISO3>.yaml` for the web-step findings you accepted, and `outbreaks/<id>/` for accepted figures and documents, a local fiche and the trace of its draft | gone for good. Back this up |
| **Source data** | `%USERPROFILE%\.cache\dienstreis\` | the INRB clone (INSP figures, zone shapefile), Natural Earth borders, the cached map outlines, `http_cache.json` | re-downloaded on the next run |
| **Per-run output** | `out_<traveller>/` where you ran the command | the reply, the dossier, map, epicurve, risk table, `stops.yaml`, `summary.json`, `llm_trace.json`, `web.json` | regenerate by running it again, though the wording will differ |
| **Maintained by hand** | `dienstreis/config/`, `dienstreis/prompts/`, `dienstreis/outbreaks/`, `dienstreis/countries/` in this repo | places, the three prompts, per outbreak its profile, prompt passages and zone spellings, and per country its sources, advisories and border measures | it is in git |

The advice folders are the thing worth protecting: they are what later advices are checked against,
and the only record of what was actually sent. `out_*/` is scratch, and is gitignored.

Both `.config` and `.cache` can be moved with `DIENSTREIS_CONTEXT`, `DIENSTREIS_LOG`,
`DIENSTREIS_ARCHIVE`, `DIENSTREIS_ADVISORIES` and `DIENSTREIS_CACHE`.

## Risk categories (health-zone level)

The windows and verdicts below are those of the Ebola profile; another outbreak sets its own in
its `outbreak.yaml`. For the trip as a whole the strictest stop wins.

| cat | rule | default verdict |
|---|---|---|
| A | zone has a new case in the last 21 days | afraden |
| B | zone affected, last case 22-42 days ago | voorwaardelijk, go/no-go close to departure |
| C | zone affected, > 42 days without a case | voorwaardelijk: drop the leg, or re-evaluate before departure |
| D | zone free, borders a zone with a case in 21 days | voorwaardelijk, re-evaluate closer to departure |
| E | zone free, province has active zones | voorwaardelijk |
| F | not affected | geen bezwaar |
| X | outside the area of the outbreak's figures | the country's border measures for this outbreak, from the registry |

Flags never change the category; they list what must be weighed (FOD formal advisory and its
reason, CDC level, family stay, healthcare work, overnight stays, long stays, rising zone).

## QA built in

- zone sum must equal the national INSP total for the same date (INSP downward revisions are
  kept in levels; new-case detection uses the running maximum)
- ECDC headline parsed and compared (ok / mismatch / page changed)
- unmatched zone spellings reported (add them to `outbreaks/<id>/zone_overrides.csv`)
- advisories older than 14 days, or never checked, flagged per country (`countries/<ISO3>.yaml`, `verified:`)
- map label overlaps and labels clipped by the frame, inset or legend counted (inset and legend go to corners without stops); em-dash, banned intensifiers and open placeholders keep the dossier's copy button off

## Known limits

- Zone-level deaths sum below the national total: INSP books some treatment-centre deaths as
  "à ventiler" (not yet assigned to a zone). Use national deaths for totals.
- Place coordinates are approximate; `config/places.csv` grows as places come up.
- Advisories and border measures are a maintained registry, not scraped: the web step checks the
  live pages each run, and you read what it found before accepting it.
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
| `test_reply_checks.py` | style, invented numbers, the ways Dutch writes "afraden", the length limits and An's questions |
| `test_overrule.py` | a rule may be set aside, never silently: reason required, rule verdict preserved |
| `test_archive.py` | advices saved, searchable, and handed back to the next advice |
| `test_cache.py` | what is fetched and when, with git and requests replaced |
| `test_sources.py` | WHO and ECDC, including every way they can fail |
| `test_display_geometry.py` | the map's simplified outlines never reach the zone lookup |
| `test_table_adapter.py` | the hand-kept table: the same fields as any adapter, national totals, unknown names, the local copy, rows accepted from the web step, an old table and an empty one |
| `test_mpox.py` | the mpox profile on its seeded WHO table: the one unmatched zone, the counts, the example trips, and a letter that says "vermoede en bevestigde gevallen" |
| `test_casus.py` | case questions: a go/no-go in the past asks whether it is a case, nothing leaves without consent (not even under `--yes`), the case road without figures, a question routed by disease, relabelling an archived advice |
| `test_route.py` | which outbreaks apply: outbreak country, neighbouring country, none; a stop's country from the map, including the France and South Sudan code traps; overrides that must name their outbreak |
| `test_multi.py` | a synthetic second outbreak: strictest first, a map and curve each, the facts covering both, overrides per outbreak; country-level advice end to end; the log and archive of before 0.3 |
| `test_request_folder.py` | a folder of mails read as one request: order by send date, loose documents, the thread reaching the itinerary step |
| `test_request_parsing.py` | reading the request mail, against an invented fixture |
| `test_regression.py` | reproduces the manual advices of August and September 2026 on frozen data dates (one trip on 22 Aug, three on 19 Sep), including the published figures of the original report (5 514 cases, 57 zones, Tshopo 15 cases of which 13 in Kisangani) |
| `test_countries.py` | the country registry: valid files, neighbours that agree, local copies and the 0.2 table only when newer, web findings merged and written only after a yes, border measures on a stop in a neighbouring country |
| `test_golden.py` | the deterministic output of the four example trips and the prompts of the three model steps, byte for byte, as they were before Ebola became a profile (frozen data dates and advisories); regenerate only on purpose with `DIENSTREIS_GOLDEN_WRITE=1` |
| `test_outbreak.py` | profiles are checked when read and refused whole; prompt passages land where the template asks |
| `test_llm_backend.py` | the claude-code backend with `claude` replaced: no API key reaches the call, a failure names claude's reason and not the connectors warning, an error with exit code 0 is still an error, a busy API gets one more try |
| `test_fiche.py` | the fiche and its documents: front matter and sections, the local copy only when newer, proposals kept only after a yes and with the ids the fiche cites, a flag never applied, a draft always a concept and never over a confirmed fiche, the command with a fake model, the fiche in the dossier with its banner, links and escaping |
| `test_dossier.py` | the dossier from a synthetic run folder: every section, the letter to copy (off while a check fails, on again after a corrected hand edit), figures embedded and scaled, questions with their answers, a case without a verdict, several outbreaks, escaping, links limited to http and file |
| `test_skeleton.py` | the facts file writes zone names with their own capitals and ECDC dates with Dutch months, and is no letter frame; the redirect line is added by the code |

The pipeline, regression and golden tests each do a full analysis against the cached data, so a complete
run takes minutes. `pytest -q --ignore=tests/test_advies_pipeline.py --ignore=tests/test_regression.py --ignore=tests/test_golden.py`
runs the rest in a couple of seconds while you work.
