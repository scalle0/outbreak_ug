# Feature log

Requests for this repo, newest first. Status: gevraagd · bezig · klaar · geweigerd · uitgesteld.

| ID | Feature | Status | Gevraagd |
|---|---|---|---|
| F-007 | Regels kunnen overrulen, met vastgelegde reden | gevraagd | 2026-09-22 |
| F-006 | Adviezen gelogd, gedateerd en doorzoekbaar, zodat nieuw advies oud advies niet tegenspreekt | gevraagd | 2026-09-22 |
| F-005 | WHO en FOD Buitenlandse Zaken elke keer meenemen, naast CDC en ECDC | gevraagd | 2026-09-22 |
| F-004 | Kaartgegevens apart van de dagcijfers verversen | klaar | 2026-09-22 |
| F-003 | Hardening van `advies`: promptisolatie, reisschemavalidatie, cijfercontrole | klaar | 2026-09-22 |
| F-002 | Alles lokaal in één commando: `dienstreis advies`, LLM enkel voor oordeel | klaar | 2026-09-22 |
| F-001 | dienstreis-advies 0.1.0: uitbraakrisico voor UGent-dienstreizen | klaar | 2026-09-22 |

## F-007 · Regels kunnen overrulen, met vastgelegde reden
- **Gevraagd:** 2026-09-22 — "lastly, the user must be able to overrule rules"
- **Status:** gevraagd
- **Open:** af te spreken wat precies overruled kan worden en hoe het vastgelegd wordt. Voorstel: per halte de categorie A-F/X of het eindoordeel kunnen overschrijven in `stops.yaml` (`override: {category: C, reason: "..."}`), met een verplichte reden. De overrule verschijnt dan in de risicotabel, in `summary.json`, in de log en in de mailprompt, zodat het model weet dat de arts van de regel afgeweken is en waarom. Een overrule zonder reden wordt geweigerd. Te bespreken: mag een overrule ook strenger zijn dan de regel (waarschijnlijk ja), en moet ze aflopen bij een volgende run met nieuwe cijfers.

## F-006 · Adviezen gelogd, gedateerd en doorzoekbaar
- **Gevraagd:** 2026-09-22 — "all advices must be logged, dated and searchable, so that rules and previous advice doesn't contradict current advice that is being generated"
- **Status:** gevraagd
- **Open:** er is al een `advice_log.csv` (datum, reiziger, haltes, categorieen, oordeel, go/no-go) en een `context.md` met notities; wat ontbreekt is de volledige tekst van het verstuurde advies en een fatsoenlijke zoekfunctie. Voorstel: elk advies integraal bewaren (mailtekst, `summary.json`, overrules) in `~/.config/dienstreis/adviezen/JJJJ-MM-DD_reiziger/`, met `dienstreis zoek <term>` op plaats, zone, reiziger, periode en oordeel. De treffers voor dezelfde bestemming gaan dan als volledige eerdere adviezen naar de mailprompt in plaats van de huidige logregels, zodat een tegenspraak zichtbaar wordt voor het model en in de notities belandt. Te bespreken: hoe lang bewaren, en dat dit persoonsgegevens van collega's zijn die dan ook naar het model gaan.

## F-005 · WHO en FOD Buitenlandse Zaken elke keer meenemen
- **Gevraagd:** 2026-09-22 — "we should also check the WHO and FOD buitenlandse zaken every time (next to CDC and eCDC...), maybe also wanda to be sure?"
- **Status:** gevraagd
- **Open:** de webstap (`--web`) kijkt nu naar FOD en CDC en is optioneel; ECDC wordt deterministisch gescrapet als kruiscontrole. Te doen: WHO Disease Outbreak News en de WHO-situatierapporten erbij, FOD en CDC bij elke run in plaats van enkel met `--web`, en de bronnenlijst in `mail.SOURCES` mee laten groeien. **Vraag aan Steven:** met "wanda" is wellicht wanda.be bedoeld, het reisadvies van het ITG. Graag bevestigen, want dat is de enige bron in het rijtje die specifiek Belgisch en klinisch is; ze heeft een ander gewicht dan FOD (veiligheid) of CDC (niveau). Te bespreken: elke bron elke keer ophalen maakt elke run trager en afhankelijk van het web, dus wellicht met een eigen cache per bron en een duidelijke melding als een bron niet bereikbaar was.

## F-004 · Kaartgegevens apart van de dagcijfers verversen
- **Gevraagd:** 2026-09-22 — "The maps we make: are these downloaded every time?"
- **Status:** klaar (2026-09-22)
- **Gebouwd:** `data.py` splitst `NEEDED` in `DAILY` (de INSP-CSV's en `aliases.csv`, 6 uur) en `SHAPES` (de shapefile van de gezondheidszones, 30 dagen): alleen wat verlopen is wordt opgehaald. De kloon gebruikt `--filter=blob:none --sparse` met een sparse-checkout van `NEEDED` (gemeten: 333 MB wordt 113 MB, alle bestanden aanwezig). Zonder git bewaart `_download_needed` de ETag per bestand en vraagt met `If-None-Match`; raw.githubusercontent.com antwoordt dan 304 zonder body (gemeten), zodat de shapefile van 66 MB niet elke zes uur opnieuw binnenkomt. `dienstreis data` toont de cachegrootte en `dienstreis data --reset-cache` wist de cache, zodat een bestaande volledige kloon vervangen wordt door een sparse. Natural Earth werd al eenmalig gecachet en blijft zo.
- **Beslissingen:** de sparse-patronen staan bewust zonder leidende slash; git waarschuwt daarover, maar de ankerversie laat de checkout van `.prj` en `.cpg` mislukken en levert een lege werkmap op.

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
- Een echte `.msg` als testfixture. De OLE-parser in `msg.py` wordt nu enkel handmatig getest; `.eml` en `.txt` zitten wel in de tests. Een `.msg` maken vraagt Outlook, en een bestaande aanvraag committen vraagt eerst een beslissing over anonimisering.
