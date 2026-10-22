from harness import radboards
from software import fixture


def test_fixture_pass():
    board = radboards.load_board("hackrf")
    result = fixture.run_fixture(board)
    assert result["status"] == "pass"
    assert result["metrics"]["snr_db"] >= board["min_snr_db"]


def test_fixture_writes_json(tmp_path):
    board = radboards.load_board("hackrf")
    fixture.run_fixture(board, out_dir=tmp_path)
    assert (tmp_path / "fixture.json").is_file()
