# Campus Captive Portal Auto Login

大学ネットワークの Captive Portal 認証を、研究室 Windows PC 上でローカル実行するためのリポジトリです。

## 目的

研究室の Windows PC を Tailscale + SSH 経由の計算リソースとして使う。

ただし、大学ネットワークの認証が切れると以下の状態になります。

- インターネット不可
- Tailscale 切断
- SSH 不可

そのため、外から復旧するのではなく、研究室 PC 自身が認証状態を確認し、必要なら Captive Portal 認証を実行します。

## 方針

WSL ではなく、Windows ネイティブの Python から実行します。

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

コマンドプロンプト、PowerShell、Windows Terminal のいずれかで実行します。

```bat
setup_windows.bat
```

実行内容:

1. `.venv` 作成
2. `requirements.txt` インストール
3. Playwright Chromium インストール
4. `.env.example` から `.env` を作成
5. `logs/` と `screenshots/` を作成

`.env` を編集します。

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

`.env` は Git に入れないでください。

## まず確認するコマンド

ローカルのコードが最新か確認します。

```bat
.venv\Scripts\python.exe captive_login.py --help
```

以下が表示されれば、現行版です。

```text
--windows-manual
--submit-mode {auto,click,nwa,form-submit,enter}
--input-mode {fill,type,human}
--entry-mode {detect-first,direct}
```

`unrecognized arguments` が出る場合は、手元の `captive_login.py` が古いか、違うディレクトリで実行しています。

## Windows で手動実行

通常実行:

```bat
run_windows.bat
```

強制実行:

```bat
run_windows.bat --force
```

送信せず、入力状態だけ確認:

```bat
run_windows.bat --dry-run --force
```

直接認証URLを開く:

```bat
run_windows.bat --force --entry-mode direct
```

## 今回の修正点

以前の実装では、`--windows-manual` が `--submit-mode` を `click` に固定していました。

そのため、次のようなコマンドを打っても、実際には `nwa` 送信を試せない状態でした。

```bat
run_windows.bat --force --submit-mode nwa
```

現在は修正済みです。`--windows-manual` は、表示ブラウザ・Chrome・永続プロファイルなどの Windows 向け既定値だけを設定し、`--submit-mode` と `--input-mode` は上書きしません。

## 試す順番

まずこれを使います。

```bat
run_windows.bat --force --entry-mode detect-first --submit-mode auto --input-mode type
```

`required parameter unavailable` が出る場合は、送信前に必要なパラメータが作られていない可能性があります。次を試します。

```bat
run_windows.bat --force --entry-mode detect-first --submit-mode auto --input-mode human
```

それでもだめなら、直接URLではなく検出URL経由にするか、送信方式を明示して試します。

```bat
run_windows.bat --force --entry-mode direct --submit-mode auto --input-mode human
run_windows.bat --force --entry-mode detect-first --submit-mode nwa --input-mode human
run_windows.bat --force --entry-mode detect-first --submit-mode enter --input-mode human
```

## モードの意味

### submit-mode

```text
auto        Nwa_SubmitForm が存在すれば nwa、なければ click
nwa         window.Nwa_SubmitForm(form.id, submit.id) を呼ぶ
click       submit ボタンをクリック
form-submit form.submit() を直接実行
enter       Enter キーで送信
```

### input-mode

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

## WSL / Linux セットアップ

WSL / Linux で試す場合は以下を使います。

```bash
chmod +x setup.sh
./setup.sh
```

ただし、headed 実行は X server / DISPLAY に依存します。Windowsで見えるブラウザを起動したい場合は、WSLではなく `setup_windows.bat` と `run_windows.bat` を使ってください。

## 注意

- `.env` をコミットしない。
- 認証情報をコードに直書きしない。
- スクリーンショットに情報が写る可能性があるため Git に入れない。
- `.playwright-profile/` は Git に入れない。
- CAPTCHA / MFA / OTP には対応しない。
- 利用前にネットワーク利用規程を確認する。
