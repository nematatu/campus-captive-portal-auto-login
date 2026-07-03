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

USERNAME_SELECTOR = os.getenv("USERNAME_SELECTOR", "#ID_formea049c70_weblogin_user").strip()
PASSWORD_SELECTOR = os.getenv("PASSWORD_SELECTOR", "#ID_formea049c70_weblogin_password").strip()
SUBMIT_SELECTOR = os.getenv("SUBMIT_SELECTOR", "#ID_formea049c70_weblogin_submit").strip()

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


def fill_field(page, selector: str, value: str, label: str) -> None:
    log(f"{label}入力開始: selector={selector}")
    locator = page.locator(selector)
    count = locator.count()
    log(f"{label}候補確認: count={count}")
    if count == 0:
        raise RuntimeError(f"{label} input was not found. selector={selector}")

    locator.first.fill(value)
    locator.first.dispatch_event("input")
    locator.first.dispatch_event("change")
    log(f"{label}入力完了")


def fill_username(page) -> None:
    fill_field(page, USERNAME_SELECTOR, USERNAME, "ユーザー名")


def fill_password(page) -> None:
    fill_field(page, PASSWORD_SELECTOR, PASSWORD, "パスワード")


def wait_submit_enabled(page) -> None:
    log(f"ログインボタン有効化待機開始: selector={SUBMIT_SELECTOR}")
    submit = page.locator(SUBMIT_SELECTOR).first
    submit.wait_for(state="attached", timeout=10_000)

    page.wait_for_function(
        """
        (selector) => {
          const el = document.querySelector(selector);
          return !!el && !el.disabled;
        }
        """,
        arg=SUBMIT_SELECTOR,
        timeout=10_000,
    )
    log("ログインボタン有効化確認完了")


def click_submit(page) -> None:
    log("ログインボタン押下開始")
    wait_submit_enabled(page)
    page.locator(SUBMIT_SELECTOR).first.click()
    log(f"ログインボタン押下完了: selector={SUBMIT_SELECTOR}")


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
            wait_submit_enabled(page)
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
