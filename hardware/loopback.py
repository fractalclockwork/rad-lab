"""TX↔RX loopback measurement for HWIL image stage (HackRF first)."""

from __future__ import annotations

import json
import subprocess
import time
import xml.sax.saxutils as xml_escape
from pathlib import Path

import numpy as np

from environment import container as devices
from software.fixture import assert_tone, measure_tone_snr, synthesize_tone
from human.assent import clamp_tx_gain


def loopback_record(sent, expected, actual, snr_db, host_monotonic_ns, **extra):
    record = {
        "sent": sent,
        "expected": expected,
        "actual": actual,
        "snr_db": snr_db,
        "host_monotonic_ns": host_monotonic_ns,
    }
    record.update(extra)
    return record


# Compatibility aliases used by older callers/tests during the rename.
hil_record = loopback_record


def write_loopback_logs(directory, records, failures=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "hil.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records)
    )
    failures = failures or []
    cases = []
    for record in records:
        name = xml_escape.escape(str(record.get("expected") or "vector"))
        body = xml_escape.escape(json.dumps(record))
        cases.append(
            f'  <testcase classname="hwil" name="{name}">\n'
            f"    <system-out>{body}</system-out>\n"
            f"  </testcase>"
        )
    for message in failures:
        text = xml_escape.escape(str(message))
        cases.append(
            f'  <testcase classname="hwil" name="loopback">\n'
            f'    <failure message="{text}">{text}</failure>\n'
            f"  </testcase>"
        )
    document = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuite name="hwil" tests="{len(cases)}" failures="{len(failures)}">\n'
        + "\n".join(cases)
        + "\n</testsuite>\n"
    )
    (directory / "junit.xml").write_text(document)


write_hil_logs = write_loopback_logs


def assert_tone_peak(metrics, tone_offset_hz, tolerance_hz=10_000.0, min_snr_db=None):
    """Shared SNR + peak check (same rule as crossboard evaluate_leg)."""
    snr_db = float(metrics["snr_db"])
    if min_snr_db is None:
        # Callers that omit min_snr_db still require a detectable tone and a
        # peak within tolerance (crossboard rule).
        if snr_db <= 0:
            raise AssertionError(
                f"loopback SNR {snr_db:.1f} dB is not positive; "
                f"no detectable tone near {tone_offset_hz} Hz"
            )
        min_snr_db = snr_db  # SNR already known good; only peak is checked below
    return assert_tone(metrics, tone_offset_hz, min_snr_db, tolerance_hz)


def _clamp_tx_gain(board):
    return clamp_tx_gain(board)


def run_loopback_simulated(board):
    """Offline path used by tests and RAD_LAB_HWIL_SIM=1."""
    sample_rate = int(board["sample_rate"])
    tone_offset_hz = float(board["tone_offset_hz"])
    min_snr = float(board.get("min_snr_db", 10.0))
    n_samples = max(4096, int(sample_rate * float(board.get("rx_ms", 400)) / 1000.0))
    iq = synthesize_tone(sample_rate, tone_offset_hz, n_samples, snr_db=min_snr + 15)
    metrics = measure_tone_snr(iq, sample_rate, tone_offset_hz)
    verdict = assert_tone(metrics, tone_offset_hz, min_snr)
    if board.get("loopback_mode") == "crossboard":
        partner_id = str(board.get("partner_board") or "pluto")
        board_id = str(board["id"])
        legs = (
            (board_id, partner_id),
            (partner_id, board_id),
        )
        return [
            loopback_record(
                sent=f"CW_TONE_TX_{tx_id.upper()}_RX_{rx_id.upper()}",
                expected=f"peak~{tone_offset_hz}Hz snr>={min_snr}dB",
                actual=f"peak={metrics['peak_hz']:.1f}Hz snr={metrics['snr_db']:.1f}dB",
                snr_db=metrics["snr_db"],
                host_monotonic_ns=time.monotonic_ns(),
                mode="simulated",
                tx_board=tx_id,
                rx_board=rx_id,
                metrics=metrics,
                verdict=verdict,
            )
            for tx_id, rx_id in legs
        ]
    return [
        loopback_record(
            sent="CW_TONE",
            expected=f"peak~{tone_offset_hz}Hz snr>={min_snr}dB",
            actual=f"peak={metrics['peak_hz']:.1f}Hz snr={metrics['snr_db']:.1f}dB",
            snr_db=metrics["snr_db"],
            host_monotonic_ns=time.monotonic_ns(),
            mode="simulated",
            metrics=metrics,
            verdict=verdict,
        )
    ]


def configure_soapy_gains(dev, board, tx_gain=None):
    """Apply board-specific SoapySDR RX and/or TX gains."""
    from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_TX  # type: ignore

    if board["id"] == "hackrf":
        try:
            dev.setGain(SOAPY_SDR_RX, 0, "LNA", float(board.get("rx_lna_db", 16)))
            dev.setGain(SOAPY_SDR_RX, 0, "VGA", float(board.get("rx_vga_db", 16)))
        except Exception:
            dev.setGain(SOAPY_SDR_RX, 0, float(board.get("rx_lna_db", 16)))
        if tx_gain is not None:
            try:
                dev.setGain(SOAPY_SDR_TX, 0, "VGA", tx_gain)
            except Exception:
                dev.setGain(SOAPY_SDR_TX, 0, tx_gain)
    else:
        try:
            dev.setGain(SOAPY_SDR_RX, 0, float(board.get("rx_lna_db", 30)))
        except Exception:
            pass
        if tx_gain is not None:
            dev.setGain(SOAPY_SDR_TX, 0, tx_gain)


def _soapy_loopback(board):
    import SoapySDR  # type: ignore
    from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_TX, SOAPY_SDR_CF32  # type: ignore

    driver = board.get("soapy_driver") or board["id"]
    devices = SoapySDR.Device.enumerate(dict(driver=driver))
    if not devices:
        raise RuntimeError(f"no Soapy devices for driver={driver}")
    dev = SoapySDR.Device(devices[0])
    sample_rate = float(board["sample_rate"])
    center_hz = float(board["center_hz"])
    tone_offset_hz = float(board["tone_offset_hz"])
    tx_gain = clamp_tx_gain(board)
    max_tx_ms = int(board.get("max_tx_ms", 200))
    rx_ms = int(board.get("rx_ms", 400))
    min_snr = float(board.get("min_snr_db", 10.0))

    for direction, chan in ((SOAPY_SDR_RX, 0), (SOAPY_SDR_TX, 0)):
        dev.setSampleRate(direction, chan, sample_rate)
        dev.setFrequency(direction, chan, center_hz)

    configure_soapy_gains(dev, board, tx_gain=tx_gain)

    rx_stream = dev.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
    tx_stream = dev.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
    n_tx = max(1024, int(sample_rate * max_tx_ms / 1000.0))
    n_rx = max(4096, int(sample_rate * rx_ms / 1000.0))
    t = np.arange(n_tx) / sample_rate
    tx_iq = (0.3 * np.exp(2j * np.pi * tone_offset_hz * t)).astype(np.complex64)
    rx_buf = np.zeros(n_rx, dtype=np.complex64)

    started = time.monotonic()
    try:
        dev.activateStream(rx_stream)
        dev.activateStream(tx_stream)
        tx_mtu = min(n_tx, 1024 * 8)
        sent = 0
        while sent < n_tx:
            chunk = tx_iq[sent : sent + tx_mtu]
            sr = dev.writeStream(tx_stream, [chunk], chunk.size)
            if sr.ret < 0:
                raise RuntimeError(f"TX writeStream failed: {sr.ret}")
            sent += sr.ret
            if (time.monotonic() - started) * 1000 > max_tx_ms * 2:
                break
        got = 0
        deadline = time.monotonic() + (rx_ms / 1000.0) + 1.0
        while got < n_rx and time.monotonic() < deadline:
            sr = dev.readStream(rx_stream, [rx_buf[got:]], n_rx - got)
            if sr.ret > 0:
                got += sr.ret
            elif sr.ret == -1:
                continue
            else:
                break
    finally:
        try:
            dev.deactivateStream(tx_stream)
            dev.closeStream(tx_stream)
        except Exception:
            pass
        try:
            dev.deactivateStream(rx_stream)
            dev.closeStream(rx_stream)
        except Exception:
            pass

    if got < 1024:
        raise RuntimeError(f"RX captured only {got} samples")
    metrics = measure_tone_snr(rx_buf[:got], sample_rate, tone_offset_hz)
    verdict = assert_tone(metrics, tone_offset_hz, min_snr)
    elapsed_ms = (time.monotonic() - started) * 1000.0
    return [
        loopback_record(
            sent="CW_TONE",
            expected=f"peak~{tone_offset_hz}Hz snr>={min_snr}dB",
            actual=f"peak={metrics['peak_hz']:.1f}Hz snr={metrics['snr_db']:.1f}dB",
            snr_db=metrics["snr_db"],
            host_monotonic_ns=time.monotonic_ns(),
            mode="hardware",
            tx_gain_db=tx_gain,
            elapsed_ms=elapsed_ms,
            metrics=metrics,
            verdict=verdict,
        )
    ]


def _container_loopback(board):
    """Run the Soapy TX/RX loopback inside rad-lab-sdr; never on the dev-host."""
    repo_root = Path(__file__).resolve().parents[1]
    script = "/work/hardware/_container_loopback.py"
    cmd = devices.docker_prefix(
        usb=True, mounts=[f"{repo_root}:/work"], workdir="/work"
    ) + ["python3", script, "--board", json.dumps(board)]
    completed = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(
            f"container loopback failed (rc={completed.returncode}): {output[-800:]}"
        )
    result = json.loads(completed.stdout)
    if result.get("status") != "pass":
        raise RuntimeError(f"container loopback failed: {output[-800:]}")
    return result["records"]


def _crossboard_loopback(board, no_prompt=None):
    """Run two-leg cross-board CW loopback (board<->partner_board) via 07_crossboard_915_cw."""
    import importlib.util
    import os

    lab_path = Path(__file__).resolve().parent / "labs" / "07_crossboard_915_cw.py"
    spec = importlib.util.spec_from_file_location("crossboard_915_cw", lab_path)
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)

    if no_prompt is None:
        no_prompt = os.environ.get("RAD_LAB_NO_PROMPT") == "1"
    report = lab.execute_crossboard_cw(no_prompt=no_prompt)
    records = []
    failures = []
    for leg in report["legs"]:
        tx_id = leg["tx_board"]
        rx_id = leg["rx_board"]
        tone_offset_hz = float(leg["tone_offset_hz"])
        min_snr = float(report["min_snr_db"])
        metrics = leg["metrics"]
        verdict = leg["verdict"]
        rec = loopback_record(
            sent=f"CW_TONE_TX_{tx_id.upper()}_RX_{rx_id.upper()}",
            expected=f"peak~{tone_offset_hz}Hz snr>={min_snr}dB",
            actual=f"peak={metrics['peak_hz']:.1f}Hz snr={metrics['snr_db']:.1f}dB",
            snr_db=metrics["snr_db"],
            host_monotonic_ns=time.monotonic_ns(),
            mode="hardware",
            tx_board=tx_id,
            rx_board=rx_id,
            tx_serial=leg.get("tx_serial", ""),
            rx_serial=leg.get("rx_serial", ""),
            tx_gain_db=leg.get("tx_gain_db"),
            elapsed_ms=leg.get("elapsed_ms"),
            metrics=metrics,
            verdict=verdict,
        )
        records.append(rec)
        if leg.get("status") != "pass":
            failures.append(
                f"{tx_id}->{rx_id}: peak={metrics['peak_hz']:.1f}Hz snr={metrics['snr_db']:.1f}dB"
            )
    if failures:
        raise RuntimeError("crossboard loopback failed: " + "; ".join(failures))
    return records


def run_loopback(board, simulate=False):
    if simulate:
        return run_loopback_simulated(board)
    if board.get("loopback_mode") == "crossboard":
        return _crossboard_loopback(board)
    return _container_loopback(board)


run_loopback_hil = run_loopback
