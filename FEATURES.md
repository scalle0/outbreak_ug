# Feature log

Requests for this repo, newest first. Status: gevraagd · bezig · klaar · geweigerd · uitgesteld.

| ID | Feature | Status | Gevraagd |
|---|---|---|---|
| F-003 | Hardening van `advies`: promptisolatie, reisschemavalidatie, cijfercontrole | klaar | 2026-09-22 |
| F-002 | Alles lokaal in één commando: `dienstreis advies`, LLM enkel voor oordeel | klaar | 2026-09-22 |
| F-001 | dienstreis-advies 0.1.0: uitbraakrisico voor UGent-dienstreizen | klaar | 2026-09-22 |

## F-003 · Hardening van `advies`: promptisolatie, reisschemavalidatie, cijfercontrole
- **Gevraagd:** 2026-09-22 — "I would want to revert the repo: launch locally on a machine, and only use LLM to parse the data from mail and write the advice (but all the rest from the local machine)", daarna: "I have put your work in de folder outbreak_ug_2: read and adjust plan"
- **Status:** klaar (2026-09-22)
- **Gebouwd:**
  - `llm.py`: de aanroep van `claude -p` draait in een lege tijdelijke map met `--strict-mcp-config --disable-slash-commands --setting-sources "" --permission-prompts none --no-session-persistence`. Zonder dat zaten de CLAUDE.md-instructies van de map waarin het commando draaide mee in de prompt die het medisch advies schrijft (gemeten: JA tegenover NEE op dezelfde vraag). `ask_json` houdt nu elke prompt, elk antwoord en elke herkansing bij; `advies` schrijft ze naar `out_*/llm_trace.json`.
  - `trip.py` (nieuw): `coerce` en `validate` tussen het model en de berekening. Leest ISO en Belgische datums (`28/11/2026`, `3/1/27`), controleert volgorde, jaartallen, transit, verblijfsvorm, en of elke plaats in `places.csv` staat of lat/lon heeft. Twee crashes werden leesbare meldingen: `date.fromisoformat` op een niet-ISO datum, en `geo.locate` op een onbekende plaats midden in de analyse. Ook `dienstreis run` loopt er nu door.
  - `mail.py`: `unknown_numbers` vergelijkt elk getal in de mail met de berekende gegevens, `verdict_note` kijkt of het regeloordeel nog in de brief staat. Beide voeden de bestaande herstelronde; de widget en het Outlook-concept worden niet meer gebouwd rond een tekst die de controles niet haalt.
  - `--apply-web` losgekoppeld van `--yes`: een reisadvies overschrijven is een oordeel, geen bevestiging van iets dat al getoond werd.
  - `pipeline.py` (nieuw): `analyse`, `log_row` en `_slug` uit `cli.py`, zodat `advies` de berekening kan draaien zonder de argumentparser te importeren.
  - Tests: 10 → 54. `test_trip.py` en `test_reply_checks.py` draaien zonder netwerk of model; `test_advies_pipeline.py` kreeg vier gevallen erbij (verzonnen getal, widget geweigerd, onbruikbaar reisschema, Belgische datums uit het model).
- **Beslissingen:**
  - De opzet van F-002 blijft. Deze ronde herstelt drie gaten die bij nazicht bleken, geen herschrijving.
  - `--tools ""` blijft, niet `--allowedTools ""`: die laatste stuurt alle tooldefinities mee, 32 868 tokens tegenover 1 587 voor dezelfde prompt (gemeten, `claude` 2.1.270).
  - De hele mail blijft herschreven worden door het model (niet enkel de `[[CLAUDE]]`-plaatshouders invullen): dat geeft beter Nederlands. De cijfers worden achteraf gecontroleerd in plaats van buiten bereik van het model gehouden.
  - `extract_json` blijft, geen `--json-schema`: die vlag bestaat enkel in de claude-code-backend en zou `api`, `manual` en `fake` uit elkaar doen lopen.
  - Nooit `--bare`: die vlag dwingt authenticatie via `ANTHROPIC_API_KEY` af en leest OAuth niet, precies wat hier niet mag.

## F-002 · Alles lokaal in één commando: `dienstreis advies`, LLM enkel voor oordeel
- **Gevraagd:** 2026-09-22
- **Status:** klaar (2026-09-22)
- **Gebouwd:** `dienstreis advies aanvraag.msg` draait de hele keten op de eigen pc: aanvraag lezen (`msg.parse_request`, .msg/.eml/.txt) → reisschema uit de mail door het model, door de gebruiker bevestigd (`advies.confirm_trip`) → deterministische analyse (`cli.analyse`: data, zones, kaart, curve, QA) → optioneel reisadviezen en nieuws op het web (`--web`) → antwoordmail door het model → tekstcontrole met één herstelronde → widget, log, contextregel, optioneel Outlook-concept. `llm.py` is de enige plaats waar een model aangesproken wordt, met vier backends (`claude-code`, `api`, `manual`, `fake`). De oordeelsregels, valkuilen en mailconventies staan in `prompts/{stops,web,reply}.md`. `~/.config/dienstreis/context.md` houdt eerdere adviezen en toezeggingen bij (`dienstreis context`).
- **Commits:** fd55b06
- **Bron:** gereconstrueerd uit git-geschiedenis

## F-001 · dienstreis-advies 0.1.0: uitbraakrisico voor UGent-dienstreizen
- **Gevraagd:** 2026-09-22
- **Status:** klaar (2026-09-22)
- **Gebouwd:** Python-CLI `dienstreis` die een reisschema (`stops.yaml`) omzet in een risicotabel per gezondheidszone (categorieën A-F/X), een kaart van het reisschema, een epidemiecurve, een Nederlands antwoordskelet en een QA-blok. Modules: `data` (INRB/INSP-cijfers, Natural Earth, ECDC-controle), `geo`, `risk`, `figures`, `mail`, `msg`, `log`. Regressietests reproduceren de handmatige adviezen van augustus en september 2026.
- **Commits:** ce4253a
- **Bron:** gereconstrueerd uit git-geschiedenis

## Voorstellen (nog niet gevraagd)
- **Kaartgegevens apart van de dagcijfers verversen.** De cache (`~/.cache/dienstreis`) is nu 333 MB voor de circa 70 MB die de code gebruikt, en de verversing van 6 uur geldt voor alles, ook voor de grenzen van de gezondheidszones die zo goed als nooit wijzigen. Drie stappen: (1) een eigen, lange vervaltermijn voor de shapefile, zodat enkel de INSP-CSV's elke 6 uur opnieuw gehaald worden; (2) `git clone --filter=blob:none --sparse` met een sparse-checkout van `NEEDED`, wat de eerste kloon van 333 MB naar ongeveer 70 MB brengt; (3) op de pad zonder git ETag of Last-Modified bewaren en met `If-None-Match` vragen, zodat een ongewijzigde shapefile van 66 MB niet elke 6 uur opnieuw binnenkomt. Punt (3) is het meest zichtbaar op een pc zonder git, het geval dat de README als typisch beschrijft.
- Een geanonimiseerde `.msg` als testfixture, om de prompts te testen tegen een echte aanvraag zonder de gegevens van een collega te committen.
