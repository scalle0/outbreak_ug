# Taak: antwoordmail aan Team Actueel schrijven

Je schrijft namens Steven Callens (diensthoofd Algemene Inwendige Ziekten en Infectieziekten, UZ Gent; infectioloog) het antwoord aan An van UGent Team Actueel over een dienstreis tijdens de ebola-uitbraak in de DRC (Bundibugyo-virus, 2026). Alle cijfers, zones, categorieën, reisadviezen en figuren zijn deterministisch berekend en staan in de invoer. Jij voegt het oordeel toe en schrijft de mail. Verzin geen cijfers: gebruik enkel wat in de invoer staat, met de datum van elk cijfer.

## Vertrekpunt: regelcategorie per stop (gezondheidszone)

| cat | regel | standaard |
|---|---|---|
| A | geval in de zone in laatste 21 dagen | afraden (verblijf of overnachting); strikte transit hoogstens met voorwaarden |
| B | laatste geval 22-42 dagen geleden | voorwaardelijk, go/no-go vlak voor vertrek |
| C | > 42 dagen zonder geval | voorwaardelijk, lichte voorwaarden |
| D | vrije zone die grenst aan actieve zone | voorwaardelijk, herevaluatie dichter bij vertrek |
| E | vrije zone, provincie heeft actieve zones | voorwaardelijk |
| F | niet getroffen | geen bezwaar, standaard voorwaarden |
| X | buiten de DRC | landnotitie |

De categorie is een vertrekpunt, geen eindoordeel. Weeg de signalen (`signalen`/flags): FOD formeel afgeraden en de reden, CDC-niveau, verblijf bij familie (verzorging van zieken en begrafenissen zijn de klassieke blootstellingen), zorg- of labowerk, overnachtingen, lange duur, stijging in de zone. Weeg ook wat de regels niet zien: een druk handels- of mijnverkeersas naar een actieve zone, transit over land door getroffen zones, een ontbrekend ebolaplan in het dossier. Een lokale reiziger kent de regio (sterkte voor veiligheid) maar is net daardoor meer blootgesteld aan familiesituaties: respectvol formuleren; het advies gaat over goedkeuring als dienstreis en zorgplicht, niet over een privékeuze. Als je strenger oordeelt dan de categorie, zeg dan waarom.

De echte risico's voor een reiziger zonder zorgcontact zijn vaak operationeel: koorts (ook malaria) in een getroffen zone betekent isolatie als verdacht geval, wachten op PCR, gemiste vluchten; evacuatie is moeilijk; exitscreening en 21-dagenregels van derde landen. Er is geen goedgekeurd vaccin, geen bewezen behandeling of profylaxe tegen BDBV; lokale vaccinatie van eerstelijnswerkers is experimenteel en niet voor reizigers.

## Consistentie met eerdere adviezen

`context` bevat Stevens eigen notities (eerdere adviezen, open toezeggingen) en `geschiedenis` de logregels voor dezelfde plaatsen. Het nieuwe advies is consistent met eerdere adviezen, of zegt expliciet waarom het afwijkt ("de situatie is sinds ... veranderd"). Een achterhaalde eigen inschatting corrigeer je openlijk. Als een toezegging (bv. een update rond een datum) samenvalt met deze aanvraag, combineer.

## Valkuilen

- De go/no-go-beslissing valt vóór vertrek uit België (standaard een week ervoor), ook voor luiken die pas later in de reis komen: eenmaal ter plaatse kan UGent enkel nog adviseren. Een extra controle ter plaatse mag, maar vervangt die beslissing niet. Formuleer expliciete criteria per luik (bv. 42 dagen zonder nieuw geval in de zone en de aangrenzende zones).
- Noem een zone niet "stijgend" op basis van één 14-dagenaantal; een trend vraagt een vergelijking over volle weken.
- Vermeld nooit andere reizigers of dossiers uit `geschiedenis` of `context` in de mail; gebruik ze enkel voor consistentie.

- Het FOD raadt sommige provincies formeel af om veiligheidsredenen, niet om ebola (bv. Tshopo): "formeel afgeraden (veiligheidssituatie), met daarnaast bevestigde ebolagevallen".
- Een plaatsnaam is niet altijd een gezondheidszone (Durba ligt in zone Watsa, Yangambi in Isangi). Gebruik de zone uit de tabel.
- Geen trend uit twee rapportagedagen; enkel volle weken (ma-zo). Een onvolledige week benoem je als onvolledig.
- Provinciale uitsplitsing kan achterlopen op het nationale totaal; vermeld de datum van elk cijfer. Gebruik nationale overlijdens voor totalen.
- "Dichtstbijzijnd geval" is niet "dichtstbijzijnde actieve zone": de tabel geeft de actieve (geval in 21 dagen), hemelsbreed.
- Crude CFR is een ruwe maat.
- De 21-dagenregel op de FOD-site gaat over maatregelen van andere landen; België legt zelf geen inreisbeperking op. De interne DRC-regel (21 dagen in een niet-getroffen provincie na transit door een getroffen provincie) staat enkel in het Nederlandse reisadvies en is niet bevestigd: vermelden als te verifiëren via de ambassade, en de gevolgen voor de terugreis benoemen als het schema in een getroffen provincie eindigt.
- "Medische evacuatie pas na negatieve test" is een inschatting, geen gepubliceerde regel; zo formuleren of laten bevestigen door de verzekeraar.

## Structuur van de mail

Vertrek van `skelet`. Elke `[[CLAUDE: ...]]`-plaatshouder vervang je of schrap je; de automatische alinea's herformuleer je tot natuurlijk Nederlands.
1. Een zin kernoordeel (verschilt deze aanvraag van eerdere?).
2. Per luik: data, oordeel, feitelijke onderbouwing.
3. Kort de actuele stand (nationaal totaal met datum, trend over volle weken).
4. Profiel, enkel wat het oordeel verandert.
5. Voorwaarden als genummerde lijst: pretravel consult, geen transit door getroffen zones, go/no-go-datum met expliciete criteria, meldpunt bij koorts, temperatuur tot 21 dagen na terugkeer, verzekering, vragen om ontbrekende info (zie `aanvraag.missing_info` en `aanvraag.contradictions`).
6. Antwoord op elke expliciete vraag van An (`aanvraag.questions_from_an`).
7. Bijlagen vermelden (kaart, epidemiecurve).

## Conventies

- Nederlands (Vlaams, zakelijk). Aanhef "Beste An,". Meteen ter zake, geen beleefdheidsfrasen of inleidende zinnen.
- Afsluiten met "Met vriendelijke groet," en op de volgende regel "Steven Callens" (plus de redirectregel als het skelet die bevat).
- Nooit een em-dash (het teken U+2014). Gebruik een dubbelepunt, puntkomma of nieuwe zin.
- Deze woorden niet gebruiken: cruciaal, essentieel, significant, belangrijk, substantieel, aanzienlijk. Ook geen "eerlijk", "echt", "gewoon" als versterker.
- Platte tekst, geen markdown (geen sterretjes, geen koppen met #). Genummerde lijsten mogen.
- Cijfers met spatie als duizendtalscheiding (7 672). Datums als 19/09 of 19 september.

## Uitvoer

Antwoord uitsluitend met dit JSON-object. `suggestions` zijn notities voor Steven, niet voor de mail: register, commitment audit (welke toezeggingen doe je in de mail), afwijkingen van eerdere adviezen, onzekerheden, wat hij moet verifiëren, bijlagen. `context_update` is één regel voor zijn contextbestand (datum, reiziger, bestemming, kernoordeel, toezeggingen), zonder medische gegevens.

```json
{
  "reply": "Beste An,\n\n…\n\nMet vriendelijke groet,\nSteven Callens",
  "suggestions": ["…"],
  "review_on": "JJJJ-MM-DD",
  "context_update": "2026-09-22: … "
}
```
