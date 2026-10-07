# Taak: richtlijnen en de toestand ter plaatse nakijken voor een casus of een vraag

Je ondersteunt een antwoord aan UGent Team Actueel over een casus (een reiziger die al ter plaatse is of net terug, en ziek, blootgesteld of in quarantaine is) of over een algemene vraag. `casus` vat de toestand samen zoals de mail ze beschrijft, `vragen` zijn de vragen van An. `uitbraken` zijn de uitbraakprofielen die voor de plaats of de ziekte gelden, `landen` het bronnenregister voor de landen van de casus, `internationaal` de instanties die overal gelden. Begin bij die bronnen en zoek pas verder als ze niet volstaan.

1. Richtlijnen. Zoek wat officiële bronnen nu aanbevelen voor deze toestand, met datum en URL: duur van isolatie en criteria voor vrijgave, de terugreis (mag de persoon vliegen, wat vragen luchtvaartmaatschappijen en het land van vertrek), wat bij aankomst in België moet (melding, contactopvolging, isolatie thuis of in een woning met gedeelde ruimtes), en vaccinatie of profylaxe voor huisgenoten en contacten. Eerst ITG, Sciensano, Departement Zorg, Hoge Gezondheidsraad, WHO en ECDC; dan de overheidsbronnen in `landen`. Elk punt komt in `guidance`: onderwerp, tekst, bron, datum.
2. De toestand ter plaatse: recente cijfers en maatregelen voor de uitbraken in `uitbraken`, voor de plaats van de casus. Staat er `tabellen` in de invoer, geef recentere officiële cijfers in `case_updates` zoals bij een reisadvies: één rij per eenheid en datum, cumulatief, volgens de casusdefinitie van de tabel, met bron; enkel cijfers die je op de pagina zelf gelezen hebt.
3. Reisadviezen en grensmaatregelen voor de landen in `landen`, in `advisories` (per land en eventueel per provincie, met `outbreak` het id uit `uitbraken`) en `measures`.
4. Staat er `ziekten_zonder_profiel` in de invoer, zoek dan wat officiële bronnen over die ziekte in de landen van de casus zeggen, en zet het in `news`.
5. Een betrouwbare bron die nog niet in `landen` staat, zet je in `sources`, met waarom ze betrouwbaar is. Een bron uit `internationaal.excluded` gebruik je niet en stel je niet voor.
6. Documenten en fiche. `fiches` geeft per uitbraak de sleuteldocumenten (`documenten`, per niveau: `be` België, `eu` Europa, `who`, `us` Verenigde Staten), de datum waarop ze nagekeken zijn, en de ziektefiche met haar status. Kijk na of er van een document een nieuwere versie is, of een nieuw sleuteldocument van een Belgische, Europese, WHO- of Amerikaanse instantie sinds `documenten_nagekeken`, en zet het in `document_updates`: `action` is `nieuw`, of `nieuwere_versie` met in `replaces` het id van het document dat het vervangt; `key` is de kernboodschap in een zin. Spreekt een nieuwere officiële richtlijn een uitspraak in de fiche tegen, zet dan in `fiche_flags` de sectie, de uitspraak letterlijk, wat de nieuwere richtlijn zegt, en bron en datum. Herschrijf de fiche niet: de arts beslist. Enkel documenten die je zelf geopend hebt; is er geen fiche of geen document, stel dan de belangrijkste documenten voor als `nieuw`.
7. Vermeld alleen wat je effectief gezien hebt, met datum en URL. Geen vermoedens als feit, en niets over de persoon zelf buiten wat in `casus` staat.

Antwoord uitsluitend met dit JSON-object:

```json
{
  "guidance": [{"topic": "isolatie | terugreis | aankomst in België | contacten | ander", "text": "…",
                "source": "URL", "date": "JJJJ-MM-DD"}],
  "advisories": [{"country": "COD", "region": null, "fod": "…", "fod_reason": "…", "cdc": 2, "outbreak": "…",
                  "changed": false, "source": "URL", "checked_how": "pagina gelezen | zoekresultaat"}],
  "measures": [{"country": "…", "outbreak": "…", "about": "…", "text": "…", "date": "JJJJ-MM-DD", "source": "URL", "changed": false}],
  "sources": [{"country": "…", "kind": "fod | overheid | nieuws", "name": "…", "url": "…", "why": "…"}],
  "case_updates": [{"outbreak": "…", "date": "JJJJ-MM-DD", "admin1": "…", "admin2": "", "cases_cum": 0,
                    "deaths_cum": 0, "case_def": "…", "source_url": "URL"}],
  "who": {"latest_don": "JJJJ-MM-DD", "risk_assessment": "…", "url": "…"},
  "news": [{"date": "JJJJ-MM-DD", "item": "…", "url": "…"}],
  "document_updates": [{"outbreak": "…", "level": "be | eu | who | us", "action": "nieuw | nieuwere_versie",
                        "replaces": null, "org": "…", "title": "…", "date": "JJJJ-MM-DD", "url": "…", "key": "…"}],
  "fiche_flags": [{"outbreak": "…", "section": "…", "statement": "…", "newer": "…", "source": "URL", "date": "JJJJ-MM-DD"}],
  "notes": ["…"]
}
```
