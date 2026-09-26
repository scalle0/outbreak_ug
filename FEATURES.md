# Feature log

Requests for this repo, newest first. Status: gevraagd · bezig · klaar · geweigerd · uitgesteld.

| ID | Feature | Status | Gevraagd |
|---|---|---|---|
| F-015 | Kort antwoord aan An, een intern dossier voor Steven, een vaste fiche per ziekte | bezig | 2026-09-26 |
| F-014 | Een map per aanvraag: meerdere mails samen lezen | klaar | 2026-09-25 |
| F-013 | Casusvragen: een reiziger die al ter plaatse is (ziek, blootgesteld, in quarantaine) | klaar | 2026-09-25 |
| F-012 | Handmatig bijgehouden cijfertabel per uitbraak, en mpox (DRC) als tweede profiel | klaar | 2026-09-25 |
| F-011 | Routering naar de uitbraken die gelden, meerdere uitbraken per advies, landniveau zonder uitbraak | klaar | 2026-09-25 |
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

## F-015 · Kort antwoord aan An, een intern dossier, een vaste fiche per ziekte
- **Gevraagd:** 2026-09-26 — "the program is responding way too broadly to the general question. So what I would like is to have a report that I can use internally with the maps and the tables and the epidemiology and the treatment, the presentation, the risks, [...] any important documents from Belgian, European, world, US guidelines, and then have a very concise response to the actual question that was in the email sent by the office"
- **Status:** bezig
- **Aanleiding:** de echte mail van 25/09, opnieuw door de tool op 25/09: juist herkend als casus, maar een mail van 547 woorden (situatie, vier lange antwoorden, zes aanbevelingen, richtlijnen met datums), terwijl wat Steven zelf nodig had als losse lijst in `sugg.txt` stond, zonder kaart, epidemiologie, klinisch beeld of richtlijnenoverzicht.
- **Beslissingen (Steven, 2026-09-26):**
  - Mail aan An: kort, ongeveer 120 woorden en hoogstens 200: het antwoord, een of twee zinnen per vraag, hoogstens drie acties; kaart en curve als bijlage ("Short with map"). Bij een casus of vraag gaan er geen bijlagen mee; de figuren staan in het dossier.
  - Dossier: een HTML-pagina per advies, met de mail bovenaan en een kopieerknop, bewaard in het archief.
  - Klinisch beeld, behandeling, vaccinatie en de Belgische, Europese, WHO- en Amerikaanse richtlijnen: een vaste fiche per ziekte, eenmaal opgesteld uit bronnen en door Steven bevestigd; de webstap meldt nieuwere richtlijnen en stelt ze voor.
- **Plan:** vier stappen, elk met een eigen commit: (1) de korte mail, (2) de dossierpagina, (3) fiche en documenten per ziekte, (4) een proefrun op verzonnen mails, die Steven leest voor de tak samengevoegd wordt.
- **Gebouwd, stap 1 (de korte mail):**
  - `prompts/reply.md` en `prompts/consult.md`: richt op 120 woorden, hoogstens 200. De mail is het antwoord (een of twee zinnen), per expliciete vraag van An een of twee zinnen, hoogstens drie acties en bij een reisadvies een halve zin over de bijlagen. Geen alinea per luik, geen stand van zaken, geen bronnenlijst, tenzij een zin het antwoord draagt.
  - Het model geeft een `dossier`-object terug in plaats van de vrije lijst `suggestions`: `vragen` (elke vraag met de zin die ze beantwoordt), `beoordeling`, `weggelaten`, `na_te_kijken`, `toezeggingen`, `vragen_aan_behandelaar`. Tot de dossierpagina er is, gaan die velden met een label naar `sugg.txt`; een oud antwoord met `suggestions` wordt nog gelezen.
  - `reply_skeleton.txt` wordt `feiten.txt`: het regeloordeel, de feiten per luik, de stand van zaken en de voorwaarden voor de reiziger, zonder briefkader of `[[CLAUDE]]`-plaatshouders. Het model krijgt het als `feiten`, "om te weten, niet om over te schrijven"; de cijfercontrole leest het zoals vroeger. De plaatshouders zijn ook uit de profielen (`conditions`) gehaald: de go/no-go is nu een van de drie acties.
  - De doorverwijzing naar steven.callens@uzgent.be zet de code zelf in de mail (`mail.with_redirect`), niet meer het model.
  - Bijlagen: kaart en curve gaan enkel mee bij een reisadvies, en het model krijgt hun bestandsnamen (`bijlagen`), zodat de mail geen curve belooft die er niet is.
  - Controles: `length_note` waarschuwt boven 200 woorden (50 meer per bijkomende uitbraak, was 500 en 100); nieuw is `questions_note`, die waarschuwt als een vraag van An geen antwoord kreeg in `dossier.vragen`. Beide sturen de herstelronde en blokkeren nooit.
  - Tests: 245 groen. Goldens: `feiten.txt` vervangt `reply_skeleton.txt` en bevat dezelfde feitenalinea's zonder het kader; in `summary.json` is `skeleton_issues` leeg (de vier plaatshouders waren het kader); de mailprompt heeft de nieuwe secties en krijgt `<feiten>` en `<bijlagen>` in plaats van `<skelet>`.
- **Gebouwd, stap 2 (het dossier):**
  - `dienstreis/dossier.py`: een HTML-pagina per advies (`dossier.html`) met elf delen: antwoord aan An, aanvraag, oordeel, epidemiologie, risico, ziektefiche (leeg tot stap 3), richtlijnen, beoordeling, web, eerdere adviezen, bronnen.
  - Bovenaan staat de mail met een kopieerknop, het aantal woorden tegenover de grens en de opmerkingen van de controles. Bij elke vraag van An staat de zin die ze beantwoordt, of "geen antwoord gekoppeld".
  - De pagina komt uit de bestanden van de run plus `dossier.json`, dat bewaart wat geen ander bestand heeft: de aanvraag, de beoordeling van het model, de controles, eerdere adviezen, logregels en de relevante regels uit `context.md`. Zo bouwt `dienstreis dossier <map>` de pagina opnieuw na een handmatige aanpassing van `reply.txt`, en doet het de controles opnieuw. Dat commando vervangt `dienstreis widget`; `mail.widget` is weg.
  - Kaart en curve worden ook voor een casus of vraag getekend, voor het dossier; enkel een reisadvies stuurt ze mee. `epi` heeft nu ook de laatste acht volle weken met overlijdens (`weeks_last8`), enkel voor het dossier: de mailstap krijgt ze niet.
  - De figuren staan in de pagina, verkleind tot 1600 pixels (Pillow, nu een expliciete afhankelijkheid), zodat de kopie in het archief zonder de map van de run opent. `dienstreis zoek` toont de link naar het dossier.
  - Opmaak volgens ScAIdev: inktkleurige bovenbalk met het knooppuntmerk, papieren achtergrond, Space Grotesk, Inter en JetBrains Mono, groen voor de hoofdknop, blauw voor info, zand voor wat blokkeert, Lucide-lijniconen, een afdrukstijl voor PDF.
  - Tests: `test_dossier.py`, 14 tests op een verzonnen run zonder netwerk. Alle 259 tests groen. Goldens: `summary.json` krijgt `weeks_last8`; de prompts zijn ongewijzigd.
- **Gebouwd, stap 3 (fiche en documenten per ziekte):**
  - `dienstreis/fiche.py`: per uitbraakprofiel `fiche.md` (front matter `status: concept | bevestigd`, `verified`, `bevestigd_door`, `bevestigd_op`, en elf vaste secties, van verwekker tot terugkeer naar België) en `documents.yaml` (sleuteldocumenten per niveau `be`, `eu`, `who`, `us`: id, organisatie, titel, datum, url, kernboodschap).
  - Een uitspraak in de fiche verwijst naar haar document als `[id]`. Een lokale kopie in `~/.config/dienstreis/outbreaks/<id>/` wint zolang ze recenter nagekeken is, net zoals bij het landenregister.
  - `dienstreis fiche <id>` toont de stand: status, ontbrekende secties, documenten per niveau en verwijzingen zonder document.
  - `dienstreis fiche <id> --opstellen [--repo]` laat met webzoeken een concept opstellen (`prompts/fiche.md`). Het concept komt lokaal, of met `--repo` in de map van het profiel. Een bevestigde fiche wordt nooit overschreven: het concept komt dan als `fiche_concept.md` ernaast. Het modelspoor blijft lokaal (`fiche_trace.json`). De `fiche`-stap krijgt 80 beurten en 40 minuten, de webstap van een advies 25.
  - De mailstap krijgt enkel een bevestigde fiche (`fiche`). Wat de mail zegt over isolatie, vaccinatie of vrijgave steunt daarop, en de getallen erin tellen als bron voor de cijfercontrole. Een concept komt nooit in de mail.
  - De webstap krijgt bij elk advies de documenten en de fiche (`fiches`). Hij stelt nieuwere of nieuwe documenten voor (`document_updates`); die komen na een ja in de lokale `documents.yaml`, met dezelfde vraag als het landenregister. Een uitspraak die een nieuwere richtlijn tegenspreekt (`fiche_flags`), staat in de terminal en in het dossier en wordt nooit toegepast.
  - Dossier: de fiche per uitbraak, met een zandkleurige banner zolang ze een concept is, verwijzingen die naar het document linken, en de vlaggen van de webstap. Onder Richtlijnen staan de documenten per niveau, de voorstellen van de webstap en de documenten van een land (`documents` in `countries/<ISO3>.yaml`). De Markdown van de fiche toont ruwe HTML als tekst en laat enkel web- en paginalinks door. Nieuwe afhankelijkheid: `markdown`.
  - Tests: `test_fiche.py` (10) en een pijplijntest: de bevestigde fiche gaat naar de mail, een concept niet, en haar getallen gelden niet als verzonnen. De goldens zien geen fiche (bevroren in `test_golden.py`), zodat ze de analyse en de prompts vastleggen en niet de tekst van de fiche. De webprompt krijgt de nieuwe opdracht en `<fiches>`, de mailprompt de regel over de bevestigde fiche.
- **Commits:** a8022e7 (stap 1), 63d1a55 (stap 2)
- **Beslissingen (uitvoering):**
  - Zonder `dossier` in het antwoord zwijgt `questions_note`: er is dan niets om de vragen mee te vergelijken, en een melding zou een vraag onbeantwoord noemen die misschien wel beantwoord is.
  - De sleutel `skeleton_issues` in `summary.json` blijft zo heten, zodat oude en nieuwe samenvattingen dezelfde vorm houden.
  - Het dossier wordt ook gebouwd als een blokkerende controle faalt (een verzonnen getal, een em-dash), want Steven heeft het nodig om de mail te verbeteren. De kopieerknop staat dan uit: een mail die de controles niet haalt, is nooit één klik van Outlook, zoals de widget vroeger niet gebouwd werd.
  - DesignSync kon niet inloggen in deze sessie. De ScAIdev-tokens komen uit de kopie in `permanentiefile/prototype/scaidev-tokens.css`, die uit `colors_and_type.css` v2 van het Claude Design-project genomen is.
  - `dienstreis dossier` bouwt de pagina in de map van de run opnieuw, niet in het archief: daar blijft wat de run schreef, zoals voor `reply.txt` en `advies.json`.
  - Het dossier bevat de aanvraag en de casus, zoals het archief. Het blijft op deze pc en gaat nergens heen.
  - De lettertypes komen van Google Fonts, zoals in `permanentiefile`. Zonder internet valt de pagina terug op de systeemletters. Een pagina die als bestand opent, stuurt geen verwijzer mee.
  - De fiche en de documenten kregen een eigen module (`fiche.py`) in plaats van een plaats in `outbreak.py`: die blijft over het profiel zelf gaan.
  - Een fiche verwijst naar een vast id (`[who-ebola-factsheet]`), niet naar een nummer. Een nummer zou verschuiven telkens de webstap een document toevoegt, en de fiche zou dan naar het verkeerde document wijzen. Een nieuwere versie van een document houdt daarom ook het id van de vorige.
  - Een nieuwere richtlijn die de fiche tegenspreekt, verandert de mail niet: de mail volgt de bevestigde fiche en zet de tegenspraak in `na_te_kijken`, zodat Steven beslist.

## F-014 · Een map per aanvraag: meerdere mails samen lezen
- **Gevraagd:** 2026-09-25 — "I will make a folder per request, rather than a msg file, because I now have three emails for one request in one hour time"
- **Status:** klaar (2026-09-25)
- **Commits:** 813c908
- **Gebouwd:** `dienstreis advies <map>` (en `dienstreis msg <map>`) leest elke `.msg`, `.eml` en `.txt` in de map als één aanvraag (`msg.parse_folder`). De volgorde komt uit de verzenddatum in de mail zelf: bij `.msg` uit de eigenschappenstroom (verzendtijd, anders ontvangsttijd), bij `.eml` uit de kop `Date`; enkel een mail zonder datum valt terug op de bestandsdatum, en de kop van die mail zegt dat. Elke mail krijgt een kop `===== Mail i van n: datum | afzender | onderwerp =====`. Losse `.docx`, `.pdf` en `.xlsx` tellen als bijlage, andere bestanden niet. Onderwerp, afzender en ontvangers zijn die van de laatste mail, zodat het Outlook-concept daarop antwoordt; of de draad het ugent.be-adres gebruikte en of de reiziger de uitbraak noemde, geldt als een van de mails het zegt. De tekstgrens per stap (12 000 tekens voor het reisschema, 6 000 voor de mail) geldt per mail. `prompts/stops.md` zegt dat een latere mail een eerdere verbetert en dat het verschil in `contradictions` hoort. Tests: `test_request_folder.py`.
- **Beslissingen:**
  - De datum in de mail beslist, niet de bestandsnaam of de bestandsdatum: bestanden die uit Outlook bewaard worden, krijgen de datum van het bewaren, niet van het verzenden.
  - Bij een tegenstrijdigheid geldt de laatste mail, en het verschil gaat naar `contradictions`, zodat het op het bevestigingsscherm staat en niet stil verdwijnt.
  - Meegenomen: een adres aan het einde van een zin werd met het punt erbij gelezen (`collega@example.org.`); het adrespatroon eindigt nu op een domeinlabel.

## F-013 · Casusvragen: een reiziger die al ter plaatse is
- **Gevraagd:** 2026-09-25 — "we should be able to add in messages from other diseases and countries"; bij de keuze van aanvraagtypes: casusvragen erbij
- **Status:** klaar (2026-09-25)
- **Aanleiding:** de mpox-aanvraag van 25/09 (een reiziger in quarantaine ter plaatse, geen reisschema) liep door `dienstreis advies` en kwam eruit als ebola-pretraveladvies: categorie F, "geen ebola-gerelateerd bezwaar", ebolakaart en -curve, een go/no-go-datum drie maanden in het verleden. Het model schreef zelf "Dossiermismatch" in `sugg.txt`, maar de pijplijn kon daar niets mee.
- **Commits:** fb34be2
- **Gebouwd:**
  - De reisschemastap geeft `type` (`reisadvies`, `casus`, `vraag`) en voor een casus of vraag `situation`, twee of drie zinnen over de toestand zoals de mail ze beschrijft; beide staan op het bevestigingsscherm en in `stops.yaml`.
  - Een reisadvies met een go/no-go-datum in het verleden wordt geweigerd met de vraag of het een casus is: zo liep de mail van 25/09 fout. De controle rekent met `--asof` als dat gegeven is, zodat tests niet op de kalender breken.
  - Een casus of vraag: de cijfers van de uitbraken op de plaats als feiten (`mail.facts`), zonder kaart, curve of oordeel; een webstap die eerst officiële richtlijnen zoekt (`prompts/web_consult.md`: isolatie, terugreis, aankomst in België, contacten; ITG, Sciensano, Departement Zorg, Hoge Gezondheidsraad, WHO, ECDC) en een mail vanuit de werkgever (`prompts/consult.md`: de behandelende arts beslist, UGent adviseert, criteria in plaats van datums, niets wat tussen artsen hoort). Een vraag zonder plaats gaat naar de actieve uitbraken die haar ziekten noemen, anders `geen`.
  - Gezondheidsgegevens: een mail met woorden als quarantaine, isolatie, ziek, besmet, symptomen of een positieve test wordt vóór de eerste modelstap getoond, en het programma vraagt toestemming. `--yes` beantwoordt die vraag niet; `--gezondheidsgegevens-ok` wel; `--llm manual` stuurt niets. Mist de woordenlijst een casus die het model wel herkent, dan komt de vraag voor de web- en mailstap, met de mededeling dat de mail al een keer verstuurd is.
  - Archief en log: `type` en `situation`; een casus vindt eerdere adviezen over dezelfde persoon; `dienstreis zoek --type`. `dienstreis herlabel` labelt een bewaard advies opnieuw (type, uitbraken) met reden; de brief blijft, de oude labels staan in `herlabeld`, de logregel volgt.
  - Het record en de logregel van 25/09 zijn opnieuw gelabeld als casus over mpox (met een kopie van archief en log vooraf).
  - Tests: `test_casus.py`, met een verzonnen casusmail (`tests/fixtures/casus_mpox.txt`).
- **Proefdraai (2026-09-25):** de verzonnen casusmail met de echte Claude Code-backend, met een tijdelijk register. De eerste run stopte: het model las de casus juist, maar liet de einddatum van een verblijf dat nog loopt leeg, en dat weigerde de reisschemacontrole. Een casus mag nu een open einddatum hebben ("sinds 30 juni"); een reis niet. De tweede run (517 s) gaf een brief die op criteria plant, bronnen en datums noemt, de drie vragen van An beantwoordt, per partij zegt wie wat doet en klinische details voor de behandelende arts in de notities houdt. Twee dingen hersteld: WHO heette "niet bereikbaar" terwijl er enkel geen recent mpox-bericht was (nu `none_found`, geen onbereikbare bron), en de webstap stelde wanda.be voor, dat in F-005 weggelaten was (nu `excluded` in `_international.yaml`: de prompts zeggen het en het register weigert zo'n bron).
- **Open:** de echte mail van 25/09 (map `MPox`) is niet opnieuw door het model gegaan: toestemming om die gezondheidsgegevens te versturen is aan Steven. `dienstreis advies` op die map, met het antwoord op de toestemmingsvraag, maakt de vergelijking met de brief die toen vertrokken is.
- **Beslissingen:**
  - Privacy (Steven, 2026-09-25: "Ask each time"): voor een casusmail met gezondheidsgegevens toont het programma wat er naar het model gaat en vraagt het toestemming voor het verstuurd wordt.
  - Het archiefrecord en de logregel van 25/09 (de mpox-casus, als ebolareis bewaard) worden opnieuw gelabeld als casusvraag over mpox zodra die velden bestaan; de tekst blijft zoals ze was (Steven, 2026-09-25).

## F-012 · Handmatige cijfertabel per uitbraak, mpox (DRC) als tweede profiel
- **Gevraagd:** 2026-09-25 — keuze "hand-kept table" voor uitbraken zonder INRB-achtige databron
- **Status:** klaar (2026-09-25)
- **Plan:** eerst nagaan of er een gecureerde mpox-bron bestaat; anders een adapter `table` op een `cases.csv` per uitbraak (datum, provincie, zone, cumulatieve gevallen en overlijdens, casusdefinitie, bron), grenzen van INRB voor de DRC en geoBoundaries voor andere landen. De webstap stelt updates voor, de arts bevestigt. Een verouderde tabel wordt in de QA en bovenaan de notities gemeld.
- **Commits:** 6aad83e, 45d4be7
- **Gebouwd (deel 1, tabel en concept):**
  - Adapter `table` (`data.py`): een met de hand bijgehouden `cases.csv` in de profielmap (datum, provincie, zone, cumulatieve gevallen en overlijdens, casusdefinitie, bron), op de zonegrenzen van een ander profiel, per provincie samengevoegd en in de cache bewaard. Een rij `NATIONAAL` geeft het nationale totaal, anders wordt opgeteld. Een lokale kopie in `~/.config/dienstreis/outbreaks/<id>/` wint zodra ze even ver of verder reikt. Ouder dan `stale_days`: bovenaan de notities, want A en B rusten op recente gevallen. Een lege tabel geeft een advies zonder cijfers voor die uitbraak, nooit een "geen bezwaar". Met een enkele rapportdatum geen curve, en dan belooft de mail er ook geen.
  - De webstap krijgt per tabeluitbraak de laatste cijfers (`tabellen`) en stelt nieuwere officiële cijfers voor (`case_updates`); wat je aanvaardt komt in de lokale tabel.
  - `outbreaks/mpox_cod_2026/`: mpox (clade I) in de DRC per provincie, als concept en niet actief. De klinische parameters staan gemarkeerd als CONCEPT. Een aanvraag die mpox noemt, krijgt een notitie die naar het concept wijst; `--uitbraak mpox_cod_2026` gebruikt het nu al.
  - Tests: `test_table_adapter.py`; `test_route.py` en `test_multi.py` aangevuld. Een proef met echte ebolacijfers en het lege mpox-concept op de reis Kinshasa-Durba toonde dat een lege tabel "geen mpox-gerelateerd bezwaar" opleverde; dat zegt nu "geen cijfers".
- **Beslissingen:**
  - Een mpox-profiel per land (Steven, 2026-09-25: "Per country"), toegevoegd naarmate aanvragen binnenkomen. Eerst `mpox_cod_2026` voor de DRC; de tabeladapter is generiek, zodat een volgend land een nieuwe map met een eigen tabel is.
- **Gebouwd (deel 2, mpox actief):**
  - Bronnenonderzoek (2026-09-25): er is geen gecureerde feed van mpox in de DRC onder het nationale niveau. INRB-UMIE heeft enkel ebola; de INSP-rapporten stoppen in april 2025; OWID en de WHO-API zijn nationaal. Het enige actuele bestand is het WHO-mpoxdashboard, met per gezondheidszone vermoede en bevestigde gevallen sinds 2024, de laatste zes weken en de laatste rapportdatum (data tot 16 augustus 2026), en een nationale weekreeks. Dus een handmatige tabel, gevuld uit dat dashboard; de webstap stelt nieuwere cijfers voor.
  - `outbreaks/mpox_cod_2026/cases.csv`: 200 zones (per zone een rij voor het zesweekse venster en een op de laatste rapportdatum) en de nationale weekreeks sinds 2023. `zone_overrides.csv` voor 14 WHO-spellingen; Dingila (Bas-Uele) heeft geen eigen zone in de INRB-shapefile en blijft ongematcht.
  - Nieuw in een profiel: `case_words` (hoe de brief de cijfers noemt; ebola: "bevestigde gevallen"), `windows.recent` (venster voor nieuwe gevallen; mpox 42, ebola 14), `flags.rising_recent`, en `national_check: false` als zone- en nationale cijfers een andere basis hebben. De zinnen per luik nemen het oordeel per categorie uit het profiel in plaats van het vast te schrijven. Ebola blijft byte voor byte gelijk.
  - Het profiel is actief: elke reis door de DRC of een buurland krijgt mpox naast ebola, met een eigen kaart en curve. In het blok "Voor <ziekte>:" staan enkel de haltes waar die uitbraak meeweegt.
  - Tests: `test_mpox.py` (de gevulde tabel, de voorbeeldreizen, de woorden in de brief). De golden- en pijplijntests blijven op ebola vastgepind: ze bewaken de ebola-uitvoer en de werking van `advies`, de routering heeft eigen tests.
- **Beslissingen (Steven, 2026-09-25):**
  - Cijfers: "Zones, all cases": per gezondheidszone, vermoede en bevestigde gevallen, uit het WHO-dashboard. Met bevestigde gevallen per provincie waren A en B niet te scheiden geweest: het dashboard geeft per provincie geen datum van het laatste bevestigde geval.
  - Regels: "Confirm as drafted": een zone met een geval in 21 dagen maakt de reis voorwaardelijk, nooit afraden; de rest geen bezwaar; voorwaarden over nauw contact, MVA-BN volgens advies 9900 van de Hoge Gezondheidsraad (zorg- of humanitair werk: aanbevolen; familiebezoek: geval per geval; seksueel risicocontact: altijd), en koorts of uitslag tot 21 dagen na terugkeer.
  - Verouderd na 60 dagen.
  - wanda.be staat niet in de bronnen, zoals beslist in F-005; het advies van de Hoge Gezondheidsraad is recenter.
- **Open:** `rising_recent: 60` is afgeleid, niet bevestigd: de bevestigde drempel was 20 bevestigde gevallen in 14 dagen, de tabel telt vermoede en bevestigde gevallen over 42 dagen. Wie houdt de tabel bij (de webstap stelt voor, de arts aanvaardt)? Een mpox-profiel voor een volgend land wordt een nieuwe map, als een aanvraag erom vraagt.

## F-011 · Routering, meerdere uitbraken per advies, landniveau
- **Gevraagd:** 2026-09-25 — "A lot of the question come for ebola, but we should be able to add in messages from other diseases and countries"; keuze: meerdere uitbraken per advies
- **Status:** klaar (2026-09-25)
- **Plan:** elke halte krijgt een landcode (`places.csv` of Natural Earth op `ADM0_A3`); een uitbraak geldt als een halte in een van haar landen ligt of binnen `radius_km` van een actieve zone. Per uitbraak een risicotabel, kaart en curve; het strengste oordeel wint. Landfeiten (FOD, pretravelregel) in `config/countries.yaml`, los van de CDC-niveaus die per ziekte gelden. Een reis zonder bekende uitbraak krijgt een advies op landniveau zonder kaart; een ziekte in de mail zonder profiel wordt bovenaan gemeld, nooit gelezen als "geen uitbraak".
- **Bronnenregister per land** (2026-09-25): "when identifying new diseases or countries a source database could be made not to repeat the same exercise again and again (for example the shp files of the country, the trusted sources of the government, most important news outlets, and the international bodies...)". Wordt de landlaag van deze feature: een bestand per land in plaats van alleen FOD-links, met grenzen (bron en niveau, de bestanden zelf in de cache), de betrouwbare overheidsbronnen (ministerie, nationaal volksgezondheidsinstituut), de nieuwsmedia die de webstap mag gebruiken, taal, FOD-pagina's en pretravelregel, elk met een `verified`-datum. Daarnaast een korte lijst internationale instanties die voor elk land gelden (WHO, ECDC, CDC, Africa CDC, ITG, Sciensano). De webstap leest het register in plaats van telkens opnieuw te zoeken, en stelt nieuwe bronnen voor die de arts bevestigt, zoals nu al bij de reisadviezen.
- **Commits:** 2fc9734, 4e46d7c, 12a8641
- **Gebouwd (deel 1, landenregister):**
  - `dienstreis/countries/<ISO3>.yaml`: per land de FOD-pagina's en het FOD-advies (land en provincie, met reden), het CDC-niveau per uitbraakprofiel, de pretravelregel, betrouwbare overheidsbronnen en nieuwsmedia, de landgrenzen en de grensmaatregelen per uitbraak, elk met datum. `_international.yaml`: WHO, WHO AFRO, ECDC, US CDC, Africa CDC, ITG, Sciensano, Departement Zorg, Reuters, AP. Het register begint met de DRC en haar negen buurlanden (grenzen berekend uit Natural Earth); van de buurlanden staan enkel naam, grenzen en de notities uit het oude `advisories.yaml` erin, de rest zoekt de webstap op.
  - `dienstreis/countries.py`: lezen, controleren, en een lokale kopie in `~/.config/dienstreis/countries/` die wint zolang ze recenter nagekeken is. Het `advisories.yaml` van 0.2 wordt nog gelezen zolang het recenter is.
  - `risk` haalt FOD en CDC per halte uit het register; een halte buiten het gebied van de cijfers krijgt de grensmaatregelen van haar land en, als het register ze kent, het FOD- en CDC-advies van dat land. De pretravelregel in de mail en de FOD-links in `sources.txt` komen uit de landen van de reis. `config/advisories.yaml` is weg.
  - De webstap krijgt het register, de buurlanden van het uitbraakland op de reis en de internationale instanties; hij kijkt per land de adviezen na, per buurland de grensmaatregelen, en stelt nieuwe bronnen voor. Wat je aanvaardt gaat naar het lokale register, met de datum van vandaag.
  - QA noemt per land wie nog nooit nagekeken is (`advisories_unverified`), in plaats van een enkele datum voor alles.
  - Tests: `test_countries.py`. Goldens: de mailskeletten en bronnenlijsten zijn ongewijzigd; `summary.json` krijgt het id van de uitbraak en de nooit nagekeken landen (Zambia, Congo-Brazzaville); de webprompt is herschreven.
- **Gebouwd (deel 2, routering en meerdere uitbraken):**
  - `route.py`: het land van elke halte (`places.csv`, of voor lat/lon de Natural Earth-contouren: `ISO_A3`, en `ADM0_A3` enkel waar `ISO_A3` -99 is; andersom zou Zuid-Soedan SDS worden in plaats van SSD). Een uitbraak geldt als een halte in een van haar landen of in een buurland ligt; geldt er geen, dan het profiel `geen`.
  - `advies` zet de uitkomst als `outbreaks:` in `stops.yaml` en toont ze op het bevestigingsscherm; na een bewerking volgt ze de haltes, tenzij de gebruiker ze zelf aanpaste of `--uitbraak` gaf. `dienstreis uitbraken` toont de profielen met hun landen en buurlanden.
  - `pipeline.analyse` beoordeelt de reis per uitbraak op haar eigen cijfers, met een eigen kaart en curve. De strengste staat bovenaan in `summary.json` en in de mail; de andere staan in `summary.outbreaks`, in het skelet onder "Voor <ziekte>:" (enkel de haltes waar ze meetellen) en in de mailstap als `andere_uitbraken`. Een overrule noemt de uitbraak die ze opzij zet; een halte kan er een per uitbraak hebben; het eindoordeel blijft een voor alles.
  - Profiel `geen` (`outbreaks/geen/`): een advies op landniveau, zonder cijfers, kaart of curve; elke halte met FOD, CDC en grensmaatregelen van haar land, en een webstap die eerst naar een uitbraak op de bestemming zoekt.
  - De reisschemastap geeft `diseases_mentioned`; een ziekte zonder profiel komt op het bevestigingsscherm, bovenaan de notities, en in de web- en mailstap.
  - Log en archief: kolom en veld `outbreaks`, en `countries` in het archief. Oude logregels en adviezen worden als ebola gelezen; het log krijgt de nieuwe kolom eenmalig, het archief wordt nooit herschreven. `for_trip` zet eerdere adviezen over dezelfde uitbraak eerst; `dienstreis zoek --uitbraak`.
  - Controles: de vensters van elke geldende uitbraak zijn toegelaten getallen; de lengtegrens krijgt 100 woorden per bijkomende uitbraak; een mail die een geldende uitbraak niet noemt, krijgt een notitie.
  - Tests: `test_route.py`, `test_multi.py` (een verzonnen tweede uitbraak op kleine zones, zonder netwerk). Goldens: skeletten, risicotabellen en bronnenlijsten ongewijzigd; `summary.json` krijgt `overall_level` en `attachments`; de drie prompts hebben de nieuwe passages.
- **Proefdraai (2026-09-25):** een verzonnen aanvraag voor een congres in Nairobi met de vraag "is er mpox?", met de echte Claude Code-backend en een tijdelijk register. Nairobi staat niet in `places.csv`: het model gaf coördinaten en de kaart gaf Kenia. Geen profiel geldt, dus landniveau zonder kaart of curve. De webstap vond wat de profielen niet kennen: mpox in Kenia (1 298 bevestigde gevallen, 320 in Nairobi, per 6 september), de vier FOD-pagina's, de screening aan de grenzen en de reisverzekeringsplicht. De notities beginnen met "De aanvraag noemt mpox, maar daarvoor bestaat geen uitbraakprofiel", en de mail noemt het advies "voorlopig". Drie gaten in het register dat hij voor Kenia schreef, meteen hersteld: een nieuw land kreeg geen naam en geen buurlanden (nu uit Natural Earth, `NAME_NL`), het model hing CDC-niveaus en maatregelen aan vrije ziektenamen die geen advies ooit terugvindt (nu onder een bekend profiel-id, met de ziekte in `about`), en de webstap wist niet welke uitbraak-id's golden (nu in de invoer).
- **Beslissingen:**
  - Categorie C voor de hele reis (2026-09-25): "yes, if the advice was not to visit worst stop or reevaluate before going there". Geen bezwaar dus alleen als het luik geschrapt of voor vertrek herbekeken wordt: dat is een voorwaardelijk oordeel. C weegt voortaan als `voorwaardelijk` in het reisoordeel (was `geen_bezwaar` sinds 0.1.0), en de categorietabel in de mailprompt noemt beide mogelijkheden. Geen van de voorbeeldreizen had C als zwaarste halte, dus de goldens veranderen alleen in die ene tabelregel.
  - Geen afstandsstraal (2026-09-25): "No: other: borders are usually closed of screening is done: those countries should be checked". Een uitbraak geldt voor een reis als een halte in een van haar landen ligt of in een buurland daarvan. Voor een halte in een buurland worden elke run de grensmaatregelen nagekeken (gesloten grens, screening, quarantaine voor wie uit het uitbraakland komt) en met datum en bron in het landbestand van het register bewaard. Het register begint met de DRC en haar negen buurlanden.

## F-010 · Generieke kern: ebola wordt het eerste uitbraakprofiel
- **Gevraagd:** 2026-09-25 — "I thought we had made this repo non diseases specific. [...] Can we rebuild this? What would be your advice?"
- **Status:** klaar (2026-09-25)
- **Gebouwd:**
  - `dienstreis/outbreak.py`: een uitbraakprofiel (`OutbreakSpec`) wordt gelezen en gecontroleerd voor het gebruikt wordt; een onbruikbaar profiel wordt geweigerd met alle problemen tegelijk. `fill` zet de passages van het profiel in de prompts waar `{{uitbraak:<naam>}}` staat.
  - `dienstreis/outbreaks/ebola_cod_2026/`: `outbreak.yaml` (databron, landen, vensters 21/42, oordeel per categorie en gewicht in het reisoordeel, eindoordelen, vlagteksten en drempels, voorwaarden, ECDC- en WHO-bron, teksten op kaart en curve), `prompt.md` (acht passages uit `reply.md` en `web.md`, letterlijk) en `zone_overrides.csv` (verhuisd uit `config/`).
  - `data.load` kiest de adapter uit het profiel (enkel `inrb` voorlopig) en geeft de reeksen aan een gedeelde `derive`; ECDC en WHO worden gelezen met de URL en titelpatronen van het profiel; een bron die het profiel niet noemt, telt niet als onbereikbaar. `risk`, `mail`, `figures`, `pipeline`, `geo`, `msg` en `llm` halen uit het profiel wat ze vroeger zelf wisten.
  - Tests: `test_golden.py` (de uitvoer van de vier voorbeeldreizen en de drie prompts, vastgelegd voor de herstructurering) en `test_outbreak.py` (profielen, passages, bronnen).
  - Daarna, apart: twee fouten die de goldens zichtbaar maakten. Zonenamen verloren hun hoofdletters ("Gezondheidszone makiso kisangani", door `.capitalize()`), en de ECDC-datum stond met een Engelse maand in de Nederlandse mail ("data tot 19 September"). De goldens zijn voor precies die zeven regels bijgewerkt; `test_skeleton.py` houdt beide vast.
- **Commits:** da3d465 (goldens), 1d25c9c, 6dbd5dd, 1dc9284
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
