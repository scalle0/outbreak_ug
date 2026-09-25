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


# Invoer

<vandaag>
VANDAAG
</vandaag>

<provincies>
[
 "Kinshasa",
 "Tshopo"
]
</provincies>

<huidige_tabel>
{
 "verified": "2099-01-01",
 "sources": {
  "fod": "https://diplomatie.belgium.be/nl/landen/congo-democratische-republiek/reizen-naar-de-democratische-republiek-congo-reisadvies/algemene-veiligheid-de-democratische-republiek-congo",
  "fod_update": "https://diplomatie.belgium.be/nl/landen/congo-democratische-republiek/reizen-naar-de-democratische-republiek-congo-reisadvies/laatste-update-de-democratische-republiek-congo",
  "cdc": "https://wwwnc.cdc.gov/travel/notices"
 },
 "default": {
  "fod": "niet_essentieel_afgeraden",
  "fod_reason": "algemene volatiliteit",
  "cdc": 2
 },
 "provinces": {
  "Ituri": {
   "fod": "formeel_afgeraden",
   "fod_reason": "veiligheidssituatie",
   "cdc": 4
  },
  "Nord-Kivu": {
   "fod": "formeel_afgeraden",
   "fod_reason": "gewapend conflict",
   "cdc": 4
  },
  "Sud-Kivu": {
   "fod": "formeel_afgeraden",
   "fod_reason": "gewapend conflict",
   "cdc": 2
  },
  "Tshopo": {
   "fod": "formeel_afgeraden",
   "fod_reason": "veiligheidssituatie",
   "cdc": 3
  },
  "Tanganyika": {
   "fod": "formeel_afgeraden",
   "fod_reason": "veiligheidssituatie",
   "cdc": 2
  },
  "Maniema": {
   "fod": "formeel_afgeraden",
   "fod_reason": "veiligheidssituatie",
   "cdc": 2
  },
  "Haut-Uele": {
   "fod": "niet_essentieel_afgeraden",
   "fod_reason": "algemene volatiliteit",
   "cdc": 3
  }
 },
 "countries": {
  "UGA": {
   "note": "Uganda outbreak declared over (WHO 25 Aug 2026); DRC border closed"
  },
  "ZMB": {
   "note": "no cases reported"
  },
  "COG": {
   "note": "no cases reported"
  }
 }
}
</huidige_tabel>

<who_laatste_don>
{
 "ok": false,
 "reason": "asof run"
}
</who_laatste_don>

<reisschema>
     stop        van        tot  nachten             zone provincie cat      oordeel  gevallen  nieuw14d  dagen_sinds_laatste            actieve_buren     dichtstbij_actief                       FOD  CDC regel_cat
 Kinshasa 2026-11-28 2026-12-05        7          Barumbu  Kinshasa   F geen bezwaar         0         0                  NaN                        -           Bulu 871 km niet_essentieel_afgeraden    2         -
Kisangani 2026-12-06 2026-12-13        7 Makiso Kisangani    Tshopo   A      afraden        20        10                  0.0 Kabondo (5), Mangobo (4) Makiso Kisangani 0 km         formeel_afgeraden    3         -
</reisschema>
