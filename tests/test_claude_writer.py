"""Het pad waar Claude het script schrijft.

De API zelf wordt niet aangeroepen; wat hier getest wordt is of een antwoord
in het afgesproken formaat ook echt door de hele keten komt: valideren,
omzetten naar scenes, en renderen. Dat is precies waar het stukloopt als het
schema en de renderer uit elkaar groeien.
"""

import json
from dataclasses import dataclass

import pytest

from ytauto.config import load_config
from ytauto.render.objects import available_shapes
from ytauto.render.scene import render_scene
from ytauto.scripting import claude_writer
from ytauto.scripting.blueprint import LESSON_KINDS, MODES, Blueprint, to_scenes, validate
from ytauto.scripting.claude_writer import WriterUnavailable, output_schema


def antwoord_van_claude() -> dict:
    """Zoals de API het volgens het schema teruggeeft."""
    return {
        "idea": "Kleuren leren met ballonnen",
        "title": "Learn Colors with Balloons | Fun Learning for Toddlers",
        "description": "A gentle video where your little one learns four colors.",
        "tags": ["toddler learning", "colors for kids", "preschool"],
        "lesson_kind": "colors",
        "backdrop_top": "#DCEEFB",
        "backdrop_bottom": "#F6E4C8",
        "items": [
            {"word": "red", "draw": "balloon", "label": "RED",
             "color": "#E8483F", "count": None},
            {"word": "blue", "draw": "balloon", "label": "BLUE",
             "color": "#4A90D9", "count": None},
            {"word": "yellow", "draw": "balloon", "label": "YELLOW",
             "color": "#F4CE47", "count": None},
        ],
        "beats": [
            {"mode": "intro_title", "narration": "Hello friends!",
             "item": None, "title": "LEARN COLORS", "subtitle": "Balloons"},
            {"mode": "reveal", "narration": "Look, a red balloon!",
             "item": 0, "title": None, "subtitle": None},
            {"mode": "teach", "narration": "This is red. Can you say red?",
             "item": 0, "title": None, "subtitle": None},
            {"mode": "question", "narration": "What color is this balloon?",
             "item": 1, "title": None, "subtitle": None},
            {"mode": "answer", "narration": "Yes, it is blue!",
             "item": 1, "title": None, "subtitle": None},
            {"mode": "find_question", "narration": "Can you find the yellow one?",
             "item": 2, "title": None, "subtitle": None},
            {"mode": "find_answer", "narration": "There it is! Well done.",
             "item": 2, "title": None, "subtitle": None},
            {"mode": "outro_title", "narration": "Bye bye!",
             "item": None, "title": "BYE BYE!", "subtitle": "Tiny Sprout"},
        ],
    }


# ---------------------------------------------------------------------------
#  Schema
# ---------------------------------------------------------------------------


def test_schema_staat_alleen_bestaande_figuren_toe():
    schema = output_schema()
    toegestaan = schema["properties"]["items"]["items"]["properties"]["draw"]["enum"]
    assert set(toegestaan) == set(available_shapes())


def test_schema_dwingt_alle_velden_af():
    """Zonder 'required' op alles kan de API velden weglaten die de code verwacht."""
    schema = output_schema()
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False

    for tak in ("items", "beats"):
        deel = schema["properties"][tak]["items"]
        assert set(deel["required"]) == set(deel["properties"])
        assert deel["additionalProperties"] is False


def test_schema_kent_dezelfde_modes_als_de_renderer():
    schema = output_schema()
    assert set(schema["properties"]["beats"]["items"]["properties"]["mode"]["enum"]) == set(MODES)
    assert set(schema["properties"]["lesson_kind"]["enum"]) == set(LESSON_KINDS)


# ---------------------------------------------------------------------------
#  Antwoord verwerken
# ---------------------------------------------------------------------------


def test_antwoord_wordt_een_geldige_blueprint():
    bp = validate(Blueprint.from_dict(antwoord_van_claude()))
    assert bp.title.startswith("Learn Colors")
    assert len(bp.items) == 3
    assert bp.word_count > 0


def test_elke_scene_uit_een_claude_script_rendert():
    bp = validate(Blueprint.from_dict(antwoord_van_claude()))
    scenes = to_scenes(bp, seed=5)
    assert len(scenes) == len(bp.beats)
    for scene in scenes:
        beeld = render_scene(scene.visual, (320, 180), seed=1)
        assert beeld.size == (320, 180)


def test_vraag_en_antwoord_tonen_hetzelfde_beeld():
    """Als de afleiders tussen vraag en antwoord verspringen, raakt het kind
    de draad kwijt en klopt de gemarkeerde keuze niet meer."""
    bp = validate(Blueprint.from_dict(antwoord_van_claude()))
    scenes = to_scenes(bp, seed=5)
    vraag = next(s for s in scenes if s.id.endswith("find_question"))
    antwoord = next(s for s in scenes if s.id.endswith("find_answer"))

    getekend = lambda scene: [o["draw"] for o in scene.visual["objects"]]
    kleuren = lambda scene: [o["color"] for o in scene.visual["objects"]]
    assert getekend(vraag) == getekend(antwoord)
    assert kleuren(vraag) == kleuren(antwoord)
    assert antwoord.visual["highlight"] is not None


def test_gemarkeerde_keuze_wijst_naar_het_juiste_item():
    bp = validate(Blueprint.from_dict(antwoord_van_claude()))
    scenes = to_scenes(bp, seed=5)
    antwoord = next(s for s in scenes if s.id.endswith("find_answer"))
    doel = bp.items[2]                       # de find-beat verwijst naar item 2
    gekozen = antwoord.visual["objects"][antwoord.visual["highlight"]]
    assert gekozen["color"] == doel.color


def test_gehallucineerd_figuur_wordt_geweigerd():
    """Mocht het schema ooit versoepeld worden, dan vangt de validatie het."""
    data = antwoord_van_claude()
    data["items"][0]["draw"] = "eenhoorn"
    with pytest.raises(Exception, match="bestaat niet"):
        validate(Blueprint.from_dict(data))


# ---------------------------------------------------------------------------
#  API-aanroep
# ---------------------------------------------------------------------------


def test_zonder_sleutel_een_duidelijke_melding(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = load_config()
    cfg.secrets.anthropic_api_key = ""
    with pytest.raises(WriterUnavailable, match="ANTHROPIC_API_KEY"):
        claude_writer.write_blueprint(cfg)


def test_volledige_aanroep_met_een_nagebootste_api(monkeypatch):
    """Controleert de aanroep zelf: model, streaming en het uitlezen."""
    gebruikt = {}

    @dataclass
    class Blok:
        type: str
        text: str

    class Antwoord:
        content = [Blok("text", json.dumps(antwoord_van_claude()))]
        stop_reason = "end_turn"
        stop_details = None

        class usage:
            input_tokens = 900
            output_tokens = 2400

    class Stream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_final_message(self):
            return Antwoord()

    class Messages:
        def stream(self, **kwargs):
            gebruikt.update(kwargs)
            return Stream()

    class NepClient:
        def __init__(self, api_key=None):
            self.messages = Messages()

    monkeypatch.setattr("anthropic.Anthropic", NepClient)

    cfg = load_config()
    cfg.secrets.anthropic_api_key = "test-sleutel"
    bp = claude_writer.write_blueprint(cfg, already_made=["Learn Shapes"], hint="iets met kleuren")

    assert bp.source == "claude"
    assert bp.key == "learn-colors-with-balloons-fun-learning-for-toddlers"
    assert gebruikt["model"] == cfg.script["model"]
    assert gebruikt["output_config"]["format"]["type"] == "json_schema"
    assert gebruikt["thinking"] == {"type": "adaptive"}
    # De al gemaakte titels en de wens moeten allebei in de prompt staan.
    prompt = gebruikt["messages"][0]["content"]
    assert "Learn Shapes" in prompt and "iets met kleuren" in prompt


def test_weigering_geeft_een_leesbare_fout(monkeypatch):
    class Details:
        explanation = "past niet binnen het beleid"

    class Antwoord:
        content = []
        stop_reason = "refusal"
        stop_details = Details()

    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self): return Antwoord()

    class Messages:
        def stream(self, **kwargs): return Stream()

    class NepClient:
        def __init__(self, api_key=None): self.messages = Messages()

    monkeypatch.setattr("anthropic.Anthropic", NepClient)
    cfg = load_config()
    cfg.secrets.anthropic_api_key = "test-sleutel"
    with pytest.raises(Exception, match="wees het verzoek af"):
        claude_writer.write_blueprint(cfg)
