# cisce-locator-saver

Saves the full list of CISCE affiliated schools from https://locate.cisce.org/ with your own browser, then makes a CSV.

The site shows a Cloudflare check ("Verify you are human"). You tick it yourself. The tool does not click it.
The tool does not control the browser. A browser that a program controls fails the check again and again.
Instead, `saver.js` runs inside your normal browser tab and reads one page every 6-8 seconds (about 335 pages, about 40 minutes).

## Part 1: save the pages (Chrome or Firefox)

1. Download `saver.js` from **Releases → latest**. Open it in Notepad. Press Ctrl+A, then Ctrl+C.
2. In your normal Chrome or Firefox, open https://locate.cisce.org/. Tick "Verify you are human" if it shows. Wait for the schools.
3. Press F12 and click **Console**.
4. Paste with Ctrl+V and press Enter.
   - If the browser does not paste, type `allow pasting`, press Enter, then paste again.
5. A box asks for the start page. Click OK (page 1).
6. Wait. Keep the tab open. The console shows `page 12/335: saved`.
   - Every 50 pages the browser downloads a file `cisce-pages-0001-0050.json`. Allow "multiple downloads" if the browser asks.
7. If the Cloudflare check comes back, a box tells you what to do:
   1. Open the page it names in a **new** tab.
   2. Tick the box there and wait for the schools.
   3. Come back to the first tab and click OK.
8. At the end a box says `done`. The files are in your Downloads folder.

To continue after a stop: open the site again and paste the script again. The start page box shows the next page.

## Part 2: make the CSV (optional)

1. Download `cisce-locator-saver.exe` from **Releases → latest**.
2. Double-click it. Windows SmartScreen can warn about an unknown app: click **More info → Run anyway**.
3. It reads the `cisce-pages-*.json` files from your Downloads folder and from its own folder.
4. It writes `cisce-output\cisce_schools.csv` next to the .exe and shows the number of schools.

CSV columns: code, name, principal, address, locality, district, state, PIN, country, gender, residence, ASISC, ICSE, ISC, CVE,
website, latitude, longitude, the total that the site states, the page file.

No .exe? `run-from-source.bat` runs the same step with Python 3.12 from python.org.

## Send the files to the team box

Drag the `cisce-pages-*.json` files into the VS Code file explorer of the box, into `~/cisce-scraper/incoming/`.
The box makes the merged list from them (`s1d-labs/cisce-scraper`).

## Build

GitHub Actions (`build.yml`) runs the tests on Windows and builds the .exe with PyInstaller. The tests run `saver.js` in Edge
against a local web server, with one Cloudflare check on page 2. The workflow then runs the .exe on a saved page and puts
`saver.js`, the .exe and the .bat on the `latest` release. The parser is the same as in `s1d-labs/cisce-scraper`.
