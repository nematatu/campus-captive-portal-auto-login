import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

import pyautogui
import pyperclip
from dotenv import load_dotenv

from open_real_browser_windows import log, resolve_captive_portal_url

load_dotenv()

USERNAME = os.getenv("CAPTIVE_USERNAME", "")
PASSWORD = os.getenv("CAPTIVE_PASSWORD", "")


def require_credentials() -> None:
    missing = []
    if not USERNAME:
        missing.append("CAPTIVE_USERNAME")
    if not PASSWORD:
        missing.append("CAPTIVE_PASSWORD")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")


def find_browser_executable() -> str | None:
    env_path = os.getenv("REAL_BROWSER_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    for command in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        path = shutil.which(command)
        if path:
            return path

    local_app_data = os.getenv("LOCALAPPDATA", "")
    program_files = os.getenv("PROGRAMFILES", "")
    program_files_x86 = os.getenv("PROGRAMFILES(X86)", "")
    candidates = [
        Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(program_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(program_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def launch_real_browser_app(url: str) -> None:
    browser_path = find_browser_executable()
    if not browser_path:
        raise RuntimeError("Chrome or Edge was not found. Set REAL_BROWSER_PATH in .env if needed.")

    args = [
        browser_path,
        f"--app={url}",
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    log(f"launch real browser: {browser_path}")
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def paste_text(text: str) -> None:
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")


def auto_type_credentials(tab_count: int, wait_seconds: float, submit: bool) -> None:
    log(f"wait for browser: {wait_seconds}s")
    time.sleep(wait_seconds)

    pyautogui.PAUSE = 0.25
    pyautogui.hotkey("alt", "tab")
    time.sleep(0.5)

    for _ in range(tab_count):
        pyautogui.press("tab")

    log("type username by clipboard paste")
    paste_text(USERNAME)
    pyautogui.press("tab")

    log("type password by clipboard paste")
    paste_text(PASSWORD)

    if submit:
        log("press Enter to submit")
        pyautogui.press("enter")
    else:
        log("submit skipped. Press the login button manually.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--headed-resolver",
        action="store_true",
        help="Show the temporary Playwright resolver browser. Default: headless resolver.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=float(os.getenv("REAL_BROWSER_WAIT_SECONDS", "5")),
        help="Seconds to wait after opening the real browser. Default: 5.",
    )
    parser.add_argument(
        "--tab-count",
        type=int,
        default=int(os.getenv("REAL_BROWSER_INITIAL_TAB_COUNT", "1")),
        help="Number of Tab key presses before typing username. Default: 1.",
    )
    parser.add_argument(
        "--no-submit",
        action="store_true",
        help="Type username/password but do not press Enter.",
    )
    parser.add_argument(
        "--url-only",
        action="store_true",
        help="Resolve and print the URL only. Do not open the real browser.",
    )
    args = parser.parse_args()

    require_credentials()
    url = resolve_captive_portal_url(headed=args.headed_resolver)

    print()
    print("Resolved URL:")
    print(url)
    print()

    if args.url_only:
        return

    launch_real_browser_app(url)
    auto_type_credentials(
        tab_count=args.tab_count,
        wait_seconds=args.wait_seconds,
        submit=not args.no_submit,
    )


if __name__ == "__main__":
    main()
