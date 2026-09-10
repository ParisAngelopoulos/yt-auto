# Lettertypes

De studio haalt deze bestanden op via zijn eigen server (`/fonts/…`), niet bij
Google. Zo ziet de pagina er ook zonder internet goed uit.

| Bestand | Waarvoor | Licentie |
|---|---|---|
| `Baloo2.ttf` | koppen | SIL OFL 1.1 — `OFL-Baloo2.txt` |
| `IBMPlexSans.ttf` | bediening en lopende tekst | SIL OFL 1.1 — `OFL-IBMPlex.txt` |
| `IBMPlexMono-Regular.ttf` | labels, aantallen, tijden | SIL OFL 1.1 — `OFL-IBMPlex.txt` |
| `IBMPlexMono-Medium.ttf` | idem, iets zwaarder | SIL OFL 1.1 — `OFL-IBMPlex.txt` |

**Baloo 2** is ook de letter die in de video's zelf getekend wordt
(`src/ytauto/render/scene.py`). Dat is bewust: wat je op het scherm van de
studio ziet, is dezelfde hand als wat er uit komt.

De SIL Open Font License staat gebruik in commerciële video's toe, ook zonder
naamsvermelding.

Een ander lettertype gebruiken? Zet het hier neer en pas de naam aan in
`src/ytauto/render/scene.py` (`load_font`, parameter `family`) voor de video's,
of in `src/ytauto/ui/panel.html` voor de pagina. Ontbreekt een bestand, dan valt
alles terug op een systeemlettertype.
