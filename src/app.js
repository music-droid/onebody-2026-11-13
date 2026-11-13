import * as pdfjsLib from "./vendor/pdfjs/pdf.min.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL("./vendor/pdfjs/pdf.worker.min.mjs", import.meta.url).href;
const FONTS = new URL("./vendor/pdfjs/standard_fonts/", import.meta.url).href;

const SET = window.OB_SET;
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const KEYNAME = "ob-k";
const ub = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));

function encUrl(path) {
  if (!path) return path;
  const p = path.startsWith("files/") ? path : "files/" + path;
  return p.endsWith(".enc") ? p : p + ".enc";
}

async function decryptEnc(url) {
  const raw = sessionStorage.getItem(KEYNAME) || localStorage.getItem(KEYNAME);
  if (!raw) throw new Error("missing key");
  const key = await crypto.subtle.importKey("raw", ub(raw), "AES-GCM", false, ["decrypt"]);
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error("fetch failed " + r.status);
  const b = new Uint8Array(await r.arrayBuffer());
  return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: b.slice(0, 12) }, key, b.slice(12)));
}

function chartList(s) {
  if (Array.isArray(s.charts) && s.charts.length) return s.charts;
  if (s.chart) return [s.chart];
  return [{ file: null, kind: "chord", label: "Chord chart" }];
}

function chartButtons(s) {
  return chartList(s).map(ch => {
    const present = !!(ch && ch.file && ch.present);
    const kind = ch?.kind || "chord";
    const label = ch?.label || (kind === "lyrics" ? "Lyrics (chord chart coming)" : "Chord chart");
    const ic = kind === "lyrics" ? "📝" : "🎸";
    if (present) {
      return `<button class="fbtn" type="button" data-pdf="${esc(ch.file)}" data-kind="${esc(label)}"><span class="ic">${ic}</span><span>${esc(label)}<small>Opens here</small></span></button>`;
    }
    const missing = kind === "lyrics" ? "Lyrics (chord chart coming)" : "Chart needed";
    return `<div class="fbtn missing" aria-disabled="true"><span class="ic">${ic}</span><span>${esc(ch?.label || "Chord chart")}<small>${esc(missing)}</small></span></div>`;
  }).join("");
}

function recHTML(s) {
  if (s.youtube) return `<div class="rec" data-yt="${esc(s.youtube)}"></div>`;
  return `<p class="nort">No recording added yet.</p>`;
}

function subHTML(sub, i, j) {
  const credit = [sub.songwriter, sub.artist].filter(Boolean).join(" · ");
  return `<div class="sub" data-i="${i}" data-j="${j}">
    <h3>${esc(sub.title)}</h3>
    ${credit ? `<div class="comp">${esc(credit)}</div>` : ""}
    ${sub.key && sub.key !== SET.songs[i].key ? `<p class="note">Key ${esc(sub.key)}</p>` : ""}
    <div class="files">${chartButtons(sub)}</div>
    ${recHTML(sub)}
  </div>`;
}

function cardHTML(s, i) {
  const credit = [s.songwriter, s.artist].filter(Boolean).join(" · ");
  const subs = (s.medley && Array.isArray(s.songs)) ? s.songs.map((sub, j) => subHTML(sub, i, j)).join("") : "";
  const ownCharts = s.medley ? "" : `<div class="files">${chartButtons(s)}</div>${recHTML(s)}`;
  return `<article class="card" id="song-${s.n}" data-i="${i}">
    <button class="card-head" type="button" aria-expanded="false" aria-controls="body-${i}">
      <span class="num">${s.n}</span>
      <span class="ht"><span class="slot">${esc(s.setLabel || (s.medley ? "Medley" : "Song"))}</span><div class="title">${esc(s.title)}</div>${credit ? `<div class="comp">${esc(credit)}</div>` : ""}</span>
      <span class="key" aria-label="Key ${esc(s.key)}">${esc(s.key || "–")}</span><span class="chev" aria-hidden="true">▾</span>
    </button>
    <div class="card-body" id="body-${i}">
      ${s.note ? `<p class="note">${esc(s.note)}</p>` : ""}
      ${ownCharts}
      ${subs}
    </div></article>`;
}

function mountYouTube(el) {
  const recs = el.querySelectorAll(".rec[data-yt]");
  recs.forEach(rec => {
    const id = rec.dataset.yt;
    if (!id || rec.querySelector("iframe")) return;
    const src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?playsinline=1&rel=0&modestbranding=1&fs=1`;
    rec.innerHTML = `<div class="yt"><iframe src="${src}" title="Recording" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>`;
  });
}

function renderHeader() {
  const e = SET.event;
  $("#event-sub").textContent = `${e.ministry || "Flourish"} · led by ${e.leader || "Justin Yglesias"}`;
  $("#event-date").textContent = e.dateLabel || "";
  document.title = `One Body · ${e.dateLabel || "Worship Night"}`;
  const parts = [];
  parts.push(`<b>Details still being confirmed</b>`);
  parts.push(`<div>Venue: ${e.venue ? esc(e.venue) : "To be confirmed"}</div>`);
  parts.push(`<div>Schedule: ${e.schedule ? esc(e.schedule) : "To be confirmed"}</div>`);
  if (e.rosterNote) parts.push(`<div>${esc(e.rosterNote)}</div>`);
  if (Array.isArray(e.roster) && e.roster.length) {
    const items = e.roster.map(r => {
      const st = r.status === "possibly" ? " <em>(possibly)</em>" : "";
      return `<li>${esc(r.name)} — ${esc(r.role)}${st}</li>`;
    }).join("");
    parts.push(`<div style="margin-top:8px"><b>Roster</b></div><ul>${items}</ul>`);
  }
  const box = $("#meta");
  box.innerHTML = parts.join("");
  box.hidden = false;
  $("#ver").textContent = `Set version ${SET.version}`;
}

function renderSongs() {
  const main = $("#songs");
  const chunks = [];
  let lastSet = null;
  SET.songs.forEach((s, i) => {
    if (s.set && s.set !== lastSet) {
      chunks.push(`<div class="set-h">${esc(s.setLabel || s.set)}</div>`);
      lastSet = s.set;
    }
    chunks.push(cardHTML(s, i));
  });
  main.innerHTML = chunks.join("");
  main.addEventListener("click", ev => {
    const head = ev.target.closest(".card-head");
    if (head) {
      const card = head.parentElement, open = !card.classList.contains("open");
      card.classList.toggle("open", open); head.setAttribute("aria-expanded", open);
      if (open) mountYouTube(card);
      return;
    }
    const f = ev.target.closest("[data-pdf]");
    if (f) {
      const card = f.closest(".card");
      const s = SET.songs[+card.dataset.i];
      const sub = f.closest(".sub");
      const title = sub ? s.songs[+sub.dataset.j].title : s.title;
      const key = sub ? (s.songs[+sub.dataset.j].key || s.key) : s.key;
      openPdf(encUrl(f.dataset.pdf), title, `${f.dataset.kind} · ${key || ""}`);
    }
  });
}

const V = { doc: null, zoom: 1, token: 0, task: null };
const viewer = $("#viewer"), pagesEl = $("#v-pages"), scrollEl = $("#v-scroll"), statusEl = $("#v-status");
const MAX_PIXELS = 16_000_000;

async function openPdf(url, title, sub) {
  $("#v-title").textContent = title; $("#v-sub").textContent = sub;
  viewer.hidden = false; document.body.style.overflow = "hidden";
  if (history.state?.viewer !== true) history.pushState({ viewer: true }, "");
  pagesEl.innerHTML = ""; statusEl.textContent = "Loading…"; V.zoom = 1;
  try {
    if (V.task) V.task.destroy();
    const data = await decryptEnc(url);
    V.task = pdfjsLib.getDocument({ data, standardFontDataUrl: FONTS, isEvalSupported: false });
    V.doc = await V.task.promise;
    await renderAll();
  } catch (err) { statusEl.textContent = "Couldn't open this file."; console.error(err); }
}

async function renderAll() {
  const doc = V.doc, token = ++V.token; if (!doc) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
  const avail = scrollEl.clientWidth - 16;
  statusEl.textContent = "";
  pagesEl.style.transform = "";
  for (let n = 1; n <= doc.numPages; n++) {
    const page = await doc.getPage(n); if (token !== V.token) return;
    const base = page.getViewport({ scale: 1 });
    const cssScale = (Math.min(avail, 1100) / base.width) * V.zoom;
    let px = cssScale * dpr;
    const area = base.width * base.height * px * px;
    if (area > MAX_PIXELS) px *= Math.sqrt(MAX_PIXELS / area);
    const vp = page.getViewport({ scale: px });
    const c = document.createElement("canvas");
    c.width = Math.floor(vp.width); c.height = Math.floor(vp.height);
    c.style.width = Math.floor(base.width * cssScale) + "px"; c.style.height = Math.floor(base.height * cssScale) + "px";
    c.setAttribute("aria-label", `Page ${n} of ${doc.numPages}`);
    if (n === 1) pagesEl.innerHTML = "";
    pagesEl.appendChild(c);
    await page.render({ canvasContext: c.getContext("2d"), viewport: vp }).promise;
    if (token !== V.token) return;
  }
  pagesEl.dataset.rendered = String(doc.numPages);
  flash(`${doc.numPages} page${doc.numPages > 1 ? "s" : ""} · ${Math.round(V.zoom * 100)}%`);
}

let flashT; function flash(t) { statusEl.textContent = t; clearTimeout(flashT); flashT = setTimeout(() => statusEl.textContent = "", 1400); }
function setZoom(z, anchor) {
  z = Math.max(0.5, Math.min(4, z)); if (Math.abs(z - V.zoom) < 0.01) return;
  const r = z / V.zoom, ax = anchor?.x ?? scrollEl.clientWidth / 2, ay = anchor?.y ?? scrollEl.clientHeight / 2;
  const sx = (scrollEl.scrollLeft + ax) * r - ax, sy = (scrollEl.scrollTop + ay) * r - ay;
  V.zoom = z; renderAll().then(() => { scrollEl.scrollLeft = sx; scrollEl.scrollTop = sy; });
}
function closeViewer(fromPop) {
  viewer.hidden = true; document.body.style.overflow = ""; V.token++;
  if (V.task) { V.task.destroy(); V.task = null; } V.doc = null; pagesEl.innerHTML = "";
  if (!fromPop && history.state?.viewer) history.back();
}
$("#v-close").onclick = () => closeViewer(false);
$("#v-in").onclick = () => setZoom(V.zoom * 1.25);
$("#v-out").onclick = () => setZoom(V.zoom / 1.25);
$("#v-fit").onclick = () => { const f = scrollEl.scrollTop / Math.max(1, scrollEl.scrollHeight); V.zoom = 1; renderAll().then(() => { scrollEl.scrollLeft = 0; scrollEl.scrollTop = f * scrollEl.scrollHeight; }); };
window.addEventListener("popstate", () => { if (!viewer.hidden) closeViewer(true); });
document.addEventListener("keydown", e => { if (!viewer.hidden && e.key === "Escape") closeViewer(false); });
let rz; window.addEventListener("resize", () => { if (!viewer.hidden) { clearTimeout(rz); rz = setTimeout(renderAll, 250); } });

let pinch = null;
const dist = t => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
scrollEl.addEventListener("touchstart", e => {
  if (e.touches.length === 2) {
    const rect = scrollEl.getBoundingClientRect();
    pinch = { d0: dist(e.touches), x: (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left, y: (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top, r: 1 };
    pagesEl.style.transformOrigin = `${scrollEl.scrollLeft + pinch.x}px ${scrollEl.scrollTop + pinch.y}px`;
  }
}, { passive: true });
scrollEl.addEventListener("touchmove", e => {
  if (pinch && e.touches.length === 2) {
    e.preventDefault();
    pinch.r = Math.max(0.5 / V.zoom, Math.min(4 / V.zoom, dist(e.touches) / pinch.d0));
    pagesEl.style.transform = `scale(${pinch.r})`;
  }
}, { passive: false });
scrollEl.addEventListener("touchend", e => {
  if (pinch && e.touches.length < 2) { const p = pinch; pinch = null; pagesEl.style.transform = ""; pagesEl.style.transformOrigin = "0 0"; setZoom(V.zoom * p.r, p); }
});
["gesturestart", "gesturechange"].forEach(ev => viewer.addEventListener(ev, e => e.preventDefault()));
scrollEl.addEventListener("wheel", e => { if (e.ctrlKey) { e.preventDefault(); setZoom(V.zoom * (e.deltaY < 0 ? 1.1 : 0.9)); } }, { passive: false });

renderHeader(); renderSongs();
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
