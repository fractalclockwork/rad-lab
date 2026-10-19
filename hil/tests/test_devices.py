import subprocess
import sys

import devices


def test_run_text_always_uses_container(monkeypatch):
    """SDR binaries must ALWAYS run inside rad-lab-sdr, never on the dev-host.

    Even with a host binary present (e.g. a dev-machine with hackrf_info in
    PATH, or SoapySDR installed), run_text must prefix the docker command so the
    container image's toolchain executes. This enforces the repository rule that
    RF hardware is never directly exercised on the dev-host.
    """
    seen = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    for binary in devices.SDR_BINARIES:
        code, text = devices.run_text([binary], usb=True)
        assert code == 0
        argv = seen[-1]
        assert argv[0] == "docker"
        assert argv[1] == "run"
        assert "--privileged" in argv
        # container image token precedes the SDR binary itself
        assert devices.IMAGE_NAME in argv
        assert argv.index(devices.IMAGE_NAME) == len(argv) - 2
        assert argv[-1] == binary


def test_lsusb_stays_host_side(monkeypatch):
    """lsusb is the single informational exception: host-side, no RF touched."""
    seen = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="Bus 001 Device 003\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    code, text = devices.run_text(["lsusb"])
    assert code == 0
    assert seen == [["lsusb"]]
    assert "Bus 001" in text


def test_parse_hackrf_info():
    text = """
Found HackRF
Serial number: 000000000000000012345678
Firmware Version: 2023.01.1
"""
    serial, board = devices.parse_hackrf_info(text)
    assert "12345678" in serial
    assert "HackRF" in board


def test_hardware_present_absent_when_no_match(monkeypatch):
    monkeypatch.setattr(devices, "lsusb_text", lambda: "Bus 001 Device 001: 1d6b:0002\n")
    assert devices.hardware_present({"id": "hackrf", "usb_vendor": "1d50", "usb_product": "6089"}) is False


def test_hardware_present_when_match(monkeypatch):
    monkeypatch.setattr(
        devices,
        "lsusb_text",
        lambda: "Bus 001 Device 003: 1d50:6089 Great Scott Gadgets HackRF\n",
    )
    assert devices.hardware_present({"id": "hackrf", "usb_vendor": "1d50", "usb_product": "6089"}) is True


def test_require_hardware_exits_when_absent(monkeypatch):
    monkeypatch.setattr(devices, "lsusb_text", lambda: "Bus 001 Device 001: 1d6b:0002\n")
    try:
        devices.require_hardware({"id": "hackrf", "usb_vendor": "1d50", "usb_product": "6089"})
    except SystemExit as exc:
        assert "not present on USB" in str(exc)
        assert "1d50:6089" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_require_hardware_passes_when_present(monkeypatch):
    monkeypatch.setattr(
        devices,
        "lsusb_text",
        lambda: "Bus 001 Device 003: 0456:b673 Analog Devices Pluto\n",
    )
    devices.require_hardware({"id": "pluto", "usb_vendor": "0456", "usb_product": "b673"})  # no raise


def test_confirm_tx_pass_via_env(monkeypatch):
    monkeypatch.setenv(devices.TX_CONFIRM_ENV, "1")
    devices.confirm_tx("some TX")  # no raise, no prompt


def test_confirm_tx_refuses_non_tty_without_env(monkeypatch):
    monkeypatch.delenv(devices.TX_CONFIRM_ENV, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    try:
        devices.confirm_tx("some TX")
    except SystemExit as exc:
        assert devices.TX_CONFIRM_ENV in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_confirm_tx_accepts_yes_on_tty(monkeypatch):
    monkeypatch.delenv(devices.TX_CONFIRM_ENV, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")
    devices.confirm_tx("some TX")  # no raise


def test_confirm_tx_rejects_non_yes_on_tty(monkeypatch):
    monkeypatch.delenv(devices.TX_CONFIRM_ENV, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")
    try:
        devices.confirm_tx("some TX")
    except SystemExit:
        pass
    else:
        raise AssertionError("expected SystemExit")


def test_confirm_tx_aborts_on_eof(monkeypatch):
    monkeypatch.delenv(devices.TX_CONFIRM_ENV, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError))
    try:
        devices.confirm_tx("some TX")
    except SystemExit:
        pass
    else:
        raise AssertionError("expected SystemExit")

