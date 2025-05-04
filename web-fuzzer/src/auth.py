# src/auth.py
import mechanicalsoup

def dvwa_login(base_url: str) -> mechanicalsoup.StatefulBrowser:
    """
    Logs into DVWA at base_url and returns an authenticated browser,
    raising RuntimeError if anything fails.
    """
    browser = mechanicalsoup.StatefulBrowser(user_agent="WebFuzzer")

    # 1) Reset/Create the DB
    browser.open(f"{base_url.rstrip('/')}/setup.php")
    browser.select_form()       # the “Create/Reset Database” form
    browser.submit_selected()

    # 2) Go to the login page explicitly
    browser.open(f"{base_url.rstrip('/')}/login.php")
    browser.select_form()       # the login form
    browser["username"] = "admin"
    browser["password"] = "password"
    browser.submit_selected()   # submit credentials

    # 3) Set security level to “Low”
    browser.open(f"{base_url.rstrip('/')}/security.php")
    browser.select_form()       # the security form
    browser["security"] = "low"
    browser.submit_selected()

    # 4) Verify login by loading index.php and checking for “Logout”
    resp = browser.open(f"{base_url.rstrip('/')}/index.php")
    if "Logout" not in resp.text:
        raise RuntimeError("DVWA login or setup failed")

    print("[*] DVWA authenticated and security set to low")
    return browser
