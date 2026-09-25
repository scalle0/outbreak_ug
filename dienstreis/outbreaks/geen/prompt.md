<!-- Passages for a trip that no outbreak profile applies to, spliced into dienstreis/prompts/*.md
     where the template says {{uitbraak:<name>}}. -->

<!-- uitbraak:opdracht -->
naar een bestemming waarvoor geen uitbraakprofiel van toepassing is

<!-- uitbraak:vertrekpunt -->
## Vertrekpunt: landniveau

Voor geen enkel land van het reisschema, en voor geen buurland ervan, bestaat een uitbraakprofiel. Er zijn dus geen zonecijfers en geen regelcategorieën: elke halte staat als X in `risico_per_stop`, met het FOD- en CDC-advies en de grensmaatregelen uit het landenregister.

"Geen profiel" betekent niet "geen uitbraak". Kijk in `web` of er op de bestemming of in een buurland een uitbraak loopt. Vindt de webstap er een, zeg dan in de mail dat het advies voorlopig is tot de cijfers bekend zijn, en zet in `suggestions` welke uitbraak een profiel nodig heeft. Vindt hij er geen, dan gaat het advies over de gewone reisrisico's van het land, kort: FOD-advies en de reden (veiligheid of gezondheid), vaccinaties en profylaxe, en wat de reiziger zelf moet nakijken.

<!-- uitbraak:valkuilen -->
- De go/no-go-beslissing valt vóór vertrek uit België (standaard een week ervoor): eenmaal ter plaatse kan UGent enkel nog adviseren.
- Een uitbraak die de webstap vindt, is zo betrouwbaar als de pagina waar ze stond: vermeld bron en datum, en schrijf geen cijfers die niet in `web` staan.
- Een FOD-advies "formeel afgeraden" om veiligheidsredenen is geen gezondheidsadvies; zeg welk van de twee het is.
- Vermeld nooit andere reizigers of dossiers uit `geschiedenis` of `context` in de mail; gebruik ze enkel voor consistentie.

<!-- uitbraak:vaste_voorwaarden -->
Het pretravel consult en de go/no-go

<!-- uitbraak:opdracht_web -->
naar een bestemming waarvoor geen uitbraakprofiel bestaat. Er zijn dus geen zonecijfers. Zoek eerst of er in de landen van het reisschema of hun buurlanden een uitbraak loopt (WHO Disease Outbreak News, ECDC, CDC, Africa CDC, en de overheidsbronnen in `landen`): "geen profiel" betekent niet "geen uitbraak". Zet wat je vindt in `news`, en in `notes` welke uitbraak een profiel nodig heeft.

<!-- uitbraak:cdc_niveau -->
het niveau voor het land, voor welke ziekte ook

<!-- uitbraak:who_rapport -->
situatierapport over een uitbraak in de landen van het reisschema

<!-- uitbraak:nieuws -->
Nieuws van de laatste 14 dagen over uitbraken, grensmaatregelen en maatregelen op luchthavens in de landen van het reisschema. Enkel betrouwbare bronnen: die in `landen` en `internationaal`; een andere bron alleen als je zegt waarom je ze vertrouwt.
