import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

load_dotenv()

DEFAULT_USERNAME_SELECTOR = 'input[name="user"]'
DEFAULT_PASSWORD_SELECTOR = 'input[name="password"]'
DEFAULT_SUBMIT_SELECTOR = 'input[type="submit"]'

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

USERNAME_SELECTOR = (os.getenv("USERNAME_SELECTOR") or DEFAULT_USERNAME_SELECTOR).strip()
PASSWORD_SELECTOR = (os.getenv("PASSWORD_SELECTOR") or DEFAULT_PASSWORD_SELECTOR).strip()
SUBMIT_SELECTOR = (os.getenv("SUBMIT_SELECTOR") or DEFAULT_SUBMIT_SELECTOR).strip()
INVALID_CREDENTIALS_TEXT = (
    os.getenv("PORTAL_INVALID_CREDENTIALS_TEXT")
    or "ユーザー名またはパスワードが無効です"
).strip()
REQUIRED_PARAMETER_TEXT = (
    os.getenv("PORTAL_REQUIRED_PARAMETER_TEXT") or "required parameter unavailable"
).strip()

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

LOGIN_OK = "ok"
LOGIN_INVALID_CREDENTIALS = "invalid_credentials"
LOGIN_REQUIRED_PARAMETER = "required_parameter"


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
    page.locator(SUBMIT_SELECTOR).first.wait_for(state="attached", timeout=10_000)
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


def log_before_submit_diagnostics(page) -> None:
    log(f"送信直前診断: current_url={page.url}")
    diagnostics = page.evaluate(
        """
        ({ usernameSelector, passwordSelector, submitSelector }) => {
          const form = document.querySelector("form");
          const user = document.querySelector(usernameSelector);
          const password = document.querySelector(passwordSelector);
          const submit = document.querySelector(submitSelector);
          return {
            form: form ? {
              id: form.id || "",
              name: form.getAttribute("name") || "",
              action: form.getAttribute("action") || "",
              actionResolved: form.action || "",
              method: form.getAttribute("method") || form.method || "",
            } : null,
            hiddenInputs: Array.from(document.querySelectorAll('input[type="hidden"]')).map((input) => ({
              name: input.getAttribute("name") || "",
              value: input.value || "",
            })),
            userInput: user ? {
              name: user.getAttribute("name") || "",
              id: user.id || "",
              hasValue: !!user.value,
            } : null,
            passwordInput: password ? {
              name: password.getAttribute("name") || "",
              id: password.id || "",
              hasValue: !!password.value,
            } : null,
            submitInput: submit ? {
              id: submit.id || "",
              disabled: !!submit.disabled,
            } : null,
          };
        }
        """,
        {
            "usernameSelector": USERNAME_SELECTOR,
            "passwordSelector": PASSWORD_SELECTOR,
            "submitSelector": SUBMIT_SELECTOR,
        },
    )

    form = diagnostics["form"]
    if form:
        log(
            "送信直前診断: "
            f"form id={form['id']!r}, name={form['name']!r}, "
            f"action={form['action']!r}, action_resolved={form['actionResolved']!r}, "
            f"method={form['method']!r}"
        )
    else:
        log("送信直前診断: form が見つかりません")

    hidden_inputs = diagnostics["hiddenInputs"]
    log(f"送信直前診断: hidden input count={len(hidden_inputs)}")
    for index, hidden_input in enumerate(hidden_inputs, start=1):
        log(
            "送信直前診断: "
            f"hidden[{index}] name={hidden_input['name']!r}, value={hidden_input['value']!r}"
        )

    for label, key in (("user", "userInput"), ("password", "passwordInput")):
        input_info = diagnostics[key]
        if input_info:
            log(
                "送信直前診断: "
                f"{label} input name={input_info['name']!r}, "
                f"id={input_info['id']!r}, value_present={input_info['hasValue']}"
            )
        else:
            log(f"送信直前診断: {label} input が見つかりません")

    submit_input = diagnostics["submitInput"]
    if submit_input:
        log(
            "送信直前診断: "
            f"submit input id={submit_input['id']!r}, disabled={submit_input['disabled']}"
        )
    else:
        log("送信直前診断: submit input が見つかりません")


def submit_login(page, submit_mode: str) -> None:
    log(f"ログイン送信開始: mode={submit_mode}")
    wait_submit_enabled(page)
    if submit_mode == "click":
        page.locator(SUBMIT_SELECTOR).first.click()
    elif submit_mode == "nwa":
        page.evaluate(
            """
            (submitSelector) => {
              const form = document.querySelector("form");
              const submit = document.querySelector(submitSelector);
              if (!form) {
                throw new Error("form was not found");
              }
              if (!submit) {
                throw new Error("submit input was not found");
              }
              if (typeof window.Nwa_SubmitForm !== "function") {
                throw new Error("Nwa_SubmitForm was not found");
              }
              window.Nwa_SubmitForm(form.id, submit.id);
            }
            """,
            SUBMIT_SELECTOR,
        )
    elif submit_mode == "form-submit":
        page.evaluate(
            """
            () => {
              const form = document.querySelector("form");
              if (!form) {
                throw new Error("form was not found");
              }
              form.submit();
            }
            """
        )
    else:
        raise RuntimeError(f"Unknown submit mode: {submit_mode}")
    log(f"ログイン送信完了: mode={submit_mode}, selector={SUBMIT_SELECTOR}")


def save_screenshot(page, path: Path) -> None:
    page.screenshot(path=str(path), full_page=True)
    log(f"スクリーンショット保存完了: {path}")


def detect_login_failure(page) -> str | None:
    body_text = page.evaluate(
        "() => document.body ? document.body.innerText : document.documentElement.innerText"
    )
    if INVALID_CREDENTIALS_TEXT and INVALID_CREDENTIALS_TEXT in body_text:
        return LOGIN_INVALID_CREDENTIALS
    if REQUIRED_PARAMETER_TEXT and REQUIRED_PARAMETER_TEXT in body_text:
        return LOGIN_REQUIRED_PARAMETER
    return None


def run_login(dry_run: bool, submit_mode: str) -> str:
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
                return LOGIN_OK

            log_before_submit_diagnostics(page)
            submit_login(page, submit_mode=submit_mode)

            log("ログイン後待機開始: 10秒")
            page.wait_for_timeout(10_000)
            log(f"ログイン後待機完了: current_url={page.url}")

            save_screenshot(page, SCREENSHOT_DIR / f"{ts}-03-after-submit.png")
            login_failure = detect_login_failure(page)
            if login_failure == LOGIN_INVALID_CREDENTIALS:
                log("認証失敗: 認証情報エラーを検出")
                return login_failure
            if login_failure == LOGIN_REQUIRED_PARAMETER:
                log("フォームパラメータ不足: required parameter unavailable を検出")
                return login_failure

            log(f"最終URL: {page.url}")
            return LOGIN_OK

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
    parser.add_argument(
        "--submit-mode",
        choices=["click", "nwa", "form-submit"],
        default="nwa",
        help="Submit method. Default: nwa.",
    )
    args = parser.parse_args()

    log("処理開始")
    log(f"mode: dry_run={args.dry_run}, force={args.force}, submit_mode={args.submit_mode}")

    online_before = check_online()

    if online_before and not args.force:
        log("オンライン判定: すでに接続済み。処理終了")
        return

    if online_before and args.force:
        log("注意: 実行前からオンライン。ログイン成功判定はできない")

    log("オフラインまたは強制実行: Captive Portal 認証処理を開始")
    login_result = run_login(dry_run=args.dry_run, submit_mode=args.submit_mode)

    if login_result == LOGIN_INVALID_CREDENTIALS:
        log("認証失敗")
        log("処理終了")
        return

    if login_result == LOGIN_REQUIRED_PARAMETER:
        log("フォームパラメータ不足")
        log("処理終了")
        return

    if args.dry_run:
        log("処理終了: dry-run")
        return

    online_after = check_online()

    if not online_before and online_after:
        log("復旧成功: オフライン状態からインターネット接続が復旧")
    elif online_before and online_after:
        log("疎通OK: ただし実行前からオンラインのため、ログイン成功とは判定しない")
    else:
        log("ログイン後も疎通失敗")

    log("処理終了")


if __name__ == "__main__":
    main()
