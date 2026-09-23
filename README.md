# yt-auto

Volautomatische productie van video's met volksverhalen, mythen en sagen.
Een verhaal wordt gekozen en herteld, een stem vertelt het voor, de
landschappen worden getekend, en YouTube krijgt de video binnen.

**Alles werkt gratis.** Zonder sleutels schrijft de ingebouwde verteller het
verhaal en spreekt Piper het in — allebei op je eigen computer, zonder
account, zonder limiet. Een sleutel koopt kwaliteit, geen werking: met Claude
worden de verhalen beter bedacht en met ElevenLabs klinkt de stem natuurlijker.
Zie [Gratis draaien](#gratis-draaien).

De pipeline kan twee niches aan. Welke er draait staat in één regel
(`channel.format` in `config/channel.yaml`):

| | |
|---|---|
| `folklore` | volksverhalen over gelaagde silhouetlandschappen — **nu actief** |
| `kids` | educatieve video's voor peuters met getekende figuren |

Jij hebt twee knoppen. Of nul, als je hem op de planner zet.

```
   ┌─ Stap 1 ──────────────┐        ┌─ Stap 2 ──────────────┐
   │  Schrijf het script   │  ───►  │   Maak de video       │
   │  hij bedenkt alles    │        │  beeld + stem + muziek│
   └───────────────────────┘        └───────────────────────┘
              │                                │
       jij leest het mee              mp4 + thumbnail, klaar
```

Of één knop, als je een Short wilt: die schrijft en rendert in één keer.

---

## Beginnen

De studio draait op je eigen computer. Er is geen website om naartoe te gaan:
je haalt het project één keer binnen en start het daarna met een dubbelklik.

### Snelste weg (macOS en Linux)

Plak deze regel in Terminal. Hij haalt alles op, installeert zichzelf en opent
de pagina:

```bash
git clone https://github.com/ParisAngelopoulos/yt-auto.git && cd yt-auto && ./start.command
```

De volgende keer hoef je alleen nog te dubbelklikken op `start.command`.

Liever klikken dan typen, of zit je op Windows? Dan de weg hieronder.

### 1. Het project downloaden

Ga naar de repository, klik op de groene knop **Code**, dan **Download ZIP**.
Pak het uit en open de map.

### 2. Python (alleen op Windows)

macOS heeft Python al. Op Windows haal je het eenmalig op bij
[python.org/downloads](https://www.python.org/downloads/). Zet bij het
installeren een vinkje bij **Add Python to PATH**, anders vindt Windows het niet.

**ffmpeg hoef je niet te installeren.** Dat komt automatisch mee.

### 3. Starten

| | |
|---|---|
| **macOS** | **rechtermuisknop** op `start.command` → **Open** → nog een keer **Open** |
| **Windows** | dubbelklik `start.bat` |
| **Linux** | dubbelklik `start.command`, of `./start.command` in een terminal |

Die rechtermuisknop op de Mac is alleen de eerste keer nodig. macOS blokkeert
gedownloade startbestanden bij een gewone dubbelklik, met de melding dat het
van een onbekende ontwikkelaar komt. Via rechtermuisknop → Open krijg je een
knop om het toch te openen. Daarna werkt dubbelklikken gewoon.

De eerste keer installeert hij zichzelf; dat duurt een paar minuten. Daarna
opent je browser binnen een paar seconden vanzelf op
<http://127.0.0.1:8765>.

Het zwarte venster dat erbij opent mag open blijven staan. Sluiten stopt de
studio. De volgende keer: weer dubbelklikken.

### 4. Meteen proberen

Klik op **Schrijf het script** en daarna op **Maak de video**. Je hoeft niets
in te vullen en er wordt niets afgeschreven: de ingebouwde verteller schrijft
het verhaal en Piper spreekt het in. Wat eruit komt is een complete video die
je kunt uploaden.

Bovenaan de pagina staat in één regel wie er schrijft, wie er inspreekt en of
dat iets kost.

Liever de opdrachtregel? `ytauto panel` doet hetzelfde.

---

## Gratis draaien

Er zijn twee dingen die bij dit soort projecten normaal geld kosten: iemand
die het script schrijft en iemand die het voorleest. Hier kan allebei
gratis, en dat is de stand waarin de studio wordt geleverd.

### Het script

`script.provider` in `config/channel.yaml` staat op `auto`. Dat betekent: pak
het beste dat beschikbaar is, en eindig altijd bij iets dat werkt.

| | | |
|---|---|---|
| `local` | **gratis** | de ingebouwde verteller. Acht tradities, zes verhaalvormen, en per verhaal andere mensen, plekken en wezens. Raakt niet op. |
| `ollama` | **gratis** | een taalmodel op je eigen computer via [ollama.com](https://ollama.com). Meer variatie dan de ingebouwde verteller. |
| `claude` | ± €0,15 per script | bedenkt zelf het onderwerp en schrijft het helemaal zelf. Het beste resultaat. |

De ingebouwde verteller stelt verhalen samen uit vaste vormen — een afspraak
bij het water, een geschenk met één voorwaarde, een weg waar je na donker
niet hoort te lopen — en vult die met de namen, plekken en wezens van een
traditie. Ze zijn correct, ze zijn lang genoeg en ze zijn van jou. Wat hij
niet kan is verrassen: wie er twintig achter elkaar bekijkt, ziet het patroon.

Wil je gratis én meer variatie, zet er dan Ollama naast:

```bash
ollama pull qwen2.5:14b      # eenmalig, een paar GB
```

Meer heb je niet te doen; de studio ziet het vanzelf. Draait Ollama niet, dan
schrijft de ingebouwde verteller het verhaal en merk je er niets van.

### De stem

`tts.provider` staat op `piper`. [Piper](https://github.com/OHF-Voice/piper1-gpl)
is een stemmodel dat op je eigen computer draait: geen sleutel, geen tegoed,
geen limiet op het aantal tekens. Het model wordt bij de eerste video eenmalig
opgehaald (ongeveer 60 MB) en werkt daarna zonder internet.

```bash
ytauto voice              # welke stem staat ingesteld, en welke er nog meer zijn
ytauto voice --download   # het model nu alvast ophalen
ytauto voice --test       # een proefzin inspreken en beluisteren
```

Een andere stem kiezen: zet de naam bij `tts.voice_model` in `channel.yaml`.
Alle stemmen zijn eerst te beluisteren op
[rhasspy.github.io/piper-samples](https://rhasspy.github.io/piper-samples).

### Wat kost dan nog wel iets

Niets, zolang je bij `auto` en `piper` blijft. Zet je een Anthropic-sleutel
in `.env`, dan gebruikt `auto` die vanaf dat moment wel — dat is de enige
manier waarop er iets afgeschreven kan worden. Wil je dat uitsluiten, zet
`script.provider` dan op `local` of `ollama`.

Publiceren op YouTube is sowieso gratis; daar heb je alleen een eenmalige
koppeling voor nodig.

---

## Shorts

Naast de lange verhalen maakt de studio staande video's van rond de minuut,
voor YouTube Shorts, TikTok en Reels. Zelfde tekenwerk, zelfde stem, zelfde
prijs — namelijk niets.

```bash
ytauto short                    # schrijven en renderen in één keer
ytauto short --hint norse       # een wens meegeven
ytauto short --script-only      # eerst lezen, later pas renderen
```

Op de bedieningspagina staat er een knop voor, onder de twee grote.

**Wat er anders is aan een Short.** Niet de lengte alleen. Een verhaal van
tien minuten mag rustig beginnen; een Short die rustig begint wordt
weggeklikt. Daarom opent hij met een haak — wat er op het spel staat, of hoe
het afloopt — en pas daarna met wie en waar. De zinnen komen uit hetzelfde
patroon als het lange verhaal, maar er worden er tien gekozen in plaats van
zeventig, en de stiltes ertussen zijn korter.

**De tekst staat in beeld.** Het grootste deel van de Shorts wordt zonder
geluid bekeken; een verhaal dat alleen verteld wordt is dan een reeks
landschappen zonder betekenis. Elke zin wordt daarom in stukjes van een paar
woorden geknipt — op de leestekens, want daar ademt de verteller — en die
stukjes staan in beeld zolang ze ongeveer duren. Uitzetten kan met
`captions: false` onder `shorts:`.

Een Short is in ongeveer een halve minuut klaar. Het beeld wordt maar één
keer per scene getekend en de stukken video worden naast elkaar gecodeerd;
dat scheelt ook bij de lange video's.

Het beeld is 1080×1920. Bijschriften staan hoger in beeld dan bij een lange
video: onderin legt YouTube zijn eigen titel, kanaalnaam en knoppen neer, en
wat daar staat leest niemand.

Aanpassen kan in `config/channel.yaml` onder `shorts:` — formaat, overgangen
en hoeveel stilte er voor en na een zin zit.

Publiceren gaat voorlopig met de hand: `ytauto short` zet de mp4 in `out/`,
en die sleep je naar YouTube. De automatische upload werkt alleen voor de
lange video's.

### De afdaling

Een tweede vorm, en de enige die van begin tot eind beweegt:

```bash
ytauto descent --list           # welke reizen er zijn
ytauto descent                  # maak er een
```

De camera zakt in één doorlopende beweging van het wateroppervlak naar het
diepste punt van de oceaan, met alles wat je onderweg passeert op zijn echte
diepte: een duiker op tien meter, de Titanic op drieduizend achthonderd, de
Challenger Deep op tienduizend negenhonderdvijfendertig. Bovenin loopt een
dieptemeter mee.

Waarom deze vorm bestaat: een reeks stilstaande beelden leest binnen een
halve seconde als diashow, en daar scrolt iedereen voorbij. Hier is er geen
enkele snede. De camera houdt bij elke mijlpaal even in terwijl de regel
erbij gesproken wordt en versnelt daarna weer, en die timing volgt de stem —
niemand hoeft iets met de hand gelijk te zetten.

Aanpassen doe je in `config/journeys.yaml`: `depth` in meters, `say` wat de
verteller zegt, `draw` welk wezen erbij hoort (die staan in
`src/ytauto/render/sea.py`). Zelf een reis toevoegen kan — de hoogte van
gebouwen, de afstand tot de planeten — zolang het maar één as is waar je
langs beweegt. De getallen moeten kloppen: dat is de hele kracht van de vorm.

Eén afdaling duurt ongeveer een minuut en kost een minuut om te maken.

Wil je alleen het beeld beoordelen, dan hoef je niet elke keer op de stem te
wachten:

```bash
ytauto descent --preview        # 20 seconden, stil, het hele bereik
ytauto descent --preview 8      # of korter
```

Dat perst de hele afdaling samen in die tijd, zonder in te spreken. Handig
bij het sleutelen aan het beeld, want daar gaat het meeste tijd in zitten.

**Waarom het eruitziet zoals het eruitziet.** Er komt geen beeldgenerator aan
te pas; alles is getekend met polygonen en verlopen. Dat betekent dat het
nooit fotorealistisch wordt, maar ook dat er geen kosten en geen
rechtenvraag zijn. Wat het beeld draagt zijn vier dingen die niets kosten:
de deeltjes komen op drie verschillende snelheden voorbij (daar leidt het oog
diepte uit af, niet uit een kleurverloop), de camera drijft zacht heen en
weer in plaats van zuiver verticaal te schuiven, vlak onder het oppervlak
danst een golfpatroon van licht, en alles onder de vijfhonderd meter krijgt
een gloed alsof het door je eigen lamp wordt aangeschenen.

---

## De sleutels — allemaal optioneel

Je hebt er geen één nodig om video's te maken. Wat je ermee koopt staat in de
laatste kolom.

| Waarvoor | Zonder sleutel gebeurt dit | Waar je hem haalt | Wat je ervoor krijgt |
|---|---|---|---|
| Claude — schrijft de scripts | de ingebouwde verteller schrijft | [console.anthropic.com](https://console.anthropic.com/settings/keys) | verhalen die echt bedacht zijn, ± €0,15 per stuk |
| ElevenLabs — spreekt in | Piper spreekt in, lokaal | [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys) → Settings → API Keys | een natuurlijkere stem, zie hieronder |
| YouTube — publiceert | je zet de mp4 zelf op YouTube | `python scripts/get_youtube_token.py` | de studio uploadt zelf, gratis |

Vul ze in op de pagina zelf, onder **Sleutels instellen**. Je plakt ze, klikt
op *Opslaan en testen*, en ziet meteen of ze werken. Ze worden opgeslagen in
`.env` op je eigen computer; dat bestand staat in `.gitignore` en komt nooit in
GitHub terecht.

Liever de terminal? `ytauto setup` vraagt hetzelfde en test het ook.

Het testen kost niets: het zijn gewone opvragingen zonder tokens.

De bolletjes rechtsboven in de pagina zeggen wat er aan de hand is:

| | |
|---|---|
| ○ | nog niet ingevuld |
| ● | ingevuld, nog niet getest |
| ✓ | getest en werkend |
| ✗ | getest, werkt niet — de reden staat bij het veld |

**ElevenLabs-verbruik:** een video van 8 minuten is ongeveer 3.500 tekens.

- Gratis (10.000 tekens/maand) → ongeveer 2 video's
- Starter, $5 (30.000) → ongeveer 8 video's
- Creator, $22 (100.000) → ongeveer 28 video's

De pipeline cachet elke ingesproken zin. Dezelfde video opnieuw renderen kost
niets extra aan spraak.

### YouTube koppelen

Dit is de enige stap die even werk is. Je doet hem één keer.

**1. Project aanmaken**
Ga naar de [Google Cloud Console](https://console.cloud.google.com) en maak een
nieuw project. De naam maakt niet uit.

**2. De API aanzetten**
*APIs & Services* → *Library* → zoek **YouTube Data API v3** → **Enable**.

**3. Toestemmingsscherm invullen**
In het linkermenu heet dit tegenwoordig **Google Auth Platform**; in oudere
projecten staat het onder *APIs & Services* → *OAuth consent screen*. Beide
leiden naar hetzelfde. Kies **External** (of *Extern*). Vul een app-naam en je
eigen e-mailadres in; de rest mag leeg.

**4. Zet de status op In production** ← de belangrijkste stap

- **Nieuwe indeling:** *Google Auth Platform* → **Audience** (Doelgroep). Daar
  staat *Publishing status: Testing* met de knop **Publish app**.
- **Oudere indeling:** *APIs & Services* → *OAuth consent screen*. Daar staat
  *Publishing status* met dezelfde knop.

Klik erop en bevestig. De status springt naar **In production**.

> Laat je hem op *Testing* staan, dan **verloopt je refresh token na zeven
> dagen** en staat je automatisering elke week stil met `invalid_grant`.
>
> Google meldt bij het publiceren dat verificatie nodig kan zijn. Dat gaat over
> apps die door ánderen gebruikt worden. Voor je eigen kanaal hoef je die
> verificatie niet te doorlopen: de app werkt gewoon, met een
> waarschuwingsscherm bij het inloggen dat je zelf wegklikt.

**5. Inloggegevens maken**
*Clients* (nieuwe indeling) of *Credentials* (oudere) → **Create client** /
*Create credentials* → *OAuth client ID* → type **Desktop app** → **Create**.
Er verschijnt een venster met een downloadknop: **Download JSON**.

**6. Het bestand neerzetten**
Hernoem het gedownloade bestand naar `client_secret.json` en zet het in de
projectmap, naast `README.md`.

**7. Het token ophalen**

```bash
python scripts/get_youtube_token.py
```

Je browser opent. Log in met het Google-account van je YouTube-kanaal.

Google waarschuwt dat de app niet geverifieerd is. Dat klopt — het is jouw
eigen app. Klik op **Geavanceerd** en dan op **Ga naar … (onveilig)**.

**8. De drie regels opslaan**
Het script drukt `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` en
`YOUTUBE_REFRESH_TOKEN` af. Plak ze in de bedieningspagina onder *Sleutels
instellen*, of zet ze in `.env`.

Controleren of het werkt: `ytauto check` toont de naam van je kanaal.

**Hoeveel kun je uploaden?** Google geeft je 10.000 eenheden per dag en een
upload kost er 1.600. Dat zijn zes video's per dag — ruim boven de drie per
week waar de pipeline op staat.

Daarna kan de pipeline zonder jou uploaden.

---

## Waar jij aan draait

Drie bestanden, geen code:

### `config/brief.md` — de toon
Dit leest Claude of het lokale model bij elk verhaal. Wil je rustiger
vertellen, andere tradities, een korter slot? Schrijf het hierin op. Het
volgende verhaal verandert mee.

De ingebouwde verteller leest de briefing niet; die haalt zijn toon uit zijn
eigen bank. Wil je hem bijsturen, dan pas je die bank aan — zie hieronder.

### `config/channel.yaml` — de knoppen
Niche, kanaalnaam, taal, lengte, stem, publicatietempo. De regels die je
waarschijnlijk als eerste aanpast:

```yaml
channel:
  format: folklore              # folklore | kids
video:
  target_duration_minutes: 11   # 8 tot 15 werkt het best voor een verhaal
script:
  provider: auto                # auto | local | ollama | claude
shorts:
  width: 1080                   # staand formaat voor Shorts en Reels
  height: 1920
  captions: true                # tekst in beeld
tts:
  provider: piper               # piper (gratis) | elevenlabs | offline
  voice_model: en_GB-alan-medium
publish:
  privacy_status: public        # zet op 'unlisted' zolang je nog meekijkt
  max_per_week: 3               # rem tegen spamdetectie
```

### `config/tales.yaml` — de verhalen met de hand
Drie complete hervertellingen, met de hand geschreven. Ze zijn beter dan wat
de ingebouwde verteller maakt en gaan daarom voor: pas als ze alle drie
gemaakt zijn, gaat de verteller zelf schrijven. Zelf een verhaal toevoegen
kan: kopieer de opbouw, `scenes` zijn de plekken en `beats` verwijzen ernaar
met hun index.

Voor de kinderniche doet `config/curriculum.yaml` hetzelfde.

De verteller zelf staat in `src/ytauto/scripting/`: de tradities en de
namen in `folk_bank.py`, de verhaalvormen in `folk_patterns.py`. Een traditie
of een vorm toevoegen is een kwestie van de opbouw kopiëren; de tests
controleren daarna vanzelf of elke nieuwe combinatie een geldig verhaal
oplevert.

---

## Volautomatisch draaien

`.github/workflows/publish.yml` draait maandag, woensdag, vrijdag en zondag om
06:00 UTC en publiceert dan één video.

Hiervoor heb je alleen de drie YouTube-waarden nodig; zet ze in je repository
onder **Settings → Secrets and variables → Actions**. De andere twee mogen
leeg blijven: in GitHub Actions draait dezelfde gratis weg als op je eigen
computer. Staan de YouTube-waarden er ook niet, dan wordt de video wel gemaakt
en niet geüpload; je haalt hem dan op bij de downloads van die run.

De boekhouding (`state/episodes.db`) wordt na elke run teruggeschreven naar de
repo. Zonder dat zou de volgende run niet weten wat er al gemaakt is.

Handmatig een run starten kan via **Actions → Nieuwe video publiceren → Run
workflow**. Zet daar `publish` uit om alleen te maken en de video als download op
te halen zonder hem te publiceren.

---

## De database

Alles wat de studio schrijft gaat in **één SQLite-bestand**: `state/episodes.db`.
Dat is echte SQL, maar zonder server die moet draaien. Je kunt het bestand
kopiëren, in een back-up zetten en met elk SQL-programma openen.

Waarom dit belangrijk is: de scripts stonden eerst alleen als losse
JSON-bestanden in `out/`. Die map staat in `.gitignore`, dus wie hem opruimde
was zijn werk kwijt. Nu bevat `out/` alleen nog gerenderde video's, en die
kun je altijd opnieuw maken.

### Wat erin staat

| Tabel | Inhoud |
|---|---|
| `episodes` | één rij per aflevering: titel, idee, beschrijving, status, video-id |
| `episode_beats` | elke gesproken zin, op volgorde, met zijn scenesoort |
| `episode_items` | wat er geleerd wordt: het woord, het figuur, de kleur |
| `episode_tags` | de YouTube-zoektermen |

Elke aflevering bewaart daarnaast zijn eigen JSON in de kolom `raw_json`. Dat
is dubbelop, en dat is bewust: de tabellen zijn om in te zoeken, de JSON is de
garantie dat je een aflevering altijd exact terugkrijgt.

### Erbij komen

In de pagina staat onderaan **Archief**: alles wat je ooit geschreven hebt,
doorzoekbaar. Klik een aflevering aan en hij staat weer klaar — video maken kan
dan meteen.

Vanaf de opdrachtregel:

```bash
ytauto library                 # alles wat er ooit geschreven is
ytauto library --search colors # zoeken op titel of idee
ytauto open colors:balloons    # een oudere aflevering terughalen
ytauto find "red balloon"      # zoeken in alle gesproken tekst
ytauto export backup.json      # alles als één JSON-bestand
```

En een eigen vraag stellen, als je SQL kent:

```bash
ytauto sql "SELECT lesson_kind, COUNT(*) n, SUM(word_count) woorden
            FROM episodes GROUP BY lesson_kind"

ytauto sql "SELECT mode, COUNT(*) n FROM episode_beats
            GROUP BY mode ORDER BY n DESC"
```

Alleen `SELECT` is toegestaan; je kunt er per ongeluk niets mee weggooien. Wil
je toch zelf rondkijken, open dan `state/episodes.db` met
[DB Browser for SQLite](https://sqlitebrowser.org) of `sqlite3 state/episodes.db`.

### Migreren gaat vanzelf

Gebruikte je de studio al voordat de database er was? Bij het opstarten worden
losse `blueprint.json`-bestanden uit `out/` alsnog opgenomen, en een oudere
database wordt bijgewerkt zonder dat er een rij verloren gaat.

---

## Wat er onder de motorkap gebeurt

```
config/brief.md ─┐   Claude / Ollama / de eigen verteller
                 ├─►         │                 ┌──► scenes ──► PNG's ──┐
tales.yaml ──────┘         blueprint ──────────┤                       ├─► ffmpeg ──► video.mp4
                  (verhaal, scenes, tekst)     ├── Piper / ElevenLabs ─┤
                                               └── muzieksynth ──► wav ┘
```

**Blueprint** is het contract. De schrijver levert het idee, de items en alle
gesproken zinnen; de code bouwt daar het beeld bij. Daardoor kan een script
nooit vragen om een figuur dat niet bestaat, terwijl de schrijver volledig vrij
is in taal en onderwerp. Alle drie de schrijvers leveren dezelfde blueprint op,
dus de rest van de pipeline merkt niet welke het geschreven heeft.

**Beelden** worden getekend, niet gegenereerd. Dat is meteen de derde
kostenpost die er niet is: geen beeld-API, geen abonnement. Elk beeld is een gelaagd
landschap: lucht, maan of zon, bergkammen en bossen die naar de kijker toe
steeds donkerder worden, en daartussen silhouetten. Dat donkerder worden is de
hele truc — verre bergen zijn bleek omdat er lucht tussen zit, en zonder dat
verloop is het een plaatje in plaats van diepte.

Tien landschappen, negen luchten, drie weertypen en 31 silhouetten
(`src/ytauto/render/silhouettes.py`): een reiziger, een burcht, een roeiboot,
een draak, staande stenen. Geen beeld-API, geen kosten, geen wisselende stijl
tussen afleveringen.

Het schema dwingt af dat de schrijver alleen plekken en figuren kiest die ook
werkelijk getekend kunnen worden. Een verzonnen silhouet komt er niet doorheen,
van wie het script ook komt.

**Verhaalopbouw** volgt vaste beats: titelkaart, opening, het verhaal zelf,
een wending waar het beeld verandert, de afloop, wat het verhaal wil zeggen,
en een bronvermelding. Meerdere beats delen dezelfde scene, zodat het beeld
blijft staan terwijl er verteld wordt en pas verandert als het verhaal van
plek verandert.

---

## Alle commando's

```bash
ytauto setup       # sleutels invoeren en meteen testen
ytauto panel       # bedieningspagina met de twee knoppen
ytauto script      # laat een aflevering schrijven
ytauto short       # maak een Short: staand beeld, rond de minuut
ytauto descent     # maak een afdaling: doorlopende beweging, geen snedes en print hem
ytauto video       # maak de video van het laatste script
ytauto publish     # zet die video op YouTube
ytauto run         # alles achter elkaar, zonder tussenkomst
ytauto library     # alles wat er ooit geschreven is
ytauto open KEY    # een oudere aflevering terughalen
ytauto find TEXT   # zoek in alle gesproken tekst
ytauto sql "..."   # een eigen SELECT op de database
ytauto export      # alles als JSON wegschrijven
ytauto status      # wat is er gemaakt, wat staat er online
ytauto voice       # de gratis stem bekijken, ophalen en testen
ytauto check       # wie er schrijft, wie er inspreekt, en wat het kost
```

---

## Wat je moet weten voor je publiceert

Dit is geen juridisch advies, maar het scheelt je een hoop gedoe.

**De verhalen zijn vrij, vertalingen niet.** Volksverhalen van eeuwen oud
kennen geen rechthebbende. Een specifieke vertaling of hervertelling uit de
twintigste eeuw wel. Daarom wordt er altijd in eigen woorden geschreven en
wordt er geen zin letterlijk overgenomen; dat staat in `config/brief.md` en
daar moet het blijven staan. De ingebouwde verteller heeft hetzelfde probleem
niet: elke zin die hij gebruikt is voor dit project geschreven.

**Noem de herkomst, en noem hem juist.** De veiligheidscontrole waarschuwt als
er geen traditie is vermeld of als de bronvermelding aan het eind ontbreekt.
Verhalen die in een levende cultuur een heilige of ceremoniële betekenis
hebben, laat de briefing bewust staan.

**Dit is geen kindercontent.** `made_for_kids` staat uit en de controle
blokkeert publiceren als je hem aanzet: een video onterecht als kindervideo
aanmerken schakelt reacties en advertenties uit en klopt niet. Zet je de niche
terug op `kids`, dan draait die regel om.

**Geweld mag benoemd worden, niet uitgeschilderd.** In een sage wordt
gevochten en gestorven; dat is geen probleem. Expliciet beschreven geweld
kost je de advertentiegeschiktheid, en daar controleert `src/ytauto/safety.py`
op.

**Geld verdienen kan pas** bij 1.000 abonnees en 4.000 uur kijktijd in een
jaar. Reken op maanden, niet weken.

**YouTube handhaaft op massaproductie.** Daarom staat `max_per_week` op 3 en
zit er minimaal 24 uur tussen twee uploads. Draai dat niet omhoog omdat het
kan.

---

## Als er iets misgaat

| Wat je ziet | Wat het is |
|---|---|
| `ffmpeg: ONTBREEKT` | `pip install imageio-ffmpeg`, of via brew, apt of winget |
| macOS: "kan niet worden geopend" | Rechtermuisknop op `start.command` → Open → Open |
| Windows: Python niet gevonden | Opnieuw installeren met het vinkje bij "Add Python to PATH" |
| `claude niet beschikbaar` | Geen `ANTHROPIC_API_KEY`. Dit is geen fout: de ingebouwde verteller neemt het over |
| `ollama niet beschikbaar` | Ollama draait niet. Ook geen fout; het is optioneel |
| De stem klinkt als een robot | `piper-tts` is niet geïnstalleerd. `pip install -e ".[voice]"` in de projectmap |
| `De stem kon niet opgehaald worden` | Eenmalige download van het stemmodel; controleer je verbinding en probeer `ytauto voice --download` |
| `ElevenLabs weigert de sleutel (401)` | Sleutel verlopen of verkeerd gekopieerd |
| `Weeklimiet bereikt` | Werkt zoals bedoeld. Verhoog `publish.max_per_week` als je echt sneller wilt |
| `Script afgekeurd door de veiligheidscontrole` | De melding noemt het woord. Pas `config/brief.md` aan |
| `thumbnail niet geplaatst` | Een eigen thumbnail vereist een geverifieerd YouTube-kanaal |
| Video duurt lang om te maken | Normaal is 8–15 minuten. Sneller: `encoder_preset: veryfast` |
| Tekst in beeld loopt niet gelijk met de stem | De stukjes krijgen tijd naar rato van hun lengte, niet op de stem uitgelijnd. Bij een gelijkmatige verteller valt dat weg; klopt het echt niet, zet `captions: false` |
| `Alle verhalen zijn gemaakt` | Kan alleen nog bij `provider: template`. Zet hem op `auto` of `local`; de verteller raakt niet op |

Tests draaien: `pytest -q`

---

## Mappen

```
state/           episodes.db — al je scripts, in SQL
assets/voices/   het stemmodel van Piper (niet in git, wordt opgehaald)
start.command    dubbelklikken op macOS/Linux
start.bat        dubbelklikken op Windows
config/          brief.md, channel.yaml, tales.yaml, journeys.yaml  ← hier stuur je
src/ytauto/
  scripting/     de drie schrijvers, de verhalenbank en het blueprint-contract
  render/        landschappen, silhouetten, zeewezens, de waterkolom, thumbnail
  audio/         muzieksynthesizer
  tts/           Piper (gratis), ElevenLabs en de teststem
  video/         ffmpeg-montage
  youtube/       upload
  ui/            bedieningspagina
out/             gerenderde video's (niet in git, altijd opnieuw te maken)
```
