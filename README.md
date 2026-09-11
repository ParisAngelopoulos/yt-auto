# yt-auto

Volautomatische productie van video's met volksverhalen, mythen en sagen.
Claude kiest een verhaal en hertelt het, ElevenLabs vertelt het voor, de
landschappen worden getekend, en YouTube krijgt de video binnen.

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
   │  Claude bedenkt alles │        │  beeld + stem + muziek│
   └───────────────────────┘        └───────────────────────┘
              │                                │
       jij leest het mee              mp4 + thumbnail, klaar
```

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

Klik op **Schrijf het script** en daarna op **Maak de video**. Zonder sleutels
werkt dat ook: het script komt dan uit `config/curriculum.yaml` en de video
krijgt een gratis robotstem. Beeld, muziek en timing zijn wel echt. Zo zie je
de hele machine draaien voordat je iets uitgeeft.

Liever de opdrachtregel? `ytauto panel` doet hetzelfde.

---

## De sleutels

Vul ze in op de pagina zelf, onder **Sleutels instellen**. Je plakt ze, klikt
op *Opslaan en testen*, en ziet meteen of ze werken. Ze worden opgeslagen in
`.env` op je eigen computer; dat bestand staat in `.gitignore` en komt nooit in
GitHub terecht.

Liever de terminal? `ytauto setup` vraagt hetzelfde en test het ook.

| Waarvoor | Waar je hem haalt | Kosten |
|---|---|---|
| Claude — schrijft de scripts | [console.anthropic.com](https://console.anthropic.com/settings/keys) | ± €0,15 per script |
| ElevenLabs — spreekt in | [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys) → Settings → API Keys | zie hieronder |
| YouTube — publiceert | `python scripts/get_youtube_token.py` | gratis |

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
Dit leest Claude bij elk verhaal. Wil je rustiger vertellen, andere tradities,
een korter slot? Schrijf het hierin op. Het volgende verhaal verandert mee.

### `config/channel.yaml` — de knoppen
Niche, kanaalnaam, taal, lengte, stem, publicatietempo. De regels die je
waarschijnlijk als eerste aanpast:

```yaml
channel:
  format: folklore              # folklore | kids
video:
  target_duration_minutes: 11   # 8 tot 15 werkt het best voor een verhaal
publish:
  privacy_status: public        # zet op 'unlisted' zolang je nog meekijkt
  max_per_week: 3               # rem tegen spamdetectie
```

### `config/tales.yaml` — het vangnet
Alleen in gebruik als Claude er niet is. Er staan drie complete
hervertellingen in. Zelf een verhaal toevoegen kan: kopieer de opbouw,
`scenes` zijn de plekken en `beats` verwijzen ernaar met hun index.

Voor de kinderniche doet `config/curriculum.yaml` hetzelfde.

---

## Volautomatisch draaien

`.github/workflows/publish.yml` draait maandag, woensdag, vrijdag en zondag om
06:00 UTC en publiceert dan één video.

Zet in je repository onder **Settings → Secrets and variables → Actions** dezelfde
vijf waarden als in je `.env`. Daarna hoef je niets meer te doen.

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
config/brief.md ─┐
                 ├─► Claude ──► blueprint ────────┬──► scenes ──► PNG's ──┐
tales.yaml ──────┘   (verhaal, scenes, tekst)    │                       ├─► ffmpeg ──► video.mp4
                                                 │   ElevenLabs ──► mp3 ─┤
                                                 └── muzieksynth ──► wav ┘
```

**Blueprint** is het contract. Claude levert het idee, de items en alle gesproken
zinnen; de code bouwt daar het beeld bij. Daardoor kan een script nooit vragen om
een figuur dat niet bestaat, terwijl Claude wel volledig vrij is in taal en
onderwerp.

**Beelden** worden getekend, niet gegenereerd. Elk beeld is een gelaagd
landschap: lucht, maan of zon, bergkammen en bossen die naar de kijker toe
steeds donkerder worden, en daartussen silhouetten. Dat donkerder worden is de
hele truc — verre bergen zijn bleek omdat er lucht tussen zit, en zonder dat
verloop is het een plaatje in plaats van diepte.

Tien landschappen, negen luchten, drie weertypen en 31 silhouetten
(`src/ytauto/render/silhouettes.py`): een reiziger, een burcht, een roeiboot,
een draak, staande stenen. Geen beeld-API, geen kosten, geen wisselende stijl
tussen afleveringen.

Het schema dwingt af dat Claude alleen plekken en figuren kiest die ook
werkelijk getekend kunnen worden. Een verzonnen silhouet komt er niet doorheen.

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
ytauto script      # laat Claude een aflevering schrijven en print hem
ytauto video       # maak de video van het laatste script
ytauto publish     # zet die video op YouTube
ytauto run         # alles achter elkaar, zonder tussenkomst
ytauto library     # alles wat er ooit geschreven is
ytauto open KEY    # een oudere aflevering terughalen
ytauto find TEXT   # zoek in alle gesproken tekst
ytauto sql "..."   # een eigen SELECT op de database
ytauto export      # alles als JSON wegschrijven
ytauto status      # wat is er gemaakt, wat staat er online
ytauto check       # sleutels, tegoed en ffmpeg controleren
```

---

## Wat je moet weten voor je publiceert

Dit is geen juridisch advies, maar het scheelt je een hoop gedoe.

**De verhalen zijn vrij, vertalingen niet.** Volksverhalen van eeuwen oud
kennen geen rechthebbende. Een specifieke vertaling of hervertelling uit de
twintigste eeuw wel. Daarom schrijft Claude altijd in eigen woorden en neemt
hij geen zinnen letterlijk over; dat staat in `config/brief.md` en daar moet
het blijven staan.

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
| `Claude niet beschikbaar` | Geen `ANTHROPIC_API_KEY`; hij gebruikt nu het sjabloon |
| `ElevenLabs weigert de sleutel (401)` | Sleutel verlopen of verkeerd gekopieerd |
| `Weeklimiet bereikt` | Werkt zoals bedoeld. Verhoog `publish.max_per_week` als je echt sneller wilt |
| `Script afgekeurd door de veiligheidscontrole` | De melding noemt het woord. Pas `config/brief.md` aan |
| `thumbnail niet geplaatst` | Een eigen thumbnail vereist een geverifieerd YouTube-kanaal |
| Video duurt lang om te maken | Normaal is 8–15 minuten. Sneller: `encoder_preset: veryfast` |
| `Alle verhalen zijn gemaakt` | De bank is op. Voeg er een toe in `config/tales.yaml`, of zet een Anthropic-sleutel in `.env` |

Tests draaien: `pytest -q`

---

## Mappen

```
state/           episodes.db — al je scripts, in SQL
start.command    dubbelklikken op macOS/Linux
start.bat        dubbelklikken op Windows
config/          brief.md, channel.yaml, tales.yaml  ← hier stuur je
src/ytauto/
  scripting/     Claude-schrijver, sjabloonschrijver, het blueprint-contract
  render/        landschappen, 31 silhouetten, 52 kinderfiguren, thumbnail
  audio/         muzieksynthesizer
  tts/           ElevenLabs en de offline teststem
  video/         ffmpeg-montage
  youtube/       upload
  ui/            bedieningspagina
out/             gerenderde video's (niet in git, altijd opnieuw te maken)
```
