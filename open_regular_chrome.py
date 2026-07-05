import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CAPTIVE_ENTRY_URL = os.getenv("CAPTIVE_ENTRY_URL", "http://neverssl.com/")
CAPTIVE_PORTAL_URL = os.getenv("CAPTIVE_PORTAL_URL", "http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php")


def log(message: str) -> None:
    print(message, flush=True)


def find_chrome() -> str | None:
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]

    for path in candidates:
        if path and Path(path).exists():
            return path

    return shutil.which("chrome") or shutil.which("chrome.exe")


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) >= 2 else "portal-flow").lower()

    if mode in {"direct", "portal"}:
        url = CAPTIVE_PORTAL_URL
    else:
        url = CAPTIVE_ENTRY_URL

    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("Chrome was not found")

    log("Regular Chrome launcher")
    log(f"chrome={chrome}")
    log(f"url={url}")
    log("This script does not use Playwright and does not create a separate browser profile.")

    subprocess.Popen([chrome, "--new-window", url], close_fds=True)
    time.sleep(2)
    log("Chrome opened. Complete the login in the regular Chrome window.")


if __name__ == "__main__":
    main()
