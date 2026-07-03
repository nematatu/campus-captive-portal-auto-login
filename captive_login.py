import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl

from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

load_dotenv()

DEFAULT_USERNAME_SELECTOR = 'input[name="user"]'
DEFAULT_PASSWORD_SELECTOR = 'input[name="password"]'
DEFAULT_SUBMIT_SELECTOR = 'input[type="submit"]'
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

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
USER_AGENT = (os.getenv("BROWSER_USER_AGENT") or DEFAULT_USER_AGENT).strip()
ACCEPT_LANGUAGE = (
    os.getenv("BROWSER_ACCEPT_LANGUAGE") or "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
).strip()
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
LOGIN_FORM_NOT_FOUND = "form_not_found"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def log(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def mask_sensitive_value(name: str, value: str) -> str:
    lowered = name.lower()
    if lowered in {"user", "username", "login", "id"}:
        return f"<masked length={len(value)}>"
    if "pass" in lowered or "password" in lowered:
        return f"<masked length={len(value)}>"
    return value


def format_post_data(post_data: str | None) -> str:
    if not post_data:
        return ""
    pairs = parse_qsl(post_data, keep_blank_values=True)
    if not pairs:
        return post_data[:500]
    masked_pairs = [
        f"{name}={mask_sensitive_value(name, value)!r}" for name, value in pairs
    ]
    return "&".join(masked_pairs)


def check_online() -> bool:
    """Return True only when CHECK_URL resolves to HTTP 204.

    This intentionally uses Python's standard library instead of shelling out to
    curl. The old implementation used /dev/null, which is Linux/WSL-specific and
    breaks Windows-native execution.
    """

    log(f"疎通確認開始: {CHECK_URL}")
    request = urllib.request.Request(
        CHECK_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": ACCEPT_LANGUAGE,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.getcode()
            final_url = response.geturl()
            log(f"疎通確認完了: HTTP {status}, final_url={final_url}")
            return status == 204
    except urllib.error.HTTPError as error:
        log(f"疎通確認完了: HTTP {error.code}, final_url={error.url}")
        return error.code == 204
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


def fill_field(page, selector: str, value: str, label: str, input_mode: str) -> None:
    log(f"{label}入力開始: selector={selector}, mode={input_mode}")
    locator = page.locator(selector)
    count = locator.count()
    log(f"{label}候補確認: count={count}")
    if count == 0:
        raise RuntimeError(f"{label} input was not found. selector={selector}")

    field = locator.first
    if input_mode == "fill":
        field.fill(value)
    elif input_mode == "type":
        field.click()
        modifier = "Meta" if sys.platform == "darwin" else "Control"
        page.keyboard.press(f"{modifier}+A")
        page.keyboard.type(value, delay=50)
    else:
        raise RuntimeError(f"Unknown input mode: {input_mode}")

    locator.first.dispatch_event("input")
    locator.first.dispatch_event("change")
    locator.first.evaluate("(el) => el.blur()")
    log(f"{label}入力完了")


def fill_username(page, input_mode: str) -> None:
    fill_field(page, USERNAME_SELECTOR, USERNAME, "ユーザー名", input_mode)


def fill_password(page, input_mode: str) -> None:
    fill_field(page, PASSWORD_SELECTOR, PASSWORD, "パスワード", input_mode)


def has_login_form(page) -> bool:
    form_count = page.locator("form").count()
    username_count = page.locator(USERNAME_SELECTOR).count()
    password_count = page.locator(PASSWORD_SELECTOR).count()
    submit_count = page.locator(SUBMIT_SELECTOR).count()
    log(
        "ログインフォーム確認: "
        f"form={form_count}, username={username_count}, "
        f"password={password_count}, submit={submit_count}, current_url={page.url}"
    )
    return form_count > 0 and username_count > 0 and password_count > 0 and submit_count > 0


def log_browser_diagnostics(page) -> None:
    diagnostics = page.evaluate(
        """
        () => ({
          userAgent: navigator.userAgent,
          language: navigator.language,
          languages: navigator.languages,
          webdriver: navigator.webdriver,
          platform: navigator.platform,
          cookieEnabled: navigator.cookieEnabled,
        })
        """
    )
    log(
        "ブラウザ診断: "
        f"userAgent={diagnostics['userAgent']!r}, "
        f"language={diagnostics['language']!r}, "
        f"languages={diagnostics['languages']!r}, "
        f"webdriver={diagnostics['webdriver']}, "
        f"platform={diagnostics['platform']!r}, "
        f"cookieEnabled={diagnostics['cookieEnabled']}"
    )


def log_cookies(context, label: str) -> None:
    cookies = context.cookies()
    log(f"{label}: cookie count={len(cookies)}")
    for index, cookie in enumerate(cookies, start=1):
        log(
            f"{label}: cookie[{index}] "
            f"name={cookie.get('name')!r}, domain={cookie.get('domain')!r}, "
            f"path={cookie.get('path')!r}, value_present={bool(cookie.get('value'))}"
        )


def setup_network_logging(page) -> None:
    def on_request(request) -> None:
        if request.is_navigation_request() or request.method == "POST":
            log(f"通信診断: request method={request.method}, url={request.url}")
            post_data = format_post_data(request.post_data)
            if post_data:
                log(f"通信診断: request post_data={post_data}")

    def on_response(response) -> None:
        request = response.request
        if request.is_navigation_request() or request.method == "POST":
            log(f"通信診断: response status={response.status}, url={response.url}")

    page.on("request", on_request)
    page.on("response", on_response)


def open_login_page(page, entry_mode: str) -> None:
    if entry_mode == "detect-first":
        log(f"Captive Portal 検出URL遷移開始: {CHECK_URL}")
        try:
            page.goto(CHECK_URL, wait_until="domcontentloaded", timeout=30_000)
            log(f"Captive Portal 検出URL遷移完了: {page.url}")
            log("検出URL後待機開始: 5秒")
            page.wait_for_timeout(5_000)
            log(f"検出URL後待機完了: current_url={page.url}")
            if has_login_form(page):
                log("Captive Portal 検出URLからログインフォームを検出")
                return
        except PlaywrightError as error:
            if "net::ERR_ABORTED" in str(error):
                log(f"Captive Portal 検出URL遷移は 204 応答のため中断扱い: {error}")
            else:
                raise
        log("Captive Portal 検出URLではログインフォーム未検出。直接認証URLへフォールバックします")
    elif entry_mode != "direct":
        raise RuntimeError(f"Unknown entry mode: {entry_mode}")

    log(f"認証ページ遷移開始: {LOGIN_URL}")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    log(f"認証ページ遷移完了: {page.url}")
    log("JSリダイレクト・描画待機開始: 5秒")
    page.wait_for_timeout(5_000)
    log(f"待機完了: current_url={page.url}")


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


def save_html(page, path: Path) -> None:
    content = page.content()
    for secret in (USERNAME, PASSWORD):
        if secret:
            content = content.replace(secret, f"<masked length={len(secret)}>")
    content = re.sub(
        r'(<input[^>]+name=["\']password["\'][^>]*value=["\'])[^"\']*(["\'])',
        r"\1<masked>\2",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r'(<input[^>]+name=["\']user["\'][^>]*value=["\'])[^"\']*(["\'])',
        r"\1<masked>\2",
        content,
        flags=re.IGNORECASE,
    )
    path.write_text(content, encoding="utf-8")
    log(f"HTML保存完了: {path}")


def detect_login_failure(page) -> str | None:
    body_text = page.evaluate(
        "() => document.body ? document.body.innerText : document.documentElement.innerText"
    )
    if INVALID_CREDENTIALS_TEXT and INVALID_CREDENTIALS_TEXT in body_text:
        return LOGIN_INVALID_CREDENTIALS
    if REQUIRED_PARAMETER_TEXT and REQUIRED_PARAMETER_TEXT in body_text:
        return LOGIN_REQUIRED_PARAMETER
    return None


def run_login(
    dry_run: bool,
    submit_mode: str,
    input_mode: str,
    before_submit_wait_ms: int,
    headless: bool,
    browser_channel: str | None,
    user_data_dir: str | None,
    entry_mode: str,
) -> str:
    require_credentials()

    ts = timestamp()
    log(f"実行ID: {ts}")

    with sync_playwright() as p:
        log("Chromium 起動開始")
        browser = None
        browser_options = {"headless": headless}
        if browser_channel:
            browser_options["channel"] = browser_channel
        context_options = {
            "viewport": {"width": 1366, "height": 768},
            "user_agent": USER_AGENT,
            "locale": "ja-JP",
            "timezone_id": "Asia/Tokyo",
            "extra_http_headers": {"Accept-Language": ACCEPT_LANGUAGE},
        }

        def launch_context():
            if user_data_dir:
                profile_dir = str(Path(user_data_dir))
                launched_context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    **browser_options,
                    **context_options,
                )
                log(f"Chromium 永続プロファイル起動完了: user_data_dir={profile_dir}")
                return None, launched_context

            launched_browser = p.chromium.launch(**browser_options)
            log("Chromium 起動完了")
            return launched_browser, launched_browser.new_context(**context_options)

        try:
            browser, context = launch_context()
        except PlaywrightError as error:
            if browser_channel and "Chromium distribution" in str(error):
                log(f"Chrome チャンネル起動失敗: {error}")
                log("Chrome チャンネルを使わず、Playwright bundled Chromium で再試行します")
                browser_options.pop("channel", None)
                browser, context = launch_context()
            elif not headless and (
                "Missing X server" in str(error)
                or "Target page, context or browser has been closed" in str(error)
            ):
                log(f"headed 起動失敗: {error}")
                log("画面表示が利用できないため、headless=True で再試行します")
                browser_options["headless"] = True
                browser, context = launch_context()
            else:
                raise

        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined,
            });
            """
        )
        page = context.new_page()
        setup_network_logging(page)
        log("新規ページ作成完了")

        try:
            open_login_page(page, entry_mode=entry_mode)
            log_browser_diagnostics(page)

            save_screenshot(page, SCREENSHOT_DIR / f"{ts}-01-opened.png")
            save_html(page, SCREENSHOT_DIR / f"{ts}-01-opened.html")
            log_cookies(context, "Cookie診断: opened")

            if not has_login_form(page):
                log("フォーム未検出: 認証フォームが見つかりません")
                log("フォーム未検出: Captive Portal 検出URLが認証ページへリダイレクトされていない可能性があります")
                log(f"最終URL: {page.url}")
                return LOGIN_FORM_NOT_FOUND

            fill_username(page, input_mode=input_mode)
            fill_password(page, input_mode=input_mode)
            wait_submit_enabled(page)
            save_screenshot(page, SCREENSHOT_DIR / f"{ts}-02-filled.png")
            save_html(page, SCREENSHOT_DIR / f"{ts}-02-filled.html")
            log_cookies(context, "Cookie診断: filled")

            if dry_run:
                log("dry-run: ログイン送信せず終了")
                log(f"最終URL: {page.url}")
                return LOGIN_OK

            if before_submit_wait_ms > 0:
                log(f"送信前待機開始: {before_submit_wait_ms}ms")
                page.wait_for_timeout(before_submit_wait_ms)
                log(f"送信前待機完了: current_url={page.url}")

            log_before_submit_diagnostics(page)
            log_cookies(context, "Cookie診断: before-submit")
            submit_login(page, submit_mode=submit_mode)

            log("ログイン後待機開始: 10秒")
            page.wait_for_timeout(10_000)
            log(f"ログイン後待機完了: current_url={page.url}")

            save_screenshot(page, SCREENSHOT_DIR / f"{ts}-03-after-submit.png")
            save_html(page, SCREENSHOT_DIR / f"{ts}-03-after-submit.html")
            log_cookies(context, "Cookie診断: after-submit")
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
            context.close()
            if browser:
                browser.close()
            log("Chromium 終了完了")


def apply_windows_manual_defaults(args: argparse.Namespace) -> None:
    """Apply a Windows-native, visible-browser preset.

    The preset is intentionally explicit so it can be used from run_windows.ps1
    without requiring a long command line each time.
    """

    args.headed = True
    args.browser_channel = args.browser_channel or "chrome"
    args.user_data_dir = args.user_data_dir or ".playwright-profile"
    args.submit_mode = "click"
    args.input_mode = "type"
    args.before_submit_wait_ms = max(args.before_submit_wait_ms, 5000)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Fill the form but do not submit.")
    parser.add_argument("--force", action="store_true", help="Run login even if connectivity check succeeds.")
    parser.add_argument(
        "--windows-manual",
        action="store_true",
        help="Use Windows-native headed defaults: Chrome channel, persistent profile, click submit, type input.",
    )
    parser.add_argument(
        "--submit-mode",
        choices=["click", "nwa", "form-submit"],
        default="nwa",
        help="Submit method. Default: nwa.",
    )
    parser.add_argument(
        "--input-mode",
        choices=["fill", "type"],
        default="type",
        help="Input method. Default: type.",
    )
    parser.add_argument(
        "--before-submit-wait-ms",
        type=int,
        default=1000,
        help="Wait time after filling the form and before submitting. Default: 1000.",
    )
    parser.add_argument("--headed", action="store_true", help="Run Chromium with a visible window.")
    parser.add_argument("--browser-channel", help="Playwright browser channel, for example chrome.")
    parser.add_argument("--user-data-dir", help="Persistent Chromium profile directory.")
    parser.add_argument(
        "--entry-mode",
        choices=["detect-first", "direct"],
        default="detect-first",
        help="Open CHECK_URL first to follow Captive Portal redirect, or open CAPTIVE_PORTAL_URL directly. Default: detect-first.",
    )
    args = parser.parse_args()

    if args.windows_manual:
        apply_windows_manual_defaults(args)

    log("処理開始")
    log(
        "mode: "
        f"dry_run={args.dry_run}, force={args.force}, windows_manual={args.windows_manual}, "
        f"submit_mode={args.submit_mode}, input_mode={args.input_mode}, "
        f"before_submit_wait_ms={args.before_submit_wait_ms}, "
        f"headless={not args.headed}, browser_channel={args.browser_channel}, "
        f"user_data_dir={args.user_data_dir}, entry_mode={args.entry_mode}"
    )

    online_before = check_online()

    if online_before and not args.force:
        log("オンライン判定: すでに接続済み。処理終了")
        return

    if online_before and args.force:
        log("注意: 実行前からオンライン。ログイン成功判定はできない")

    log("オフラインまたは強制実行: Captive Portal 認証処理を開始")
    login_result = run_login(
        dry_run=args.dry_run,
        submit_mode=args.submit_mode,
        input_mode=args.input_mode,
        before_submit_wait_ms=args.before_submit_wait_ms,
        headless=not args.headed,
        browser_channel=args.browser_channel,
        user_data_dir=args.user_data_dir,
        entry_mode=args.entry_mode,
    )

    if login_result == LOGIN_INVALID_CREDENTIALS:
        log("認証失敗")
        log("処理終了")
        return

    if login_result == LOGIN_REQUIRED_PARAMETER:
        log("フォームパラメータ不足")
        log("処理終了")
        return

    if login_result == LOGIN_FORM_NOT_FOUND:
        log("フォーム未検出")
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
