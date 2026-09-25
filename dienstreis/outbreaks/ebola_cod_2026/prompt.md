<!-- Passages of the prompts that are about this outbreak, spliced into dienstreis/prompts/*.md
     where the template says {{uitbraak:<name>}}. Each section runs from its marker to the next;
     trailing blank lines are dropped. Clinical judgement: change deliberately. -->

<!-- uitbraak:opdracht -->
tijdens de ebola-uitbraak in de DRC (Bundibugyo-virus, 2026)

<!-- uitbraak:vertrekpunt -->
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

<!-- uitbraak:valkuilen -->
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

<!-- uitbraak:vaste_voorwaarden -->
Het pretravel consult, de go/no-go met criteria, en het meldpunt bij koorts met temperatuuropvolging tot 21 dagen

<!-- uitbraak:opdracht_web -->
in de DRC tijdens de ebola-uitbraak (Bundibugyo-virus, 2026). De cijfers per gezondheidszone komen uit de INSP-situatierapporten en zijn al verwerkt.

<!-- uitbraak:cdc_niveau -->
niveau per provincie voor ebola

<!-- uitbraak:who_rapport -->
WHO-situatierapport over de DRC

<!-- uitbraak:nieuws -->
Nieuws van de laatste 14 dagen dat nog niet in de data kan zitten: nieuwe provincie of zone, mediagemelde gevallen langs het reisschema, grensmaatregelen, maatregelen op luchthavens, wijzigingen in de 21-dagenregels van derde landen. Enkel betrouwbare bronnen (INSP, WHO, ECDC, CDC, Actualite.cd, Radio Okapi, Reuters, AP).
