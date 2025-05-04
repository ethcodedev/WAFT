# src/auth.py
import mechanicalsoup

def dvwa_login(base_url: str) -> mechanicalsoup.StatefulBrowser:
    """
    Logs into DVWA at base_url and returns an authenticated browser
    or raises RuntimeError on failure.
    """
    browser = mechanicalsoup.StatefulBrowser(user_agent="WebFuzzer")
    # 1) Reset/Create DB
    resp = browser.open(f"{base_url.rstrip('/')}/setup.php")
    browser.select_form()                # picks the first (and only) form
    browser.submit_selected()            # clicks Create/Reset Database

    # 2) Go to login page (visiting base URL redirects you)
    resp = browser.open(base_url)
    browser.select_form()                # DVWA login form
    browser["username"] = "admin"
    browser["password"] = "password"
    browser.submit_selected()

    # 3) Set security level to Low
    resp = browser.open(f"{base_url.rstrip('/')}/security.php")
    browser.select_form()                # security form
    browser["security"] = "low"
    browser.submit_selected()

    # 4) Verify we’re on the DVWA home/dashboard
    home = browser.open(base_url)
    if "Dashboard" not in home.text:
        raise RuntimeError("DVWA login or setup failed")
    print("[*] DVWA authenticated and security set to low")
    return browser
