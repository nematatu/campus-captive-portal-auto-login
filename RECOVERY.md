# Recovery

Stop running this repository for now. The runners are disabled.

If Chrome profiles, incognito mode, and other browsers all fail on the same Windows PC, but another device such as a Mac can still log in, the problem is probably not a browser profile anymore.

The likely state is device-level or network-level captive portal state for that Windows PC, such as IP address, adapter, DNS, or a server-side portal session tied to the device.

## Do not do these

Do not open the direct portal URL first.

```text
http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php
```

Do not keep retrying automation.

Do not use Playwright for recovery.

## Step 1: stop Chrome and clear local network cache

Open Command Prompt as Administrator and run:

```bat
ipconfig /flushdns
ipconfig /release
ipconfig /renew
```

Then reboot Windows.

## Step 2: forget and reconnect to the network

If this is Wi-Fi:

1. Windows Settings
2. Network & internet
3. Wi-Fi
4. Manage known networks
5. Forget the university network
6. Reconnect manually

If this is Ethernet:

1. Unplug Ethernet
2. Wait at least 60 seconds
3. Plug it back in
4. Reboot if the captive portal still fails

## Step 3: reset Windows network stack

Use this only if Step 1 and Step 2 fail.

Open Command Prompt as Administrator:

```bat
netsh winsock reset
netsh int ip reset
ipconfig /flushdns
```

Then reboot Windows.

## Step 4: try the normal user path only

After reboot, use the normal browser path that worked before. Do not use this repository.

Do not directly open `cp-login.php`.

Use whatever page or OS prompt normally brings up the university login page.

## Step 5: if it still fails

Contact the campus network administrator and say:

```text
This Windows PC can no longer complete captive portal login, but another device can.
Different browsers and incognito mode fail, so it does not appear to be a browser profile issue.
Please clear the captive portal session/state for this device or tell me the correct login entry URL.
```

Avoid saying that you need bypass. Ask for session/state reset and the correct official login flow.

## Repository status

The runners have been disabled to avoid causing more state changes:

```text
run_windows.bat
run_force.bat
run_human.bat
run_regular_chrome.bat
```
