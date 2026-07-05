# Campus Captive Portal Auto Login

大学ネットワークの Captive Portal 認証を、研究室 Windows PC 上でローカル実行するためのリポジトリです。

## 目的

研究室の Windows PC を Tailscale + SSH 経由の計算リソースとして使う。

ただし、大学ネットワークの認証が切れると以下の状態になります。

- インターネット不可
- Tailscale 切断
- SSH 不可

そのため、外から復旧するのではなく、研究室 PC 自身が認証状態を確認し、必要なら Captive Portal 認証を実行します。

## 現在の判断

Playwright が起動した Chrome で、人間が手動入力しても `required parameter unavailable` が出る一方、普段使っている Chrome で同じ URL を開くとログインできる場合、問題は入力処理ではありません。

差分は次です。

```text
Playwright Chrome:
  Playwright 管理の起動方式
  別プロファイル
  自動化向け起動フラグ

通常 Chrome:
  普段のユーザープロファイル
  保存済み Cookie / 設定
  通常の起動方式
```

そのため、Playwright での完全自動ログインだけに寄せず、通常 Chrome をそのまま開く経路を追加しています。

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

## 通常 Chrome を使う実行

Playwright Chrome ではなく、Windows に入っている通常 Chrome をそのまま起動します。

まず、通常HTTP入口を開きます。

```bat
run_regular_chrome.bat
```

ログイン画面が表示されない場合は、直接ポータルURLを開きます。

```bat
run_regular_chrome_direct.bat
```

これらは `open_regular_chrome.py` を呼び出します。

```text
Playwright を使わない
別プロファイルを作らない
Chrome を通常起動する
```

## Playwright で実行

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

今回の観測結果から、優先順位は次です。

```bat
run_regular_chrome.bat
```

ログイン画面が出なければ次です。

```bat
run_regular_chrome_direct.bat
```

これで手動ログインできるなら、Playwright 起動 Chrome の問題です。

次に Playwright 側を比較します。

```bat
run_human.bat
```

まだ `required parameter unavailable` が出る場合、Playwright Chrome 経路は一旦捨ててください。

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
