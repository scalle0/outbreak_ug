# Feature log

Requests for this repo, newest first. Status: gevraagd · bezig · klaar · geweigerd · uitgesteld.

| ID | Feature | Status | Gevraagd |
|---|---|---|---|
| F-013 | Casusvragen: een reiziger die al ter plaatse is (ziek, blootgesteld, in quarantaine) | gevraagd | 2026-09-25 |
| F-012 | Handmatig bijgehouden cijfertabel per uitbraak, en mpox (DRC) als tweede profiel | gevraagd | 2026-09-25 |
| F-011 | Routering naar de uitbraken die gelden, meerdere uitbraken per advies, landniveau zonder uitbraak | gevraagd | 2026-09-25 |
| F-010 | Generieke kern: ebola wordt het eerste uitbraakprofiel, zonder gedragswijziging | klaar | 2026-09-25 |
| F-009 | Kortere mail aan Team Actueel | klaar | 2026-09-22 |
| F-008 | Kaart sneller: elk advies ruim een minuut korter | klaar | 2026-09-22 |
| F-007 | Regels kunnen overrulen, met vastgelegde reden | klaar | 2026-09-22 |
| F-006 | Adviezen gelogd, gedateerd en doorzoekbaar, zodat nieuw advies oud advies niet tegenspreekt | klaar | 2026-09-22 |
| F-005 | WHO en FOD Buitenlandse Zaken elke keer meenemen, naast CDC en ECDC | klaar | 2026-09-22 |
| F-004 | Kaartgegevens apart van de dagcijfers verversen | klaar | 2026-09-22 |
| F-003 | Hardening van `advies`: promptisolatie, reisschemavalidatie, cijfercontrole | klaar | 2026-09-22 |
| F-002 | Alles lokaal in één commando: `dienstreis advies`, LLM enkel voor oordeel | klaar | 2026-09-22 |
| F-001 | dienstreis-advies 0.1.0: uitbraakrisico voor UGent-dienstreizen | klaar | 2026-09-22 |

## F-013 · Casusvragen: een reiziger die al ter plaatse is
- **Gevraagd:** 2026-09-25 — "we should be able to add in messages from other diseases and countries"; bij de keuze van aanvraagtypes: casusvragen erbij
- **Status:** gevraagd
- **Aanleiding:** de mpox-aanvraag van 25/09 (een reiziger in quarantaine ter plaatse, geen reisschema) liep door `dienstreis advies` en kwam eruit als ebola-pretraveladvies: categorie F, "geen ebola-gerelateerd bezwaar", ebolakaart en -curve, een go/no-go-datum drie maanden in het verleden. Het model schreef zelf "Dossiermismatch" in `sugg.txt`, maar de pijplijn kon daar niets mee.
- **Plan:** de reisschemastap geeft `type: reisadvies | casus | vraag`, te wijzigen op het bevestigingsscherm; voor casus en vraag geen kaart of curve, een eigen mail- en webprompt (ITG, Sciensano, Departement Zorg, WHO, ECDC), dezelfde controles; waarschuwing bij een go/no-go-datum in het verleden.
- **Open:** privacy van casusmails (identificeerbare gezondheidsgegevens naar Anthropic): bevestigingsvraag, `--llm manual` als standaard, of pseudonimiseren. Het archiefrecord en de logregel van 25/09 staan als ebolareis; opnieuw labelen zodra de velden bestaan?

## F-012 · Handmatige cijfertabel per uitbraak, mpox (DRC) als tweede profiel
- **Gevraagd:** 2026-09-25 — keuze "hand-kept table" voor uitbraken zonder INRB-achtige databron
- **Status:** gevraagd
- **Plan:** eerst nagaan of er een gecureerde mpox-bron bestaat; anders een adapter `table` op een `cases.csv` per uitbraak (datum, provincie, zone, cumulatieve gevallen en overlijdens, casusdefinitie, bron), grenzen van INRB voor de DRC en geoBoundaries voor andere landen. De webstap stelt updates voor, de arts bevestigt. Een verouderde tabel wordt in de QA en bovenaan de notities gemeld.
- **Open:** de klinische parameters van mpox (vensters, oordeel per categorie, bevestigde of vermoedelijke gevallen, zone of provincie, voorwaarden, familievlag, drempel voor "stijgend", vaccinatie in de pretravelregel) zijn een oordeel van de arts; er gaat niets live zonder zijn bevestiging. Wie houdt `cases.csv` bij, hoe vaak, en vanaf welke ouderdom is ze verouderd?

## F-011 · Routering, meerdere uitbraken per advies, landniveau
- **Gevraagd:** 2026-09-25 — "A lot of the question come for ebola, but we should be able to add in messages from other diseases and countries"; keuze: meerdere uitbraken per advies
- **Status:** gevraagd
- **Plan:** elke halte krijgt een landcode (`places.csv` of Natural Earth op `ADM0_A3`); een uitbraak geldt als een halte in een van haar landen ligt of binnen `radius_km` van een actieve zone. Per uitbraak een risicotabel, kaart en curve; het strengste oordeel wint. Landfeiten (FOD, pretravelregel) in `config/countries.yaml`, los van de CDC-niveaus die per ziekte gelden. Een reis zonder bekende uitbraak krijgt een advies op landniveau zonder kaart; een ziekte in de mail zonder profiel wordt bovenaan gemeld, nooit gelezen als "geen uitbraak".
- **Bronnenregister per land** (2026-09-25): "when identifying new diseases or countries a source database could be made not to repeat the same exercise again and again (for example the shp files of the country, the trusted sources of the government, most important news outlets, and the international bodies...)". Wordt de landlaag van deze feature: een bestand per land in plaats van alleen FOD-links, met grenzen (bron en niveau, de bestanden zelf in de cache), de betrouwbare overheidsbronnen (ministerie, nationaal volksgezondheidsinstituut), de nieuwsmedia die de webstap mag gebruiken, taal, FOD-pagina's en pretravelregel, elk met een `verified`-datum. Daarnaast een korte lijst internationale instanties die voor elk land gelden (WHO, ECDC, CDC, Africa CDC, ITG, Sciensano). De webstap leest het register in plaats van telkens opnieuw te zoeken, en stelt nieuwe bronnen voor die de arts bevestigt, zoals nu al bij de reisadviezen.
- **Open:** is een reis waarvan de zwaarste halte C is (meer dan 42 dagen zonder geval) bedoeld als "geen bezwaar" voor de hele reis? Zo werkt het nu, terwijl de halte zelf "voorwaardelijk" zegt. Routeringsstraal standaard 500 km?

## F-010 · Generieke kern: ebola wordt het eerste uitbraakprofiel
- **Gevraagd:** 2026-09-25 — "I thought we had made this repo non diseases specific. [...] Can we rebuild this? What would be your advice?"
- **Status:** klaar (2026-09-25)
- **Gebouwd:**
  - `dienstreis/outbreak.py`: een uitbraakprofiel (`OutbreakSpec`) wordt gelezen en gecontroleerd voor het gebruikt wordt; een onbruikbaar profiel wordt geweigerd met alle problemen tegelijk. `fill` zet de passages van het profiel in de prompts waar `{{uitbraak:<naam>}}` staat.
  - `dienstreis/outbreaks/ebola_cod_2026/`: `outbreak.yaml` (databron, landen, vensters 21/42, oordeel per categorie en gewicht in het reisoordeel, eindoordelen, vlagteksten en drempels, voorwaarden, ECDC- en WHO-bron, teksten op kaart en curve), `prompt.md` (acht passages uit `reply.md` en `web.md`, letterlijk) en `zone_overrides.csv` (verhuisd uit `config/`).
  - `data.load` kiest de adapter uit het profiel (enkel `inrb` voorlopig) en geeft de reeksen aan een gedeelde `derive`; ECDC en WHO worden gelezen met de URL en titelpatronen van het profiel; een bron die het profiel niet noemt, telt niet als onbereikbaar. `risk`, `mail`, `figures`, `pipeline`, `geo`, `msg` en `llm` halen uit het profiel wat ze vroeger zelf wisten.
  - Tests: `test_golden.py` (de uitvoer van de vier voorbeeldreizen en de drie prompts, vastgelegd voor de herstructurering) en `test_outbreak.py` (profielen, passages, bronnen).
  - Daarna, apart: twee fouten die de goldens zichtbaar maakten. Zonenamen verloren hun hoofdletters ("Gezondheidszone makiso kisangani", door `.capitalize()`), en de ECDC-datum stond met een Engelse maand in de Nederlandse mail ("data tot 19 September"). De goldens zijn voor precies die zeven regels bijgewerkt; `test_skeleton.py` houdt beide vast.
- **Commits:** da3d465 (goldens), 1d25c9c, 6dbd5dd, en de herstelcommit erna
- **Bewezen:** alle goldens byte voor byte gelijk, regressietests ongewijzigd groen, 150+ tests groen. Figuren: de vier epicurves en twee van de vier kaarten byte voor byte gelijk; op de andere twee verschuiven enkele labels een paar pixels. Dat gebeurt ook tussen twee runs van dezelfde code, dus het komt niet van de herstructurering (zie Voorstellen).
- **Beslissingen:**
  - Herstructureren in plaats van een nieuwe repo: ongeveer 60 procent van de code (mail lezen, de drie modelstappen, controles, overrules, archief, log, widget) is al ziekte-onafhankelijk (Steven, 2026-09-25).
  - Volgorde: eerst de generieke kern, dan routering en meerdere uitbraken, dan de cijfertabel en mpox, dan casusvragen (Steven, 2026-09-25).
  - Klinische parameters staan in het profiel en worden door de arts bevestigd; de code verzint ze niet.
  - `Nom` en `PROVINCE` blijven de kolomnamen die een adapter levert: hernoemen tijdens de herstructurering zou de tests aanpassen die de herstructurering net moeten bewaken.
  - `advisories.yaml` blijft in deze stap ongewijzigd, net als de FOD-links in `mail.py` en de pretravelregel in de voorwaarden: dat zijn landfeiten, geen ziektefeiten, en ze verhuizen in F-011 naar het bronnenregister per land.
  - De valkuilen uit `reply.md` zijn als een blok naar het ebolaprofiel verhuisd. Welke ervan voor elke ziekte gelden, blijkt pas naast een tweede profiel; dan worden ze gesplitst, met een nagekeken diff.
  - De kolom `new21` is weg: ze werd berekend en nergens gelezen.
  - De bewaarde kaartcontouren dragen nu het id van de uitbraak in hun naam. De eerste run na de update bouwt ze eenmalig opnieuw op (ongeveer anderhalve minuut).
- **Beslissingen:**
  - Herstructureren in plaats van een nieuwe repo: ongeveer 60 procent van de code (mail lezen, de drie modelstappen, controles, overrules, archief, log, widget) is al ziekte-onafhankelijk (Steven, 2026-09-25).
  - Volgorde: eerst de generieke kern, dan routering en meerdere uitbraken, dan de cijfertabel en mpox, dan casusvragen (Steven, 2026-09-25).
  - Klinische parameters staan in het profiel en worden door de arts bevestigd; de code verzint ze niet.
  - `Nom` en `PROVINCE` blijven de kolomnamen die een adapter levert: hernoemen tijdens de herstructurering zou de tests aanpassen die de herstructurering net moeten bewaken.

## F-009 · Kortere mail aan Team Actueel
- **Gevraagd:** 2026-09-22 — "the mail indeed has to be much shorter"
- **Status:** klaar (2026-09-22)
- **Gebouwd:** `prompts/reply.md` heeft een paragraaf Lengte (richtlijn 350 woorden, maximum 500) en een herschreven structuur: kernoordeel in een of twee zinnen, twee tot drie zinnen per luik met alleen de cijfers die het oordeel dragen, stand van zaken in twee zinnen, profiel alleen als het het oordeel verandert, hoogstens zes voorwaarden van elk een regel, en per vraag van An hoogstens drie zinnen. Expliciet erbij: de valkuilen staan er om fouten te vermijden, niet om te tonen dat het model eraan gedacht heeft, en wat uit de mail valt hoort in `suggestions`, waar wel uitgeweid mag worden. `mail.length_note` telt de woorden tussen aanhef en ondertekening en voedt de bestaande herstelronde.
- **Beslissingen:**
  - De lengtecontrole waarschuwt, ze blokkeert niet. Een te lange maar correcte mail is verstuurbaar; alleen de arts kan oordelen of de lengte terecht is. Ze zit dus bij `notes`, naast `verdict_note`, en niet bij `issues`.
  - De grens telt de eigenlijke tekst, niet de aanhef en de ondertekening, zodat de redirectregel de telling niet beinvloedt.

## F-008 · Kaart sneller: elk advies ruim een minuut korter
- **Gevraagd:** 2026-09-22 — "pick up F-008"
- **Status:** klaar (2026-09-22)
- **Gebouwd:** `data.display_geometry()` berekent de provinciegrenzen en de vereenvoudigde zonecontouren eenmaal en bewaart ze in de cache, met de mtime en grootte van de shapefile als sleutel; contouren van een oudere shapefile worden opgeruimd. `fetch_countries()` bewaart de landgrenzen op dezelfde manier vereenvoudigd, want die worden twee keer per kaart getekend (achtergrond en locatiekaartje). `figures.itinerary_map` gebruikt die contouren in plaats van elke run opnieuw te dissolven.
- **Gemeten:** `itinerary_map` gaat van 106 naar 21 seconden; een volledig advies van ongeveer 115 naar ongeveer 30 seconden. De eerste run na een nieuwe shapefile duurt eenmalig langer (ongeveer 100 seconden) omdat de contouren dan gemaakt worden. Cache erbij: 4,9 MB.
- **Beslissingen:**
  - Er wordt eerst op volle resolutie gedissolveerd en pas daarna vereenvoudigd. Andersom laat de vereenvoudiging gaten en pieken achter langs de provinciegrenzen, en dat is net de lijn op de kaart die moet kloppen.
  - De vereenvoudiging raakt uitsluitend wat getekend wordt. `geo.zone_of`, `geo.neighbours` en `geo.nearest_active` blijven op de exacte grenzen werken: daar hangt de zone-indeling en dus het risico van af. `test_display_geometry.py` legt dat vast, inclusief een punt vlak bij een zonegrens.
  - Tolerantie 0,0025 graden, ongeveer 250 m. De kaart is 12,5 inch op 300 dpi voor een land van 2 000 km breed, dus ongeveer 500 m per pixel: fijner detail kan niet op papier verschijnen.
  - Voor en na visueel vergeleken op een reis Kinshasa-Kisangani-Durba: de zones, kleuren, arcering, de blauwe omlijning en het locatiekaartje zijn niet te onderscheiden. Wat wel verschuift zijn enkele labelposities (Mangobo, Kabondo, Mongbwalu, Damas), omdat adjustText op minieme hoekpuntverschillen anders uitkomt. `label_overlaps` en `labels_clipped` blijven 0.

## F-007 · Regels kunnen overrulen, met vastgelegde reden
- **Gevraagd:** 2026-09-22 — "lastly, the user must be able to overrule rules"
- **Status:** klaar (2026-09-22)
- **Gebouwd:** in `stops.yaml` kan een halte `override: {category: C, reason: "..."}` krijgen, en de reis `override: {verdict: "...", reason: "..."}` voor het eindoordeel. De reden is verplicht (minstens 15 tekens) en een onbekende categorie of sleutel wordt geweigerd (`trip._check_override`). `risk` bewaart wat de regels zeiden in `rule_category` en zet de overrule als signaal bij de halte; `rule_overall()` blijft naast `overall()` bestaan. De overrule komt terug in de risicotabel (kolom `regel_cat`), in `summary.json` (`overrides`, `rule_overall`), in de logregel (`overrules`), in het archief en in de mailprompt, met de instructie het oordeel te schrijven zoals het nu is en kort te zeggen waarom, zonder de regelcategorie te noemen.
- **Beslissingen:**
  - Een overrule mag beide kanten op: strenger dan de regel (F naar B) is even geldig als milder. De regels kennen het dossier niet.
  - Een overrule geldt voor dat ene advies; ze staat in `stops.yaml` en gaat niet automatisch mee naar een volgende run met nieuwe cijfers. Dat is bewust: een overrule die blijft gelden zou een oude beoordeling stilzwijgend over nieuwe gegevens leggen.
  - `mail.verdict_note` controleert niet langer op de regelwoorden wanneer de arts zelf een eindoordeel geschreven heeft; daar valt niets tegen af te toetsen.
  - Drie oordelen naast elkaar, omdat ze drie verschillende vragen beantwoorden: `rule_overall` (wat de regels zeggen, voor elke overrule), `effective_overall` (de categorieen zoals ze nu staan, met de overrules per halte) en `overall` (het advies zoals het buitengaat, inclusief een eigen eindoordeel). Een eerste versie liet `overall` terugvallen op `rule_overall`, waardoor een overrule per halte het eindoordeel niet meer beinvloedde; `test_rule_overall_reports_what_the_rules_said_not_the_override` houdt dat tegen.

## F-006 · Adviezen gelogd, gedateerd en doorzoekbaar
- **Gevraagd:** 2026-09-22 — "all advices must be logged, dated and searchable, so that rules and previous advice doesn't contradict current advice that is being generated"
- **Status:** klaar (2026-09-22)
- **Gebouwd:** `archive.py` bewaart elk advies in `~/.config/dienstreis/adviezen/JJJJ-MM-DD_reiziger/` (`advies.json` met reiziger, data, haltes, zones, provincies, categorieen, oordeel, overrules en de volledige mailtekst; `reply.txt`; `summary.json`). `dienstreis zoek [term] [--sinds] [--tot] [--oordeel] [--overruled] [--vol]` zoekt op plaats, zone, provincie, reiziger of notitie, nieuwste eerst. `archive.for_trip` geeft de eerdere adviezen voor dezelfde plaatsen, zones of provincies mee aan de mailprompt (`eerdere_adviezen`), met de volledige tekst: een logregel van een regel kan niet tonen dat een nieuw advies een ouder tegenspreekt, de tekst wel. De logregel houdt nu ook `overrules` en `advice_dir` bij, zodat log en archief naar elkaar verwijzen.
- **Beslissingen:**
  - De volledige mailtekst gaat mee naar het model, niet enkel de samenvatting. Dat is het punt van de functie, maar het betekent ook dat reisgegevens van collega's uit eerdere dossiers meegestuurd worden. Staat in de privacyparagraaf van de README.
  - Twee adviezen voor dezelfde persoon op dezelfde dag krijgen een map met achtervoegsel, ze overschrijven elkaar niet.
  - Een onleesbaar `advies.json` wordt overgeslagen in plaats van de zoekopdracht te laten mislukken.

## F-005 · WHO en FOD Buitenlandse Zaken elke keer meenemen
- **Gevraagd:** 2026-09-22 — "we should also check the WHO and FOD buitenlandse zaken every time (next to CDC and eCDC...), maybe also wanda to be sure?"
- **Status:** klaar (2026-09-22)
- **Gebouwd:** `data.who_snapshot()` leest het recentste Disease Outbreak News over ebola in de DRC uit de WHO-API (`who.int/api/news/diseaseoutbreaknews`), met datum, titel, link en ouderdom in dagen. `data.sources_snapshot()` haalt WHO en ECDC bij elke run op; beide falen zacht en komen in het QA-blok terecht (`who`, `who_days_old`, `sources_unreachable`). De webstap staat nu standaard aan (`--no-web` om ze over te slaan) en kijkt FOD, CDC en WHO na; `prompts/web.md` vraagt expliciet of er een nieuwer DON of een WHO-risicobeoordeling is. WHO staat ook in `mail.SOURCES`.
- **Beslissingen:**
  - wanda.be valt weg op vraag van Steven (2026-09-22).
  - De WHO-pagina wordt niet gescrapet maar via de JSON-API gelezen: de pagina wordt client-side opgebouwd, een regex over de HTML vindt niets (nagegaan, leverde eerst "no DRC Ebola item" op).
  - FOD en CDC blijven in de webstap in plaats van deterministisch gescrapet te worden: het zijn lopende teksten, en het verschil tussen "formeel afgeraden om veiligheidsredenen" en "om gezondheidsredenen" bepaalt de formulering van het advies.
  - Een `--asof`-run haalt geen live bronnen op: de pagina's van vandaag horen niet bij de cijfers van vorige maand.

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

## Uitgevoerde proefdraai (2026-09-22)

Een volledige run met de echte Claude Code-backend op een verzonnen aanvraag (`tests/fixtures/aanvraag_testpersoon.eml`), met log, context en archief in een tijdelijke map. Duur ongeveer zes minuten: 25 s reisschema, 202 s webstap, 138 s mail. De mailcontroles slaagden in de eerste poging, dus geen herstelronde.

Wat goed ging: de Belgische datums (28/11/2026) kwamen correct als ISO terug; alle cijfers in de mail waren terug te voeren op de berekende gegevens (20 gevallen, 9 overlijdens, 10 in 14 dagen, nationaal 7 672 / 3 699, CFR 48 procent, volle weken 569-586-586-572 kloppen alle met `summary.json`); de webstap vond echte, bruikbare zaken (het project Fleuve Congo sans Ebola op de as Kisangani-Kinshasa, de dronepogingen op Bangoka die de formele FOD-afrading voor Tshopo verklaren, de Amerikaanse en Canadese inreismaatregelen); en het model weigerde uitdrukkelijk de zone "stijgend" te noemen op basis van een enkele 14-dagentelling, precies zoals de valkuilen in `prompts/reply.md` vragen.

Een fout gevonden en hersteld: de mail schreef "het laatste geval dateert van vandaag" terwijl `dagen_sinds_laatste` telt vanaf de laatste INSP-rapportage (19/09) en de run op 22/09 liep, drie dagen ernaast. Het getal klopte, de formulering niet, en geen enkele controle kan dat vangen. `prompts/reply.md` heeft er nu een valkuil voor.

Aandachtspunt, geen fout: de mail telde 1 642 woorden. De cijfercontrole bewijst dat een getal ergens uit de invoer komt, niet dat het waar is; cijfers die uit de webstap komen (het aantal gehospitaliseerden, de cholera-aantallen, de WHO-cijfers van DON617) zijn zo betrouwbaar als de webpagina die het model gelezen heeft. Het veld `checked_how` in `web.json` zegt of de pagina zelf gelezen is of enkel een zoekresultaat.

## Voorstellen (nog niet gevraagd)
- Kaarten reproduceerbaar maken. Twee runs van dezelfde code op dezelfde gegevens plaatsen enkele labels een paar pixels anders (gezien op de kaarten Yangambi en Haut-Uele, 2026-09-25); zones, kleuren en route zijn gelijk. adjustText zet zelf een vaste seed en `PYTHONHASHSEED=0` helpt niet, dus de oorzaak zit elders. Zolang dat zo is, kunnen de kaarten niet mee in de goldentests.
- Een echte `.msg` als testfixture. De OLE-parser in `msg.py` wordt nu enkel handmatig getest; `.eml` en `.txt` zitten wel in de tests. Een `.msg` maken vraagt Outlook, en een bestaande aanvraag committen vraagt eerst een beslissing over anonimisering.
