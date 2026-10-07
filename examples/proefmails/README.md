# Proefmails (F-015, stap 4)

Verzonnen aanvragen, een per soort advies, om de korte mail en het dossier op na te lezen. Namen,
reizen en de casus zijn verzonnen; er staan geen gegevens van echte personen in.

| Mail | Soort | Wat het test |
|---|---|---|
| `1_reis_kisangani_yangambi.txt` | reisadvies | getroffen zone (Tshopo), boottransport, twee vragen van An |
| `2_reis_kampala_kasese.txt` | reisadvies | buurland van de DRC, grensmaatregelen, een vraag om de grens over te steken |
| `3_casus_koorts_kisangani.txt` | casus | reiziger ter plaatse met koorts en een mogelijk contact, gezondheidsgegevens |
| `4_vraag_mpox_vaccinatie.txt` | vraag | algemene vraag zonder reis, zorgwerk |

Draaien als proefrun (niets in het archief, de log of `context.md`):

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\venvs\outbreak_ug"
uv run dienstreis advies examples\proefmails\1_reis_kisangani_yangambi.txt --proef --yes --no-open --out out_proef_1
```

De casus (3) heeft `--gezondheidsgegevens-ok` nodig: de mail is verzonnen, maar ziet eruit als
gezondheidsgegevens, en zonder die vlag vraagt het programma eerst toestemming.
