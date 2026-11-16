// CISCE locator saver. Paste this into the DevTools console (F12 → Console) of https://locate.cisce.org/ in your normal
// Chrome or Firefox, AFTER you passed the "Verify you are human" check yourself. It never clicks the check.
// It reads one listing page every 6-8 s with your own browser session and downloads the pages as cisce-pages-NNNN-NNNN.json
// (50 pages per file). If the check comes back, it stops and asks you to tick it in a new tab. Paste again to resume.
// To stop: click "Stop" in the box at the top right (it downloads what is not downloaded yet).
(async () => {
  if (window.cisceSaver) { alert("CISCE saver is already running in this tab. Click Stop in its box first."); return; }
  const DELAY_MS = window.CISCE_DELAY_MS ?? 6000, CHUNK = 50, KEY = "cisce-saver-next";
  let n = +(prompt("CISCE saver: start at page", localStorage.getItem(KEY) || "1") || 0), last = Infinity, fails = 0, end = "";
  if (!n) return;
  const state = window.cisceSaver = { stop: false };
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;top:8px;right:8px;z-index:2147483647;background:#fff;color:#000;border:2px solid #c00;" +
    "padding:8px 10px;font:14px sans-serif;box-shadow:0 2px 8px #0005";
  box.innerHTML = '<b>CISCE saver</b> <span></span> <button type="button">Stop</button>';
  const status = box.querySelector("span"), stopBtn = box.querySelector("button");
  stopBtn.onclick = () => { state.stop = true; stopBtn.disabled = true; stopBtn.textContent = "Stopping ..."; };
  document.body.append(box);
  const show = s => { status.textContent = s; console.log(`CISCE saver: ${s}`); };
  const sleep = async ms => { for (const end = Date.now() + ms; Date.now() < end && !state.stop;) await new Promise(r => setTimeout(r, 200)); };
  const isChallenge = t => /<title>\s*(Just a moment|Attention Required)/.test(t) || (t.includes("challenge-platform") && !t.includes("school-card"));
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
    console.log(`%cCISCE saver: downloaded ${a.download}`, "color: green");
  };
  try {
    while (n <= last && !state.stop) {
      show(`page ${n}${last < Infinity ? "/" + last : ""} ...`);
      let r, t;
      try { r = await fetch(`/?page=${n}`, { credentials: "include", cache: "no-store" }); t = await r.text(); }
      catch (e) { r = { status: 0 }; t = ""; }
      if (isChallenge(t)) {
        download();                          // keep what is done if the tab gets closed
        if (!confirm(`Cloudflare check on page ${n}.\n\n1. Open https://locate.cisce.org/?page=${n} in a NEW tab.\n` +
                     `2. Tick "Verify you are human" there and wait for the schools.\n3. Come back here and click OK.\n\nCancel = stop.`)) break;
        continue;
      }
      if (r.status !== 200 || (!t.includes("school-card") && n < last)) {   // an error in the middle of the list: wait, retry
        if (++fails > 5) { end = `page ${n} failed 5 times (HTTP ${r.status}). Paste the script again later to continue.`; break; }
        show(`page ${n}: HTTP ${r.status || "no answer"}, retry ${fails}/5 in 60 s`);
        await sleep(60000);
        continue;
      }
      fails = 0;
      if (!t.includes("school-card")) break;   // after the last page
      last = Math.ceil(total(t) / 10) || last;
      const name = `page-${String(n).padStart(4, "0")}.html`;
      pages[name] = t;
      localStorage.setItem(KEY, n + 1);
      if (Object.keys(pages).length >= CHUNK) download();
      if (n++ < last) await sleep(DELAY_MS + Math.random() * 2000);
    }
  } finally {
    download();
    delete window.cisceSaver;
    box.remove();
  }
  if (!end && n > last) { localStorage.removeItem(KEY); end = "done. Send the cisce-pages-*.json files from your Downloads folder."; }
  alert(`CISCE saver: ${end || `stopped before page ${n}. Paste the script again to continue from there.`}`);
})();
