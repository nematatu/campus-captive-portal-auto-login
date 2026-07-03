# Campus Captive Portal Auto Login

Campus captive portal auto-login tool for headless machines.

This repository is intended for machines that lose Internet access when campus network authentication expires. It checks connectivity, opens the captive portal with Playwright, submits credentials, and verifies that Internet connectivity has recovered.

## Target use case

```text
NVIDIA Windows PC / WSL
├─ Tailscale
├─ SSH
├─ Playwright
└─ Scheduled auto-login
```

When the campus authentication expires, Tailscale also disconnects. Therefore the machine must recover by itself through scheduled execution.

## Requirements

- Python 3.10+
- Playwright
- Chromium installed by Playwright
- Windows, WSL, Linux, or macOS

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```env
CAPTIVE_PORTAL_URL=http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php
CAPTIVE_USERNAME=your-id
CAPTIVE_PASSWORD=your-password
```

Do not commit `.env`.

## Test page rendering

This only opens the login page and saves a screenshot. It does not submit credentials.

```bash
python test.py
```

Output:

```text
login.png
```

## Dry-run form fill

This opens the portal, fills credentials, and saves screenshots, but does not click the login button.

```bash
python captive_login.py --dry-run
```

## Actual login

```bash
python captive_login.py
```

The script first checks Internet connectivity. If the network is already online, it exits without logging in.

Force login regardless of connectivity:

```bash
python captive_login.py --force
```

## Scheduling

Recommended interval: 30 minutes to 1 hour.

The script only logs in when connectivity check fails, so normal authenticated periods cause minimal access.

## Notes

- CAPTCHA, MFA, or OTP are not handled.
- Store credentials only in `.env` or environment variables.
- Confirm that automated authentication is allowed under your network policy before using this.
