import numpy as np

import fixture
import radboards


def test_fixture_passes_for_hackrf():
    board = radboards.load_board("hackrf")
    result = fixture.run_fixture(board)
    assert result["status"] == "pass"
    assert result["metrics"]["snr_db"] >= board["min_snr_db"]


def test_measure_tone_snr_detects_peak():
    sr = 2_000_000
    offset = 100_000
    iq = fixture.synthesize_tone(sr, offset, 8192, snr_db=30)
    metrics = fixture.measure_tone_snr(iq, sr, offset)
    assert abs(metrics["peak_hz"] - offset) < sr / 8192 * 4
    assert metrics["snr_db"] > 15


def test_measure_tone_snr_ignores_dc_spike():
    # HackRF (and all quadrature receivers) show a strong DC/LO-leakage spike.
    # It is a measurement artifact, so the reported peak must land on the tone,
    # not on the 0 Hz artifact.
    sr = 2_000_000
    offset = 100_000
    n = 8192
    iq = fixture.synthesize_tone(sr, offset, n, snr_db=30)
    # Add a very strong DC bias (bigger than the tone) to emulate the spike.
    iq = iq + 5.0  # type: ignore[operator]
    metrics = fixture.measure_tone_snr(np.asarray(iq, dtype=np.complex64), sr, offset)
    assert abs(metrics["peak_hz"] - offset) < sr / n * 4


def test_fixture_writes_json(tmp_path):
    board = radboards.load_board("hackrf")
    fixture.run_fixture(board, out_dir=tmp_path)
    assert (tmp_path / "fixture.json").is_file()
