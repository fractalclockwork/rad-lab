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


def test_firmware_versions_match_pluto():
    assert firmware.firmware_versions_match("v0.39", "v0.39")
    assert firmware.firmware_versions_match("v0.39", "0.39")
    assert firmware.firmware_versions_match("0.39", "v0.39")
    assert not firmware.firmware_versions_match("v0.39", "v0.38")


def test_hackrf_yaml_firmware_fields():
    board = radboards.load_board("hackrf")
    assert board["firmware_target"] == "2026.01.3"
    assert board["firmware_bin"] == "hackrf_one_usb.bin"
    assert "firmware-bin/hackrf_one_usb.bin" in board["firmware_bin_path"]


def test_pluto_yaml_firmware_fields():
    board = radboards.load_board("pluto")
    assert board["firmware_target"] == "v0.39"
    assert board["firmware_bin"] == "pluto.frm"
    assert board["firmware_bin_path"].endswith("pluto.frm")
    assert board["soapy_driver"] == "plutosdr"
