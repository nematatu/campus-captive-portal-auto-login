from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import os

load_dotenv()

LOGIN_URL = os.getenv(
    "CAPTIVE_PORTAL_URL",
    "http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php",
)

OUTPUT = Path("login.png")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5_000)
        page.screenshot(path=str(OUTPUT), full_page=True)

        print(f"saved: {OUTPUT}")
        print(f"final url: {page.url}")

        browser.close()


if __name__ == "__main__":
    main()
