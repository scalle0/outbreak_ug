# Taak: reisschema uit een dienstreisaanvraag halen

Je helpt Steven Callens (diensthoofd Algemene Inwendige Ziekten en Infectieziekten, UZ Gent), die UGent Team Actueel (An, actueel@ugent.be) adviseert over infectieziekterisico bij dienstreizen. Hieronder staat een aanvraag: meestal een door An doorgestuurde mail met haar samenvatting bovenaan en het reisformulier van de reiziger eronder, soms met een risicoanalyse als bijlage.

Haal het reisschema eruit. Je beoordeelt hier nog geen risico.

Regels:
- Een stop per verblijfplaats, in chronologische volgorde, met datums in ISO (JJJJ-MM-DD). `from` is de dag van aankomst, `to` de dag van vertrek van die plaats, ook als de reiziger die dag meteen doorreist. Twee opeenvolgende stops delen dus die datum: Sakania `to: 2026-10-10` en Lubumbashi `from: 2026-10-10`. Zet niet de laatste overnachting als `to`: het aantal nachten wordt berekend als `to` min `from`, en dat aantal telt mee in de beoordeling.
- Neem transitpunten op (luchthaven, rivierhaven, grensovergang) met `transit_only: true` als de reiziger er enkel passeert.
- Gebruik bij voorkeur plaatsnamen uit `bekende_plaatsen`. Voor een onbekende plaats geef je `lat` en `lon` (decimaal) en zet je de plaats in `missing_info` als je de coördinaten niet zeker kent.
- Accommodatie: `lodging: family` als de reiziger bij familie of kennissen verblijft, anders `hotel`. Zet dit per stop als het verschilt, en in `profile` wat voor het grootste deel van de reis geldt.
- `healthcare_work: true` enkel als de reiziger in een zorginstelling of labo werkt of met patiënten of stalen in contact komt.
- Tegenstrijdigheden (bv. een einddatum in An's samenvatting die afwijkt van het formulier, 3/1/27 versus 2027-03-01) zet je in `contradictions`. Kies in het schema de lezing die het best past bij het formulier van de reiziger zelf en zeg welke je koos.
- `questions_from_an`: elke expliciete vraag of verzoek van An, letterlijk samengevat.
- `missing_info`: wat nodig is voor een goed advies en ontbreekt (vervoer tussen de stops, aard van het werk, verzekering, ebolaplan).
- `review_on`: de go/no-go-datum, een week voor vertrek uit België. Eenmaal de reiziger vertrokken is, kan UGent een luik nog moeilijk tegenhouden; latere controles ter plaatse komen hoogstens bovenop deze datum.
- `traveller`: naam zoals in de aanvraag. `note`: aard van de reis in een paar woorden (veldwerk, congres, labo).

Antwoord uitsluitend met dit JSON-object:

```json
{
  "traveller": "Naam",
  "note": "veldwerk, verblijf bij familie",
  "nationality": "…",
  "profile": {"lodging": "hotel|family", "healthcare_work": false},
  "sent_to_ugent_address": false,
  "review_on": "JJJJ-MM-DD",
  "stops": [
    {"place": "Kinshasa", "from": "JJJJ-MM-DD", "to": "JJJJ-MM-DD"},
    {"place": "Onbekende plaats", "lat": 1.23, "lon": 25.6, "from": "…", "to": "…", "lodging": "family", "transit_only": false}
  ],
  "work_nature": "…",
  "transport": "…",
  "questions_from_an": ["…"],
  "contradictions": ["…"],
  "missing_info": ["…"]
}
```
