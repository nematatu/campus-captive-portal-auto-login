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


def log(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def check_online() -> bool:
    log(f"疎通確認開始: {CHECK_URL}")
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
        status = result.stdout.strip()
        log(f"疎通確認完了: HTTP {status or 'no response'}")
        return status == "204"
    except Exception as error:
        log(f"疎通確認失敗: {error}")
        return False


def require_credentials() -> None:
    log("認証情報確認開始")
    missing = []
    if not USERNAME:
        missing.append("CAPTIVE_USERNAME")
    if not PASSWORD:
        missing.append("CAPTIVE_PASSWORD")

    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing environment variables: {names}")

    log("認証情報確認完了")


def fill_username(page) -> None:
    log("ユーザー名入力開始")
    if USERNAME_SELECTOR:
        page.locator(USERNAME_SELECTOR).first.fill(USERNAME)
        log(f"ユーザー名入力完了: selector={USERNAME_SELECTOR}")
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
        count = locator.count()
        log(f"ユーザー名候補確認: selector={selector}, count={count}")
        if count > 0:
            locator.first.fill(USERNAME)
            log(f"ユーザー名入力完了: selector={selector}")
            return

    raise RuntimeError("Username input was not found. Set USERNAME_SELECTOR in .env.")


def fill_password(page) -> None:
    log("パスワード入力開始")
    locator = page.locator(PASSWORD_SELECTOR)
    count = locator.count()
    log(f"パスワード候補確認: selector={PASSWORD_SELECTOR}, count={count}")
    if count == 0:
        raise RuntimeError("Password input was not found. Set PASSWORD_SELECTOR in .env.")
    locator.first.fill(PASSWORD)
    log(f"パスワード入力完了: selector={PASSWORD_SELECTOR}")


def click_submit(page) -> None:
    log("ログインボタン押下開始")
    if SUBMIT_SELECTOR:
        page.locator(SUBMIT_SELECTOR).first.click()
        log(f"ログインボタン押下完了: selector={SUBMIT_SELECTOR}")
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
        count = locator.count()
        log(f"ログインボタン候補確認: selector={selector}, count={count}")
        if count > 0:
            locator.first.click()
            log(f"ログインボタン押下完了: selector={selector}")
            return

    raise RuntimeError("Submit button was not found. Set SUBMIT_SELECTOR in .env.")


def save_screenshot(page, path: Path) -> None:
    page.screenshot(path=str(path), full_page=True)
    log(f"スクリーンショット保存完了: {path}")


def run_login(dry_run: bool) -> None:
    require_credentials()

    ts = timestamp()
    log(f"実行ID: {ts}")

    with sync_playwright() as p:
        log("Chromium 起動開始")
        browser = p.chromium.launch(headless=True)
        log("Chromium 起動完了")

        page = browser.new_page(viewport={"width": 1280, "height": 900})
        log("新規ページ作成完了")

        try:
            log(f"認証ページ遷移開始: {LOGIN_URL}")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
            log(f"認証ページ遷移完了: {page.url}")

            log("JSリダイレクト・描画待機開始: 5秒")
            page.wait_for_timeout(5_000)
            log(f"待機完了: current_url={page.url}")

            save_screenshot(page, SCREENSHOT_DIR / f"{ts}-01-opened.png")

            fill_username(page)
            fill_password(page)
            save_screenshot(page, SCREENSHOT_DIR / f"{ts}-02-filled.png")

            if dry_run:
                log("dry-run: ログイン送信せず終了")
                log(f"最終URL: {page.url}")
                return

            click_submit(page)

            log("ログイン後待機開始: 10秒")
            page.wait_for_timeout(10_000)
            log(f"ログイン後待機完了: current_url={page.url}")

            save_screenshot(page, SCREENSHOT_DIR / f"{ts}-03-after-submit.png")
            log(f"最終URL: {page.url}")

        except PlaywrightTimeoutError as error:
            error_path = SCREENSHOT_DIR / f"{ts}-error-timeout.png"
            save_screenshot(page, error_path)
            log(f"タイムアウト: {error}")
            raise error
        except Exception as error:
            error_path = SCREENSHOT_DIR / f"{ts}-error.png"
            save_screenshot(page, error_path)
            log(f"エラー: {error}")
            raise error
        finally:
            log("Chromium 終了開始")
            browser.close()
            log("Chromium 終了完了")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Fill the form but do not submit.")
    parser.add_argument("--force", action="store_true", help="Run login even if connectivity check succeeds.")
    args = parser.parse_args()

    log("処理開始")
    log(f"mode: dry_run={args.dry_run}, force={args.force}")

    if not args.force and check_online():
        log("オンライン判定: すでに接続済み。処理終了")
        return

    log("オフラインまたは強制実行: Captive Portal 認証処理を開始")
    run_login(dry_run=args.dry_run)

    if args.dry_run:
        log("処理終了: dry-run")
        return

    if check_online():
        log("成功: インターネット接続が復旧")
    else:
        log("失敗: ログイン試行後も疎通確認に失敗")

    log("処理終了")


if __name__ == "__main__":
    main()
