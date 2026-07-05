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

LOGIN_URL = os.getenv("CAPTIVE_PORTAL_URL", "http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php")
CHECK_URL = os.getenv("CHECK_URL", "http://connectivitycheck.gstatic.com/generate_204")
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
    os.getenv("PORTAL_INVALID_CREDENTIALS_TEXT") or "ユーザー名またはパスワードが無効です"
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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def normalize_argv(argv: list[str]) -> list[str]:
    """Accept common Windows/manual shorthand.

    Examples:
      force -> --force
      /force -> --force
      -force -> --force
      —force -> --force
      direct -> --entry-mode direct
      human -> --input-mode human
      nwa -> --submit-mode nwa
    """

    normalized: list[str] = []
    flag_aliases = {
        "force": "--force",
        "dry-run": "--dry-run",
        "dryrun": "--dry-run",
        "windows-manual": "--windows-manual",
        "windows": "--windows-manual",
        "headed": "--headed",
        "keep-open-on-failure": "--keep-open-on-failure",
        "keep-open": "--keep-open-on-failure",
    }
    entry_modes = {"detect-first", "direct"}
    submit_modes = {"auto", "click", "nwa", "form-submit", "enter"}
    input_modes = {"fill", "type", "human"}

    expecting_value_for: str | None = None
    options_with_values = {
        "--submit-mode",
        "--input-mode",
        "--before-submit-wait-ms",
        "--browser-channel",
        "--user-data-dir",
        "--entry-mode",
    }

    for raw_arg in argv:
        arg = raw_arg.strip()
        if not arg:
            continue

        arg = arg.replace("—", "--").replace("–", "--").replace("−", "-")

        if expecting_value_for:
            normalized.append(arg)
            expecting_value_for = None
            continue

        if arg in options_with_values:
            normalized.append(arg)
            expecting_value_for = arg
            continue

        lowered = arg.lower().lstrip("-/")

        if lowered in flag_aliases:
            normalized.append(flag_aliases[lowered])
        elif lowered in entry_modes:
            normalized.extend(["--entry-mode", lowered])
        elif lowered in submit_modes:
            normalized.extend(["--submit-mode", lowered])
        elif lowered in input_modes:
            normalized.extend(["--input-mode", lowered])
        else:
            normalized.append(arg)

    return normalized


def mask_sensitive_value(name: str, value: str) -> str:
    lowered = name.lower()
    if lowered in {"user", "username", "login", "id"} or "pass" in lowered:
        return f"<masked length={len(value)}>"
    return value


def format_post_data(post_data: str | None) -> str:
    if not post_data:
        return ""
    pairs = parse_qsl(post_data, keep_blank_values=True)
    if not pairs:
        return post_data[:500]
    return "&".join(
        f"{name}={mask_sensitive_value(name, value)!r}" for name, value in pairs
    )


def check_online() -> bool:
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
    missing = []
    if not USERNAME:
        missing.append("CAPTIVE_USERNAME")
    if not PASSWORD:
        missing.append("CAPTIVE_PASSWORD")

    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing environment variables: {names}. Edit .env first.")


def get_first(page, selector: str, label: str):
    locator = page.locator(selector)
    count = locator.count()
    log(f"{label}確認: selector={selector}, count={count}")
    if count == 0:
        raise RuntimeError(f"{label} was not found. selector={selector}")
    return locator.first


def fire_input_events(locator) -> None:
    locator.dispatch_event("input")
    locator.dispatch_event("change")
    locator.evaluate("(el) => el.blur()")


def fill_field(page, selector: str, value: str, label: str, input_mode: str) -> None:
    field = get_first(page, selector, label)
    log(f"{label}入力開始: mode={input_mode}")

    if input_mode == "fill":
        field.fill(value)
    elif input_mode == "type":
        field.click()
        modifier = "Meta" if sys.platform == "darwin" else "Control"
        page.keyboard.press(f"{modifier}+A")
        page.keyboard.type(value, delay=50)
    else:
        raise RuntimeError(f"Unknown selector input mode: {input_mode}")

    fire_input_events(field)
    log(f"{label}入力完了")


def fill_login(page, input_mode: str) -> None:
    if input_mode == "human":
        log("人間操作風入力開始")
        username = get_first(page, USERNAME_SELECTOR, "ユーザー名 input")
        username.click()
        modifier = "Meta" if sys.platform == "darwin" else "Control"
        page.keyboard.press(f"{modifier}+A")
        page.keyboard.type(USERNAME, delay=80)
        page.keyboard.press("Tab")
        page.keyboard.press(f"{modifier}+A")
        page.keyboard.type(PASSWORD, delay=80)
        page.keyboard.press("Tab")
        log("人間操作風入力完了")
        return

    fill_field(page, USERNAME_SELECTOR, USERNAME, "ユーザー名 input", input_mode)
    fill_field(page, PASSWORD_SELECTOR, PASSWORD, "パスワード input", input_mode)


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
    return form_count > 0 and username_count > 0 and password_count > 0


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
            page.wait_for_timeout(5_000)
            log(f"Captive Portal 検出URL遷移完了: {page.url}")
            if has_login_form(page):
                log("Captive Portal 検出URLからログインフォームを検出")
                return
        except PlaywrightError as error:
            if "net::ERR_ABORTED" in str(error):
                log(f"Captive Portal 検出URL遷移は204応答のため中断扱い: {error}")
            else:
                raise
        log("Captive Portal 検出URLではログインフォーム未検出。直接認証URLへフォールバック")
    elif entry_mode != "direct":
        raise RuntimeError(f"Unknown entry mode: {entry_mode}")

    log(f"認証ページ遷移開始: {LOGIN_URL}")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(5_000)
    log(f"認証ページ遷移完了: {page.url}")


def save_artifacts(page, ts: str, label: str) -> None:
    png = SCREENSHOT_DIR / f"{ts}-{label}.png"
    html = SCREENSHOT_DIR / f"{ts}-{label}.html"

    page.screenshot(path=str(png), full_page=True)

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
    html.write_text(content, encoding="utf-8")
    log(f"保存完了: {png}, {html}")


def log_before_submit(page) -> None:
    diagnostics = page.evaluate(
        """
        ({ usernameSelector, passwordSelector, submitSelector }) => {
          const form = document.querySelector("form");
          const user = document.querySelector(usernameSelector);
          const password = document.querySelector(passwordSelector);
          const submit = document.querySelector(submitSelector);
          return {
            url: location.href,
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
              name: submit.getAttribute("name") || "",
              value: submit.value || "",
              disabled: !!submit.disabled,
            } : null,
            hasNwaSubmitForm: typeof window.Nwa_SubmitForm === "function",
          };
        }
        """,
        {
            "usernameSelector": USERNAME_SELECTOR,
            "passwordSelector": PASSWORD_SELECTOR,
            "submitSelector": SUBMIT_SELECTOR,
        },
    )
    log(f"送信直前診断: url={diagnostics['url']}")
    log(f"送信直前診断: form={diagnostics['form']}")
    log(f"送信直前診断: hidden input count={len(diagnostics['hiddenInputs'])}")
    for index, hidden in enumerate(diagnostics["hiddenInputs"], start=1):
        log(f"送信直前診断: hidden[{index}] name={hidden['name']!r}, value={hidden['value']!r}")
    log(f"送信直前診断: user={diagnostics['userInput']}")
    log(f"送信直前診断: password={diagnostics['passwordInput']}")
    log(f"送信直前診断: submit={diagnostics['submitInput']}")
    log(f"送信直前診断: Nwa_SubmitForm={diagnostics['hasNwaSubmitForm']}")


def has_nwa_submit_form(page) -> bool:
    return bool(page.evaluate("() => typeof window.Nwa_SubmitForm === 'function'"))


def wait_submit_enabled(page, required: bool) -> None:
    submit = page.locator(SUBMIT_SELECTOR)
    if submit.count() == 0:
        if required:
            raise RuntimeError(f"submit was not found. selector={SUBMIT_SELECTOR}")
        log("submit未検出。Enter送信を続行")
        return

    submit.first.wait_for(state="attached", timeout=10_000)
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


def submit_login(page, submit_mode: str) -> None:
    log(f"ログイン送信開始: mode={submit_mode}")

    if submit_mode == "auto":
        submit_mode = "nwa" if has_nwa_submit_form(page) else "click"
        log(f"auto送信で選択: {submit_mode}")

    if submit_mode == "nwa":
        wait_submit_enabled(page, required=True)
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
    elif submit_mode == "click":
        wait_submit_enabled(page, required=True)
        page.locator(SUBMIT_SELECTOR).first.click()
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
    elif submit_mode == "enter":
        wait_submit_enabled(page, required=False)
        page.keyboard.press("Enter")
    else:
        raise RuntimeError(f"Unknown submit mode: {submit_mode}")

    log(f"ログイン送信完了: mode={submit_mode}")


def detect_login_failure(page) -> str | None:
    body_text = page.evaluate(
        "() => document.body ? document.body.innerText : document.documentElement.innerText"
    )
    if INVALID_CREDENTIALS_TEXT and INVALID_CREDENTIALS_TEXT in body_text:
        return LOGIN_INVALID_CREDENTIALS
    if REQUIRED_PARAMETER_TEXT and REQUIRED_PARAMETER_TEXT in body_text:
        return LOGIN_REQUIRED_PARAMETER
    return None


def launch_context(playwright, args: argparse.Namespace):
    browser_options = {"headless": not args.headed}
    if args.browser_channel:
        browser_options["channel"] = args.browser_channel

    context_options = {
        "viewport": {"width": 1366, "height": 768},
        "user_agent": USER_AGENT,
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
        "extra_http_headers": {"Accept-Language": ACCEPT_LANGUAGE},
    }

    if args.user_data_dir:
        context = playwright.chromium.launch_persistent_context(
            str(Path(args.user_data_dir)),
            **browser_options,
            **context_options,
        )
        log(f"永続プロファイル起動完了: user_data_dir={args.user_data_dir}")
        return None, context

    browser = playwright.chromium.launch(**browser_options)
    return browser, browser.new_context(**context_options)


def run_login(args: argparse.Namespace) -> str:
    require_credentials()
    ts = timestamp()

    with sync_playwright() as p:
        browser = None
        try:
            browser, context = launch_context(p, args)
        except PlaywrightError as error:
            if args.browser_channel and "Chromium distribution" in str(error):
                log(f"Chrome チャンネル起動失敗: {error}")
                log("Chrome チャンネルを使わず、Playwright bundled Chromium で再試行")
                args.browser_channel = None
                browser, context = launch_context(p, args)
            else:
                raise

        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = context.new_page()
        setup_network_logging(page)
        keep_open = False

        try:
            open_login_page(page, entry_mode=args.entry_mode)
            save_artifacts(page, ts, "01-opened")

            if not has_login_form(page):
                keep_open = args.keep_open_on_failure
                return LOGIN_FORM_NOT_FOUND

            fill_login(page, input_mode=args.input_mode)
            save_artifacts(page, ts, "02-filled")

            if args.dry_run:
                return LOGIN_OK

            if args.before_submit_wait_ms > 0:
                page.wait_for_timeout(args.before_submit_wait_ms)

            log_before_submit(page)
            submit_login(page, submit_mode=args.submit_mode)

            page.wait_for_timeout(10_000)
            save_artifacts(page, ts, "03-after-submit")

            failure = detect_login_failure(page)
            if failure:
                keep_open = args.keep_open_on_failure
                return failure

            return LOGIN_OK

        except (PlaywrightTimeoutError, Exception) as error:
            save_artifacts(page, ts, "error")
            keep_open = args.keep_open_on_failure
            raise error
        finally:
            if keep_open:
                log("失敗時保持: ブラウザを閉じずに待機します。終了するには Ctrl+C")
                try:
                    page.wait_for_timeout(24 * 60 * 60 * 1000)
                except KeyboardInterrupt:
                    pass
            context.close()
            if browser:
                browser.close()


def apply_windows_manual_defaults(args: argparse.Namespace) -> None:
    args.headed = True
    args.browser_channel = args.browser_channel or "chrome"
    args.user_data_dir = args.user_data_dir or ".playwright-profile"
    args.before_submit_wait_ms = max(args.before_submit_wait_ms, 5000)
    if args.keep_open_on_failure is None:
        args.keep_open_on_failure = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="入力だけ行い、送信しない")
    parser.add_argument("--force", action="store_true", help="接続済み判定でもログイン処理を実行する")
    parser.add_argument("--windows-manual", action="store_true", help="Windows向け既定値を使う")
    parser.add_argument(
        "--submit-mode",
        choices=["auto", "click", "nwa", "form-submit", "enter"],
        default="auto",
        help="送信方式。既定はauto",
    )
    parser.add_argument(
        "--input-mode",
        choices=["fill", "type", "human"],
        default="type",
        help="入力方式。humanはTab/Enter中心",
    )
    parser.add_argument("--before-submit-wait-ms", type=int, default=1000)
    parser.add_argument("--headed", action="store_true", help="表示ブラウザで起動")
    parser.add_argument("--browser-channel", help="chrome など")
    parser.add_argument("--user-data-dir", help="永続プロファイルディレクトリ")
    parser.add_argument("--entry-mode", choices=["detect-first", "direct"], default="detect-first")
    parser.add_argument("--keep-open-on-failure", action="store_true", default=None, help="失敗時にブラウザを閉じない")

    raw_args = sys.argv[1:]
    normalized_args = normalize_argv(raw_args)
    if raw_args != normalized_args:
        log(f"引数正規化: raw={raw_args} -> normalized={normalized_args}")

    args, unknown = parser.parse_known_args(normalized_args)
    if unknown:
        log(f"警告: 未使用の引数を無視します: {unknown}")

    if args.windows_manual:
        apply_windows_manual_defaults(args)
    elif args.keep_open_on_failure is None:
        args.keep_open_on_failure = False

    return args


def main() -> None:
    args = parse_args()
    log(
        "mode: "
        f"dry_run={args.dry_run}, force={args.force}, windows_manual={args.windows_manual}, "
        f"submit_mode={args.submit_mode}, input_mode={args.input_mode}, "
        f"before_submit_wait_ms={args.before_submit_wait_ms}, headed={args.headed}, "
        f"browser_channel={args.browser_channel}, user_data_dir={args.user_data_dir}, "
        f"entry_mode={args.entry_mode}, keep_open_on_failure={args.keep_open_on_failure}"
    )

    online_before = check_online()
    if online_before and not args.force:
        log("オンライン判定: すでに接続済み。処理終了")
        return
    if online_before and args.force:
        log("注意: 実行前からオンライン。ログイン成功判定はできない")

    result = run_login(args)

    if result == LOGIN_INVALID_CREDENTIALS:
        log("認証失敗: 認証情報エラー")
        return
    if result == LOGIN_REQUIRED_PARAMETER:
        log("フォームパラメータ不足: detect-first / auto / human / enter を試してください")
        return
    if result == LOGIN_FORM_NOT_FOUND:
        log("フォーム未検出")
        return
    if args.dry_run:
        log("処理終了: dry-run")
        return

    online_after = check_online()
    if not online_before and online_after:
        log("復旧成功")
    elif online_before and online_after:
        log("疎通OK。ただし実行前からオンライン")
    else:
        log("ログイン後も疎通失敗")


if __name__ == "__main__":
    main()
