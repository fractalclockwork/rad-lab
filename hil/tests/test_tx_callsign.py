import os

import pytest

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "tx_callsign", Path(__file__).resolve().parents[1] / "labs" / "04_tx_callsign_fm.py"
)
tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tx)


def test_sanitize_accepts_normal_call():
    assert tx.sanitize_callsign("w1aw") == "W1AW"


def test_sanitize_rejects_no_digit():
    with pytest.raises(SystemExit, match="invalid callsign"):
        tx.sanitize_callsign("NOCALL")


def test_resolve_requires_callsign(monkeypatch):
    monkeypatch.delenv("RAD_LAB_CALLSIGN", raising=False)
    with pytest.raises(SystemExit, match="callsign required"):
        tx.resolve_callsign(None)


def test_resolve_from_env(monkeypatch):
    monkeypatch.setenv("RAD_LAB_CALLSIGN", "k0test")
    assert tx.resolve_callsign(None) == "K0TEST"


def test_cli_overrides_env(monkeypatch):
    monkeypatch.setenv("RAD_LAB_CALLSIGN", "k0test")
    assert tx.resolve_callsign("n0call") == "N0CALL"
