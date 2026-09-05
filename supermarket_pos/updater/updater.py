"""Detached updater process. It never writes inside the persistent Data directory."""
import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--executable", required=True)
    return parser.parse_args()


def wait_for_process(pid: int):
    if pid == os.getpid():
        return
    try:
        if os.name == "nt":
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                ctypes.windll.kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)
                ctypes.windll.kernel32.CloseHandle(handle)
        else:
            while True:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                except PermissionError:
                    break
                time.sleep(0.25)
    except OSError:
        pass


def terminate_main(pid: int):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def copy_tree(source: Path, target: Path):
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        if any(part.lower() == "data" for part in relative.parts):
            continue
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def install(package: Path, app_dir: Path, executable: Path):
    with tempfile.TemporaryDirectory(prefix="supermarket-pos-extract-") as temp:
        staging = Path(temp)
        if package.suffix.lower() == ".zip":
            with zipfile.ZipFile(package) as archive:
                for member in archive.infolist():
                    destination = (staging / member.filename).resolve()
                    if staging not in destination.parents and destination != staging:
                        raise ValueError("Update archive contains an unsafe path")
                archive.extractall(staging)
            roots = list(staging.iterdir())
            source = roots[0] if len(roots) == 1 and roots[0].is_dir() else staging
            copy_tree(source, app_dir)
        elif package.suffix.lower() == ".exe":
            shutil.copy2(package, executable)
        else:
            raise ValueError("Unsupported update package")


def main():
    args = parse_args()
    package = Path(args.package).resolve()
    app_dir = Path(args.app_dir).resolve()
    executable = Path(args.executable).resolve()
    terminate_main(args.pid)
    wait_for_process(args.pid)
    install(package, app_dir, executable)
    package.unlink(missing_ok=True)
    subprocess.Popen([str(executable)], cwd=str(app_dir), start_new_session=True, close_fds=True)


if __name__ == "__main__":
    main()
