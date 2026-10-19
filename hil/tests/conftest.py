"""Pytest configuration for the HIL bring-up suite.

Hardware-requiring tests are skipped unless the board's VID:PID is visible on
the host USB bus (checked via `devices.usb_matches`, host-side `lsusb` only —
no RF touched). Tests that need a physical DUT should request the
``requires_hardware`` fixture or carry the ``hardware`` marker.

The ``hardware`` marker additionally requires ``--run-hardware`` so a test run
never silently keys a transmitter just because a board happens to be attached.
"""

from __future__ import annotations

import pytest

from devices import usb_matches


def pytest_addoption(parser):
    parser.addoption(
        "--run-hardware",
        action="store_true",
        default=False,
        help="allow hardware-marked tests to run when the DUT is on USB",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "hardware: test requires an SDR board on USB (skipped otherwise; also needs --run-hardware)",
    )


def pytest_collection_modifyitems(config, items):
    run_hardware = config.getoption("--run-hardware")
    for item in items:
        if "hardware" in item.keywords and not run_hardware:
            item.add_marker(
                pytest.mark.skip(reason="needs --run-hardware and an SDR board on USB")
            )


@pytest.fixture
def requires_hardware():
    """Return a callable that skips the test unless *board_id* is on USB.

    Usage::

        def test_something(requires_hardware):
            requires_hardware("hackrf")
            # ... exercise hardware ...
    """

    def _check(board_id):
        from radboards import load_board

        board = load_board(board_id)
        vendor = str(board.get("usb_vendor", "")).lower()
        product = str(board.get("usb_product", "")).lower()
        if not vendor or not product:
            pytest.skip(f"{board_id}: board YAML missing usb_vendor/usb_product")
        if not usb_matches(vendor, product):
            pytest.skip(
                f"{board_id}: not present on USB ({vendor}:{product}); "
                "attach the DUT or use software-only stages"
            )

    return _check


@pytest.fixture
def no_hardware(monkeypatch):
    """Force `devices.usb_matches` to return nothing so hardware paths refuse.

    Useful for asserting fail-closed behavior without a DUT.
    """
    import devices

    monkeypatch.setattr(devices, "usb_matches", lambda *a, **k: [])
