import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
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

USERNAME_SELECTOR = os.getenv("USERNAME_SELECTOR", "").strip()
PASSWORD_SELECTOR = os.getenv("PASSWORD_SELECTOR", 'input[type="password"]').strip()
SUBMIT_SELECTOR = os.getenv("SUBMIT_SELECTOR", "").strip()

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def check_online() -> bool:
    try:
        result = subprocess.run(
            [
                "curl",
                "-L",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                CHECK_URL,
            ],
            timeout=10,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() == "204"
    except Exception:
        return False


def require_credentials() -> None:
    missing = []
    if not USERNAME:
        missing.append("CAPTIVE_USERNAME")
    if not PASSWORD:
        missing.append("CAPTIVE_PASSWORD")

    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing environment variables: {names}")


def fill_username(page) -> None:
    if USERNAME_SELECTOR:
        page.locator(USERNAME_SELECTOR).first.fill(USERNAME)
        return

    candidates = [
        'input[name*="user" i]',
        'input[name*="id" i]',
        'input[name*="login" i]',
        'input[type="text"]',
        'input:not([type])',
    ]

    for selector in candidates:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.fill(USERNAME)
            return

    raise RuntimeError("Username input was not found. Set USERNAME_SELECTOR in .env.")


def fill_password(page) -> None:
    locator = page.locator(PASSWORD_SELECTOR)
    if locator.count() == 0:
        raise RuntimeError("Password input was not found. Set PASSWORD_SELECTOR in .env.")
    locator.first.fill(PASSWORD)


def click_submit(page) -> None:
    if SUBMIT_SELECTOR:
        page.locator(SUBMIT_SELECTOR).first.click()
        return

    candidates = [
        'input[type="submit"]',
        'button[type="submit"]',
        'button:has-text("ログイン")',
        'input[value*="ログイン"]',
        'button',
    ]

    for selector in candidates:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.click()
            return

    raise RuntimeError("Submit button was not found. Set SUBMIT_SELECTOR in .env.")


def run_login(dry_run: bool) -> None:
    require_credentials()

    ts = timestamp()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(5_000)
            page.screenshot(path=str(SCREENSHOT_DIR / f"{ts}-01-opened.png"), full_page=True)

            fill_username(page)
            fill_password(page)
            page.screenshot(path=str(SCREENSHOT_DIR / f"{ts}-02-filled.png"), full_page=True)

            if dry_run:
                print("dry-run: form filled. login was not submitted.")
                print(f"final url: {page.url}")
                return

            click_submit(page)
            page.wait_for_timeout(10_000)
            page.screenshot(path=str(SCREENSHOT_DIR / f"{ts}-03-after-submit.png"), full_page=True)
            print(f"final url: {page.url}")

        except PlaywrightTimeoutError as error:
            page.screenshot(path=str(SCREENSHOT_DIR / f"{ts}-error-timeout.png"), full_page=True)
            raise error
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Fill the form but do not submit.")
    parser.add_argument("--force", action="store_true", help="Run login even if connectivity check succeeds.")
    args = parser.parse_args()

    if not args.force and check_online():
        print("online: already connected. nothing to do.")
        return

    print("offline or forced: running captive portal login.")
    run_login(dry_run=args.dry_run)

    if args.dry_run:
        return

    if check_online():
        print("success: internet connectivity restored.")
    else:
        print("failed: login attempted, but connectivity check still failed.")


if __name__ == "__main__":
    main()
