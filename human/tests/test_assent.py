import sys

import human.assent as assent
from environment import container


def test_require_hardware_exits_when_absent(monkeypatch):
    monkeypatch.setattr(container, "lsusb_text", lambda: "Bus 001 Device 001: 1d6b:0002\n")
    try:
        assent.require_hardware({"id": "hackrf", "usb_vendor": "1d50", "usb_product": "6089"})
    except SystemExit as exc:
        assert "not present on USB" in str(exc)
        assert "1d50:6089" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_require_hardware_passes_when_present(monkeypatch):
    monkeypatch.setattr(
        container,
        "lsusb_text",
        lambda: "Bus 001 Device 003: 0456:b673 Analog Devices Pluto\n",
    )
    assent.require_hardware({"id": "pluto", "usb_vendor": "0456", "usb_product": "b673"})


def test_confirm_tx_pass_via_env(monkeypatch):
    monkeypatch.setenv(assent.TX_CONFIRM_ENV, "1")
    assent.confirm_tx("some TX")


def test_confirm_tx_refuses_non_tty_without_env(monkeypatch):
    monkeypatch.delenv(assent.TX_CONFIRM_ENV, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    try:
        assent.confirm_tx("some TX")
    except SystemExit as exc:
        assert assent.TX_CONFIRM_ENV in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_confirm_tx_accepts_yes_on_tty(monkeypatch):
    monkeypatch.delenv(assent.TX_CONFIRM_ENV, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")
    assent.confirm_tx("some TX")
