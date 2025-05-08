#!/usr/bin/env python3
import argparse
import sys
import time
import html
import requests
from src.auth import dvwa_login
from src.discover import crawl_site, guess_pages, enumerate_inputs


def do_discover(args):
    # 1) Authenticate if requested
    browser = None
    if args.custom_auth == "dvwa":
        try:
            browser = dvwa_login(args.url)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    # 2) Crawl links
    print("[*] Crawling site for links…")
    pages = crawl_site(args.url, browser)

    # 3) Prepare extensions list (if any)
    ext_list = None
    if args.extensions:
        with open(args.extensions) as ef:
            ext_list = [line.strip() for line in ef if line.strip()]

    # 4) Guess hidden pages, passing in ext_list (or let default=['.php',''] kick in)
    print("[*] Guessing pages from words list…")
    pages |= guess_pages(args.url, args.common_words, extensions=ext_list)

    # 5) Enumerate inputs
    print("[*] Enumerating inputs on each discovered page:")
    for page in sorted(pages):
        inputs = enumerate_inputs(page, browser)
        print(f"\nPage: {page}")
        if inputs["params"]:
            print("  • query params:", ", ".join(inputs["params"]))
        if inputs["forms"]:
            print("  • form inputs: ", ", ".join(inputs["forms"]))
        if inputs["cookies"]:
            print("  • cookies:     ", ", ".join(inputs["cookies"]))

def load_file(path):
    """Read a file of newline‑delimited entries, return a list of strings."""
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def fetch(url, browser=None):
    """
    Issue a GET against url (using browser if provided), 
    return (response, elapsed_ms).
    """
    start = time.time()
    if browser:
        resp = browser.open(url)
        elapsed = (time.time() - start) * 1000
        return resp, elapsed
    else:
        resp = requests.get(url, timeout=10)
        elapsed = (time.time() - start) * 1000
        return resp, elapsed

def submit_form(url, field_name, payload, browser=None):
    """
    Open `url`, set form field `field_name` to `payload`, submit it.
    Returns (response, elapsed_ms).
    """
    start = time.time()
    if browser:
        browser.open(url)
        browser.select_form()
        browser[field_name] = payload
        resp = browser.submit_selected()
        elapsed = (time.time() - start) * 1000
        return resp, elapsed
    else:
        # naive fallback: POST payload as form data
        data = {field_name: payload}
        resp = requests.post(url, data=data, timeout=10)
        elapsed = (time.time() - start) * 1000
        return resp, elapsed

def send_cookie(url, name, payload, browser=None):
    """
    Set a cookie `name`=`payload`, then GET `url`.
    Returns (response, elapsed_ms).
    """
    start = time.time()
    if browser:
        browser.session.cookies.set(name, payload)
        resp = browser.open(url)
        elapsed = (time.time() - start) * 1000
        return resp, elapsed
    else:
        cookies = {name: payload}
        resp = requests.get(url, cookies=cookies, timeout=10)
        elapsed = (time.time() - start) * 1000
        return resp, elapsed

def analyze_and_report(test_id, resp, elapsed, sanitized, sensitive, slow_thresh):
    """
    Given a test identifier, response object, elapsed ms, list of sanitized chars,
    list of sensitive strings, and slow threshold (ms), return a list of
    (label, output_line) tuples, instead of printing directly.
    """
    findings = []
    code = getattr(resp, "status_code", None)
    body = getattr(resp, "text", "")

    # 1) Slow?
    if elapsed > slow_thresh:
        findings.append((
            "Slow",
            f"[Slow]  {test_id} → {int(elapsed)} ms"
        ))

    # 2) HTTP errors?
    if code is not None and code != 200:
        findings.append((
            "Error",
            f"[Error] {test_id} → HTTP {code}"
        ))

    # 3) Unsanitized chars (XSS)
    for ch in sanitized:
        esc = html.escape(ch)
        if ch in body and esc not in body:
            findings.append((
                "XSS",
                f"[XSS]   {test_id} → raw '{ch}' found"
            ))

    # 4) Sensitive data leaks
    for secret in sensitive:
        if secret in body:
            findings.append((
                "Leak",
                f"[Leak]  {test_id} → '{secret}' leaked"
            ))

    return findings

# TODO: Fill in helper functions
def do_test(args):
    # 1) Auth if needed
    browser = None
    if args.custom_auth == "dvwa":
        try:
            browser = dvwa_login(args.url)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    # 2) Discover pages & inputs (reuse your discover pipeline)
    pages = crawl_site(args.url, browser)
    if args.common_words:
        ext_list = load_file(args.extensions) if args.extensions else None
        pages |= guess_pages(args.url, args.common_words, extensions=ext_list)
    all_inputs = {p: enumerate_inputs(p, browser) for p in pages}

    # 3) Load your test data
    vectors   = load_file(args.vectors)
    sanitized = load_file(args.sanitized_chars) if args.sanitized_chars else ['<','>']
    sensitive = load_file(args.sensitive)
    slow_ms   = args.slow

        # … after loading vectors, sanitized, sensitive, slow_ms …
    IGNORE_FIELDS  = {"user_token", "PHPSESSID", "security"}
    seen_findings = set()

    # Plain GET on each URL once to check for leaks and slow responses before injection
    for raw_page in all_inputs:
        page = raw_page.rstrip('/')
        resp, elapsed = fetch(page, browser)
        for label, line in analyze_and_report(
                page, resp, elapsed,
                sanitized, sensitive, slow_ms):
            if (page, label) in seen_findings:
                continue
            seen_findings.add((page, label))
            print(line)

    # 4) Fuzz each input
    print("[*] Fuzzing inputs…")
    for raw_page, ins in all_inputs.items():
        # Normalize page URL
        page = raw_page.rstrip('/')
        base = page.split('?')[0]

        # — query parameters
        for param in ins['params']:
            if param in IGNORE_FIELDS:
                continue
            for payload in vectors:
                test_id = f"{base}?{param}={payload}"
                resp, elapsed = fetch(test_id, browser)

                # grab findings now instead of printing
                for label, line in analyze_and_report(
                        test_id, resp, elapsed,
                        sanitized, sensitive, slow_ms):

                    # dedupe by test_id+label
                    if (test_id, label) in seen_findings:
                        continue
                    seen_findings.add((test_id, label))

                    # print only unique findings
                    print(line + "hey")

        # — form fields
        for field in ins['forms']:
            if field in IGNORE_FIELDS:
                continue
            for payload in vectors:
                test_id = f"{page} [form:{field}]"
                resp, elapsed = submit_form(page, field, payload, browser)

                for label, line in analyze_and_report(
                        test_id, resp, elapsed,
                        sanitized, sensitive, slow_ms):
                    if (test_id, label) in seen_findings:
                        continue
                    seen_findings.add((test_id, label))
                    print(line)

        # — cookies
        for cookie in ins['cookies']:
            if cookie in IGNORE_FIELDS:
                continue
            for payload in vectors:
                test_id = f"{page} [cookie:{cookie}]"
                resp, elapsed = send_cookie(page, cookie, payload, browser)

                for label, line in analyze_and_report(
                        test_id, resp, elapsed,
                        sanitized, sensitive, slow_ms):
                    if (test_id, label) in seen_findings:
                        continue
                    seen_findings.add((test_id, label))
                    print(line)


def main():
    parser = argparse.ArgumentParser(prog="fuzz", description="Web fuzzer tool")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # discover command
    d = subparsers.add_parser("discover", help="Enumerate inputs")
    d.add_argument("url", help="Target base URL")
    d.add_argument("--common-words", required=True, help="Wordlist for page guessing")
    d.add_argument("--extensions", default= None, help="Newline‑delimited file of extensions (e.g. .php, .jsp); defaults to .php and '' ")
    d.add_argument("--custom-auth", choices=["dvwa"], help="Run DVWA login/setup flow")
    d.set_defaults(func=do_discover)

    # test command
    t = subparsers.add_parser("test", help="Run vulnerability tests")
    t.add_argument("url", help="Target base URL")
    t.add_argument("--vectors", required=True, help="Payload list file")
    t.add_argument("--sanitized-chars", default=None, help="File of chars that *should* be escaped (default: <,>)")
    t.add_argument("--sensitive", required=True, help="File with newline‑delimited sensitive strings")
    t.add_argument("--slow", type=int, default=500, help="Threshold in ms to flag slow responses")
    t.add_argument("--extensions", help="(reuse for test lookup)")
    t.add_argument("--common-words", help="(reuse for discover phase)")
    t.add_argument("--custom-auth", choices=["dvwa"], help="Run DVWA login/setup flow")
    t.set_defaults(func=do_test)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
