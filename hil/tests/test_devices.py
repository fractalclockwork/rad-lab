import devices


def test_usb_matches():
    text = "Bus 001 Device 002: ID 1d50:6089 Great Scott Gadgets HackRF One\n"
    matches = devices.usb_matches("1d50", "6089", text)
    assert len(matches) == 1


def test_parse_hackrf_info():
    text = """
Found HackRF
Serial number: 000000000000000012345678
Firmware Version: 2023.01.1
"""
    serial, board = devices.parse_hackrf_info(text)
    assert "12345678" in serial
    assert "HackRF" in board
