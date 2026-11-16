# cisce-locator-saver

Saves the full list of CISCE affiliated schools from https://locate.cisce.org/ on a Windows PC, in your own Microsoft Edge.

The site shows a Cloudflare check ("Verify you are human") to automated visitors. **You** tick it in the browser window. The tool
does not click it. After that the tool opens one page every 6-8 seconds (about 335 pages, about 40 minutes) and saves each page.

## Use

1. Download `cisce-locator-saver.exe` from **Releases → latest**. Put it in an empty folder (for example `C:\cisce`).
2. Double-click it. A console window and an Edge window open.
   - Windows SmartScreen can warn about an unknown app: click **More info → Run anyway**.
3. When the console says `please tick 'Verify you are human'`, tick the box in the Edge window.
4. Wait. Do not close the Edge window. If the check comes back, the console beeps: tick it again.
5. At the end the console shows `N schools in ...\cisce-output\cisce_schools.csv`. Press Enter to close.

To continue after a stop: double-click again. Saved pages are kept (`cisce-output\pages`).

## Output (`cisce-output\` next to the .exe)

- `pages\page-0001.html` ... the saved pages (send these: the parser on the team box reads them).
- `cisce_schools.csv`: code, name, principal, address, locality, district, state, PIN, country, gender, residence, ASISC,
  ICSE, ISC, CVE, website, latitude, longitude, the total that the site states.
- `browser-profile\`: the tool's own Edge profile (keeps the Cloudflare cookie). Delete it when done.

Send the `pages` folder (zip) and the CSV to the team box.

## If Edge does not pass the check

Save the pages by hand: in a normal Edge window open `https://locate.cisce.org/?page=1`, press Ctrl+S, choose "Webpage, HTML only",
save into `cisce-output\pages`. Repeat for the next pages. Then run `cisce-locator-saver.exe --parse-only` to make the CSV.

## Options

```
cisce-locator-saver.exe --parse-only          CSV from the pages already saved (also pages saved by hand)
cisce-locator-saver.exe --browser chrome      use Google Chrome instead of Edge
cisce-locator-saver.exe --delay 10            more seconds between pages (minimum 6)
cisce-locator-saver.exe --out D:\cisce        another output folder
```

No .exe? `run-from-source.bat` runs the same tool with Python 3.12 from python.org.

## Build

GitHub Actions (`build.yml`) builds the .exe on Windows with PyInstaller, runs the tests and a smoke test of the .exe with Edge
against a local web server, and puts the .exe on the `latest` release. The parser is the one of `s1d-labs/cisce-scraper`.
