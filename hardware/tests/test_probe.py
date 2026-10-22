from environment import container
from hardware import probe


def test_parse_hackrf_info():
    text = """
Found HackRF
Serial number: 000000000000000012345678
Firmware Version: 2023.01.1
"""
    serial, board = probe.parse_hackrf_info(text)
    assert "12345678" in serial
    assert "HackRF" in board


def test_hardware_present_absent_when_no_match(monkeypatch):
    monkeypatch.setattr(container, "lsusb_text", lambda: "Bus 001 Device 001: 1d6b:0002\n")
    assert probe.hardware_present({"id": "hackrf", "usb_vendor": "1d50", "usb_product": "6089"}) is False


def test_hardware_present_when_match(monkeypatch):
    monkeypatch.setattr(
        container,
        "lsusb_text",
        lambda: "Bus 001 Device 003: 1d50:6089 Great Scott Gadgets HackRF\n",
    )
    assert probe.hardware_present({"id": "hackrf", "usb_vendor": "1d50", "usb_product": "6089"}) is True
