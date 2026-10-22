# Container-side loopback entrypoint inside rad-lab-sdr.
import json
import sys
from pathlib import Path

REPO = Path("/work")
sys.path.insert(0, str(REPO))
from hardware.loopback import _soapy_loopback  # noqa: E402

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--board", required=True, help="board dict as JSON")
    args = p.parse_args()
    board = json.loads(args.board)
    records = _soapy_loopback(board)
    sys.stdout.write(json.dumps({"status": "pass", "records": records}) + "\n")
