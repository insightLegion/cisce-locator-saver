"""Tests: the parser on saved pages, and the whole save loop against a local web server (no access to locate.cisce.org)."""
import csv
import http.server
import sys
import threading
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import saver  # noqa: E402

PAGES = Path(__file__).parent / "pages"


def test_parse_result_page():
    rows = dict(saver.parse((PAGES / "result-isc-india-p1.html").read_text(encoding="utf-8")))
    assert len(rows) == 10 and rows["AN001"]["pin"] == "744103" and rows["AP003"]["website"] == "https://www.loyolapublicschool.org"
    assert rows["AN001"]["icse"] and rows["AN001"]["isc"] and rows["AN001"]["listed_total"] == 1928


def test_challenge_page():
    page = (PAGES / "cloudflare-challenge.html").read_text(encoding="utf-8")
    assert saver.is_challenge(page) and saver.parse(page) == []


def test_save_loop_and_csv(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_bytes((PAGES / "result-isc-india-p1.html").read_bytes())
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(site)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = "msedge" if sys.platform == "win32" else "chromium"
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["saver", "--out", str(out), "--base", f"http://127.0.0.1:{srv.server_port}", "--delay", "0",
                                      "--max-pages", "2", "--headless", "--browser", browser])
    saver.main()
    srv.shutdown()
    assert sorted(f.name for f in (out / "pages").iterdir()) == ["page-0001.html", "page-0002.html"]
    rows = list(csv.DictReader(open(out / "cisce_schools.csv", encoding="utf-8-sig")))
    assert len(rows) == 10 and rows[0]["code"] == "AN001"
