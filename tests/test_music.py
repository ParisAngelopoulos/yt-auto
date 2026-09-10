"""De muzieksynthesizer.

De aanleiding voor deze tests: bij bepaalde lengtes begon de laatste noot
voorbij het einde van het spoor. Een negatieve slicelengte leverde dan bijna
de hele noot op in plaats van niets, en de hele render klapte eruit. Dat is
precies het soort fout dat pas opvalt als je hem draait, dus staat de
maatgrens hier expliciet in.
"""

import numpy as np
import pytest

from ytauto.audio.music import BAR_SECONDS, SAMPLE_RATE, build_music, synth_bed

# Rond de maatgrens en vlak erna zit het gevaar: daar valt een noot buiten.
RAND_GEVALLEN = [
    0.5, 1.0, 2.39, BAR_SECONDS, 2.41, 3.0, 4.79, 2 * BAR_SECONDS, 4.81,
    5.5, 7.19, 3 * BAR_SECONDS, 7.21, 9.6, 12.0, 20.0, 65.4, 74.5, 120.0,
]


@pytest.mark.parametrize("seconden", RAND_GEVALLEN)
def test_elke_lengte_levert_muziek(seconden):
    bed = synth_bed(seconden, seed=7)
    assert len(bed) == int(seconden * SAMPLE_RATE)
    assert np.all(np.isfinite(bed))


@pytest.mark.parametrize("seconden", RAND_GEVALLEN)
def test_niets_stuurt_over(seconden):
    """Oversturing klinkt als geknetter en is bij kindercontent onacceptabel."""
    assert np.max(np.abs(synth_bed(seconden, seed=3))) <= 1.0


def test_dezelfde_seed_geeft_dezelfde_muziek():
    assert np.array_equal(synth_bed(12.0, seed=42), synth_bed(12.0, seed=42))


def test_andere_seed_geeft_andere_muziek():
    assert not np.array_equal(synth_bed(12.0, seed=1), synth_bed(12.0, seed=2))


def test_begint_en_eindigt_stil():
    """Een harde inzet schrikt op; er hoort een vloeiende fade te zitten."""
    bed = synth_bed(30.0, seed=5)
    rand = int(0.15 * SAMPLE_RATE)
    midden = np.max(np.abs(bed[len(bed) // 2 - rand:len(bed) // 2 + rand]))
    assert np.max(np.abs(bed[:rand])) < midden * 0.5
    assert np.max(np.abs(bed[-rand:])) < midden * 0.5


def test_schrijft_een_leesbaar_wav(tmp_path):
    import wave

    pad = build_music(tmp_path / "bed.wav", 6.0, seed=1)
    with wave.open(str(pad)) as handle:
        assert handle.getnchannels() == 1
        assert handle.getframerate() == SAMPLE_RATE
        assert handle.getnframes() == int(6.0 * SAMPLE_RATE)
