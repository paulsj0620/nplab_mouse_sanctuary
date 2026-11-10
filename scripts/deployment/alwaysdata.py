"""Preview or deploy the tested working copy to nplab. See --help for activation."""
import base64
import urllib.request
import argparse
import fcntl
import hashlib
import io
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import zipfile

SSH = "nplab@ssh-nplab.alwaysdata.net"
FILES = (
    "scripts/__init__.py", "scripts/paths.py", "scripts/app/__init__.py",
    "scripts/app/server.py", "scripts/app/service.py", "scripts/app/experiments.py",
    "scripts/imports/__init__.py", "scripts/imports/facs.py", "scripts/imports/histology.py",
    "scripts/imports/validation.py", "scripts/statistics/__init__.py",
    "scripts/statistics/statistical.py", "requirements/requirements.txt",
    "static/index.html", "static/app.js", "static/chart.js", "static/i18n.js",
    "static/study.js", "static/fcs.js", "static/style.css", "static/mouse-cemetery.png",
)
LIMIT = 16 * 1024 * 1024
START = "/home/nplab/mouse-sanctuary/.venv/bin/python -m scripts.app.server --alwaysdata"


def release_id(files):
    digest = hashlib.sha256()
    for name in FILES:
        digest.update(name.encode() + b"\0" + hashlib.sha256(files[name]).digest())
    return digest.hexdigest()[:24]


def archive(root):
    root = root.resolve()
    files = {}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            path = root / name
            if path.resolve() != path or not path.is_file():
                raise ValueError(f"Missing or linked source file: {name}")
            files[name] = path.read_bytes()
            bundle.writestr(name, files[name])
    return release_id(files), buffer.getvalue()


def switch(base, version):
    current = base / "current"
    if current.exists() and not current.is_symlink():
        raise ValueError("current already exists as a regular file or directory")
    previous = os.readlink(current) if current.is_symlink() else None
    with tempfile.TemporaryDirectory(dir=base) as tmp:
        link = Path(tmp) / "current"
        link.symlink_to("releases/" + version)
        os.replace(link, current)
    if previous:
        print("Previous release:", previous)


def receive(base, incoming, version, python):
    if not re.fullmatch("[0-9a-f]{24}", version):
        raise ValueError("Invalid release identifier")
    releases = base / "releases"
    if base.is_symlink() or releases.is_symlink():
        raise ValueError("Deployment directories must not be symbolic links")
    releases.mkdir(exist_ok=True)
    dest = releases / version
    with tempfile.TemporaryDirectory(dir=releases) as tmp:
        temp = Path(tmp)
        if incoming is not None:
            with zipfile.ZipFile(io.BytesIO(incoming)) as bundle:
                if sorted(bundle.namelist()) != sorted(FILES) or sum(i.file_size for i in bundle.infolist()) > LIMIT:
                    raise ValueError("Unexpected release contents")
                files = {name: bundle.read(name) for name in FILES}
            if release_id(files) != version:
                raise ValueError("Transfer checksum mismatch")
            for name, data in files.items():
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            # Keep host-owned experiment settings outside all deployable code.
            (temp / "config").mkdir()
            for name in ("experiment_types.json", "import_profiles.json"):
                (temp / "config" / name).symlink_to(base / "config" / name)
        candidate = temp if incoming is not None else dest
        if not candidate.is_dir() or candidate.is_symlink():
            raise ValueError("Requested release is unavailable")
        if release_id({n: (candidate / n).read_bytes() for n in FILES}) != version:
            raise ValueError("Release contents differ")
        subprocess.run([str(python), "-B", "-c", PREFLIGHT], cwd=candidate, check=True)
        if incoming is not None and not dest.exists():
            temp.rename(dest)
        elif incoming is not None and (dest.is_symlink() or release_id({n: (dest / n).read_bytes() for n in FILES}) != version):
            raise ValueError("Existing release differs")
        switch(base, version)
    print("Selected release:", version, flush=True)


PREFLIGHT = """
from importlib.metadata import version
from pathlib import Path
from scripts.app.server import make_server
from scripts.imports import facs, histology, validation
from scripts.statistics import statistical
for line in Path('requirements/requirements.txt').read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        package, expected = line.strip().split('==')
        if version(package) != expected:
            raise SystemExit('Dependency mismatch: ' + package + ' requires ' + expected)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog="After staging, set the site working directory to mouse-sanctuary/current and its command to: " + START + ". Save once; on later deployments click Restart under Web > Sites.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--deploy", action="store_true", help="stage and select the current working copy over SSH")
    group.add_argument("--rollback", metavar="RELEASE", help="select a previously staged release over SSH")
    group.add_argument("--receive", choices=["new","previous"], help=argparse.SUPPRESS)
    parser.add_argument("--version-id", help=argparse.SUPPRESS)
    parser.add_argument("--restart-site", metavar="SITE_ID", help="restart the selected alwaysdata site after switching; requires ALWAYSDATA_API_TOKEN")
    args = parser.parse_args()
    if args.restart_site and (not (args.deploy or args.rollback) or not args.restart_site.isdecimal() or not os.getenv("ALWAYSDATA_API_TOKEN")):
        parser.error("--restart-site requires --deploy/--rollback, a numeric site ID, and ALWAYSDATA_API_TOKEN")
    if args.receive:
        base = Path.home() / "mouse-sanctuary"
        os.umask(0o077)
        with (base / ".code-deploy.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            payload = sys.stdin.buffer.read(LIMIT+1) if args.receive == "new" else None
            if payload and len(payload) > LIMIT:
                raise ValueError("Release too large")
            receive(base, payload, args.version_id, base / ".venv/bin/python")
        return
    if args.rollback:
        version, payload = args.rollback, b""
    else:
        version, payload = archive(Path(__file__).resolve().parents[2])
    if not (args.deploy or args.rollback):
        print(f"Preview: {version} ({len(payload):,} bytes). No connection made.")
        print("\n".join(FILES))
        return
    mode = "previous" if args.rollback else "new"
    command = shlex.join(["mouse-sanctuary/.venv/bin/python", "-c", Path(__file__).read_text(), "--receive", mode, "--version-id", version])
    subprocess.run(["ssh", "-T", SSH, command], input=payload, check=True)
    if args.restart_site:
        credentials = os.environ["ALWAYSDATA_API_TOKEN"] + " account=nplab:"
        request = urllib.request.Request(
            f"https://api.alwaysdata.com/v1/site/{args.restart_site}/restart/",
            headers={"Authorization": "Basic " + base64.b64encode(credentials.encode()).decode()},
            method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            print("Restart accepted:", response.status)
        return
    print("Activate under Web > Sites: save the initial settings or click Restart.")
    print("Working directory: mouse-sanctuary/current\nCommand:", START)


if __name__ == "__main__":
    main()
