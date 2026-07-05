# Recovery: regular Chrome cannot login after direct portal access

If regular Chrome stopped logging in after opening the captive portal URL directly, the likely cause is a bad portal session, cookie, or cached state in the normal Chrome profile.

This does not usually mean the account is broken. It usually means Chrome is reusing a failed captive portal state.

## First recovery steps

1. Close all Chrome windows.
2. Reopen Chrome.
3. Open this page in the address bar:

```text
chrome://settings/siteData
```

4. Search for:

```text
cpauth
```

5. Delete all matching site data.
6. Search for:

```text
miyazaki
```

7. Delete matching captive portal / university network site data.
8. Close all Chrome windows again.
9. Open a plain HTTP page, not the direct portal URL:

```text
http://neverssl.com/
```

If the login page appears, log in manually.

## If that does not recover it

Open:

```text
chrome://settings/clearBrowserData
```

Use:

```text
Time range: Last 24 hours
Cached images and files: on
Cookies and other site data: on
```

Then close Chrome and try:

```text
http://neverssl.com/
```

This may sign you out of some sites. Prefer the site-specific deletion above first.

## What not to do

Do not open the direct portal URL first:

```text
http://cpauth.cc.miyazaki-u.ac.jp/guest/cp-login.php
```

Use a normal HTTP entry URL and let the network redirect Chrome to the correct portal URL with required parameters.

## Repository change

The direct regular Chrome runner has been removed. `open_regular_chrome.py` now refuses direct portal launch unless explicitly enabled with:

```text
ALLOW_DIRECT_PORTAL_URL=1
```

Do not enable this unless you have confirmed that the portal accepts direct access.
