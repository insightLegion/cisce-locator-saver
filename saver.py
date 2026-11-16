"""CISCE locator saver, part 2: makes cisce_schools.csv from the pages that saver.js downloaded in your browser.

Part 1 is saver.js (see README): it runs in your own browser and downloads cisce-pages-NNNN-NNNN.json files.
Double-click cisce-locator-saver.exe: it reads those files from your Downloads folder and from its own folder, writes the pages
into cisce-output\\pages and the list into cisce-output\\cisce_schools.csv. Pages saved by hand (Ctrl+S) in that folder count too.

    options: --out DIR  --in DIR (more folders with cisce-pages-*.json)
"""
import argparse
import csv
import html
import json
import re
import sys
import traceback
from pathlib import Path

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


def unpack(out_dir, folders):
    """Write the pages of every cisce-pages-*.json (downloaded by saver.js) into out_dir/pages."""
    pages = out_dir / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    folders = list(dict.fromkeys(Path(f) for f in folders))
    for folder in folders:
        for bundle in sorted(folder.glob("cisce-pages-*.json")):
            try:
                data = json.loads(bundle.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:                  # a broken or half-downloaded file: skip it, keep the others
                print(f"{bundle}: cannot read ({e}), skipped")
                continue
            for name, content in data.items():
                if re.fullmatch(r"page-\d{4}\.html", name):        # the names come from a file: no paths
                    (pages / name).write_text(content, encoding="utf-8")
            print(f"{bundle}: unpacked")
    if not any(pages.iterdir()):
        print("No cisce-pages-*.json found in:\n  " + "\n  ".join(map(str, folders)) + "\nRun saver.js in your browser first (README).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    ap.add_argument("--out", default=str(here / "cisce-output"))
    ap.add_argument("--in", dest="inputs", action="append", default=[], help="folder with cisce-pages-*.json (more than one is OK)")
    args = ap.parse_args()
    out_dir = Path(args.out)
    print(f"Output folder: {out_dir}")
    unpack(out_dir, [*args.inputs, here, Path.home() / "Downloads", out_dir])
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
        print("\nStopped.")
    except Exception:
        traceback.print_exc()
        code = 1
    if getattr(sys, "frozen", False):            # keep the console window open after a double-click
        try:
            input("\nPress Enter to close ...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(code)
