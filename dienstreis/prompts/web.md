# Taak: reisadviezen, grensmaatregelen en recent nieuws nakijken

Je ondersteunt een advies over infectieziekterisico voor een dienstreis {{uitbraak:opdracht_web}} Jouw taak is enkel wat in die data nog niet zit.

`landen` is het bronnenregister voor de landen van het reisschema: per land de FOD-pagina's en het FOD-advies, het CDC-niveau per uitbraak, betrouwbare overheidsbronnen en nieuwsmedia, en de gekende grensmaatregelen, met de datum waarop het register nagekeken is (`verified: null`: nog nooit). `internationaal` zijn de instanties die voor elk land gelden. Begin bij die bronnen en zoek pas verder als ze niet volstaan.

1. Reisadviezen. Controleer voor elk land in `landen` de live pagina's, en in het uitbraakland voor elke provincie in `provincies`:
   - FOD Buitenlandse Zaken (België): algemene veiligheid, laatste update, gezondheid en hygiëne (links in `landen.<land>.fod.pages`). Heeft een land nog geen pagina's, zoek ze op en zet ze onder `sources`. De site weigert soms automatische opvraging; gebruik dan zoekresultaten en zeg dat.
   - CDC Travel Health Notices ({{uitbraak:cdc_niveau}}).
   Vergelijk met `landen`. `fod` is `formeel_afgeraden` of `niet_essentieel_afgeraden`; `fod_reason` zegt waarom (veiligheid versus gezondheid, dat verschil is voor de formulering belangrijk). `region` is de provincie, of `null` voor het advies voor het hele land. Zet in `outbreak` het id uit `uitbraken` waarvoor het CDC-niveau of de grensmaatregel geldt; gaat het over een ziekte zonder profiel, neem dan het eerste id en noem de ziekte in `about`.
2. Grensmaatregelen. Voor elk land in `buurlanden` (landen van het reisschema die grenzen aan een uitbraakland): is de grens met het uitbraakland dicht, is er screening bij in- of uitreis, quarantaine of een inreisverbod voor wie uit het uitbraakland komt? Kijk ook of het uitbraakland zelf exitscreening doet. Vergelijk met `landen.<land>.measures` en geef per land alle maatregelen die nu gelden, met datum en bron, en `changed: true` als ze verschillen van wat er staat.
3. WHO. `who_laatste_don` bevat het laatste Disease Outbreak News over deze uitbraak, gelezen uit de WHO-API. Kijk na of er sindsdien een nieuwer DON of een nieuwer {{uitbraak:who_rapport}} is, en of de WHO een risicobeoordeling of reisadvies formuleert (de WHO raadt zelden reisbeperkingen aan; als ze dat wel doet, is dat op zich nieuws). Zet wat je vindt in `who`.
4. {{uitbraak:nieuws}} Staat er `ziekten_zonder_profiel` in de invoer, zoek dan ook of die ziekte in de landen van het reisschema speelt, en zet wat je vindt in `news`.
5. Bronnen. Een betrouwbare overheidsbron, FOD-pagina of nieuwsmedium dat je gebruikt hebt en dat nog niet in `landen` staat, zet je in `sources`, met waarom het betrouwbaar is. De arts beslist of het in het register komt.
6. Vermeld alleen wat je effectief gezien hebt, met datum en URL. Geen vermoedens als feit.

Antwoord uitsluitend met dit JSON-object:

```json
{
  "advisories": [
    {"country": "COD", "region": "Tshopo", "fod": "formeel_afgeraden", "fod_reason": "veiligheidssituatie", "cdc": 3,
     "outbreak": "…", "changed": false, "source": "URL", "checked_how": "pagina gelezen | zoekresultaat"}
  ],
  "measures": [{"country": "UGA", "outbreak": "…", "about": "…", "text": "…", "date": "JJJJ-MM-DD", "source": "URL", "changed": false}],
  "sources": [{"country": "UGA", "kind": "fod | overheid | nieuws", "name": "…", "url": "…", "why": "…"}],
  "who": {"latest_don": "JJJJ-MM-DD", "newer_than_input": false, "risk_assessment": "…",
          "travel_restrictions_advised": false, "url": "…"},
  "news": [{"date": "JJJJ-MM-DD", "item": "…", "url": "…"}],
  "notes": ["…"]
}
```
