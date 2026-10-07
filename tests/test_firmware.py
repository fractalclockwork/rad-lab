import firmware
import radboards


def test_serials_match_short_and_full():
    full = "0000000000000000a06063c823864f5f"
    assert firmware.serials_match(full, full)
    assert firmware.serials_match(full, "a06063c823864f5f")
    assert firmware.serials_match("a06063c823864f5f", full)
    assert not firmware.serials_match(full, "deadbeef")


def test_parse_firmware_version():
    text = "Firmware Version: 2021.03.1 (API:1.04)\n"
    assert firmware.parse_firmware_version(text) == "2021.03.1"


def test_hackrf_yaml_firmware_fields():
    board = radboards.load_board("hackrf")
    assert board["firmware_target"] == "2026.01.3"
    assert board["firmware_bin"] == "hackrf_one_usb.bin"
    assert "firmware-bin/hackrf_one_usb.bin" in board["firmware_bin_path"]
