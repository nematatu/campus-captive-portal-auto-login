import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

load_dotenv()

LOGIN_URL = os.getenv(
    "CAPTIVE_PORTAL_URL",
    "http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php",
)
CHECK_URL = os.getenv(
    "CHECK_URL",
    "http://connectivitycheck.gstatic.com/generate_204",
)
USERNAME = os.getenv("CAPTIVE_USERNAME", "")
PASSWORD = os.getenv("CAPTIVE_PASSWORD", "")
USERNAME_SELECTOR = (os.getenv("USERNAME_SELECTOR") or 'input[name="user"]').strip()
PASSWORD_SELECTOR = (os.getenv("PASSWORD_SELECTOR") or 'input[name="password"]').strip()
SUBMIT_SELECTOR = (os.getenv("SUBMIT_SELECTOR") or 'input[type="submit"]').strip()

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def log(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def require_credentials() -> None:
    missing = []
    if not USERNAME:
        missing.append("CAPTIVE_USERNAME")
    if not PASSWORD:
        missing.append("CAPTIVE_PASSWORD")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")


def has_login_form(page) -> bool:
    return (
        page.locator(USERNAME_SELECTOR).count() > 0
        and page.locator(PASSWORD_SELECTOR).count() > 0
        and page.locator(SUBMIT_SELECTOR).count() > 0
    )


def save_state(page, label: str, ts: str) -> None:
    png_path = SCREENSHOT_DIR / f"{ts}-{label}.png"
    html_path = SCREENSHOT_DIR / f"{ts}-{label}.html"
    page.screenshot(path=str(png_path), full_page=True)
    html = page.content()
    for secret in (USERNAME, PASSWORD):
        if secret:
            html = html.replace(secret, f"<masked length={len(secret)}>")
    html_path.write_text(html, encoding="utf-8")
    log(f"saved: {png_path}")
    log(f"saved: {html_path}")


def open_portal(page) -> None:
    log(f"open check url: {CHECK_URL}")
    try:
        page.goto(CHECK_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5_000)
        log(f"after check url: {page.url}")
        if has_login_form(page):
            log("login form found from captive portal redirect")
            return
    except PlaywrightError as error:
        log(f"check url navigation ended: {error}")

    log(f"open login url directly: {LOGIN_URL}")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(5_000)
    log(f"after login url: {page.url}")


def main() -> None:
    require_credentials()
    ts = timestamp()

    with sync_playwright() as p:
        context = None
        try:
            launch_options = {"headless": False, "channel": "chrome"}
            context = p.chromium.launch_persistent_context(
                user_data_dir=".playwright-profile",
                viewport={"width": 1366, "height": 768},
                locale="ja-JP",
                timezone_id="Asia/Tokyo",
                **launch_options,
            )
        except PlaywrightError as error:
            log(f"chrome channel failed: {error}")
            log("fallback to Playwright Chromium")
            context = p.chromium.launch_persistent_context(
                user_data_dir=".playwright-profile",
                headless=False,
                viewport={"width": 1366, "height": 768},
                locale="ja-JP",
                timezone_id="Asia/Tokyo",
            )

        page = context.new_page()
        try:
            open_portal(page)
            save_state(page, "01-opened", ts)

            if not has_login_form(page):
                log("login form was not found")
                log(f"current url: {page.url}")
                input("Press Enter to close browser: ")
                return

            log("fill username")
            page.locator(USERNAME_SELECTOR).first.click()
            page.keyboard.press("Control+A")
            page.keyboard.type(USERNAME, delay=50)

            log("fill password")
            page.locator(PASSWORD_SELECTOR).first.click()
            page.keyboard.press("Control+A")
            page.keyboard.type(PASSWORD, delay=50)

            page.locator(SUBMIT_SELECTOR).first.wait_for(state="attached", timeout=10_000)
            save_state(page, "02-filled", ts)

            print()
            print("ブラウザ上でログインボタンを手動クリックしてください。")
            print("ログイン操作が終わったら、このターミナルで Enter を押してください。")
            input("Enter after manual login: ")

            page.wait_for_timeout(5_000)
            log(f"after manual login: {page.url}")
            save_state(page, "03-after-manual-login", ts)
        finally:
            context.close()


if __name__ == "__main__":
    main()
