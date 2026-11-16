"""CISCE locator saver: saves every page of https://locate.cisce.org/ from your own browser, then writes a CSV.

You pass the Cloudflare check ("Verify you are human") yourself in the browser window. The tool never clicks it. After that it
opens one page every 6-8 seconds and saves it. If the check comes back, it beeps and waits for you. Run it again to resume.

    cisce-locator-saver.exe                 save all pages, then write cisce_schools.csv
    cisce-locator-saver.exe --parse-only    only write the CSV from the pages already in the folder (also pages saved by hand)
    options: --out DIR  --delay 6  --browser msedge|chrome|chromium  --max-pages N  --base URL  --headless
"""
import argparse
import csv
import html
import json
import math
import random
import re
import sys
import time
import traceback
from pathlib import Path

BASE = "https://locate.cisce.org"

# --- parser: the same as crawl.py in github.com/s1d-labs/cisce-scraper (pure, tested) -----------------------------------------
CARD = re.compile(r'<div class="school-card">(.*?)(?=<div class="school-card">|</tbody>)', re.S)
HEAD = re.compile(r'<h6[^>]*>\s*([A-Z]{2,4}\d+)\s*-\s*(.*?)</h6>', re.S)
BODY = re.compile(r'<p class="mb-1">(.*?)</p>', re.S)
BADGE = re.compile(r'class="badge badge-outline-(red|blue|green)[^"]*">\s*(.*?)\s*</span>', re.S)
SITE_LINK = re.compile(r'<a href="([^"]*)"\s+class="[^"]*visit-btn')
LOCATIONS = re.compile(r'const locations = (\{.*?\});\s*$', re.M)
TOTAL = re.compile(r'Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)\s+entries')
PIN = re.compile(r"^\d[\d \-]{2,9}$")
FIELDS = ["code", "name", "principal", "address", "locality", "district", "state", "pin", "country", "gender", "residence", "asisc",
          "icse", "isc", "cve", "website", "lat", "lng", "listed_total", "file"]


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def is_challenge(page):
    return bool(re.search(r"<title>\s*(Just a moment|Attention Required)", page)) or "challenge-platform" in page and "school-card" not in page


def listed_total(page):
    m = TOTAL.search(page)
    return int(m.group(3)) if m else None


def split_address(lines):
    parts = [p.strip(" .-") for p in ", ".join(lines).split(",") if p.strip(" .-")]
    out = {"country": "", "pin": "", "state": "", "district": "", "locality": ""}
    if parts and not PIN.match(parts[-1]):
        out["country"] = parts.pop()
    if parts and PIN.match(parts[-1]):
        out["pin"] = parts.pop().replace(" ", "")
    if parts:
        out["state"] = parts.pop()
    if parts:
        out["district"] = parts.pop()
    out["locality"] = ", ".join(parts)
    return out


def parse(page):
    coords = {}
    m = LOCATIONS.search(page)
    if m:
        for s in json.loads(m.group(1)).get("schools", []):
            coords[s["name"].split(" - ", 1)[0].strip()] = (s.get("lat"), s.get("lng"))
    total, out = listed_total(page), []
    for card in CARD.findall(page):
        h = HEAD.search(card)
        if not h:
            continue
        code, name = h.group(1), text(h.group(2))
        body = BODY.search(card)
        principal, address_lines = "", []
        if body:
            first, _, rest = body.group(1).partition("<br>")
            principal = text(first)
            address_lines = [text(x) for x in rest.split("\n") if text(x)]
        badges = [(c, text(t)) for c, t in BADGE.findall(card)]
        blue = [t for c, t in badges if c == "blue"]
        green = {t for c, t in badges if c == "green"}
        link = SITE_LINK.search(card)
        lat, lng = coords.get(code, (None, None))
        out.append((code, {
            "code": code, "name": name, "principal": principal,
            "address": ", ".join(a.rstrip(",") for a in address_lines), **split_address(address_lines),
            "gender": next((t for c, t in badges if c == "red"), ""),
            "residence": next((t for t in blue if t != "ASISC"), ""),
            "asisc": "ASISC" in blue, "icse": "ICSE" in green, "isc": "ISC" in green, "cve": "CVE" in green,
            "website": html.unescape(link.group(1)).strip() if link else "",
            "lat": lat, "lng": lng, "listed_total": total,
        }))
    return out
# ------------------------------------------------------------------------------------------------------------------------------


def write_csv(out_dir):
    pages = out_dir / "pages"
    schools = {}
    for f in sorted(pages.glob("*.htm*")):
        for code, d in parse(f.read_text(encoding="utf-8", errors="replace")):
            schools[code] = {**d, "file": f.name}
    path = out_dir / "cisce_schools.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:          # utf-8-sig: Excel opens it correctly
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(schools[c] for c in sorted(schools))
    totals = {d["listed_total"] for d in schools.values() if d["listed_total"]}
    print(f"\n{len(schools)} schools in {path}  (the site says: {', '.join(map(str, sorted(totals))) or 'unknown'})")
    return len(schools)


def load(page, url, settle_s=15):
    """Open url; while the Cloudflare check shows, wait for the person to tick it. Returns the page HTML."""
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    asked, start = False, time.time()
    while True:
        try:
            content = page.content()
        except Exception:                       # the page navigates by itself after the check
            time.sleep(1)
            continue
        if "school-card" in content or TOTAL.search(content):
            return content
        if is_challenge(content):
            if not asked:
                print("\a\n>>> Cloudflare check in the browser window: please tick 'Verify you are human'. Waiting ...", flush=True)
                asked = True
            time.sleep(2)
            continue
        if time.time() - start > settle_s:      # no schools and no check: a page after the last one
            return content
        time.sleep(1)


def save_all(out_dir, args):
    from playwright.sync_api import sync_playwright
    pages = out_dir / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(out_dir / "browser-profile"), channel=None if args.browser == "chromium" else args.browser,
                                                   headless=args.headless, viewport={"width": 1200, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        n, last = 1, None
        while args.max_pages is None or n <= args.max_pages:
            f = pages / f"page-{n:04d}.html"
            if f.exists():
                content = f.read_text(encoding="utf-8", errors="replace")
                print(f"page {n}: already saved")
            else:
                content = load(page, f"{args.base}/?page={n}")
                rows = parse(content)
                if not rows:
                    print(f"page {n}: no schools, end of the list")
                    break
                f.write_text(content, encoding="utf-8")
                print(f"page {n}{'/' + str(last) if last else ''}: {len(rows)} schools saved", flush=True)
                time.sleep(args.delay + random.uniform(0, 2))
            total = listed_total(content)
            if total:
                last = math.ceil(total / 10)
            if last and n >= last:
                break
            n += 1
        ctx.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    ap.add_argument("--out", default=str(here / "cisce-output"))
    ap.add_argument("--delay", type=float, default=6.0, help="seconds between pages (6 or more)")
    ap.add_argument("--browser", default="msedge", choices=["msedge", "chrome", "chromium"])
    ap.add_argument("--max-pages", type=int)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--headless", action="store_true", help="for tests only")
    ap.add_argument("--parse-only", action="store_true")
    args = ap.parse_args()
    args.delay = max(args.delay, 6.0) if args.base == BASE else args.delay
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {out_dir}")
    if not args.parse_only:
        save_all(out_dir, args)
    write_csv(out_dir)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    code = 0
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped. Run the tool again to continue from the last saved page.")
    except Exception:
        traceback.print_exc()
        code = 1
    if getattr(sys, "frozen", False):            # keep the console window open after a double-click
        try:
            input("\nPress Enter to close ...")
        except EOFError:
            pass
    sys.exit(code)
