"""Tests: the parser on saved pages, saver.js in a real browser against a local web server (no access to locate.cisce.org),
and the unpack + CSV step on the files that saver.js downloaded."""
import csv
import http.server
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import saver  # noqa: E402

HERE = Path(__file__).parent
PAGES = HERE / "pages"


def test_parse_result_page():
    rows = dict(saver.parse((PAGES / "result-isc-india-p1.html").read_text(encoding="utf-8")))
    assert len(rows) == 10 and rows["AN001"]["pin"] == "744103" and rows["AP003"]["website"] == "https://www.loyolapublicschool.org"
    assert rows["AN001"]["icse"] and rows["AN001"]["isc"] and rows["AN001"]["listed_total"] == 1928


def test_challenge_page():
    page = (PAGES / "cloudflare-challenge.html").read_text(encoding="utf-8")
    assert saver.is_challenge(page) and saver.parse(page) == []


class Site(http.server.BaseHTTPRequestHandler):
    """/?page=N: the result page with a total of 20 schools (2 pages); the first request for page 2 gets the Cloudflare check."""
    result = (PAGES / "result-isc-india-p1.html").read_bytes().replace(b"of 1928 entries", b"of 20 entries")
    challenge = (PAGES / "cloudflare-challenge.html").read_bytes()
    challenged = False

    def do_GET(self):
        status, body = 200, self.result
        if self.path.endswith("page=2") and not Site.challenged:
            Site.challenged, status, body = True, 403, self.challenge
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def run_saver_js(downloads, delay_ms=0, until="done", click_stop_after_page=None):
    """Run saver.js in a browser against Site; returns the dialog messages. Downloads go to the folder `downloads`."""
    from playwright.sync_api import sync_playwright
    Site.challenged = False
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dialogs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge" if sys.platform == "win32" else None)
        page = browser.new_page()
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept("1") if d.type == "prompt" else d.accept()))
        page.on("download", lambda d: d.save_as(downloads / d.suggested_filename))
        page.goto(f"http://127.0.0.1:{srv.server_port}/?page=1")
        page.evaluate(f"window.CISCE_DELAY_MS = {delay_ms}; localStorage.clear()")
        page.add_script_tag(content=(HERE.parent / "saver.js").read_text(encoding="utf-8"))
        end = time.time() + 30
        while not any(until in m for m in dialogs) and time.time() < end:
            if click_stop_after_page and page.evaluate("localStorage.getItem('cisce-saver-next')") == str(click_stop_after_page + 1):
                page.get_by_role("button", name="Stop").click()
                click_stop_after_page = None
            page.wait_for_timeout(100)
        page.wait_for_timeout(500)
        assert page.locator("text=CISCE saver").count() == 0          # the box is gone at the end
        browser.close()
    srv.shutdown()
    return dialogs


def test_saver_js_then_csv(tmp_path, monkeypatch):
    downloads = tmp_path / "Downloads"
    dialogs = run_saver_js(downloads)
    assert any("Cloudflare check on page 2" in m for m in dialogs) and any("done" in m for m in dialogs)
    assert sorted(f.name for f in downloads.iterdir()) == ["cisce-pages-0001-0001.json", "cisce-pages-0002-0002.json"]
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["saver", "--out", str(out), "--in", str(downloads)])
    saver.main()
    assert sorted(f.name for f in (out / "pages").iterdir()) == ["page-0001.html", "page-0002.html"]
    rows = list(csv.DictReader(open(out / "cisce_schools.csv", encoding="utf-8-sig")))
    assert len(rows) == 10 and rows[0]["code"] == "AN001" and rows[0]["listed_total"] == "20"


def test_saver_js_stop_button(tmp_path):
    downloads = tmp_path / "Downloads"
    dialogs = run_saver_js(downloads, delay_ms=5000, until="stopped", click_stop_after_page=1)
    assert any("stopped before page 2" in m for m in dialogs)
    assert sorted(f.name for f in downloads.iterdir()) == ["cisce-pages-0001-0001.json"]
