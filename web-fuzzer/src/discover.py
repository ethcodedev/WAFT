# src/discover.py

import requests
import mechanicalsoup
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup

def same_domain(a: str, b: str) -> bool:
    return urlparse(a).netloc == urlparse(b).netloc

def crawl_site(base_url: str, browser=None, max_pages=100) -> set[str]:
    """
    BFS‑crawl all links under base_url (no off‑site, no infinite loops).
    Returns a set of discovered URLs.
    """
    visited = set()
    queue = [base_url.rstrip('/')]
    if browser is None:
        browser = mechanicalsoup.StatefulBrowser(user_agent="WebFuzzer")

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        try:
            resp = browser.open(url)
        except Exception:
            continue

        visited.add(url)
        # parse out all <a href="...">
        for tag in resp.soup.select("a[href]"):
            link = urljoin(url, tag["href"].split('#')[0])
            if same_domain(base_url, link) and link not in visited:
                queue.append(link)

    return visited

def guess_pages(base_url: str, words_file: str, extensions=None) -> set[str]:
    """
    Read newline‑delimited words from words_file. For each word and extension,
    attempt HEAD on base_url/word+ext; collect those returning status 200.
    """
    if extensions is None:
        extensions = [".php", ""]
    found = set()
    with open(words_file) as f:
        words = [w.strip() for w in f if w.strip()]
    for w in words:
        for ext in extensions:
            url = urljoin(base_url.rstrip('/') + "/", f"{w}{ext}")
            try:
                r = requests.head(url, allow_redirects=True, timeout=3)
                if r.status_code == 200:
                    found.add(url)
            except requests.RequestException:
                continue
    return found

def enumerate_inputs(url: str, browser=None) -> dict:
    """
    For a given URL, return dict with keys:
      - params: list of query‑param names
      - forms: list of <input name="..."> on the page
      - cookies: list of cookie names in browser/session
    """
    # fetch page
    if browser:
        resp = browser.open(url)
        text = resp.soup
        cookies = browser.session.cookies
    else:
        r = requests.get(url, timeout=5)
        text = BeautifulSoup(r.text, "html.parser")
        cookies = r.cookies

    # query params
    params = list(parse_qs(urlparse(url).query).keys())

    # form inputs
    forms = [inp["name"] for inp in text.select("input[name]")]

    # cookies
    cookie_names = [c.name for c in cookies]

    return {"params": params, "forms": forms, "cookies": cookie_names}
