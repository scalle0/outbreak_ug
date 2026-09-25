# Taak: reisadviezen, grensmaatregelen en recent nieuws nakijken

Je ondersteunt een advies over infectieziekterisico voor een dienstreis in de DRC tijdens de ebola-uitbraak (Bundibugyo-virus, 2026). De cijfers per gezondheidszone komen uit de INSP-situatierapporten en zijn al verwerkt. Jouw taak is enkel wat in die data nog niet zit.

`landen` is het bronnenregister voor de landen van het reisschema: per land de FOD-pagina's en het FOD-advies, het CDC-niveau per uitbraak, betrouwbare overheidsbronnen en nieuwsmedia, en de gekende grensmaatregelen, met de datum waarop het register nagekeken is (`verified: null`: nog nooit). `internationaal` zijn de instanties die voor elk land gelden. Begin bij die bronnen en zoek pas verder als ze niet volstaan.

1. Reisadviezen. Controleer voor elk land in `landen` de live pagina's, en in het uitbraakland voor elke provincie in `provincies`:
   - FOD Buitenlandse Zaken (België): algemene veiligheid, laatste update, gezondheid en hygiëne (links in `landen.<land>.fod.pages`). Heeft een land nog geen pagina's, zoek ze op en zet ze onder `sources`. De site weigert soms automatische opvraging; gebruik dan zoekresultaten en zeg dat.
   - CDC Travel Health Notices (niveau per provincie voor ebola).
   Vergelijk met `landen`. `fod` is `formeel_afgeraden` of `niet_essentieel_afgeraden`; `fod_reason` zegt waarom (veiligheid versus gezondheid, dat verschil is voor de formulering belangrijk). `region` is de provincie, of `null` voor het advies voor het hele land. Zet in `outbreak` het id uit `uitbraken` waarvoor het CDC-niveau of de grensmaatregel geldt; gaat het over een ziekte zonder profiel, neem dan het eerste id en noem de ziekte in `about`.
2. Grensmaatregelen. Voor elk land in `buurlanden` (landen van het reisschema die grenzen aan een uitbraakland): is de grens met het uitbraakland dicht, is er screening bij in- of uitreis, quarantaine of een inreisverbod voor wie uit het uitbraakland komt? Kijk ook of het uitbraakland zelf exitscreening doet. Vergelijk met `landen.<land>.measures` en geef per land alle maatregelen die nu gelden, met datum en bron, en `changed: true` als ze verschillen van wat er staat.
3. WHO. `who_laatste_don` bevat het laatste Disease Outbreak News over deze uitbraak, gelezen uit de WHO-API. Kijk na of er sindsdien een nieuwer DON of een nieuwer WHO-situatierapport over de DRC is, en of de WHO een risicobeoordeling of reisadvies formuleert (de WHO raadt zelden reisbeperkingen aan; als ze dat wel doet, is dat op zich nieuws). Zet wat je vindt in `who`.
4. Nieuws van de laatste 14 dagen dat nog niet in de data kan zitten: nieuwe provincie of zone, mediagemelde gevallen langs het reisschema, grensmaatregelen, maatregelen op luchthavens, wijzigingen in de 21-dagenregels van derde landen. Enkel betrouwbare bronnen: die in `landen` en `internationaal`; een andere bron alleen als je zegt waarom je ze vertrouwt. Staat er `ziekten_zonder_profiel` in de invoer, zoek dan ook of die ziekte in de landen van het reisschema speelt, en zet wat je vindt in `news`.
5. Bronnen. Een betrouwbare overheidsbron, FOD-pagina of nieuwsmedium dat je gebruikt hebt en dat nog niet in `landen` staat, zet je in `sources`, met waarom het betrouwbaar is. De arts beslist of het in het register komt.
6. Cijfers. Staat er `tabellen` in de invoer, dan rust die uitbraak op een tabel die met de hand bijgehouden wordt, met de laatste datum en de laatste cijfers per eenheid (`niveau`: provincie of gezondheidszone). Zoek recentere officiële cijfers (ministerie of nationaal instituut, WHO, Africa CDC) en geef ze in `case_updates`: één rij per eenheid en datum, cumulatief, volgens de `casusdefinitie` van de tabel, met de bron. Enkel cijfers die je op de pagina zelf gelezen hebt, niet uit een zoekresultaat; een nationaal totaal krijgt `admin1: "NATIONAAL"`.
7. Vermeld alleen wat je effectief gezien hebt, met datum en URL. Geen vermoedens als feit.

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
  "case_updates": [{"outbreak": "…", "date": "JJJJ-MM-DD", "admin1": "…", "admin2": "", "cases_cum": 0,
                    "deaths_cum": 0, "case_def": "bevestigd", "source_url": "URL"}],
  "notes": ["…"]
}
```


# Invoer

<vandaag>
VANDAAG
</vandaag>

<uitbraken>
[
 {
  "id": "ebola_cod_2026",
  "naam": "Ebola (Bundibugyo-virus)"
 }
]
</uitbraken>

<provincies>
[
 "Kinshasa",
 "Tshopo"
]
</provincies>

<landen>
{
 "COD": {
  "iso3": "COD",
  "name_nl": "Democratische Republiek Congo",
  "verified": "2099-01-01",
  "fod": {
   "pages": [
    [
     "FOD Buitenlandse Zaken, algemene veiligheid DRC",
     "https://diplomatie.belgium.be/nl/landen/congo-democratische-republiek/reizen-naar-de-democratische-republiek-congo-reisadvies/algemene-veiligheid-de-democratische-republiek-congo"
    ],
    [
     "FOD Buitenlandse Zaken, laatste update DRC",
     "https://diplomatie.belgium.be/nl/landen/congo-democratische-republiek/reizen-naar-de-democratische-republiek-congo-reisadvies/laatste-update-de-democratische-republiek-congo"
    ],
    [
     "FOD Buitenlandse Zaken, gezondheid en hygiene DRC",
     "https://diplomatie.belgium.be/nl/landen/congo-democratische-republiek/reizen-naar-de-democratische-republiek-congo-reisadvies/gezondheid-en-hygiene-de-democratische-republiek-congo"
    ]
   ],
   "default": {
    "level": "niet_essentieel_afgeraden",
    "reason": "algemene volatiliteit"
   },
   "regions": {
    "Ituri": {
     "level": "formeel_afgeraden",
     "reason": "veiligheidssituatie"
    },
    "Nord-Kivu": {
     "level": "formeel_afgeraden",
     "reason": "gewapend conflict"
    },
    "Sud-Kivu": {
     "level": "formeel_afgeraden",
     "reason": "gewapend conflict"
    },
    "Tshopo": {
     "level": "formeel_afgeraden",
     "reason": "veiligheidssituatie"
    },
    "Tanganyika": {
     "level": "formeel_afgeraden",
     "reason": "veiligheidssituatie"
    },
    "Maniema": {
     "level": "formeel_afgeraden",
     "reason": "veiligheidssituatie"
    },
    "Haut-Uele": {
     "level": "niet_essentieel_afgeraden",
     "reason": "algemene volatiliteit"
    }
   }
  },
  "cdc": {
   "ebola_cod_2026": {
    "default": 2,
    "regions": {
     "Ituri": 4,
     "Nord-Kivu": 4,
     "Sud-Kivu": 2,
     "Tshopo": 3,
     "Tanganyika": 2,
     "Maniema": 2,
     "Haut-Uele": 3
    }
   }
  },
  "government": [
   {
    "name": "INSP",
    "what": "situatierapporten",
    "url": "https://insp.cd/"
   }
  ],
  "news": [
   {
    "name": "Radio Okapi",
    "url": "https://www.radiookapi.net"
   },
   {
    "name": "Actualite.cd",
    "url": "https://actualite.cd"
   }
  ],
  "measures": []
 }
}
</landen>

<buurlanden>
[]
</buurlanden>

<internationaal>
{
 "verified": "2026-09-25",
 "bodies": [
  {
   "name": "WHO",
   "what": "Disease Outbreak News",
   "url": "https://www.who.int/emergencies/disease-outbreak-news"
  },
  {
   "name": "WHO AFRO",
   "what": "situatierapporten voor Afrika",
   "url": "https://www.afro.who.int"
  },
  {
   "name": "ECDC",
   "what": "epidemiologische updates en risicobeoordelingen",
   "url": "https://www.ecdc.europa.eu"
  },
  {
   "name": "US CDC",
   "what": "Travel Health Notices",
   "url": "https://wwwnc.cdc.gov/travel/notices"
  },
  {
   "name": "Africa CDC",
   "what": "epidemic intelligence",
   "url": "https://africacdc.org"
  },
  {
   "name": "ITG",
   "what": "reisgeneeskunde en infectieziekten (Antwerpen)",
   "url": "https://www.itg.be"
  },
  {
   "name": "Sciensano",
   "what": "Belgische volksgezondheid",
   "url": "https://www.sciensano.be"
  },
  {
   "name": "Departement Zorg",
   "what": "infectieziektebestrijding Vlaanderen",
   "url": "https://www.departementzorg.be"
  }
 ],
 "news": [
  {
   "name": "Reuters",
   "url": "https://www.reuters.com"
  },
  {
   "name": "AP",
   "url": "https://apnews.com"
  }
 ]
}
</internationaal>

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
