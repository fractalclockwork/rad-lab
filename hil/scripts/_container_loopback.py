# Container-side loopback entrypoint. Executes the Soapy TX/RX loopback inside
# rad-lab-sdr so the dev-host never imports SoapySDR or drives RF directly.
# Invoked by hil._container_loopback (host orchestration) as:
#   docker run --rm --privileged -v /dev/bus/usb:/dev/bus/usb \
#     -v <repo>:/work -w /work rad-lab-sdr \
#     python3 /work/hil/scripts/_container_loopback.py --board '<json>'
# Result JSON is written to stdout; the host parent parses it.
import json
import sys

sys.path.insert(0, "/work/hil/scripts")
from hil import _soapy_loopback  # noqa: E402  (container-side only)

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--board", required=True, help="board dict as JSON")
    args = p.parse_args()

    board = json.loads(args.board)
    records = _soapy_loopback(board)
    sys.stdout.write(json.dumps({"status": "pass", "records": records}) + "\n")
