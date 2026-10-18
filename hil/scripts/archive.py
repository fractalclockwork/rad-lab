#!/usr/bin/env python3
"""Fetch and checksum the local documentation cache."""

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "archive" / "manifest.yaml"
STATUS = ROOT / "archive" / "cache" / "status.json"
IMAGE_NAME = "rad-lab-sdr"


def load_manifest():
    data = yaml.safe_load(MANIFEST.read_text())
    return data.get("items") or []


def load_status():
    if STATUS.exists():
        return json.loads(STATUS.read_text())
    return {"items": {}}


def save_status(status):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=2) + "\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "rad-lab-archive"})
    timeout = 600 if dest.suffix in {".xz", ".zip", ".gz", ".bz2"} else 120
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        payload = response.read()
    dest_is_html = dest.suffix.lower() in {".html", ".htm", ".md"}
    if "text/html" in content_type and not (
        dest_is_html or url.lower().endswith((".html", ".htm", ".md"))
    ):
        raise RuntimeError(f"URL returned HTML, not a file: {url}")
    dest.write_bytes(payload)


def extract_item(item):
    """Unpack a cached archive when the manifest sets extract: true."""
    if not item.get("extract"):
        return True
    archive_path = ROOT / item["path"]
    extract_dir = ROOT / item["extract_dir"]
    marker = ROOT / item["extract_marker"] if item.get("extract_marker") else None
    if marker is not None and marker.is_file():
        print(f"extracted {item['id']} (marker present)", flush=True)
        return True
    extract_dir.mkdir(parents=True, exist_ok=True)
    name = archive_path.name
    if name.endswith(".tar.xz") or name.endswith(".txz"):
        import tarfile

        with tarfile.open(archive_path, "r:xz") as archive:
            archive.extractall(path=extract_dir.parent)
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        import tarfile

        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(path=extract_dir.parent)
    elif name.endswith(".zip"):
        import zipfile

        # ZIP releases (e.g. plutosdr-fw) unpack flat; extract into extract_dir.
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(path=extract_dir)
    else:
        print(f"fail {item['id']}: unsupported archive type {name}", file=sys.stderr)
        return False
    if marker is not None and not marker.is_file():
        # Release tarball often unpacks to hackrf-2026.01.3/ at extract_dir.parent.
        print(
            f"fail {item['id']}: missing extract marker {item['extract_marker']}",
            file=sys.stderr,
        )
        return False
    print(f"extracted {item['id']}", flush=True)
    return True


def record(status, item, path):
    entry = {
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "retrieved": datetime.now(timezone.utc).isoformat(),
    }
    status["items"][item["id"]] = entry
    return entry


def fetch_item(item, status):
    path = ROOT / item["path"]
    expected = (item.get("sha256") or "").strip()
    known = status["items"].get(item["id"], {}).get("sha256", "")
    check = expected or known
    if path.exists() and check and sha256_file(path) == check:
        print(f"skip {item['id']}", flush=True)
        if item.get("extract") and not extract_item(item):
            return False
        return True
    if path.exists() and not check:
        record(status, item, path)
        print(f"hashed {item['id']}")
        if item.get("extract") and not extract_item(item):
            return False
        return True
    if item.get("manual"):
        if path.exists():
            record(status, item, path)
            print(f"hashed {item['id']}")
            if item.get("extract") and not extract_item(item):
                return False
            return True
        print(f"manual {item['id']}: place the file at {item['path']}", flush=True)
        return True
    try:
        download(item["url"], path)
    except Exception as exc:
        print(f"fail {item['id']}: {exc}", file=sys.stderr)
        return bool(item.get("optional"))
    entry = record(status, item, path)
    if expected and entry["sha256"] != expected:
        print(f"fail {item['id']}: sha256 mismatch", file=sys.stderr)
        return False
    print(f"fetched {item['id']}", flush=True)
    if item.get("extract") and not extract_item(item):
        return False
    return True


def save_image():
    out = ROOT / "archive" / "cache" / "images" / f"{IMAGE_NAME}.tar"
    out.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["docker", "save", "-o", str(out), IMAGE_NAME],
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        print(completed.stderr or completed.stdout, file=sys.stderr)
        return 1
    status = load_status()
    status["items"][f"docker-{IMAGE_NAME}"] = {
        "sha256": sha256_file(out),
        "bytes": out.stat().st_size,
        "retrieved": datetime.now(timezone.utc).isoformat(),
        "path": str(out.relative_to(ROOT)),
    }
    save_status(status)
    print(f"saved {out}", flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Refresh the local archive cache")
    parser.add_argument("--save-image", action="store_true")
    args = parser.parse_args(argv)
    if args.save_image:
        return save_image()
    status = load_status()
    ok = True
    for item in load_manifest():
        if not fetch_item(item, status):
            ok = False
    save_status(status)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
