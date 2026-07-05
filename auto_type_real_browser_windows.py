import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

import pyautogui
import pygetwindow as gw
from dotenv import load_dotenv

from open_real_browser_windows import log

load_dotenv()

USERNAME = os.getenv("CAPTIVE_USERNAME", "")
PASSWORD = os.getenv("CAPTIVE_PASSWORD", "")
LOGIN_URL = os.getenv(
    "CAPTIVE_PORTAL_URL",
    "http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php",
)
CHECK_URL = os.getenv(
    "CHECK_URL",
    "http://connectivitycheck.gstatic.com/generate_204",
)
DEFAULT_ENTRY_URLS = [
    LOGIN_URL,
    CHECK_URL,
    "http://neverssl.com/",
    "http://example.com/",
    "http://detectportal.firefox.com/canonical.html",
    "http://www.msftconnecttest.com/connecttest.txt",
    "http://captive.apple.com/hotspot-detect.html",
]

PORTAL_TITLE_KEYWORDS = [
    "宮崎大学ネットワーク認証",
    "ネットワーク認証",
    "認証",
    "cpauth",
    "cp-login",
]
BROWSER_TITLE_KEYWORDS = [
    "chrome",
    "edge",
    "google chrome",
    "microsoft edge",
]


def require_credentials() -> None:
    missing = []
    if not USERNAME:
        missing.append("CAPTIVE_USERNAME")
    if not PASSWORD:
        missing.append("CAPTIVE_PASSWORD")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")


def parse_entry_urls(cli_entry_urls: str | None) -> list[str]:
    raw = cli_entry_urls or os.getenv("REAL_BROWSER_ENTRY_URLS") or ""
    if raw.strip():
        urls = []
        for part in raw.replace("\n", ";").split(";"):
            value = part.strip()
            if value:
                urls.append(value)
        return urls
    return DEFAULT_ENTRY_URLS


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
    log(f"entry url: {url}")
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def list_window_titles() -> list[str]:
    titles = []
    for window in gw.getAllWindows():
        title = (window.title or "").strip()
        if title:
            titles.append(title)
    return titles


def title_contains_any(title: str, keywords: list[str]) -> bool:
    lowered = title.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def find_portal_window():
    candidates = []
    for window in gw.getAllWindows():
        title = (window.title or "").strip()
        if title and title_contains_any(title, PORTAL_TITLE_KEYWORDS):
            candidates.append(window)
    return candidates[-1] if candidates else None


def activate_window(window) -> bool:
    try:
        if window.isMinimized:
            window.restore()
        window.activate()
        time.sleep(0.8)
        log(f"activated window: {window.title!r}")
        return True
    except Exception as error:
        log(f"window activation failed: title={window.title!r}, error={error}")
        return False


def open_until_portal(entry_urls: list[str], wait_each_seconds: float):
    for index, url in enumerate(entry_urls, start=1):
        log(f"try entry url {index}/{len(entry_urls)}: {url}")
        launch_real_browser_app(url)
        deadline = time.time() + max(wait_each_seconds, 1)
        while time.time() < deadline:
            portal_window = find_portal_window()
            if portal_window and activate_window(portal_window):
                return portal_window
            time.sleep(0.5)

        log(f"portal window not detected for entry url: {url}")

    log("portal window was not detected from any entry URL")
    log("visible window titles:")
    for title in list_window_titles():
        log(f"  {title}")
    return None


def type_text_directly(text: str, interval: float) -> None:
    pyautogui.write(text, interval=interval)


def submit_login_button(submit_tab_count: int, submit_key: str) -> None:
    for _ in range(submit_tab_count):
        pyautogui.press("tab")

    if submit_key == "space":
        log("press Space on focused login button")
        pyautogui.press("space")
    elif submit_key == "enter":
        log("press Enter on focused login button")
        pyautogui.press("enter")
    else:
        raise RuntimeError(f"Unknown submit key: {submit_key}")


def auto_type_credentials(
    tab_count: int,
    submit: bool,
    char_interval: float,
    submit_tab_count: int,
    submit_key: str,
) -> None:
    pyautogui.PAUSE = 0.2

    # Keyboard-only flow. No clipboard paste and no manual click.
    for _ in range(tab_count):
        pyautogui.press("tab")

    log("type username directly")
    type_text_directly(USERNAME, interval=char_interval)
    pyautogui.press("tab")

    log("type password directly")
    type_text_directly(PASSWORD, interval=char_interval)

    if submit:
        submit_login_button(submit_tab_count=submit_tab_count, submit_key=submit_key)
    else:
        log("submit skipped")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--entry-url",
        dest="entry_urls",
        help="Semicolon-separated URL list to try. Default: REAL_BROWSER_ENTRY_URLS or built-in URLs.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=float(os.getenv("REAL_BROWSER_WAIT_SECONDS", "8")),
        help="Seconds to wait for portal page per entry URL. Default: 8.",
    )
    parser.add_argument(
        "--tab-count",
        type=int,
        default=int(os.getenv("REAL_BROWSER_INITIAL_TAB_COUNT", "1")),
        help="Number of Tab key presses before typing username. Default: 1.",
    )
    parser.add_argument(
        "--submit-tab-count",
        type=int,
        default=int(os.getenv("REAL_BROWSER_SUBMIT_TAB_COUNT", "1")),
        help="Number of Tab key presses from password field to login button. Default: 1.",
    )
    parser.add_argument(
        "--submit-key",
        choices=["space", "enter"],
        default=os.getenv("REAL_BROWSER_SUBMIT_KEY", "space"),
        help="Key used on focused login button. Default: space.",
    )
    parser.add_argument(
        "--char-interval",
        type=float,
        default=float(os.getenv("REAL_BROWSER_CHAR_INTERVAL", "0.05")),
        help="Delay between typed characters. Default: 0.05.",
    )
    parser.add_argument(
        "--no-submit",
        action="store_true",
        help="Type username/password but do not submit.",
    )
    args = parser.parse_args()

    require_credentials()
    entry_urls = parse_entry_urls(args.entry_urls)
    log("entry URL candidates:")
    for url in entry_urls:
        log(f"  {url}")

    portal_window = open_until_portal(entry_urls, wait_each_seconds=args.wait_seconds)
    if not portal_window:
        raise RuntimeError("Captive Portal window was not detected. Add a working URL to REAL_BROWSER_ENTRY_URLS.")

    auto_type_credentials(
        tab_count=args.tab_count,
        submit=not args.no_submit,
        char_interval=args.char_interval,
        submit_tab_count=args.submit_tab_count,
        submit_key=args.submit_key,
    )


if __name__ == "__main__":
    main()
