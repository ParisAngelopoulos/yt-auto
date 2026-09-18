"""Scripts laten schrijven door een taalmodel dat op je eigen computer draait.

Ollama (https://ollama.com) draait open modellen lokaal. Er is geen sleutel,
geen tegoed en geen limiet: je betaalt met de tijd van je eigen machine. Dat
is het middenpad tussen de ingebouwde verteller (altijd beschikbaar, maar hij
volgt patronen) en Claude (het beste resultaat, maar het kost geld).

Aanzetten:

    ollama pull qwen2.5:14b          # eenmalig, een paar GB
    ollama serve                     # draait meestal al vanzelf

en in channel.yaml:

    script:
      provider: auto                 # of: ollama
      ollama_model: qwen2.5:14b

De opdracht en het schema zijn precies dezelfde als die Claude krijgt. Wat
een klein model vaker fout doet is de lengte: die scripts komen er korter uit.
Lukt het helemaal niet, dan valt de pipeline terug op de ingebouwde verteller,
zodat de knop altijd iets oplevert.
"""

from __future__ import annotations

import json

import requests

from ..config import Config
from .blueprint import Blueprint, BlueprintError, validate
from .claude_writer import (WriterUnavailable, build_system_prompt,
                            build_user_prompt, output_schema)

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:14b"

# Een compleet script is zo'n 6000 tokens uitvoer. Op een gewone processor
# duurt dat een paar minuten; vandaar de ruime tijdslimiet.
TIMEOUT = 900


def host(cfg: Config) -> str:
    return str(cfg.script.get("ollama_host") or DEFAULT_HOST).rstrip("/")


def model(cfg: Config) -> str:
    return str(cfg.script.get("ollama_model") or DEFAULT_MODEL)


def installed_models(cfg: Config) -> list[str]:
    """De modellen die op deze machine staan. Lege lijst als Ollama niet draait."""
    try:
        antwoord = requests.get(f"{host(cfg)}/api/tags", timeout=3)
        antwoord.raise_for_status()
    except requests.RequestException:
        return []
    return [m.get("name", "") for m in antwoord.json().get("models", [])]


def is_available(cfg: Config) -> bool:
    """Draait Ollama, en staat het ingestelde model er?"""
    aanwezig = installed_models(cfg)
    if not aanwezig:
        return False
    gewenst = model(cfg)
    # 'qwen2.5:14b' en 'qwen2.5' verwijzen naar hetzelfde model; Ollama noemt
    # het eerste. Daarom ook op de naam voor de dubbele punt vergelijken.
    return any(naam == gewenst or naam.split(":")[0] == gewenst.split(":")[0]
               for naam in aanwezig)


def write_blueprint(
    cfg: Config,
    already_made: list[str] | None = None,
    hint: str | None = None,
) -> Blueprint:
    """Laat het lokale model een complete aflevering schrijven."""
    aanwezig = installed_models(cfg)
    if not aanwezig:
        raise WriterUnavailable(
            f"Ollama is niet bereikbaar op {host(cfg)}. Installeer het via "
            "ollama.com, of zet script.provider op 'local'."
        )
    if not is_available(cfg):
        raise WriterUnavailable(
            f"Het model {model(cfg)!r} staat niet op deze machine. "
            f"Haal het op met: ollama pull {model(cfg)}"
        )

    vorm = cfg.channel.get("format", "kids")
    payload = {
        "model": model(cfg),
        "stream": False,
        "format": output_schema(vorm),
        "messages": [
            {"role": "system", "content": build_system_prompt(cfg)},
            {"role": "user", "content": build_user_prompt(already_made or [], hint)},
        ],
        "options": {"temperature": 0.9, "num_ctx": 16384, "num_predict": 12000},
    }

    try:
        antwoord = requests.post(f"{host(cfg)}/api/chat", json=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise WriterUnavailable(f"Ollama antwoordde niet: {exc}") from exc

    if antwoord.status_code != 200:
        raise WriterUnavailable(
            f"Ollama gaf status {antwoord.status_code}: {antwoord.text[:200]}"
        )

    tekst = antwoord.json().get("message", {}).get("content", "").strip()
    if not tekst:
        raise WriterUnavailable("Ollama gaf een leeg antwoord terug.")

    try:
        data = json.loads(tekst)
    except json.JSONDecodeError as exc:
        raise BlueprintError(
            f"Het lokale model leverde geen geldige JSON: {exc}. "
            "Kleine modellen struikelen hier vaker over; probeer een groter model."
        ) from exc

    data["source"] = "ollama"
    data["format"] = vorm
    if vorm == "folklore":
        data["lesson_kind"] = data.pop("tradition", "")
        data.setdefault("items", [])
        data.setdefault("backdrop_top", "#0B1026")
        data.setdefault("backdrop_bottom", "#2A2B52")

    blueprint = validate(Blueprint.from_dict(data))
    blueprint.key = _make_key(blueprint)
    print(f"  Ollama ({model(cfg)}): {blueprint.word_count} woorden script")
    return blueprint


def _make_key(bp: Blueprint) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", bp.title.lower()).strip("-")[:60]
    return slug or "episode"


def check_credentials(cfg: Config) -> dict:
    """Voor 'ytauto check' en de bedieningspagina. Kost niets en vraagt niets."""
    aanwezig = installed_models(cfg)
    if not aanwezig:
        return {"ok": False,
                "reason": f"Ollama draait niet op {host(cfg)} (optioneel)"}
    if not is_available(cfg):
        return {"ok": False,
                "reason": f"model {model(cfg)!r} ontbreekt — ollama pull {model(cfg)}"}
    return {"ok": True, "model": model(cfg),
            "detail": f"{model(cfg)}, lokaal en gratis"}
