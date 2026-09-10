"""De database.

Hier staat het werk van de gebruiker in, dus de nadruk ligt op twee dingen:
een bestaande database mag bij het migreren niets verliezen, en een script
dat erin gaat moet er exact zo weer uit komen.
"""

import json
import sqlite3

import pytest

from ytauto.db import MIGRATIONS, Store, connect, migrate
from ytauto.scripting.blueprint import Beat, Blueprint, Item

V1_SCHEMA = """
CREATE TABLE episodes (
    key TEXT PRIMARY KEY, lesson_id TEXT NOT NULL, theme_id TEXT NOT NULL,
    title TEXT NOT NULL, status TEXT NOT NULL, video_id TEXT, duration_s REAL,
    error TEXT, created_at TEXT NOT NULL, published_at TEXT
);
"""


def maak_blueprint(key="colors:balloons", titel="Learn Colors") -> Blueprint:
    return Blueprint(
        idea="Kleuren met ballonnen", title=titel, description="Een rustige les.",
        tags=["toddler", "colors"], lesson_kind="colors",
        backdrop_top="#DCEEFB", backdrop_bottom="#F6E4C8",
        items=[Item(word="red", draw="balloon", label="RED", color="#E8483F"),
               Item(word="blue", draw="balloon", label="BLUE", color="#4A90D9")],
        beats=[Beat("intro_title", "Hello friends!", title="LEARN COLORS"),
               Beat("reveal", "Look, a red balloon!", item=0),
               Beat("teach", "This is red. Can you say red?", item=0),
               Beat("review", "Blue!", item=1)],
        source="claude", key=key,
    )


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.db")


# ---------------------------------------------------------------------------
#  Migreren
# ---------------------------------------------------------------------------


def test_verse_database_krijgt_de_nieuwste_versie(tmp_path):
    with connect(tmp_path / "nieuw.db") as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
        tabellen = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"episodes", "episode_items", "episode_beats", "episode_tags"} <= tabellen


def test_oude_database_verliest_geen_rijen(tmp_path):
    """De belangrijkste test: wie de studio al gebruikte mag niets kwijtraken."""
    pad = tmp_path / "oud.db"
    conn = sqlite3.connect(pad)
    conn.executescript(V1_SCHEMA)
    conn.execute(
        "INSERT INTO episodes VALUES ('colors:balloons','colors','balloons',"
        "'Learn Colors','uploaded','abc123',540.5,NULL,'2026-01-01T00:00:00+00:00',"
        "'2026-01-02T00:00:00+00:00')")
    conn.commit()
    conn.close()

    with connect(pad) as conn:
        rij = conn.execute("SELECT * FROM episodes WHERE key='colors:balloons'").fetchone()

    assert rij["title"] == "Learn Colors"
    assert rij["status"] == "uploaded"
    assert rij["video_id"] == "abc123"
    assert rij["duration_s"] == 540.5
    assert rij["published_at"] == "2026-01-02T00:00:00+00:00"
    assert rij["lesson_kind"] == "colors"          # heette eerst lesson_id
    assert rij["slug"] == "colors-balloons"        # afgeleid tijdens de migratie


def test_migreren_gebeurt_maar_een_keer(tmp_path):
    pad = tmp_path / "een.db"
    with connect(pad):
        pass
    conn = sqlite3.connect(pad)
    assert migrate(conn) == 0                      # tweede keer valt er niets te doen
    conn.close()


# ---------------------------------------------------------------------------
#  Script bewaren
# ---------------------------------------------------------------------------


def test_script_komt_er_exact_zo_weer_uit(store):
    bp = maak_blueprint()
    store.save_blueprint(bp)
    terug = store.load_blueprint(bp.key)

    assert terug is not None
    assert terug.title == bp.title
    assert terug.idea == bp.idea
    assert terug.tags == bp.tags
    assert [b.narration for b in terug.beats] == [b.narration for b in bp.beats]
    assert [b.mode for b in terug.beats] == [b.mode for b in bp.beats]
    assert [i.word for i in terug.items] == [i.word for i in bp.items]
    assert terug.items[0].color == "#E8483F"
    assert terug.beats[0].title == "LEARN COLORS"


def test_ook_zonder_json_kolom_compleet_terug(store):
    """De tabellen zijn op zichzelf genoeg; raw_json is de dubbele bodem."""
    bp = maak_blueprint()
    store.save_blueprint(bp)
    with connect(store.db_path) as conn:
        conn.execute("UPDATE episodes SET raw_json = NULL WHERE key = ?", (bp.key,))

    terug = store.load_blueprint(bp.key)
    assert terug is not None
    assert [b.narration for b in terug.beats] == [b.narration for b in bp.beats]
    assert [i.label for i in terug.items] == [i.label for i in bp.items]


def test_onbekende_sleutel_geeft_niets(store):
    assert store.load_blueprint("bestaat:niet") is None


def test_opnieuw_opslaan_vervangt_de_tekst_maar_niet_de_status(store):
    bp = maak_blueprint()
    store.save_blueprint(bp)
    store.mark_uploaded(bp.key, "video123")

    bp.beats.append(Beat("outro", "Bye bye!"))
    store.save_blueprint(bp)

    terug = store.load_blueprint(bp.key)
    assert terug.beats[-1].narration == "Bye bye!"
    rij = store.all_episodes()[0]
    assert rij["status"] == "uploaded" and rij["video_id"] == "video123"


def test_geen_dubbele_zinnen_na_opnieuw_opslaan(store):
    bp = maak_blueprint()
    store.save_blueprint(bp)
    store.save_blueprint(bp)
    assert len(store.load_blueprint(bp.key).beats) == len(bp.beats)


# ---------------------------------------------------------------------------
#  Zoeken en overzicht
# ---------------------------------------------------------------------------


def test_archief_toont_wat_er_is(store):
    store.save_blueprint(maak_blueprint("a:1", "Learn Colors"))
    store.save_blueprint(maak_blueprint("b:2", "Learn Shapes"))

    rijen = store.library()
    assert len(rijen) == 2
    assert all(r["beats"] == 4 for r in rijen)


def test_archief_kan_zoeken(store):
    store.save_blueprint(maak_blueprint("a:1", "Learn Colors"))
    store.save_blueprint(maak_blueprint("b:2", "Learn Shapes"))

    assert [r["key"] for r in store.library(search="Shapes")] == ["b:2"]


def test_zoeken_in_gesproken_tekst(store):
    store.save_blueprint(maak_blueprint())
    treffers = store.search_lines("red balloon")
    assert len(treffers) == 1
    assert treffers[0]["mode"] == "reveal"


def test_stats_tellen_op(store):
    store.save_blueprint(maak_blueprint("a:1"))
    store.save_blueprint(maak_blueprint("b:2"))
    s = store.stats()
    assert s["afleveringen"] == 2
    assert s["zinnen"] == 8
    assert s["woorden"] > 0


# ---------------------------------------------------------------------------
#  Binnenhalen en uitvoeren
# ---------------------------------------------------------------------------


def test_losse_bestanden_worden_opgenomen(store, tmp_path):
    out = tmp_path / "out"
    (out / "colors-balloons").mkdir(parents=True)
    maak_blueprint().save(out / "colors-balloons" / "blueprint.json")

    assert store.import_json_files(out) == ["colors:balloons"]
    assert store.load_blueprint("colors:balloons") is not None


def test_rij_zonder_script_krijgt_zijn_tekst_alsnog(store, tmp_path):
    """Rijen uit de oude boekhouding bestaan wel maar zijn leeg."""
    store.mark_planned("colors:balloons", "colors", "balloons", "Learn Colors")
    out = tmp_path / "out"
    (out / "colors-balloons").mkdir(parents=True)
    maak_blueprint().save(out / "colors-balloons" / "blueprint.json")

    assert store.import_json_files(out) == ["colors:balloons"]
    assert len(store.load_blueprint("colors:balloons").beats) == 4


def test_bestaand_script_wordt_niet_overschreven(store, tmp_path):
    store.save_blueprint(maak_blueprint())
    out = tmp_path / "out"
    (out / "colors-balloons").mkdir(parents=True)
    maak_blueprint().save(out / "colors-balloons" / "blueprint.json")
    assert store.import_json_files(out) == []


def test_onleesbaar_bestand_stopt_het_binnenhalen_niet(store, tmp_path):
    out = tmp_path / "out"
    (out / "kapot").mkdir(parents=True)
    (out / "kapot" / "blueprint.json").write_text("{dit is geen json")
    (out / "goed").mkdir(parents=True)
    maak_blueprint().save(out / "goed" / "blueprint.json")

    assert store.import_json_files(out) == ["colors:balloons"]


def test_exporteren_levert_leesbare_json(store, tmp_path):
    store.save_blueprint(maak_blueprint())
    doel = tmp_path / "export.json"
    assert store.export_all(doel) == 1

    data = json.loads(doel.read_text())
    assert data[0]["title"] == "Learn Colors"
    assert len(data[0]["beats"]) == 4


# ---------------------------------------------------------------------------
#  Eigen vragen
# ---------------------------------------------------------------------------


def test_eigen_select_werkt(store):
    store.save_blueprint(maak_blueprint())
    rijen = store.query("SELECT COUNT(*) AS n FROM episode_beats")
    assert rijen[0]["n"] == 4


@pytest.mark.parametrize("gevaarlijk", [
    "DELETE FROM episodes",
    "DROP TABLE episodes",
    "UPDATE episodes SET title='weg'",
    "INSERT INTO episodes (key) VALUES ('x')",
])
def test_alleen_lezen(store, gevaarlijk):
    """De opdrachtregel geeft een vrije vraag door; die mag niets slopen."""
    with pytest.raises(ValueError, match="SELECT"):
        store.query(gevaarlijk)


def test_mislukte_afleveringen_mogen_opnieuw(store):
    store.save_blueprint(maak_blueprint())
    store.mark_failed("colors:balloons", "ffmpeg kapot")
    assert "colors:balloons" not in store.taken_keys()
    # het script blijft wel bewaard
    assert store.load_blueprint("colors:balloons") is not None


# ---------------------------------------------------------------------------
#  Volksverhalen
# ---------------------------------------------------------------------------


def maak_verhaal():
    from ytauto.scripting.blueprint import StoryScene

    return Blueprint(
        idea="test", title="The Tale", description="Een verhaal.", tags=["folklore"],
        lesson_kind="norse", backdrop_top="#0B1026", backdrop_bottom="#2A2B52",
        items=[],
        scenes=[StoryScene(setting="forest", time="night", weather="mist",
                           caption="The wood",
                           subjects=[{"draw": "traveller", "x": 0.4,
                                      "scale": 0.16, "depth": 0.9}]),
                StoryScene(setting="coast", time="dawn")],
        beats=[Beat("title", "The Tale.", scene=0, title="THE TALE"),
               Beat("tell", "He walked into the wood.", scene=0),
               Beat("close", "He came out at the sea.", scene=1)],
        format="folklore", key="the-tale",
    )


def test_verhaal_komt_er_exact_zo_weer_uit(store):
    bp = maak_verhaal()
    store.save_blueprint(bp)
    terug = store.load_blueprint(bp.key)

    assert terug.format == "folklore"
    assert len(terug.scenes) == 2
    assert terug.scenes[0].setting == "forest"
    assert terug.scenes[0].subjects[0]["draw"] == "traveller"
    assert [b.scene for b in terug.beats] == [0, 0, 1]


def test_verhaal_komt_ook_zonder_json_kolom_terug(store):
    """De tabellen moeten op zichzelf genoeg zijn, ook voor verhalen."""
    bp = maak_verhaal()
    store.save_blueprint(bp)
    with connect(store.db_path) as conn:
        conn.execute("UPDATE episodes SET raw_json = NULL WHERE key = ?", (bp.key,))

    terug = store.load_blueprint(bp.key)
    assert terug.format == "folklore"
    assert [(s.setting, s.time) for s in terug.scenes] == [("forest", "night"), ("coast", "dawn")]
    assert [b.scene for b in terug.beats] == [0, 0, 1]
    assert [b.narration for b in terug.beats] == [b.narration for b in bp.beats]


def test_oude_database_krijgt_de_nieuwe_kolommen(tmp_path):
    """Een database van voor de volksverhalen mag niet omvallen."""
    pad = tmp_path / "oud.db"
    conn = sqlite3.connect(pad)
    conn.executescript(V1_SCHEMA)
    conn.execute("INSERT INTO episodes VALUES ('colors:balloons','colors','balloons',"
                 "'Learn Colors','planned',NULL,NULL,NULL,'2026-01-01T00:00:00+00:00',NULL)")
    conn.commit()
    conn.close()

    with connect(pad) as conn:
        rij = conn.execute("SELECT * FROM episodes").fetchone()
    assert rij["format"] == "kids"          # bestaande rijen zijn leervideo's
    assert rij["scenes_json"] is None
