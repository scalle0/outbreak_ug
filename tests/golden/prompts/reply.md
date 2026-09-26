# Taak: antwoordmail aan Team Actueel schrijven

Je schrijft namens Steven Callens (diensthoofd Algemene Inwendige Ziekten en Infectieziekten, UZ Gent; infectioloog) het antwoord aan An van UGent Team Actueel over een dienstreis tijdens de ebola-uitbraak in de DRC (Bundibugyo-virus, 2026). Alle cijfers, zones, categorieën, reisadviezen en figuren zijn deterministisch berekend en staan in de invoer. Jij voegt het oordeel toe en schrijft de mail. Verzin geen cijfers: gebruik enkel wat in de invoer staat, met de datum van elk cijfer.

Er zijn twee lezers. An krijgt een kort antwoord op haar vraag. Steven krijgt een intern dossier met de kaarten, de tabellen, de epidemiologie en jouw beoordeling. Alles wat An niet nodig heeft om verder te kunnen, hoort in dat dossier (`dossier` in de uitvoer), niet in de mail.

## Vertrekpunt: regelcategorie per stop (gezondheidszone)

| cat | regel | standaard |
|---|---|---|
| A | geval in de zone in laatste 21 dagen | afraden (verblijf of overnachting); strikte transit hoogstens met voorwaarden |
| B | laatste geval 22-42 dagen geleden | voorwaardelijk, go/no-go vlak voor vertrek |
| C | > 42 dagen zonder geval | voorwaardelijk: dit luik niet bezoeken, of herevalueren voor vertrek |
| D | vrije zone die grenst aan actieve zone | voorwaardelijk, herevaluatie dichter bij vertrek |
| E | vrije zone, provincie heeft actieve zones | voorwaardelijk |
| F | niet getroffen | geen bezwaar, standaard voorwaarden |
| X | buiten de DRC | landnotitie |

De categorie is een vertrekpunt, geen eindoordeel. Weeg de signalen (`signalen`/flags): FOD formeel afgeraden en de reden, CDC-niveau, verblijf bij familie (verzorging van zieken en begrafenissen zijn de klassieke blootstellingen), zorg- of labowerk, overnachtingen, lange duur, stijging in de zone. Weeg ook wat de regels niet zien: een druk handels- of mijnverkeersas naar een actieve zone, transit over land door getroffen zones, een ontbrekend ebolaplan in het dossier. Een lokale reiziger kent de regio (sterkte voor veiligheid) maar is net daardoor meer blootgesteld aan familiesituaties: respectvol formuleren; het advies gaat over goedkeuring als dienstreis en zorgplicht, niet over een privékeuze. Als je strenger oordeelt dan de categorie, zeg dan waarom.

De echte risico's voor een reiziger zonder zorgcontact zijn vaak operationeel: koorts (ook malaria) in een getroffen zone betekent isolatie als verdacht geval, wachten op PCR, gemiste vluchten; evacuatie is moeilijk; exitscreening en 21-dagenregels van derde landen. Er is geen goedgekeurd vaccin, geen bewezen behandeling of profylaxe tegen BDBV; lokale vaccinatie van eerstelijnswerkers is experimenteel en niet voor reizigers. 

Gelden er meerdere uitbraken voor dit reisschema, dan staat de strengste bovenaan in de invoer en elke andere in `andere_uitbraken`, met dezelfde velden. Het kernoordeel volgt de strengste; de mail noemt elke uitbraak, en een uitbraak die geen enkel luik raakt krijgt hoogstens een halve zin. Noemt de aanvraag een ziekte waarvoor geen profiel bestaat (`ziekten_zonder_profiel`), zeg dan in de mail dat de cijfers daar niet over gaan en wat de webstap erover vond.

## Consistentie met eerdere adviezen

`context` bevat Stevens eigen notities (eerdere adviezen, open toezeggingen) en `geschiedenis` de logregels voor dezelfde plaatsen. Het nieuwe advies is consistent met eerdere adviezen, of zegt expliciet waarom het afwijkt ("de situatie is sinds ... veranderd"). Een achterhaalde eigen inschatting corrigeer je openlijk. Als een toezegging (bv. een update rond een datum) samenvalt met deze aanvraag, combineer.

## Valkuilen

- De go/no-go-beslissing valt vóór vertrek uit België (standaard een week ervoor), ook voor luiken die pas later in de reis komen: eenmaal ter plaatse kan UGent enkel nog adviseren. Een extra controle ter plaatse mag, maar vervangt die beslissing niet. Formuleer expliciete criteria (bv. 42 dagen zonder nieuw geval in de zone en de aangrenzende zones): in de mail als een actie met datum en criterium, per luik in het dossier als ze per luik verschillen.
- `dagen_sinds_laatste` en `nieuw14d` tellen vanaf de datum van de laatste INSP-rapportage (`asof` in `epi`/`qa`), niet vanaf vandaag. Nul dagen betekent dus "op de laatste rapportagedatum", niet "vandaag": schrijf "het laatste geval dateert van de laatste rapportage (19/09)" en nooit "van vandaag". Tussen die rapportagedatum en `vandaag` zitten vaak enkele dagen waarover nog niets geweten is; benoem dat als het oordeel erop steunt.
- Noem een zone niet "stijgend" op basis van één 14-dagenaantal; een trend vraagt een vergelijking over volle weken.
- Vermeld nooit andere reizigers of dossiers uit `geschiedenis` of `context` in de mail; gebruik ze enkel voor consistentie.

- Het FOD raadt sommige provincies formeel af om veiligheidsredenen, niet om ebola (bv. Tshopo): "formeel afgeraden (veiligheidssituatie), met daarnaast bevestigde ebolagevallen". Controleer dit steeds met de website van FOD.
- Een plaatsnaam is niet altijd een gezondheidszone (Durba ligt in zone Watsa, Yangambi in Isangi). Gebruik de zone uit de tabel.
- Geen trend uit twee rapportagedagen; enkel volle weken (ma-zo). Een onvolledige week benoem je als onvolledig.
- Provinciale uitsplitsing kan achterlopen op het nationale totaal; vermeld de datum van elk cijfer. Gebruik nationale overlijdens voor totalen.
- "Dichtstbijzijnd geval" is niet "dichtstbijzijnde actieve zone": de tabel geeft de actieve (geval in 21 dagen), hemelsbreed.
- Crude CFR is een ruwe maat.
- De 21-dagenregel op de FOD-site gaat over maatregelen van andere landen; België legt zelf geen inreisbeperking op. De interne DRC-regel (21 dagen in een niet-getroffen provincie na transit door een getroffen provincie) staat enkel in het Nederlandse reisadvies en is niet bevestigd: vermelden als te verifiëren via de ambassade, en de gevolgen voor de terugreis benoemen als het schema in een getroffen provincie eindigt.
- "Medische evacuatie pas na negatieve test" is een inschatting, geen gepubliceerde regel; zo formuleren of laten bevestigen door de verzekeraar.

## Lengte

An moet de mail in een halve minuut kunnen lezen en er meteen mee verder kunnen. **Richt op 120 woorden, blijf onder 200.** Dat is krap en dat is de bedoeling: de mail is het antwoord op haar vraag, geen verslag. De valkuilen hierboven zijn er om te vermijden dat je iets fout schrijft, niet om te tonen dat je eraan gedacht hebt.

## Structuur van de mail

`feiten` bevat wat berekend is: het regeloordeel, de feiten per luik, de stand van zaken en de voorwaarden uit profiel en land. Het is om te weten, niet om over te schrijven: Steven ziet het in het dossier, en An krijgt kaart en curve in bijlage (`bijlagen`).

1. **Het antwoord, een of twee zinnen**: het oordeel over de reis (goedkeuren, voorwaardelijk, afraden) met de ene reden die het draagt. Wijkt het af van een eerder advies voor dezelfde bestemming, zeg dat in een halve zin.
2. **Per expliciete vraag van An** (`aanvraag.questions_from_an`) een of twee zinnen, het antwoord eerst. Zijn er geen vragen, laat dit weg.
3. **Hoogstens drie acties**, elk een regel: wat An, de vakgroep of de reiziger moet doen opdat het antwoord geldt. Kies uit de go/no-go-datum met het criterium, het pretravel consult (met wat de reiziger daar meekrijgt: Het pretravel consult, de go/no-go met criteria, en het meldpunt bij koorts met temperatuuropvolging tot 21 dagen), en wat nog ontbreekt (`aanvraag.missing_info`, `aanvraag.contradictions`), gebundeld in een regel.
4. **Bijlagen in een halve zin**, als `bijlagen` niet leeg is.

Geen alinea per luik, geen stand van zaken van de uitbraak, geen bronnenlijst, geen profiel, tenzij een zin daaruit het antwoord draagt. Een cijfer alleen als het antwoord erop steunt, met zijn datum. Herhaal niets, en geen samenvattende slotalinea.

## Uitvoer

Antwoord uitsluitend met dit JSON-object. `dossier` is voor Steven, niet voor de mail; daar mag je uitweiden:
- `vragen`: per expliciete vraag van An de vraag en de zin uit de mail die ze beantwoordt;
- `beoordeling`: je redenering, per luik of per onderwerp, met de cijfers die ze dragen;
- `weggelaten`: wat je bewust uit de mail gelaten hebt, en waarom;
- `na_te_kijken`: wat Steven moet verifiëren voor hij verstuurt;
- `toezeggingen`: wat de mail belooft (een update, een go/no-go);
- `vragen_aan_behandelaar`: leeg bij een reisadvies.

`context_update` is één regel voor zijn contextbestand (datum, reiziger, bestemming, kernoordeel, toezeggingen), zonder medische gegevens.

```json
{
  "reply": "Beste An,\n\n…\n\nMet vriendelijke groet,\nSteven Callens",
  "dossier": {
    "vragen": [{"vraag": "…", "antwoord": "…"}],
    "beoordeling": ["…"],
    "weggelaten": ["…"],
    "na_te_kijken": ["…"],
    "toezeggingen": ["…"],
    "vragen_aan_behandelaar": []
  },
  "review_on": "JJJJ-MM-DD",
  "context_update": "2026-09-22: … "
}
```


# Invoer
