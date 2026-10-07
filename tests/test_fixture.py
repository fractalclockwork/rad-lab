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


def test_fixture_writes_json(tmp_path):
    board = radboards.load_board("hackrf")
    fixture.run_fixture(board, out_dir=tmp_path)
    assert (tmp_path / "fixture.json").is_file()
