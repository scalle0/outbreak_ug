# Taak: reisadviezen en recent nieuws nakijken

Je ondersteunt een advies over infectieziekterisico voor een dienstreis in de DRC tijdens de ebola-uitbraak (Bundibugyo-virus, 2026). De cijfers per gezondheidszone komen uit de INSP-situatierapporten en zijn al verwerkt. Jouw taak is enkel wat in die data nog niet zit.

1. Reisadviezen. Controleer voor elke provincie in `provincies` de live pagina's:
   - FOD Buitenlandse Zaken (België): algemene veiligheid, laatste update, gezondheid en hygiëne (links in `huidige_tabel.sources`). De site weigert soms automatische opvraging; gebruik dan zoekresultaten en zeg dat.
   - CDC Travel Health Notices (niveau per provincie voor ebola).
   Vergelijk met `huidige_tabel`. `fod` is `formeel_afgeraden` of `niet_essentieel_afgeraden`; `fod_reason` zegt waarom (veiligheid versus gezondheid, dat verschil is voor de formulering belangrijk).
2. WHO. `who_laatste_don` bevat het laatste Disease Outbreak News over deze uitbraak, gelezen uit de WHO-API. Kijk na of er sindsdien een nieuwer DON of een nieuwer WHO-situatierapport over de DRC is, en of de WHO een risicobeoordeling of reisadvies formuleert (de WHO raadt zelden reisbeperkingen aan; als ze dat wel doet, is dat op zich nieuws). Zet wat je vindt in `who`.
3. Nieuws van de laatste 14 dagen dat nog niet in de data kan zitten: nieuwe provincie of zone, mediagemelde gevallen langs het reisschema, grensmaatregelen, maatregelen op luchthavens, wijzigingen in de 21-dagenregels van derde landen. Enkel betrouwbare bronnen (INSP, WHO, ECDC, CDC, Actualite.cd, Radio Okapi, Reuters, AP).
4. Vermeld alleen wat je effectief gezien hebt, met datum en URL. Geen vermoedens als feit.

Antwoord uitsluitend met dit JSON-object:

```json
{
  "advisories": [
    {"province": "Tshopo", "fod": "formeel_afgeraden", "fod_reason": "veiligheidssituatie", "cdc": 3,
     "changed": false, "source": "URL", "checked_how": "pagina gelezen | zoekresultaat"}
  ],
  "who": {"latest_don": "JJJJ-MM-DD", "newer_than_input": false, "risk_assessment": "…",
          "travel_restrictions_advised": false, "url": "…"},
  "news": [{"date": "JJJJ-MM-DD", "item": "…", "url": "…"}],
  "notes": ["…"]
}
```
