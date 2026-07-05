# Campus Captive Portal Auto Login

大学ネットワークの Captive Portal 認証を、研究室 Windows PC 上でローカル実行するためのリポジトリです。

## 目的

研究室の Windows PC を Tailscale + SSH 経由の計算リソースとして使う。

ただし、大学ネットワークの認証が切れると以下の状態になります。

- インターネット不可
- Tailscale 切断
- SSH 不可

そのため、外から復旧するのではなく、研究室 PC 自身が認証状態を確認し、必要なら Captive Portal 認証を実行します。

## 重要な前提

`required parameter unavailable` が出る場合、ID/パスワード入力の問題ではなく、認証ページへの入り方が問題である可能性が高いです。

Captive Portal は、`cp-login.php` を直接開くだけではなく、通常の HTTP ページへアクセスしたときのリダイレクトで必要パラメータを付ける場合があります。

そのため、現在の既定値は `direct` ではなく `portal-flow` です。

```text
http://neverssl.com/
  ↓
大学ネットワーク側で Captive Portal にリダイレクト
  ↓
必要パラメータ付きの認証ページ
  ↓
ログイン
```

## Windows セットアップ

```bat
setup_windows.bat
```

`.env` を編集します。

```env
CAPTIVE_PORTAL_URL=http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php
CAPTIVE_ENTRY_URL=http://neverssl.com/
CAPTIVE_USERNAME=your-id
CAPTIVE_PASSWORD=your-password
CHECK_URL=http://connectivitycheck.gstatic.com/generate_204
USERNAME_SELECTOR=input[name="user"]
PASSWORD_SELECTOR=input[name="password"]
SUBMIT_SELECTOR=input[type="submit"]
PORTAL_INVALID_CREDENTIALS_TEXT=ユーザー名またはパスワードが無効です
PORTAL_REQUIRED_PARAMETER_TEXT=required parameter unavailable
BROWSER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36
BROWSER_ACCEPT_LANGUAGE=ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7
```

`.env` は Git に入れないでください。

## まず確認するコマンド

```bat
.venv\Scripts\python.exe captive_login.py --help
```

以下が表示されれば、現行版です。

```text
--windows-manual
--submit-mode {auto,click,nwa,form-submit,enter}
--input-mode {fill,type,human}
--entry-mode {portal-flow,detect-first,direct}
```

`unrecognized arguments` が出る場合は、手元の `captive_login.py` が古いか、違うディレクトリで実行しています。

## Windows で実行

通常実行:

```bat
run_windows.bat
```

強制実行:

```bat
run_force.bat
```

人間操作寄りで実行:

```bat
run_human.bat
```

内部的には、現在の `run_human.bat` は次に相当します。

```bat
run_windows.bat force portal-flow auto human
```

## 試す順番

まずこれです。

```bat
run_force.bat
```

だめなら、次です。

```bat
run_human.bat
```

まだ `required parameter unavailable` が出る場合は、`.env` の `CAPTIVE_ENTRY_URL` を別の HTTP URL に変えます。

候補:

```env
CAPTIVE_ENTRY_URL=http://example.com/
```

または:

```env
CAPTIVE_ENTRY_URL=http://httpforever.com/
```

その後、再実行します。

```bat
run_human.bat
```

## entry-mode

```text
portal-flow  通常HTTPページから Captive Portal リダイレクトを踏む。既定値。
detect-first CHECK_URL からリダイレクト検出を試し、だめなら直接URLへフォールバック。
direct       CAPTIVE_PORTAL_URL を直接開く。required parameter unavailable が出やすい。
```

## submit-mode

```text
auto        Nwa_SubmitForm が存在すれば nwa、なければ click
nwa         window.Nwa_SubmitForm(form.id, submit.id) を呼ぶ
click       submit ボタンをクリック
form-submit form.submit() を直接実行
enter       Enter キーで送信
```

## input-mode

```text
fill   Playwright の fill() で値を入れる
type   入力欄をクリックして Ctrl+A → type する
human  ユーザー名欄をクリックし、Tab / type / Enter に寄せる
```

## ログとスクリーンショット

スクリーンショットとHTMLは `screenshots/` に保存されます。

```text
screenshots/YYYYMMDD-HHMMSS-01-opened.png
screenshots/YYYYMMDD-HHMMSS-01-opened.html
screenshots/YYYYMMDD-HHMMSS-02-filled.png
screenshots/YYYYMMDD-HHMMSS-02-filled.html
screenshots/YYYYMMDD-HHMMSS-03-after-submit.png
screenshots/YYYYMMDD-HHMMSS-03-after-submit.html
```

HTML保存時、`.env` のユーザー名とパスワードはマスクされます。

## 注意

- `.env` をコミットしない。
- 認証情報をコードに直書きしない。
- スクリーンショットに情報が写る可能性があるため Git に入れない。
- `.playwright-profile/` は Git に入れない。
- CAPTCHA / MFA / OTP には対応しない。
- 利用前にネットワーク利用規程を確認する。
