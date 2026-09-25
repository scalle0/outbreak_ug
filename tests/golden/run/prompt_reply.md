# Taak: antwoordmail aan Team Actueel schrijven

Je schrijft namens Steven Callens (diensthoofd Algemene Inwendige Ziekten en Infectieziekten, UZ Gent; infectioloog) het antwoord aan An van UGent Team Actueel over een dienstreis tijdens de ebola-uitbraak in de DRC (Bundibugyo-virus, 2026). Alle cijfers, zones, categorieën, reisadviezen en figuren zijn deterministisch berekend en staan in de invoer. Jij voegt het oordeel toe en schrijft de mail. Verzin geen cijfers: gebruik enkel wat in de invoer staat, met de datum van elk cijfer.

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

- De go/no-go-beslissing valt vóór vertrek uit België (standaard een week ervoor), ook voor luiken die pas later in de reis komen: eenmaal ter plaatse kan UGent enkel nog adviseren. Een extra controle ter plaatse mag, maar vervangt die beslissing niet. Formuleer expliciete criteria per luik (bv. 42 dagen zonder nieuw geval in de zone en de aangrenzende zones).
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

An moet de mail in een minuut kunnen lezen en er meteen mee verder kunnen. **Richt op 350 woorden, blijf onder 500.** Dat is krap en dat is de bedoeling: het dwingt je te kiezen wat An echt nodig heeft.

Wat je weglaat uit de mail is niet verloren, het hoort in `suggestions`, dat Steven wel leest:
- je redenering, je twijfels, wat je overwogen en verworpen hebt;
- achtergrond over de uitbraak die het oordeel niet verandert;
- wat Steven nog moet verifiëren, en welke toezeggingen hij in de mail doet.

De mail is een antwoord, geen verslag van je denkwerk. De valkuilen hierboven zijn er om te vermijden dat je iets fout schrijft, niet om te tonen dat je eraan gedacht hebt. Schrijf niet wat An al ziet in de kaart en de curve in bijlage. Herhaal een cijfer niet twee keer. Geen samenvattende slotalinea.

## Structuur van de mail

Vertrek van `skelet`. Elke `[[CLAUDE: ...]]`-plaatshouder vervang je of schrap je; de automatische alinea's herformuleer je tot natuurlijk Nederlands, korter mag.

1. **Kernoordeel, een of twee zinnen.** Wat is het antwoord, en wijkt het af van een eerder advies voor dezelfde bestemming?
2. **Per luik twee tot drie zinnen**: oordeel, en het ene of twee cijfers die dat oordeel dragen. Niet alle beschikbare cijfers, alleen wat het oordeel draagt. Een luik zonder bezwaar is een halve zin.
3. **Stand van zaken, twee zinnen**: nationaal totaal met de datum, en de trend over volle weken.
4. **Profiel**: alleen als het het oordeel verandert. Verandert het niets, laat het weg.
5. **Voorwaarden, hoogstens zes, elk een regel.** Alleen wat voor deze reis geldt. Het pretravel consult, de go/no-go met criteria, en het meldpunt bij koorts met temperatuuropvolging tot 21 dagen horen er zo goed als altijd bij; de rest neem je alleen op als dit dossier erom vraagt. Ontbrekende informatie (`aanvraag.missing_info`, `aanvraag.contradictions`) bundel je in een enkele voorwaarde, niet een per item.
6. **Antwoord op elke expliciete vraag van An** (`aanvraag.questions_from_an`): per vraag hoogstens drie zinnen, het antwoord eerst. Zijn er geen vragen, laat dit weg.
7. Bijlagen in een halve zin.

## Uitvoer

Antwoord uitsluitend met dit JSON-object. `suggestions` zijn notities voor Steven, niet voor de mail, en hier mag je wel uitweiden: je redenering, wat je bewust uit de mail gelaten hebt, register, commitment audit (welke toezeggingen doe je in de mail), afwijkingen van eerdere adviezen, onzekerheden, wat hij moet verifiëren, bijlagen. `context_update` is één regel voor zijn contextbestand (datum, reiziger, bestemming, kernoordeel, toezeggingen), zonder medische gegevens.

```json
{
  "reply": "Beste An,\n\n…\n\nMet vriendelijke groet,\nSteven Callens",
  "suggestions": ["…"],
  "review_on": "JJJJ-MM-DD",
  "context_update": "2026-09-22: … "
}
```


# Invoer

<vandaag>
VANDAAG
</vandaag>

<skelet>
Beste An,

[[CLAUDE: kernoordeel in een zin; vergelijk met eerdere aanvragen voor dezelfde bestemming. Regel-uitkomst: niet goedkeuren in huidige vorm (minstens een luik af te raden).]]

Mijn beoordeling per luik:

1. Kinshasa (28 november tot 5 december): geen bezwaar. Geen bevestigde gevallen in gezondheidszone Barumbu of in de provincie Kinshasa; de dichtstbijzijnde zone met recente gevallen (Bulu) ligt op circa 870 km; valt Kinshasa onder het algemene FOD-advies (niet-essentiële reizen naar de DRC afgeraden); de CDC hanteert niveau 2.
2. Kisangani (6 december tot 13 december): af te raden. Gezondheidszone Makiso Kisangani telt 20 bevestigde gevallen (9 overlijdens), waarvan 10 in de laatste 14 dagen; raadt de FOD alle reizen naar Tshopo formeel af (veiligheidssituatie); de CDC hanteert niveau 3.

Stand van zaken (INSP): 7 672 bevestigde gevallen en 3 699 overlijdens (CFR 48 procent). Nieuwe gevallen per volledige week, laatste vier weken: 569, 586, 586, 572.

[[CLAUDE: profiel en context van Reiziger T: verblijf, duur, aard van het werk, wat het dossier over de uitbraak zegt. Enkel wat het oordeel verandert.]]

Voorwaarden:
1. Pretravel consult (gele koorts verplicht, malariaprofylaxe) en registratie via Travellers Online.
2. Geen reizen naar of transit door getroffen gezondheidszones; geen contact met zieken of overledenen, geen begrafenissen, geen bushmeat.
3. [[CLAUDE: go/no-go-datum en criteria, of 'korte check een week voor vertrek']]
4. Temperatuur opvolgen tot 21 dagen na terugkeer; bij koorts eerst telefonisch contact met het ITG of onze dienst.

[[CLAUDE: antwoord op elke expliciete vraag van An]]

In bijlage de kaart met het reisschema en de bijgewerkte epidemiecurve.

Met vriendelijke groet,
Steven Callens
</skelet>

<risico_per_stop>
[
 {
  "place": "Kinshasa",
  "start": "2026-11-28",
  "end": "2026-12-05",
  "nights": 7,
  "zone": "Barumbu",
  "province": "Kinshasa",
  "category": "F",
  "verdict": "geen bezwaar",
  "label": "niet getroffen",
  "cases": 0,
  "deaths": 0,
  "new14": 0,
  "days_since_last": null,
  "neighbours_active": [],
  "nearest_active": {
   "zone": "Bulu",
   "province": "Sud-Ubangi",
   "km": 871,
   "cases": 1,
   "days_since_last": 9
  },
  "fod": "niet_essentieel_afgeraden",
  "fod_reason": "algemene volatiliteit",
  "cdc": 2,
  "flags": [],
  "lodging": null,
  "transit_only": false
 },
 {
  "place": "Kisangani",
  "start": "2026-12-06",
  "end": "2026-12-13",
  "nights": 7,
  "zone": "Makiso Kisangani",
  "province": "Tshopo",
  "category": "A",
  "verdict": "afraden",
  "label": "getroffen zone, recent geval (<= 21 d)",
  "cases": 20,
  "deaths": 9,
  "new14": 10,
  "days_since_last": 0.0,
  "neighbours_active": [
   {
    "zone": "Kabondo",
    "province": "Tshopo",
    "cases": 5,
    "new14": 1,
    "days_since_last": 0
   },
   {
    "zone": "Mangobo",
    "province": "Tshopo",
    "cases": 4,
    "new14": 1,
    "days_since_last": 6
   }
  ],
  "nearest_active": {
   "zone": "Makiso Kisangani",
   "province": "Tshopo",
   "km": 0,
   "cases": 20,
   "days_since_last": 0
  },
  "fod": "formeel_afgeraden",
  "fod_reason": "veiligheidssituatie",
  "cdc": 3,
  "flags": [
   "FOD raadt provincie formeel af (veiligheidssituatie)",
   "CDC niveau 3",
   "overnachting(en) in getroffen gebied: 7",
   "stijgend in de zone: 10 nieuwe gevallen in 14 dagen"
  ],
  "lodging": null,
  "transit_only": false
 }
]
</risico_per_stop>

<regel_oordeel>
niet goedkeuren in huidige vorm (minstens een luik af te raden)
</regel_oordeel>

<epi>
{
 "path": "epicurve_20260919.png",
 "weekly_cases_last4_full_weeks": {
  "23-08": 569,
  "30-08": 586,
  "06-09": 586,
  "13-09": 572
 },
 "last_total": 7672,
 "last_deaths": 3699,
 "cfr": 48.2
}
</epi>

<qa>
{
 "zone_sum_matches_national": true,
 "ecdc_matches": null,
 "who": {
  "ok": false,
  "reason": "asof run"
 },
 "who_days_old": null,
 "sources_unreachable": [],
 "unmatched_zone_names": [],
 "advisories_verified_days_ago": X,
 "advisories_stale": false,
 "advisories_unverified": [],
 "advisories_source": "X",
 "map_label_overlaps": X,
 "map_labels_clipped": X,
 "skeleton_issues": [
  "4 open [[CLAUDE]]-plaatshouder(s)"
 ],
 "overrules_count": 0
}
</qa>

<ecdc>
{
 "ok": false,
 "reason": "asof run"
}
</ecdc>

<aanvraag>
{
 "traveller": "Reiziger T",
 "note": "veldwerk",
 "nationality": null,
 "profile": {
  "lodging": "hotel",
  "healthcare_work": false
 },
 "work_nature": null,
 "transport": null,
 "questions_from_an": [
  "Geldt de 21-dagenregel?"
 ],
 "contradictions": [],
 "missing_info": [
  "vervoer"
 ],
 "review_on": "2026-11-20"
}
</aanvraag>

<aanvraag_tekst>
Beste Steven,

Nieuwe aanvraag:
28/11 - 5/12 Kinshasa
6/12-13/12 Kisangani - Tshopo

Graag jouw advies. Geldt de 21-dagen regel?

An

Van: Iemand
REISINFO
Bestemming: Kisangani
Accommodatie: hotel

</aanvraag_tekst>

<context>
- 2026-09-10: Kisangani-luik Hubeau afgeraden

</context>

<geschiedenis>
[]
</geschiedenis>

<eerdere_adviezen>
[]
</eerdere_adviezen>

<overrules>
[]
</overrules>

<regel_oordeel_zonder_overrule>
niet goedkeuren in huidige vorm (minstens een luik af te raden)
</regel_oordeel_zonder_overrule>

<web>
{
 "advisories": [],
 "news": [
  {
   "date": "2026-09-18",
   "item": "nieuws",
   "url": "https://example.org"
  }
 ],
 "who": {
  "latest_don": "2026-09-10"
 }
}
</web>
