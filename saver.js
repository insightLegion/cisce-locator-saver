// CISCE locator saver. Paste this into the DevTools console (F12 → Console) of https://locate.cisce.org/ in your normal
// Chrome or Firefox, AFTER you passed the "Verify you are human" check yourself. It never clicks the check.
// It reads one listing page every 6-8 s with your own browser session and downloads the pages as cisce-pages-NNNN-NNNN.json
// (50 pages per file). If the check comes back, it stops and asks you to tick it in a new tab. Paste again to resume.
(async () => {
  const DELAY_MS = window.CISCE_DELAY_MS ?? 6000, CHUNK = 50, KEY = "cisce-saver-next";
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const isChallenge = t => /<title>\s*(Just a moment|Attention Required)/.test(t) || (t.includes("challenge-platform") && !t.includes("school-card"));
  const total = t => +((t.match(/Showing\s+\d+\s+to\s+\d+\s+of\s+(\d+)\s+entries/) || [])[1] || 0);
  const download = pages => {
    const names = Object.keys(pages);
    if (!names.length) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(pages)], { type: "application/json" }));
    a.download = `cisce-pages-${names[0].slice(5, 9)}-${names.at(-1).slice(5, 9)}.json`;
    document.body.append(a); a.click(); a.remove();
    console.log(`%cdownloaded ${a.download}`, "color: green");
  };
  let n = +(prompt("CISCE saver: start at page", localStorage.getItem(KEY) || "1") || 0);
  if (!n) return;
  let last = Infinity, pages = {};
  while (n <= last) {
    let r, t;
    try { r = await fetch(`/?page=${n}`, { credentials: "include" }); t = await r.text(); }
    catch (e) { console.warn(`page ${n}: no answer (${e}), retry in 30 s`); await sleep(30000); continue; }
    if (isChallenge(t)) {
      download(pages); pages = {};       // keep what is done if the tab gets closed
      alert(`Cloudflare check on page ${n}.\n\n1. Open https://locate.cisce.org/?page=${n} in a NEW tab.\n2. Tick "Verify you are human" there and wait for the schools.\n3. Come back to this tab and click OK.`);
      continue;
    }
    if (r.status !== 200) { console.warn(`page ${n}: HTTP ${r.status}, retry in 60 s`); await sleep(60000); continue; }
    if (!t.includes("school-card")) { console.log(`page ${n}: no schools, end of the list`); break; }
    last = Math.ceil(total(t) / 10) || last;
    pages[`page-${String(n).padStart(4, "0")}.html`] = t;
    localStorage.setItem(KEY, n + 1);
    console.log(`page ${n}/${last}: saved`);
    if (Object.keys(pages).length >= CHUNK) { download(pages); pages = {}; }
    if (n++ < last) await sleep(DELAY_MS + Math.random() * 2000);
  }
  download(pages);
  localStorage.removeItem(KEY);
  alert("CISCE saver: done. Send the cisce-pages-*.json files from your Downloads folder.");
})();
