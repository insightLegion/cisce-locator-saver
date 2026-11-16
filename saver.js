// CISCE locator saver. Paste this into the DevTools console (F12 → Console) of https://locate.cisce.org/ in your normal
// Chrome or Firefox, AFTER you passed the "Verify you are human" check yourself. It never clicks the check.
// It reads one listing page every 6-8 s with your own browser session and downloads the pages as cisce-pages-NNNN-NNNN.json
// (50 pages per file). If the check comes back, the box on the page asks you to tick it in a new tab, then click Continue.
// To stop: click "Stop" in the box at the top right (it downloads what is not downloaded yet). Paste again to resume.
(async () => {
  if (window.cisceSaver) { alert("CISCE saver is already running in this tab. Click Stop in its box first."); return; }
  const DELAY_MS = window.CISCE_DELAY_MS ?? 6000, RETRY_MS = window.CISCE_RETRY_MS ?? 60000, CHUNK = 50, KEY = "cisce-saver-next";
  const store = {   // the next page to fetch, kept in this site's localStorage; private windows can refuse it
    get: () => { try { return localStorage.getItem(KEY); } catch { return null; } },
    set: v => { try { v == null ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, v); } catch {} },
  };
  let n = +(prompt("CISCE saver: start at page", store.get() || "1") || 0), last = Infinity, fails = 0, end = "";
  if (!n) return;
  const state = window.cisceSaver = { stop: false, wake: () => {}, ctl: null }, files = [];
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;top:8px;right:8px;z-index:2147483647;background:#fff;color:#000;border:2px solid #c00;" +
    "padding:8px 10px;font:14px sans-serif;box-shadow:0 2px 8px #0005;max-width:420px;white-space:pre-line";
  box.innerHTML = '<b>CISCE saver</b> <span></span> <button type="button" hidden>Continue</button> <button type="button">Stop</button>';
  const [status] = box.getElementsByTagName("span"), [goBtn, stopBtn] = box.getElementsByTagName("button");
  stopBtn.onclick = () => {
    state.stop = true; stopBtn.disabled = true; stopBtn.textContent = "Stopping ...";
    state.wake(); state.ctl?.abort();
  };
  document.body.append(box);
  const show = s => { status.textContent = s; console.log(`CISCE saver: ${s}`); };
  // One timer per wait: a chain of short timers runs only once a minute in a hidden tab (Chrome "intensive throttling").
  const sleep = ms => new Promise(r => { const id = setTimeout(r, ms); state.wake = () => { clearTimeout(id); r(); }; });
  // An in-page question, not confirm(): Chrome cancels confirm() when you switch to another tab.
  const ask = msg => new Promise(r => {
    show(msg); goBtn.hidden = false;
    goBtn.onclick = () => { goBtn.hidden = true; r(true); };
    state.wake = () => { goBtn.hidden = true; r(false); };
  });
  const hasSchools = t => /school-card|<li><b>[A-Z]{2,4}\d+<\/b><\/li>/.test(t);    // card layout (2026) or table layout (2023-25)
  // Only the interactive check ("Just a moment..."): normal pages also load Cloudflare's challenge-platform script.
  const isChallenge = (r, t) => r.headers?.get("cf-mitigated") === "challenge" || /<title>\s*Just a moment/.test(t);
  const total = t => +((t.match(/Showing\s+\d+\s+to\s+\d+\s+of\s+(\d+)\s+entries/) || [])[1] || 0);
  let pages = {};
  const download = () => {
    const names = Object.keys(pages);
    if (!names.length) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(pages)], { type: "application/json" }));
    a.download = `cisce-pages-${names[0].slice(5, 9)}-${names.at(-1).slice(5, 9)}.json`;
    document.body.append(a); a.click(); a.remove();
    pages = {};
    files.push(a.download);
    store.set(+names.at(-1).slice(5, 9) + 1);   // resume after the last page that is in a downloaded file, not before
    console.log(`%cCISCE saver: downloaded ${a.download}`, "color: green");
  };
  try {
    while (n <= last && !state.stop) {
      show(`page ${n}${last < Infinity ? "/" + last : ""} ...`);
      let r, t;
      state.ctl = new AbortController();         // Stop, or no answer in 60 s, ends the request
      const signal = AbortSignal.any ? AbortSignal.any([state.ctl.signal, AbortSignal.timeout(60000)]) : state.ctl.signal;
      try { r = await fetch(`/?page=${n}`, { credentials: "include", cache: "no-store", signal }); t = await r.text(); }
      catch (e) { r = { status: 0 }; t = ""; }
      if (state.stop) break;
      if (isChallenge(r, t)) {
        download();                          // keep what is done if the tab gets closed
        if (!await ask(`Cloudflare check on page ${n}.\n1. Open https://locate.cisce.org/?page=${n} in a NEW tab.\n` +
                       `2. Tick "Verify you are human" there and wait for the schools.\n3. Come back here and click Continue.`)) break;
        continue;
      }
      if (r.status !== 200 || (!hasSchools(t) && n < last)) {   // an error in the middle of the list: wait, retry
        if (++fails >= 5) { end = `page ${n} failed 5 times (HTTP ${r.status || "no answer"}). Paste the script again later to continue.`; break; }
        show(`page ${n}: HTTP ${r.status || "no answer"}, retry ${fails}/4 in ${RETRY_MS / 1000} s`);
        await sleep(RETRY_MS);
        continue;
      }
      fails = 0;
      if (!hasSchools(t)) break;   // after the last page
      last = Math.ceil(total(t) / 10) || last;
      pages[`page-${String(n).padStart(4, "0")}.html`] = t;
      state.next = n + 1;
      if (Object.keys(pages).length >= CHUNK) download();
      if (n++ < last) await sleep(DELAY_MS + Math.random() * 2000);
    }
  } finally {
    download();
    delete window.cisceSaver;
    box.remove();
  }
  const list = files.length ? `\n\n${files.length} file(s) in this run:\n${files.join("\n")}\nIf one is not in your Downloads folder, the browser blocked it: allow downloads for this site and paste again from its first page.` : "";
  if (!end && n > last) { store.set(null); end = "done. Send the cisce-pages-*.json files from your Downloads folder."; }
  alert(`CISCE saver: ${end || `stopped before page ${n}. Paste the script again to continue from there.`}${list}`);
})();
