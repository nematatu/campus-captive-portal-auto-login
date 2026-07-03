# Campus Captive Portal Auto Login

大学ネットワークの Captive Portal 認証を、Playwright で自動化するためのリポジトリ。

## 目的

研究室の NVIDIA PC を、Tailscale + SSH 経由の計算リソースとして使う。

ただし、大学ネットワークの認証が切れると以下の状態になる。

- インターネット不可
- Tailscale 切断
- SSH 不可

そのため、PC 自身が定期的に認証状態を確認し、必要なら自動で再認証する。

## 想定構成

```text
NVIDIA Windows PC / WSL
├─ Tailscale
├─ SSH
├─ Playwright
└─ 定期実行スクリプト
```

## 現時点のファイル

```text
.
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.sh
└── test.py
```

- `test.py`: 認証ページを開いて `login.png` を保存するだけ。ログインはしない。
- `setup.sh`: Conda 環境作成、依存関係インストール、`test.py` 実行まで行う。
- `captive_login.py`: まだ未実装。本番用の自動ログインスクリプト予定。

## セットアップ

WSL / Linux では以下を実行する。

```bash
chmod +x setup.sh
./setup.sh
```

`setup.sh` は以下を行う。

1. Conda 環境 `playwright` を作成
2. 環境を有効化
3. `requirements.txt` をインストール
4. Playwright Chromium をインストール
5. Chromium 実行に必要な apt パッケージをインストール
6. `python test.py` を実行

## 手動セットアップ

```bash
conda create -y -n playwright python=3.12
conda activate playwright
pip install -r requirements.txt
playwright install chromium
```

WSL で Chromium のライブラリ不足が出た場合:

```bash
sudo apt update
sudo apt install -y \
  libnspr4 \
  libnss3 \
  libatk-bridge2.0-0 \
  libxkbcommon0 \
  libgbm1 \
  libasound2t64
```

`libasound2t64` が無い場合:

```bash
sudo apt install -y libasound2
```

## 設定

`.env.example` を `.env` にコピーする。

```bash
cp .env.example .env
```

`.env` 例:

```env
CAPTIVE_PORTAL_URL=http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php
CAPTIVE_USERNAME=your-id
CAPTIVE_PASSWORD=your-password
CHECK_URL=http://connectivitycheck.gstatic.com/generate_204
```

`.env` は Git に入れない。

## テスト

```bash
python test.py
```

成功すると以下が生成される。

```text
login.png
```

`login.png` に認証フォームが表示されていれば、Playwright から認証ページを開けている。

## 本番スクリプトの予定

`captive_login.py` は以下の流れにする予定。

```text
外部疎通確認
↓
接続できるなら終了
↓
接続できないなら認証ページを開く
↓
ID / Password 入力
↓
ログインボタン押下
↓
数秒待機
↓
再度疎通確認
```

通常実行:

```bash
python captive_login.py
```

送信なしの確認:

```bash
python captive_login.py --dry-run
```

強制実行:

```bash
python captive_login.py --force
```

## 定期実行方針

推奨間隔:

```text
30分〜1時間
```

理由:

- 認証期限が短すぎるわけではない
- 5分間隔は不要
- 接続できている場合はログイン処理をしない

## Windows タスクスケジューラ案

WSL から実行する場合の例:

```powershell
wsl.exe -d Ubuntu -- bash -lc 'cd ~/src/github.com/nematatu/campus-captive-portal-auto-login && source ~/miniconda3/etc/profile.d/conda.sh && conda activate playwright && python captive_login.py'
```

実際の WSL 名、Conda パス、リポジトリパスに合わせて修正する。

## 注意

- `.env` をコミットしない
- 認証情報をコードに直書きしない
- スクリーンショットに情報が写る可能性があるため Git に入れない
- CAPTCHA / MFA / OTP には対応しない
- 利用前にネットワーク利用規程を確認する

## TODO

- [x] 認証ページ表示テスト
- [x] セットアップスクリプト
- [ ] `captive_login.py` 実装
- [ ] ID / Password 自動入力
- [ ] Dry Run モード
- [ ] ログイン送信
- [ ] 疎通確認
- [ ] Windows タスクスケジューラ設定
