# Campus Captive Portal Auto Login

大学ネットワークの Captive Portal 認証を、Playwright で補助するためのリポジトリ。

## 目的

研究室の Windows PC を、Tailscale + SSH 経由の計算リソースとして使う。

ただし、大学ネットワークの認証が切れると以下の状態になる。

- インターネット不可
- Tailscale 切断
- SSH 不可

そのため、PC 自身で認証ページを開き、ブラウザ上でログインできる状態にする。

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
├── manual_login_windows.py
├── test.py
└── captive_login.py
```

- `manual_login_windows.py`: Windows 上でブラウザを表示し、ID/Password入力後、最後のログイン操作だけ手動で行うためのスクリプト。
- `captive_login.py`: 自動送信用の既存スクリプト。
- `setup_windows.bat`: Windows ネイティブ環境の初期セットアップ。Python がなければ winget で Python 3.12 のインストールも試す。
- `run_windows.bat`: `manual_login_windows.py` を実行するラッパー。
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

`.env` は Git に入れない。

## Windows で手動実行

通常実行:

```bat
run_windows.bat
```

`run_windows.bat` は内部で以下に相当する実行を行う。

```bat
.venv\Scripts\python.exe manual_login_windows.py
```

流れ:

```text
CHECK_URL を開く
↓
Captive Portal にリダイレクトされれば、そのページを使う
↓
リダイレクトされなければ CAPTIVE_PORTAL_URL を直接開く
↓
ID / Password を入力
↓
ブラウザを開いたまま停止
↓
ユーザーがブラウザ上でログインボタンを手動クリック
↓
ターミナルで Enter
↓
スクリーンショットとHTMLを保存
```

`required parameter unavailable` が出る場合、まずこの手動実行を使う。自動送信ではなく、ブラウザ上で実際にログインボタンを押すことで、ページ側のJavaScriptやhidden input更新をそのまま使う。

## 実行ログ

スクリーンショットとHTMLは `screenshots/` に保存される。

```text
screenshots/YYYYMMDD-HHMMSS-01-opened.png
screenshots/YYYYMMDD-HHMMSS-02-filled.png
screenshots/YYYYMMDD-HHMMSS-03-after-manual-login.png
```

HTML保存時、`.env` のユーザー名とパスワードはマスクされる。

## 自動送信を試す場合

既存の `captive_login.py` を直接実行する。

```bat
.venv\Scripts\python.exe captive_login.py --windows-manual --force
```

ただし、`required parameter unavailable` が出る場合は、`manual_login_windows.py` を優先する。

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
