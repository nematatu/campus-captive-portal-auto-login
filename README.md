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

`neverssl.com` が Captive Portal にリダイレクトされないなら、`neverssl.com` を入口URLとして使う前提は間違いです。

このリポジトリでは、入口URLを自動で決め打ちしません。`CAPTIVE_ENTRY_URL` には、通常Chromeで実際にログイン画面が出ることを確認したURLだけを入れてください。

また、ポータルURLを直接開く運用はしません。必要パラメータのないURLを直接開くと、不完全な状態がChrome側に残る可能性があります。

通常Chromeでログインできなくなった場合は、`RECOVERY.md` を見て、Chromeの該当サイトデータを削除してください。

## Windows セットアップ

```bat
setup_windows.bat
```

`.env` を編集します。

```env
CAPTIVE_PORTAL_URL=http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php
CAPTIVE_ENTRY_URL=
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

## CAPTIVE_ENTRY_URL の決め方

`CAPTIVE_ENTRY_URL` は推測で入れないでください。

正しい決め方は次です。

```text
1. 通常Chromeを使う
2. 手動でいくつかのURLを開く
3. ログイン画面に遷移できたURLを確認する
4. そのURLだけを CAPTIVE_ENTRY_URL に入れる
```

ログイン画面に遷移しないURLは使いません。

## 通常 Chrome を使う実行

Playwright Chrome ではなく、Windows に入っている通常 Chrome をそのまま起動します。

```bat
run_regular_chrome.bat
```

これは `CAPTIVE_ENTRY_URL` を通常Chromeで開きます。

```text
Playwright を使わない
別プロファイルを作らない
Chrome を通常起動する
直接ポータルURLは開かない
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

ただし、Playwright が起動した Chrome で手動操作しても失敗する場合、Playwright 経路は一旦使わないでください。

## 注意

- `.env` をコミットしない。
- 認証情報をコードに直書きしない。
- スクリーンショットに情報が写る可能性があるため Git に入れない。
- `.playwright-profile/` は Git に入れない。
- CAPTCHA / MFA / OTP には対応しない。
- 利用前にネットワーク利用規程を確認する。
