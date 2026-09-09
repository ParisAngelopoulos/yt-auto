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
from .blueprint import LESSON_KINDS, MODES, Blueprint, BlueprintError, validate

BRIEF_PATH = ROOT / "config" / "brief.md"


class WriterUnavailable(RuntimeError):
    """Geen API-sleutel of de anthropic-package ontbreekt."""


# ---------------------------------------------------------------------------
#  Schema
# ---------------------------------------------------------------------------


def output_schema() -> dict:
    """JSON-schema dat de API afdwingt. Alles verplicht, niets extra's."""
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

    # Streamen omdat een compleet script makkelijk 6000 tokens uitvoer is;
    # zonder streaming loopt zo'n aanroep tegen de HTTP-timeout aan.
    with client.messages.stream(
        model=model,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        system=build_system_prompt(cfg),
        messages=[{"role": "user", "content": build_user_prompt(already_made or [], hint)}],
        output_config={"format": {"type": "json_schema", "schema": output_schema()}},
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
