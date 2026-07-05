import argparse
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

load_dotenv()

CHECK_URL = os.getenv(
    "CHECK_URL",
    "http://connectivitycheck.gstatic.com/generate_204",
)
LOGIN_URL = os.getenv(
    "CAPTIVE_PORTAL_URL",
    "http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php",
)
USER_AGENT = (
    os.getenv("BROWSER_USER_AGENT")
    or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
).strip()
ACCEPT_LANGUAGE = (
    os.getenv("BROWSER_ACCEPT_LANGUAGE") or "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
).strip()

OUTPUT_DIR = Path("screenshots")
OUTPUT_DIR.mkdir(exist_ok=True)


def log(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def looks_like_connectivity_check(url: str) -> bool:
    return "connectivitycheck.gstatic.com/generate_204" in url


def save_resolved_url(url: str, ts: str) -> None:
    path = OUTPUT_DIR / f"{ts}-resolved-url.txt"
    path.write_text(url + "\n", encoding="utf-8")
    log(f"resolved url saved: {path}")


def resolve_captive_portal_url(headed: bool) -> str:
    ts = timestamp()
    log(f"resolve start: {CHECK_URL}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=".playwright-url-resolver-profile",
            headless=not headed,
            viewport={"width": 1366, "height": 768},
            user_agent=USER_AGENT,
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            extra_http_headers={"Accept-Language": ACCEPT_LANGUAGE},
        )
        page = context.new_page()
        try:
            try:
                page.goto(CHECK_URL, wait_until="domcontentloaded", timeout=30_000)
            except PlaywrightError as error:
                log(f"check url navigation ended: {error}")

            page.wait_for_timeout(5_000)
            final_url = page.url
            log(f"after check url: {final_url}")

            if looks_like_connectivity_check(final_url) or final_url == "about:blank":
                log("check url did not produce a captive portal URL; fallback to CAPTIVE_PORTAL_URL")
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(5_000)
                final_url = page.url
                log(f"after login url: {final_url}")

            save_resolved_url(final_url, ts)
            return final_url
        finally:
            context.close()


def open_in_normal_browser(url: str) -> None:
    log("open resolved url in normal Windows browser")
    if sys.platform.startswith("win"):
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        webbrowser.open(url)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--headed-resolver",
        action="store_true",
        help="Show the temporary Playwright resolver browser. Default: headless resolver.",
    )
    parser.add_argument(
        "--url-only",
        action="store_true",
        help="Print and save the resolved URL without opening the normal browser.",
    )
    args = parser.parse_args()

    url = resolve_captive_portal_url(headed=args.headed_resolver)
    print()
    print("Resolved URL:")
    print(url)
    print()

    if args.url_only:
        return

    open_in_normal_browser(url)
    print("通常のWindowsブラウザで開きました。")
    print("そのブラウザ上でユーザー情報を入力し、ログインボタンを押してください。")


if __name__ == "__main__":
    main()
