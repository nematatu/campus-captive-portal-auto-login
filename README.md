# Campus Captive Portal Auto Login

Campus captive portal auto-login tool for headless machines.

This repository is intended for machines that lose Internet access when campus network authentication expires. It checks connectivity, opens the captive portal with Playwright, submits credentials, and verifies that Internet connectivity has recovered.

## Background

The target environment has these properties:

- A machine is used as a remote compute resource.
- The machine is expected to run headlessly.
- Internet access is blocked when campus captive portal authentication expires.
- Tailscale also disconnects when Internet access is blocked.
- Remote SSH cannot be used after authentication expires.
- Therefore, the machine must recover by itself through local scheduled execution.

## Confirmed network behavior

In the tested environment, multiple devices connected behind the same router can be authenticated together.

Example:

```text
MacBook --- Wi-Fi ----+
                     |
Windows --- LAN ------+--> Router --> Campus network
```

When the MacBook completes captive portal authentication, the Windows machine behind the same router also regains Internet access and Tailscale reconnects.

This means the authentication state is probably associated with the router-side network identity, not each client device behind the router. Still, this repository assumes the safest design: the compute machine can authenticate by itself when needed.

## Target use case

```text
NVIDIA Windows PC / WSL
├─ Tailscale
├─ SSH
├─ Playwright
└─ Scheduled auto-login
```

When the campus authentication expires, Tailscale also disconnects. Therefore the machine must recover by itself through scheduled execution.

## Repository files

```text
.
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.sh
└── test.py
```

Current status:

- `test.py`: opens the captive portal page and saves a screenshot.
- `setup.sh`: creates a Conda environment, installs dependencies, installs system packages, and runs `test.py`.
- `captive_login.py`: not added yet. This will be the actual auto-login script.

## Requirements

- Python 3.10+
- Conda or another Python environment manager
- Playwright
- Chromium installed by Playwright
- Windows, WSL, Linux, or macOS

For the current WSL workflow, Conda environment name is assumed to be:

```text
playwright
```

## Quick setup on WSL/Linux

Use the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

The script performs:

1. Create Conda environment `playwright` if missing.
2. Activate the environment.
3. Install Python packages from `requirements.txt`.
4. Install Playwright Chromium.
5. Install required Linux shared libraries for Chromium.
6. Run `python test.py`.

Expected output:

```text
login.png
```

If `login.png` shows the campus network login form, Playwright can reach and render the captive portal.

## Manual setup on WSL/Linux

```bash
conda create -y -n playwright python=3.12
conda activate playwright
pip install -r requirements.txt
playwright install chromium
```

Install system dependencies:

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

If `libasound2t64` is unavailable:

```bash
sudo apt install -y libasound2
```

Then run:

```bash
python test.py
```

## Setup on Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python test.py
```

This repository currently prioritizes WSL because the target machine uses WSL for remote operation.

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
CHECK_URL=http://connectivitycheck.gstatic.com/generate_204
```

Do not commit `.env`.

`.env` is ignored by `.gitignore`.

## Test page rendering

This only opens the login page and saves a screenshot. It does not submit credentials.

```bash
python test.py
```

Output:

```text
login.png
```

Success condition:

- `login.png` is created.
- The screenshot shows the captive portal login form.
- The script prints the final URL.

## Known Playwright dependency error

If Chromium fails with:

```text
error while loading shared libraries: libnspr4.so: cannot open shared object file
```

Install the missing libraries:

```bash
sudo apt update
sudo apt install -y libnspr4 libnss3 libatk-bridge2.0-0 libxkbcommon0 libgbm1 libasound2t64
```

If needed:

```bash
sudo apt install -y libasound2
```

## Planned auto-login flow

The actual login script will follow this logic:

```text
Check Internet connectivity
↓
If online: exit
↓
If offline: open captive portal with Playwright
↓
Fill username and password
↓
Click login button
↓
Wait several seconds
↓
Check Internet connectivity again
↓
Report success or failure
```

Connectivity check target:

```text
http://connectivitycheck.gstatic.com/generate_204
```

Expected status when online:

```text
204
```

## Dry-run form fill

Planned command:

```bash
python captive_login.py --dry-run
```

Expected behavior:

- Open the portal.
- Fill credentials.
- Save screenshots.
- Do not click the login button.

This is safer for validating selectors before submitting credentials.

## Actual login

Planned command:

```bash
python captive_login.py
```

The script should first check Internet connectivity. If the network is already online, it should exit without logging in.

Force login regardless of connectivity:

```bash
python captive_login.py --force
```

## Scheduling policy

Recommended interval:

```text
30 minutes to 1 hour
```

Rationale:

- The authentication lifetime is roughly long enough that very frequent checks are unnecessary.
- The script should only log in when connectivity check fails.
- Normal authenticated periods cause only a lightweight connectivity check.

The intended deployment is:

```text
NVIDIA PC
├─ scheduled task every 30-60 minutes
├─ connectivity check
├─ auto-login only when offline
└─ Tailscale reconnects after Internet recovery
```

## Windows Task Scheduler idea

For native Windows Python:

```text
Program:
python

Arguments:
C:\path\to\campus-captive-portal-auto-login\captive_login.py

Trigger:
Every 30 minutes or every 1 hour
```

For WSL execution from Windows Task Scheduler, use a command like:

```powershell
wsl.exe -d Ubuntu -- bash -lc 'cd ~/src/github.com/nematatu/campus-captive-portal-auto-login && source ~/miniconda3/etc/profile.d/conda.sh && conda activate playwright && python captive_login.py'
```

Adjust the WSL distribution name and Conda path for the actual machine.

## Security notes

- Do not commit `.env`.
- Do not hard-code credentials into Python files.
- Keep screenshots out of Git if they may contain sensitive information.
- `.gitignore` excludes `.env`, screenshots, logs, and generated PNG files.

## Policy notes

Use this only if automated authentication is allowed under the relevant network policy.

This project does not bypass authentication. It automates the same browser login flow that a user would normally perform.

## Limitations

- CAPTCHA is not supported.
- MFA is not supported.
- OTP is not supported.
- If the captive portal changes its form structure, selectors may need to be updated.
- If the machine cannot reach the captive portal while offline, auto-login will fail.

## Next steps

1. Run `setup.sh`.
2. Confirm that `login.png` shows the login form.
3. Add `captive_login.py`.
4. Test dry-run form filling.
5. Test actual login when authentication expires.
6. Add scheduled execution.
