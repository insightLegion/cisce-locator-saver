# cisce-locator-saver

Saves the full list of CISCE affiliated schools from https://locate.cisce.org/ with your own browser, then makes a CSV.

The site shows a Cloudflare check ("Verify you are human"). You tick it yourself. The tool does not click it.
The tool does not control the browser. A browser that a program controls fails the check again and again.
Instead, `saver.js` runs inside your normal browser tab and reads one page every 6-8 seconds (about 335 pages, about 40 minutes).

## Part 1: save the pages (Chrome or Firefox)

1. Open https://raw.githubusercontent.com/insightLegion/cisce-locator-saver/main/saver.js in your browser. Press Ctrl+A, then Ctrl+C.
   (Do not double-click a downloaded `saver.js`: Windows tries to run it as a script.)
2. In your normal Chrome or Firefox, open https://locate.cisce.org/. Tick "Verify you are human" if it shows. Wait for the schools.
3. Press F12 and click **Console**.
4. Paste with Ctrl+V and press Enter.
   - If the browser does not paste, type `allow pasting`, press Enter, then paste again.
5. A box asks for the start page. Click OK (page 1).
6. Wait. Keep the tab open. A red box at the top right shows `page 12/335 ...`.
   - To stop: click **Stop** in that box. The tool downloads the pages that it did not download yet.
   - Every 50 pages the browser downloads a file `cisce-pages-0001-0050.json`.
   - At the second file the browser asks about "multiple downloads". Click **Allow**. If you block it, the files after it are lost.
   - You can use other tabs or minimise the window. Do not close this tab.
7. If the Cloudflare check comes back, the red box tells you what to do:
   1. Open the page it names in a **new** tab.
   2. Tick the box there and wait for the schools.
   3. Come back to the first tab and click **Continue** in the red box. (**Stop** ends the run.)
8. At the end a message says `done` and lists the files of this run. Check that they are in your Downloads folder.

To continue after a stop: paste the script again. The start page box shows the next page.
If one page fails 5 times (the site is down), the tool stops and tells you. Paste it again later.
If a file is missing, paste again and type the first page of that file as the start page.

## Part 2: make the CSV (optional)

1. Download `cisce-locator-saver.exe` from **Releases → latest**.
2. Double-click it. Windows SmartScreen can warn about an unknown app: click **More info → Run anyway**.
3. It reads the `cisce-pages-*.json` files from your Downloads folder and from its own folder.
4. It writes `cisce-output\cisce_schools.csv` next to the .exe and shows the number of schools and any missing pages.

CSV columns: code, name, principal, address, locality, district, state, PIN, country, gender, residence, ASISC, ICSE, ISC, CVE,
website, latitude, longitude, the total that the site states, the page file.

No .exe? Put `run-from-source.bat` and `saver.py` (both on the release) in one folder; the .bat runs the same step with Python 3.12 from python.org.

## Send the files to the team box

Send the `cisce-pages-*.json` files to trideep (or drag them into the VS Code file explorer of his team box).
On the box they go into `<data dir>/locator-<date>-saved-by-hand/`; `link/merge.py` of `s1d-labs/cisce-scraper` reads them.

## Build

GitHub Actions (`build.yml`) runs the tests on Windows and builds the .exe with PyInstaller. The tests run `saver.js` in Edge
against a local web server, with one Cloudflare check on page 2. The workflow then runs the .exe on a saved page and puts
`saver.js`, `saver.py`, the .exe and the .bat on the `latest` release. The parser is the same as in `s1d-labs/cisce-scraper`.
