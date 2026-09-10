"""Claude bedenkt het idee en schrijft alle gesproken tekst.

De opzet is bewust gesplitst: Claude levert de woorden en de itemkeuze,
de code bouwt daar het beeld bij. Daardoor kan een script nooit vragen om
een figuur dat niet bestaat, terwijl Claude wel volledig vrij is in taal,
onderwerp en opbouw.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import ROOT, Config
from ..render.objects import available_shapes
from ..render.silhouettes import available_silhouettes
from ..render.story_scene import available_settings, available_times, available_weather
from .blueprint import (LESSON_KINDS, MODES, STORY_MODES, Blueprint, BlueprintError,
                        validate)

BRIEF_PATH = ROOT / "config" / "brief.md"


class WriterUnavailable(RuntimeError):
    """Geen API-sleutel of de anthropic-package ontbreekt."""


# ---------------------------------------------------------------------------
#  Schema
# ---------------------------------------------------------------------------


def output_schema(format: str = "kids") -> dict:
    """JSON-schema dat de API afdwingt. Alles verplicht, niets extra's."""
    if format == "folklore":
        return story_schema()
    return kids_schema()


def story_schema() -> dict:
    """Schema voor een volksverhaal.

    De enums doen het echte werk: Claude kan alleen plekken, tijden en
    figuren kiezen die de renderer ook kan tekenen. Een verzonnen silhouet
    komt er zo niet doorheen.
    """
    subject = {
        "type": "object",
        "properties": {
            "draw": {"type": "string", "enum": available_silhouettes()},
            "x": {"type": "number"},
            "scale": {"type": "number"},
            "depth": {"type": "number"},
        },
        "required": ["draw", "x", "scale", "depth"],
        "additionalProperties": False,
    }
    scene = {
        "type": "object",
        "properties": {
            "setting": {"type": "string", "enum": available_settings()},
            "time": {"type": "string", "enum": available_times()},
            "weather": {"type": "string", "enum": available_weather()},
            "caption": {"type": ["string", "null"]},
            "subjects": {"type": "array", "items": subject},
        },
        "required": ["setting", "time", "weather", "caption", "subjects"],
        "additionalProperties": False,
    }
    beat = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": list(STORY_MODES)},
            "narration": {"type": "string"},
            "scene": {"type": "integer"},
            "title": {"type": ["string", "null"]},
            "subtitle": {"type": ["string", "null"]},
        },
        "required": ["mode", "narration", "scene", "title", "subtitle"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "idea": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "tradition": {"type": "string"},
            "scenes": {"type": "array", "items": scene},
            "beats": {"type": "array", "items": beat},
        },
        "required": ["idea", "title", "description", "tags", "tradition",
                     "scenes", "beats"],
        "additionalProperties": False,
    }


def kids_schema() -> dict:
    shapes = available_shapes()
    return {
        "type": "object",
        "properties": {
            "idea": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "lesson_kind": {"type": "string", "enum": list(LESSON_KINDS)},
            "backdrop_top": {"type": "string"},
            "backdrop_bottom": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "word": {"type": "string"},
                        "draw": {"type": "string", "enum": shapes},
                        "label": {"type": "string"},
                        "color": {"type": ["string", "null"]},
                        "count": {"type": ["integer", "null"]},
                    },
                    "required": ["word", "draw", "label", "color", "count"],
                    "additionalProperties": False,
                },
            },
            "beats": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "enum": list(MODES)},
                        "narration": {"type": "string"},
                        "item": {"type": ["integer", "null"]},
                        "title": {"type": ["string", "null"]},
                        "subtitle": {"type": ["string", "null"]},
                    },
                    "required": ["mode", "narration", "item", "title", "subtitle"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "idea", "title", "description", "tags", "lesson_kind",
            "backdrop_top", "backdrop_bottom", "items", "beats",
        ],
        "additionalProperties": False,
    }


# ---------------------------------------------------------------------------
#  Prompt
# ---------------------------------------------------------------------------


def build_system_prompt(cfg: Config) -> str:
    if cfg.channel.get("format", "kids") == "folklore":
        return build_story_prompt(cfg)
    return build_kids_prompt(cfg)


def build_story_prompt(cfg: Config) -> str:
    brief = BRIEF_PATH.read_text(encoding="utf-8") if BRIEF_PATH.exists() else ""
    minuten = cfg.video["target_duration_minutes"]

    return f"""Je hertelt volksverhalen, mythen en sagen voor een YouTube-kanaal.

# Kanaal
Naam: {cfg.channel['name']}
Taal van de video: {cfg.channel['language']} — schrijf ALLE narration in die taal.
Publiek: {cfg.channel['audience']}
Streeflengte: ongeveer {minuten} minuten gesproken tekst.

# Briefing van de eigenaar
{brief}

# Wat je oplevert

Een blueprint met `scenes` en `beats`.

`scenes` zijn de plekken waar het verhaal speelt. Vier tot acht is genoeg;
meerdere beats delen dezelfde scene en dat hoort ook zo, want het beeld moet
blijven staan terwijl er verteld wordt. Elke scene heeft:

  - `setting`: {", ".join(available_settings())}
  - `time`: {", ".join(available_times())}
  - `weather`: none, mist, rain of snow
  - `caption`: een korte plaatsaanduiding die één keer in beeld komt bij
    aankomst, of null
  - `subjects`: nul tot vier silhouetten in het landschap. Elk figuur heeft:
      `draw`  — UITSLUITEND uit deze lijst:
                {", ".join(available_silhouettes())}
      `x`     — 0 is links, 1 is rechts. Zet niets precies in het midden
                tenzij het het onderwerp van de scene is.
      `scale` — hoogte als deel van het beeld. Een mens in de verte is 0.08,
                dichtbij 0.20. Een burcht 0.15, een boom 0.25, een draak 0.22.
      `depth` — 0 is ver weg, 1 is vlakbij. Bepaalt hoe donker het figuur is
                en hoe laag het staat. Gebruik 0.5 voor iets aan de horizon,
                0.9 voor iets op de voorgrond.

`beats` zijn de scenes op volgorde. Elke beat heeft een `mode`, de gesproken
tekst, en `scene`: de index (0-gebaseerd) van de plek waar hij speelt.

  - `title`  de titelkaart. Vul `title` en `subtitle` in; de subtitle noemt
             de herkomst, bijvoorbeeld "Een sage uit Noorwegen".
  - `open`   waar en wanneer het verhaal begint
  - `tell`   het verhaal zelf; hier zitten de meeste beats
  - `turn`   een wending. Laat de scene hier veranderen.
  - `speech` iemand spreekt
  - `close`  de afloop
  - `moral`  wat het verhaal wil zeggen, zonder belerend te worden
  - `source` één beat aan het eind over de herkomst van het verhaal

Begin met precies één `title` en eindig met `close`, dan `moral`, dan `source`.

# Hoe je vertelt

Eén zin per beat, hooguit twee. De verteller leest voor; korte zinnen geven
hem lucht en de kijker tijd om het beeld te zien. Vermijd bijzinnen die over
drie regels doorlopen.

Beschrijf wat er gebeurt, niet wat je ervan vindt. "Hij liep de brug over en
keek niet om" is sterker dan "Hij was heel dapper".

Gebruik de tijd van de dag als verteller. Een verhaal dat in de schemer
begint en in het donker eindigt, vertelt zichzelf half.

# Herkomst en respect

Vertel bestaande verhalen na. Ze zijn eeuwenoud en dus vrij van rechten,
maar een specifieke vertaling of hervertelling kan dat niet zijn: schrijf
altijd in je eigen woorden en neem geen zinnen letterlijk over.

Noem de traditie waar het verhaal uit komt, en noem hem juist. Verzin geen
"oude legende" die niet bestaat, en schuif geen verhaal toe aan een volk waar
het niet vandaan komt. Als je een verhaal niet goed genoeg kent om het
correct toe te schrijven, kies dan een ander.

Behandel levende tradities met dezelfde zorg als je eigen. Verhalen die in
een cultuur een heilige of ceremoniële betekenis hebben zijn geen materiaal
voor een kanaal; laat die staan.

`tradition` is een kort kenmerk van de herkomst in kleine letters, zoals
"norse", "japanese", "irish", "slavic", "greek".

# Lengte
De verteller spreekt ongeveer 140 woorden per minuut. Voor {minuten} minuten
heb je dus rond de {int(minuten) * 140} woorden nodig, verdeeld over ongeveer
{int(minuten) * 9} beats.

# Titel en beschrijving
`title` is de YouTube-titel: de naam van het verhaal, eventueel met de
herkomst erachter. Geen clickbait, geen hoofdletters door elkaar.
`description` is drie tot vijf zinnen over het verhaal en waar het vandaan
komt. `tags` zijn zes tot twaalf korte zoektermen."""


def build_kids_prompt(cfg: Config) -> str:
    brief = BRIEF_PATH.read_text(encoding="utf-8") if BRIEF_PATH.exists() else ""
    shapes = ", ".join(available_shapes())
    minutes = cfg.video["target_duration_minutes"]

    return f"""Je schrijft afleveringen voor een YouTube-kanaal met leervideo's voor jonge kinderen.

# Kanaal
Naam: {cfg.channel['name']}
Taal van de video: {cfg.channel['language']} — schrijf ALLE narration in die taal.
Publiek: {cfg.channel['audience']}
Streeflengte: ongeveer {minutes} minuten gesproken tekst.

# Briefing van de eigenaar
{brief}

# Hoe je de aflevering oplevert

Je levert een blueprint met `items` en `beats`.

`items` zijn de dingen die geleerd worden. Elk item heeft:
  - `word`: het woord dat de verteller uitspreekt, kleine letters ("red", "cow", "three")
  - `draw`: welk figuur getekend wordt — UITSLUITEND uit deze lijst:
    {shapes}
  - `label`: wat groot in beeld komt, hoofdletters ("RED", "COW", "3")
  - `color`: hexkleur zoals "#E8483F" wanneer de kleur de leerstof is of het
    figuur geen eigen kleur heeft (vormen). Anders `null`, dan krijgt het
    figuur zijn natuurlijke kleur — een koe wordt dan wit met zwart, wat
    bijna altijd de juiste keuze is bij dieren, fruit en voertuigen.
  - `count`: alleen bij tellen het aantal (1 tot en met 10). Anders `null`.

`beats` zijn de scenes op volgorde. Elke beat heeft een `mode`:
  - `intro_title`   opening met de titel in beeld (`title` invullen)
  - `intro_preview` vertelt wat het kind gaat leren
  - `card`          tussenkaart voor een nieuwe ronde (`title` invullen)
  - `reveal`        toon het item, benoem het          (`item` invullen)
  - `teach`         zeg het woord, vraag het na te zeggen
  - `echo`          samen herhalen en prijzen
  - `question`      stel een vraag over het item; er volgt vanzelf stilte
  - `answer`        geef het antwoord en prijs
  - `find_question` drie dingen in beeld, vraag het juiste aan te wijzen
  - `find_answer`   wijs het juiste aan en prijs
  - `review`        snelle herhaling, één of twee woorden
  - `outro`         warme afsluiting
  - `outro_title`   laatste beeld met een groetwoord (`title` invullen)

Regels voor beats:
  - `item` is de index in `items` (0-gebaseerd), of `null` bij intro, card en outro.
  - `question` moet altijd direct gevolgd worden door `answer` over hetzelfde item.
  - `find_question` moet altijd direct gevolgd worden door `find_answer`.
  - Voor `find_question` zijn minstens drie items nodig.
  - Vul `title` en `subtitle` alleen bij `intro_title`, `card` en `outro_title`.

# Lengte
De verteller spreekt ongeveer 140 woorden per minuut. Voor {minutes} minuten
heb je dus rond de {int(minutes) * 140} woorden nodig, verdeeld over ongeveer
{int(minutes) * 14} beats. Ga liever iets over dan eronder.

# Achtergrond
`backdrop_top` en `backdrop_bottom` vormen een zacht verticaal verloop achter
alles. Kies rustige, lichte tinten die bij het onderwerp passen. Nooit fel of
donker: het beeld moet achtergrond blijven, de figuren zijn de hoofdrol.

# Titel en beschrijving
`title` is de YouTube-titel. Beschrijvend en gewoon leesbaar, geen hoofdletters
door elkaar, geen clickbait, geen emoji-spam.
`description` is twee tot vier zinnen over wat het kind leert, gericht aan de
ouder. Geen links, geen oproepen tot actie.
`tags` zijn zes tot twaalf korte zoektermen."""


def build_user_prompt(already_made: list[str], hint: str | None = None) -> str:
    lines = ["Bedenk en schrijf de volgende aflevering."]
    if hint:
        lines.append(f"\nDe eigenaar vraagt specifiek om: {hint}")
    if already_made:
        recent = already_made[-25:]
        lines.append(
            "\nDeze afleveringen bestaan al. Kies een duidelijk ander onderwerp "
            "(en niet dezelfde soort les als de laatste twee):\n- "
            + "\n- ".join(recent)
        )
    lines.append("\nLever alleen de blueprint volgens het schema.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  API-aanroep
# ---------------------------------------------------------------------------


def write_blueprint(
    cfg: Config,
    already_made: list[str] | None = None,
    hint: str | None = None,
) -> Blueprint:
    """Laat Claude een complete aflevering bedenken en schrijven."""
    try:
        import anthropic
    except ImportError as exc:                                  # pragma: no cover
        raise WriterUnavailable(
            "De package 'anthropic' ontbreekt. Draai: pip install -r requirements.txt"
        ) from exc

    api_key = cfg.secrets.anthropic_api_key
    if not api_key:
        raise WriterUnavailable(
            "ANTHROPIC_API_KEY ontbreekt. Zet hem in .env of in je GitHub Actions secrets."
        )

    client = anthropic.Anthropic(api_key=api_key)
    model = cfg.script.get("model", "claude-opus-5")
    vorm = cfg.channel.get("format", "kids")

    # Streamen omdat een compleet script makkelijk 6000 tokens uitvoer is;
    # zonder streaming loopt zo'n aanroep tegen de HTTP-timeout aan.
    with client.messages.stream(
        model=model,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        system=build_system_prompt(cfg),
        messages=[{"role": "user", "content": build_user_prompt(already_made or [], hint)}],
        output_config={"format": {"type": "json_schema", "schema": output_schema(vorm)}},
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", "") or ""
        raise BlueprintError(f"Claude wees het verzoek af. {detail}".strip())

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise BlueprintError("Claude gaf geen tekst terug.")

    data = json.loads(text)
    data["source"] = "claude"
    data["format"] = vorm
    if vorm == "folklore":
        # De traditie neemt de plek in van het lesonderwerp; de planner
        # gebruikt dat veld om afwisseling te bewaken.
        data["lesson_kind"] = data.pop("tradition", "")
        data.setdefault("items", [])
        data.setdefault("backdrop_top", "#0B1026")
        data.setdefault("backdrop_bottom", "#2A2B52")
    blueprint = validate(Blueprint.from_dict(data))

    usage = response.usage
    blueprint.key = _make_key(blueprint)
    print(
        f"  Claude ({model}): {usage.input_tokens} tokens in, "
        f"{usage.output_tokens} uit — {blueprint.word_count} woorden script"
    )
    return blueprint


def _make_key(bp: Blueprint) -> str:
    """Korte, unieke sleutel voor de map- en databasenaam."""
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", bp.title.lower()).strip("-")[:60]
    return slug or "episode"


def check_credentials(cfg: Config) -> dict:
    """Kijkt of de sleutel werkt, zonder een script te schrijven.

    Gebruikt de modellenlijst: dat is een gewone opvraging zonder tokens,
    dus het testen van je sleutel kost niets.
    """
    api_key = cfg.secrets.anthropic_api_key
    if not api_key:
        return {"ok": False, "reason": "Geen ANTHROPIC_API_KEY gevonden"}

    try:
        import anthropic
    except ImportError:
        return {"ok": False, "reason": "De package 'anthropic' is niet geïnstalleerd"}

    gewenst = cfg.script.get("model", "claude-opus-5")
    try:
        modellen = [m.id for m in anthropic.Anthropic(api_key=api_key).models.list()]
    except Exception as exc:                                    # noqa: BLE001
        naam = type(exc).__name__
        if "Authentication" in naam:
            return {"ok": False, "reason": "De sleutel wordt geweigerd. Kloppen alle tekens?"}
        if "PermissionDenied" in naam:
            return {"ok": False, "reason": "De sleutel mag hier niet bij. Staat er tegoed op je account?"}
        if "Connection" in naam or "Timeout" in naam:
            return {"ok": False, "reason": "Claude is niet bereikbaar. Staat je internet aan?"}
        return {"ok": False, "reason": f"{naam}: {str(exc)[:160]}"}

    if gewenst not in modellen:
        return {
            "ok": True,
            "model": gewenst,
            "warning": (
                f"Het ingestelde model {gewenst!r} zit niet in de lijst van je "
                f"account. Pas script.model aan in channel.yaml."
            ),
        }
    return {"ok": True, "model": gewenst}
