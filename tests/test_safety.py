"""De veiligheidscontroles zijn wat het kanaal beschermt."""

from ytauto.config import load_config
from ytauto.planner import all_candidates
from ytauto.safety import check_blueprint, check_text
from ytauto.scripting.template_writer import write_blueprint


def test_gewone_kindertekst_is_schoon():
    assert check_text("Look! A red balloon. Can you say red?").ok


def test_eng_woord_wordt_geblokkeerd():
    report = check_text("The scary monster is here")
    assert not report.ok
    assert any("scary" in i for i in report.issues)


def test_oproep_tot_actie_wordt_geblokkeerd():
    assert not check_text("Please subscribe to our channel!").ok


def test_merknaam_wordt_geblokkeerd():
    assert not check_text("Today we play with Peppa").ok


def test_losse_letters_geven_geen_valse_treffer():
    """'die' zit in 'diet' maar mag daar niet op aanslaan."""
    assert check_text("A healthy diet and a red apple").ok


def test_alle_sjabloonafleveringen_zijn_veilig():
    cfg = load_config()
    for plan in all_candidates(cfg):
        bp = write_blueprint(cfg, plan)
        report = check_blueprint(cfg, bp)
        assert report.ok, f"{plan.key}: {report.summary()}"


def test_made_for_kids_uitzetten_blokkeert():
    cfg = load_config()
    plan = all_candidates(cfg)[0]
    bp = write_blueprint(cfg, plan)
    cfg.raw["publish"]["made_for_kids"] = False
    assert not check_blueprint(cfg, bp).ok
