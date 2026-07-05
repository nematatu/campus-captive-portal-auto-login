# Campus Captive Portal Auto Login

大学ネットワークの Captive Portal 認証を補助するためのリポジトリ。

## 目的

研究室の Windows PC を、Tailscale + SSH 経由の計算リソースとして使う。

ただし、大学ネットワークの認証が切れると以下の状態になる。

- インターネット不可
- Tailscale 切断
- SSH 不可

そのため、PC 自身で認証ページを開き、ブラウザ上でログインできる状態にする。

## 現在の方針

Playwright 管理下の Chrome でログイン送信すると、手動クリックでも `required parameter unavailable` が出るケースがある。

一方で、Playwright で得られた `final_url` を通常の Windows ブラウザで開き、そこでログインすると成功する。

そのため、現在は以下の方式にする。

```text
Playwright で Captive Portal の final_url だけ取得
↓
通常の Chrome / Edge を --app モードで開く
↓
OSレベルのキーボード入力で ID / Password を入力
↓
Enter で送信
```

## ファイル

```text
.
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.sh
├── setup_windows.bat
├── run_windows.bat
├── auto_type_real_browser_windows.py
├── open_real_browser_windows.py
├── manual_login_windows.py
├── test.py
└── captive_login.py
```

- `auto_type_real_browser_windows.py`: final_url を解決し、通常の Chrome / Edge に対して OS レベルのキー入力で ID / Password 入力と Enter 送信を行う。
- `open_real_browser_windows.py`: Playwright で Captive Portal の final_url を解決し、通常の Windows ブラウザで開く。
- `run_windows.bat`: `auto_type_real_browser_windows.py` を実行するラッパー。
- `manual_login_windows.py`: Playwright 管理下ブラウザで入力し、最後だけ手動クリックする旧切り分け用スクリプト。
- `captive_login.py`: 自動送信用の既存スクリプト。
- `setup_windows.bat`: Windows ネイティブ環境の初期セットアップ。Python がなければ winget で Python 3.12 のインストールも試す。
- `test.py`: 認証ページを開いて `login.png` を保存する簡易確認用。

## Windows セットアップ

コマンドプロンプト、PowerShell、Windows Terminal のいずれかで実行する。

```bat
setup_windows.bat
```

実行内容:

1. Python 3.10 以上の確認
2. Python が見つからない場合は winget で Python 3.12 をインストール
3. `.venv` 作成
4. `requirements.txt` インストール
5. Playwright Chromium インストール
6. `.env.example` から `.env` を作成
7. `logs/` と `screenshots/` を作成

`.env` を編集する。

```env
CAPTIVE_PORTAL_URL=http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php
CAPTIVE_USERNAME=your-id
CAPTIVE_PASSWORD=your-password
CHECK_URL=http://connectivitycheck.gstatic.com/generate_204
USERNAME_SELECTOR=input[name="user"]
PASSWORD_SELECTOR=input[name="password"]
SUBMIT_SELECTOR=input[type="submit"]
PORTAL_INVALID_CREDENTIALS_TEXT=ユーザー名またはパスワードが無効です
PORTAL_REQUIRED_PARAMETER_TEXT=required parameter unavailable
```

必要なら通常ブラウザのパスと入力待機時間を指定する。

```env
REAL_BROWSER_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
REAL_BROWSER_WAIT_SECONDS=5
REAL_BROWSER_INITIAL_TAB_COUNT=1
```

`.env` は Git に入れない。

## Windows で実行

```bat
run_windows.bat
```

`run_windows.bat` は内部で以下に相当する実行を行う。

```bat
.venv\Scripts\python.exe auto_type_real_browser_windows.py
```

流れ:

```text
CHECK_URL を Playwright で開く
↓
Captive Portal にリダイレクトされた final_url を取得
↓
通常の Chrome / Edge を --app モードで起動
↓
少し待機
↓
Tab を指定回数押す
↓
ID を貼り付け
↓
Tab
↓
Password を貼り付け
↓
Enter で送信
```

Enter送信せず、入力だけ行う場合:

```bat
run_windows.bat --no-submit
```

URLだけ確認する場合:

```bat
run_windows.bat --url-only
```

入力位置がずれる場合は、Tab回数を調整する。

```bat
run_windows.bat --tab-count 2
run_windows.bat --tab-count 3
```

ページ表示が遅い場合は、待機秒数を増やす。

```bat
run_windows.bat --wait-seconds 8
```

URL解決用の一時 Playwright ブラウザを表示したい場合:

```bat
run_windows.bat --headed-resolver
```

## 実行ログ

解決したURLは `screenshots/` に保存される。

```text
screenshots/YYYYMMDD-HHMMSS-resolved-url.txt
```

## 旧方式

通常ブラウザで開くだけの場合:

```bat
.venv\Scripts\python.exe open_real_browser_windows.py
```

Playwright 管理下ブラウザでID/Passwordを入力し、最後だけ手動クリックする旧切り分け用スクリプト:

```bat
.venv\Scripts\python.exe manual_login_windows.py
```

自動送信を試す場合:

```bat
.venv\Scripts\python.exe captive_login.py --windows-manual --force
```

ただし、Playwright 管理下ブラウザで `required parameter unavailable` が出る場合は、`run_windows.bat` の通常ブラウザ + OS キー入力方式を使う。

## WSL / Linux セットアップ

WSL / Linux で試す場合は以下を使う。

```bash
chmod +x setup.sh
./setup.sh
```

ただし、headed 実行は X server / DISPLAY に依存する。Windowsで通常ブラウザを開きたい場合は、WSLではなく `setup_windows.bat` と `run_windows.bat` を使う。

## 注意

- `.env` をコミットしない。
- 認証情報をコードに直書きしない。
- スクリーンショットに情報が写る可能性があるため Git に入れない。
- `.playwright-profile/` と `.playwright-url-resolver-profile/` は Git に入れない。
- CAPTCHA / MFA / OTP には対応しない。
- 利用前にネットワーク利用規程を確認する。
