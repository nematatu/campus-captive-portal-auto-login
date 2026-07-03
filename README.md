# Campus Captive Portal Auto Login

大学ネットワークの Captive Portal 認証を、Playwright で自動化するためのリポジトリ。

## 目的

研究室の Windows PC を、Tailscale + SSH 経由の計算リソースとして使う。

ただし、大学ネットワークの認証が切れると以下の状態になる。

- インターネット不可
- Tailscale 切断
- SSH 不可

そのため、PC 自身が認証状態を確認し、必要なら Captive Portal 認証を実行する。

## 今回の方針

WSL ではなく、Windows ネイティブの Python から実行する。

理由:

- WSL の headed 実行は X server / DISPLAY に依存する。
- 今回は、実際に見えるブラウザを起動して、通常の人間操作に近い形でログイン認証したい。
- Windows 側で Chrome / Chromium を起動すれば、通常のデスクトップセッション上でブラウザ操作を確認できる。

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
├── test.py
└── captive_login.py
```

- `captive_login.py`: 本番用ログインスクリプト。
- `setup_windows.bat`: Windows ネイティブ環境の初期セットアップ。
- `run_windows.bat`: Windows 上で headed ブラウザを起動してログイン処理を実行。
- `test.py`: 認証ページを開いて `login.png` を保存する簡易確認用。

## Windows セットアップ

コマンドプロンプト、PowerShell、Windows Terminal のいずれかで実行する。

```bat
setup_windows.bat
```

実行内容:

1. `.venv` 作成
2. `requirements.txt` インストール
3. Playwright Chromium インストール
4. `.env.example` から `.env` を作成
5. `logs/` と `screenshots/` を作成

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
BROWSER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36
BROWSER_ACCEPT_LANGUAGE=ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7
```

`.env` は Git に入れない。

## Windows で手動実行

通常実行:

```bat
run_windows.bat
```

`run_windows.bat` は内部で以下に相当する実行を行う。

```bat
.venv\Scripts\python.exe captive_login.py --windows-manual
```

`--windows-manual` は以下のプリセットを適用する。

```text
--headed
--browser-channel chrome
--user-data-dir .playwright-profile
--submit-mode click
--input-mode type
--before-submit-wait-ms 5000
```

Google Chrome が Playwright から見つからない場合、スクリプトは Playwright bundled Chromium にフォールバックする。

強制実行:

```bat
run_windows.bat --force
```

送信なし確認:

```bat
run_windows.bat --dry-run --force
```

直接認証URLを開く:

```bat
run_windows.bat --force --entry-mode direct
```

## Python から直接実行する場合

```bat
.venv\Scripts\python.exe captive_login.py --windows-manual --force
```

Chrome チャンネルを使わない場合:

```bat
.venv\Scripts\python.exe captive_login.py --headed --user-data-dir .playwright-profile --submit-mode click --input-mode type --before-submit-wait-ms 5000 --force
```

## 実行ログ

スクリーンショットとHTMLは `screenshots/` に保存される。

```text
screenshots/YYYYMMDD-HHMMSS-01-opened.png
screenshots/YYYYMMDD-HHMMSS-02-filled.png
screenshots/YYYYMMDD-HHMMSS-03-after-submit.png
```

HTML保存時、`.env` のユーザー名とパスワードはマスクされる。

## WSL / Linux セットアップ

WSL / Linux で試す場合は以下を使う。

```bash
chmod +x setup.sh
./setup.sh
```

ただし、headed 実行は X server / DISPLAY に依存する。Windowsで見えるブラウザを起動したい場合は、WSLではなく `setup_windows.bat` と `run_windows.bat` を使う。

## 注意

- `.env` をコミットしない。
- 認証情報をコードに直書きしない。
- スクリーンショットに情報が写る可能性があるため Git に入れない。
- `.playwright-profile/` は Git に入れない。
- CAPTCHA / MFA / OTP には対応しない。
- 利用前にネットワーク利用規程を確認する。
