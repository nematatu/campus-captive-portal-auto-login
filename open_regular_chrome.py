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
ALLOW_DIRECT_PORTAL_URL = os.getenv("ALLOW_DIRECT_PORTAL_URL", "").strip() == "1"
EXTRA_ENTRY_URLS = [
    value.strip()
    for value in os.getenv("EXTRA_ENTRY_URLS", "http://example.com/,http://httpforever.com/").split(",")
    if value.strip()
]


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


def urls_for_mode(mode: str) -> list[str]:
    mode = mode.lower()

    if mode in {"direct", "portal"}:
        if not ALLOW_DIRECT_PORTAL_URL:
            log("Direct portal URL launch is disabled by default.")
            log("Do not open CAPTIVE_PORTAL_URL directly unless you know the portal accepts direct access.")
            log("Use the entry URL flow instead: run_regular_chrome.bat")
            return []
        return [CAPTIVE_PORTAL_URL]

    if mode in {"both", "all", "debug"}:
        urls = [CAPTIVE_ENTRY_URL, *EXTRA_ENTRY_URLS]
        deduped = []
        for url in urls:
            if url and url not in deduped:
                deduped.append(url)
        return deduped

    return [CAPTIVE_ENTRY_URL]


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) >= 2 else "entry").lower()
    urls = urls_for_mode(mode)

    if not urls:
        return

    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("Chrome was not found")

    log("Regular Chrome launcher")
    log(f"chrome={chrome}")
    log(f"mode={mode}")
    log("This script does not use Playwright and does not create a separate browser profile.")

    for index, url in enumerate(urls, start=1):
        log(f"open[{index}]={url}")
        if index == 1:
            subprocess.Popen([chrome, "--new-window", url], close_fds=True)
        else:
            subprocess.Popen([chrome, url], close_fds=True)
        time.sleep(1)

    log("Chrome opened. Complete the login in the regular Chrome window if the login page appears.")
    log("If no login page appears, the network may already be authenticated or this entry URL is not being intercepted.")


if __name__ == "__main__":
    main()
