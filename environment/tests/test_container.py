import subprocess

from environment import container


def test_run_text_always_uses_container(monkeypatch):
    seen = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    for binary in container.SDR_BINARIES:
        code, text = container.run_text([binary], usb=True)
        assert code == 0
        argv = seen[-1]
        assert argv[0] == "docker"
        assert container.IMAGE_NAME in argv
        assert argv[-1] == binary


def test_lsusb_stays_host_side(monkeypatch):
    seen = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="Bus 001 Device 003\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    code, text = container.run_text(["lsusb"])
    assert code == 0
    assert seen == [["lsusb"]]
