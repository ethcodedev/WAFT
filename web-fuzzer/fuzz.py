#!/usr/bin/env python3
import argparse
import sys
from src.auth import dvwa_login

def do_discover(args):
    # If custom auth requested, run it first
    browser = None
    if args.custom_auth == "dvwa":
        try:
            browser = dvwa_login(args.url)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    # For now we just echo the parameters; later you'll use `browser` for crawling
    print(f"[discover] target={args.url}, common_words={args.common_words}, custom_auth={args.custom_auth}")

def do_test(args):
    # If custom auth requested, run it first
    browser = None
    if args.custom_auth == "dvwa":
        try:
            browser = dvwa_login(args.url)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    # Echo for now; later you'll use `browser` for injection & analysis
    print(f"[test] target={args.url}, vectors={args.vectors}, custom_auth={args.custom_auth}")

def main():
    parser = argparse.ArgumentParser(prog="fuzz", description="Web fuzzer tool")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # discover command
    d = subparsers.add_parser("discover", help="Enumerate inputs")
    d.add_argument("url", help="Target base URL")
    d.add_argument("--common-words", required=True, help="Wordlist for page guessing")
    d.add_argument("--custom-auth", choices=["dvwa"], help="Run DVWA login/setup flow")
    d.set_defaults(func=do_discover)

    # test command
    t = subparsers.add_parser("test", help="Run vulnerability tests")
    t.add_argument("url", help="Target base URL")
    t.add_argument("--vectors", required=True, help="Payload list file")
    t.add_argument("--custom-auth", choices=["dvwa"], help="Run DVWA login/setup flow")
    t.set_defaults(func=do_test)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
