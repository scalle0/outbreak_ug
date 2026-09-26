# Taak: een ziektefiche en de sleuteldocumenten opstellen

Je stelt voor Steven Callens (diensthoofd Algemene Inwendige Ziekten en Infectieziekten, UZ Gent; infectioloog) de vaste ziektefiche op voor een uitbraak {{uitbraak:opdracht}}. Hij gebruikt ze als achtergrond bij zijn adviezen over dienstreizen en casussen voor UGent: wat hij moet weten over de ziekte, niet over een bepaalde reiziger. De fiche blijft een concept tot hij ze nagelezen en bevestigd heeft; pas dan steunen zijn mails erop.

`uitbraak` beschrijft het profiel (naam, landen, wat de cijfers tellen). `secties` zijn de vaste secties van de fiche, in die volgorde. `bestaande_fiche` en `bestaande_documenten` zijn wat er al is, of leeg: behoud wat klopt en zeg in `notities` wat je veranderd hebt en waarom. `internationaal` zijn de instanties die voor elk land gelden; een bron uit `internationaal.excluded` gebruik je niet.

## Bronnen

Zoek de sleuteldocumenten per niveau en open ze zelf:
- `be`: Sciensano (procedures, meldingsplicht), Hoge Gezondheidsraad (vaccinatie), ITG (reisgeneeskunde), Departement Zorg (Vlaamse infectieziektebestrijding);
- `eu`: ECDC (risicobeoordeling, richtlijnen voor reizigers en contacten);
- `who`: WHO (Disease Outbreak News, richtlijnen voor klinische zorg, isolatie en vaccinatie);
- `us`: CDC (klinische informatie, reizigers, contacten).

Per document: `id` (kort, kleine letters en koppeltekens, bv. `hgr-9900-mpox-vaccinatie`), `org`, `title`, `date` (van het document zelf, JJJJ-MM-DD), `url`, en `key`: de kernboodschap voor deze adviezen in een zin. Vier tot acht documenten per niveau is genoeg; kies wat een arts die reizigers adviseert echt nodig heeft.

## De fiche

Per sectie korte alinea's of een lijst, in het Nederlands, zakelijk, voor een arts. Elke uitspraak verwijst naar het document waarop ze steunt, met het id tussen vierkante haken: "Incubatie 2 tot 21 dagen [who-ebola-factsheet]." Een uitspraak zonder document komt er niet in.

- **Verwekker**: virus of bacterie, stam of clade, wat daarover bekend is.
- **Overdracht**: hoe, wanneer iemand besmettelijk is, wat geen overdracht geeft.
- **Incubatie**: bereik en mediaan, en welk venster de richtlijnen gebruiken voor opvolging.
- **Klinisch beeld**: vroege en late symptomen, wat het onderscheidt van malaria of andere koorts bij een reiziger.
- **Ernst en letaliteit**: CFR met de bron en de periode, risicogroepen. Geen cijfer zonder datum.
- **Diagnose**: test, staal, waar in België (referentielabo), wanneer een test betrouwbaar is.
- **Behandeling**: ondersteunend, specifieke middelen met hun status (goedgekeurd, onderzoek, compassionate use).
- **Vaccinatie en PEP**: welk vaccin, voor wie, beschikbaarheid in België, post-expositieprofylaxe.
- **Preventie voor reizigers**: wat een reiziger zonder zorgcontact moet doen en laten.
- **Isolatie en vrijgave**: duur en criteria volgens de richtlijnen, voor een patiënt en voor contacten.
- **Terugkeer naar België**: melding, contactopvolging, wie wat regelt, thuisisolatie.

Staat iets niet in de bronnen, schrijf dat dan ("geen goedgekeurd vaccin tegen deze stam [id]"), in plaats van een algemene uitspraak. Verzin geen cijfers, geen namen van producten en geen datums. Geen em-dash, geen versterkers als cruciaal, essentieel, significant, belangrijk, substantieel, aanzienlijk.

## Uitvoer

Antwoord uitsluitend met dit JSON-object. `secties` heeft de titels uit `secties` als sleutels, met Markdown als tekst (lijsten mogen, geen koppen).

```json
{
  "secties": {"Verwekker": "…", "Overdracht": "…"},
  "documenten": {
    "be": [{"id": "…", "org": "…", "title": "…", "date": "JJJJ-MM-DD", "url": "…", "key": "…"}],
    "eu": [],
    "who": [],
    "us": []
  },
  "notities": ["…"]
}
```
