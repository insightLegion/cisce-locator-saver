"""Tests: the parser on saved pages, saver.js in a real browser against a local web server (no access to locate.cisce.org),
and the unpack + CSV step on the files that saver.js downloaded."""
import csv
import os
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
    first_page2 = "challenge"        # what the first request for page 2 gets: "challenge" or "error" (HTTP 500)

    def do_GET(self):
        status, body = 200, self.result
        if self.path.endswith("page=2") and not Site.challenged:
            Site.challenged = True
            # a server error page that loads Cloudflare's normal challenge-platform script: not a check, retry it
            status, body = (403, self.challenge) if Site.first_page2 == "challenge" else \
                (500, b"<html><head><title>500</title><script src='/cdn-cgi/challenge-platform/scripts/jsd/main.js'></script></head></html>")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def run_saver_js(downloads, delay_ms=0, until="done", click_stop_after_page=None, first_page2="challenge"):
    """Run saver.js in a browser against Site; returns the dialog messages and the questions shown in the box
    (the box's Continue button is clicked). Downloads go to the folder `downloads`."""
    from playwright.sync_api import sync_playwright
    Site.challenged, Site.first_page2 = False, first_page2
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dialogs = []
    with sync_playwright() as p:
        kind = os.environ.get("CISCE_TEST_BROWSER", "chromium")       # chromium (Edge on Windows) or firefox
        browser = p.firefox.launch() if kind == "firefox" else p.chromium.launch(channel="msedge" if sys.platform == "win32" else None)
        page = browser.new_page()
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept("1") if d.type == "prompt" else d.accept()))
        page.on("download", lambda d: d.save_as(downloads / d.suggested_filename))
        page.goto(f"http://127.0.0.1:{srv.server_port}/?page=1")
        page.evaluate(f"window.CISCE_DELAY_MS = {delay_ms}; window.CISCE_RETRY_MS = 500; localStorage.clear()")
        page.add_script_tag(content=(HERE.parent / "saver.js").read_text(encoding="utf-8"))
        end = time.time() + 30
        while not any(until in m for m in dialogs) and time.time() < end:
            go = page.get_by_role("button", name="Continue")
            if go.count() and go.is_visible():
                dialogs.append("box: " + page.locator("text=CISCE saver").locator("..").inner_text())
                go.click()
            if click_stop_after_page and page.evaluate("window.cisceSaver && window.cisceSaver.next") == click_stop_after_page + 1:
                page.get_by_role("button", name="Stop").click()
                click_stop_after_page = None
            page.wait_for_timeout(100)
        page.wait_for_timeout(500)
        assert page.locator("text=CISCE saver").count() == 0          # the box is gone at the end
        run_saver_js.resume = page.evaluate("localStorage.getItem('cisce-saver-next')")
        browser.close()
    srv.shutdown()
    return dialogs


def test_saver_js_then_csv(tmp_path, monkeypatch):
    downloads = tmp_path / "Downloads"
    dialogs = run_saver_js(downloads)
    assert any("Cloudflare check on page 2" in m for m in dialogs) and any("done" in m for m in dialogs)
    assert run_saver_js.resume is None   # a finished run leaves no resume page
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
    resume_page = run_saver_js.resume
    assert any("stopped before page 2" in m for m in dialogs)
    assert sorted(f.name for f in downloads.iterdir()) == ["cisce-pages-0001-0001.json"]
    assert resume_page == "2"          # the next run starts after the last downloaded page


def test_saver_js_error_page_is_retried_not_a_check(tmp_path):
    downloads = tmp_path / "Downloads"
    dialogs = run_saver_js(downloads, first_page2="error")
    assert not any("Cloudflare check" in m for m in dialogs) and any("done" in m for m in dialogs)
    assert sorted(f.name for f in downloads.iterdir()) == ["cisce-pages-0001-0002.json"]


def test_csv_skips_a_broken_page_and_lists_missing_pages(tmp_path, capsys):
    good = (PAGES / "result-isc-india-p1.html").read_text(encoding="utf-8")
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "page-0001.html").write_text(good, encoding="utf-8")
    (tmp_path / "pages" / "page-0003.html").write_text(good, encoding="utf-8")
    broken = '<div class="school-card"></tbody>\nconst locations = {not json};\n'
    (tmp_path / "pages" / "page-0004.html").write_text(broken, encoding="utf-8")
    assert saver.write_csv(tmp_path) == 10
    out = capsys.readouterr().out
    assert "page-0004.html: cannot read" in out and "Missing pages (1): 2" in out
