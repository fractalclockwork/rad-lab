"""TX↔RX loopback HIL for SDR boards (HackRF first)."""

from __future__ import annotations

import json
import time
import xml.sax.saxutils as xml_escape
from pathlib import Path

import numpy as np

from fixture import measure_tone_snr, synthesize_tone


def hil_record(sent, expected, actual, snr_db, host_monotonic_ns, **extra):
    record = {
        "sent": sent,
        "expected": expected,
        "actual": actual,
        "snr_db": snr_db,
        "host_monotonic_ns": host_monotonic_ns,
    }
    record.update(extra)
    return record


def write_hil_logs(directory, records, failures=None):
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
            f'  <testcase classname="hil" name="{name}">\n'
            f"    <system-out>{body}</system-out>\n"
            f"  </testcase>"
        )
    for message in failures:
        text = xml_escape.escape(str(message))
        cases.append(
            f'  <testcase classname="hil" name="hil">\n'
            f'    <failure message="{text}">{text}</failure>\n'
            f"  </testcase>"
        )
    document = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuite name="hil" tests="{len(cases)}" failures="{len(failures)}">\n'
        + "\n".join(cases)
        + "\n</testsuite>\n"
    )
    (directory / "junit.xml").write_text(document)


def assert_tone_peak(metrics, tone_offset_hz, tolerance_hz=5000.0):
    """Require the spectrum peak on the transmitted offset, not a noise-bin SNR."""
    peak = float(metrics["peak_hz"])
    offset = float(tone_offset_hz)
    if abs(peak - offset) > float(tolerance_hz):
        raise AssertionError(
            f"loopback peak {peak:.1f} Hz is not near {offset:.1f} Hz "
            f"(snr {float(metrics['snr_db']):.1f} dB)"
        )


def _clamp_tx_gain(board):
    requested = float(board.get("txvga_db", 0))
    ceiling = float(board.get("max_tx_db", requested))
    if requested > ceiling:
        raise ValueError(
            f"txvga_db {requested} exceeds max_tx_db {ceiling}; refuse TX"
        )
    return requested


def run_loopback_simulated(board):
    """Offline path used by tests and RAD_LAB_HIL_SIM=1."""
    sample_rate = int(board["sample_rate"])
    tone_offset_hz = float(board["tone_offset_hz"])
    min_snr = float(board.get("min_snr_db", 10.0))
    n_samples = max(4096, int(sample_rate * float(board.get("rx_ms", 400)) / 1000.0))
    iq = synthesize_tone(sample_rate, tone_offset_hz, n_samples, snr_db=min_snr + 15)
    metrics = measure_tone_snr(iq, sample_rate, tone_offset_hz)
    if metrics["snr_db"] < min_snr:
        raise AssertionError(
            f"loopback SNR {metrics['snr_db']:.1f} dB below {min_snr} dB"
        )
    assert_tone_peak(metrics, tone_offset_hz)
    return [
        hil_record(
            sent="CW_TONE",
            expected=f"peak~{tone_offset_hz}Hz snr>={min_snr}dB",
            actual=f"peak={metrics['peak_hz']:.1f}Hz snr={metrics['snr_db']:.1f}dB",
            snr_db=metrics["snr_db"],
            host_monotonic_ns=time.monotonic_ns(),
            mode="simulated",
            metrics=metrics,
        )
    ]


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
    tx_gain = _clamp_tx_gain(board)
    max_tx_ms = int(board.get("max_tx_ms", 200))
    rx_ms = int(board.get("rx_ms", 400))
    min_snr = float(board.get("min_snr_db", 10.0))

    for direction, chan in ((SOAPY_SDR_RX, 0), (SOAPY_SDR_TX, 0)):
        dev.setSampleRate(direction, chan, sample_rate)
        dev.setFrequency(direction, chan, center_hz)

    if board["id"] == "hackrf":
        # HackRF maps LNA/VGA / TXVGA through Soapy gain elements when available.
        try:
            dev.setGain(SOAPY_SDR_RX, 0, "LNA", float(board.get("rx_lna_db", 16)))
            dev.setGain(SOAPY_SDR_RX, 0, "VGA", float(board.get("rx_vga_db", 16)))
        except Exception:
            dev.setGain(SOAPY_SDR_RX, 0, float(board.get("rx_lna_db", 16)))
        try:
            dev.setGain(SOAPY_SDR_TX, 0, "VGA", tx_gain)
        except Exception:
            dev.setGain(SOAPY_SDR_TX, 0, tx_gain)
    else:
        dev.setGain(SOAPY_SDR_RX, 0, float(board.get("rx_lna_db", 30)))
        dev.setGain(SOAPY_SDR_TX, 0, tx_gain)

    rx_stream = dev.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
    tx_stream = dev.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
    n_tx = max(1024, int(sample_rate * max_tx_ms / 1000.0))
    n_rx = max(4096, int(sample_rate * rx_ms / 1000.0))
    t = np.arange(n_tx) / sample_rate
    # Scale well below full scale.
    tx_iq = (0.3 * np.exp(2j * np.pi * tone_offset_hz * t)).astype(np.complex64)
    rx_buf = np.zeros(n_rx, dtype=np.complex64)

    started = time.monotonic()
    try:
        dev.activateStream(rx_stream)
        dev.activateStream(tx_stream)
        # Overlap short TX with RX capture.
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
            elif sr.ret == -1:  # timeout
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
    if metrics["snr_db"] < min_snr:
        raise AssertionError(
            f"loopback SNR {metrics['snr_db']:.1f} dB below {min_snr} dB"
        )
    assert_tone_peak(metrics, tone_offset_hz)
    elapsed_ms = (time.monotonic() - started) * 1000.0
    return [
        hil_record(
            sent="CW_TONE",
            expected=f"peak~{tone_offset_hz}Hz snr>={min_snr}dB",
            actual=f"peak={metrics['peak_hz']:.1f}Hz snr={metrics['snr_db']:.1f}dB",
            snr_db=metrics["snr_db"],
            host_monotonic_ns=time.monotonic_ns(),
            mode="hardware",
            tx_gain_db=tx_gain,
            elapsed_ms=elapsed_ms,
            metrics=metrics,
        )
    ]


def run_loopback_hil(board, simulate=False):
    if simulate:
        return run_loopback_simulated(board)
    return _soapy_loopback(board)
