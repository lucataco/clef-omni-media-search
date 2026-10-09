import { Searcher, norm } from "./search.js";

const WALL_SIZE = 150;       // tiles on the idle wall
const MAX_RESULTS = 72;      // tiles placed when searching
const PLAYING = 14;          // top results that play their clip (muted)
const BASE_W = 160, BASE_H = 90;

const $ = (s) => document.querySelector(s);
const wall = $("#wall"), input = $("#q"), clearBtn = $("#clear"), matched = $("#matched");
const hudL = $("#hud-left"), hudR = $("#hud-right");

const index = await (await fetch("data/index.json")).json();
const searcher = new Searcher(index);
const segs = index.segments;
const C = index.concepts;
const stats = index.stats;

// ------------------------------------------------------------------ tiles

const tiles = segs.map((s, i) => {
  const el = document.createElement("div");
  el.className = "tile hidden";
  el.innerHTML = `<img loading="lazy" decoding="async" alt=""><span class="score"></span>`;
  el.querySelector("img").src = s.poster;
  el.addEventListener("mouseenter", () => play(i, true));
  el.addEventListener("mouseleave", () => { if (!playingSet.has(i)) stop(i); });
  el.addEventListener("click", () => openModal(i));
  wall.appendChild(el);
  return { el, i, x: 0, y: 0, s: 0.5, video: null };
});

function place(t, x, y, scale, visible, delay = 0) {
  t.x = x; t.y = y; t.s = scale;
  t.el.style.transitionDelay = `${delay}ms`;
  t.el.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
  t.el.style.zIndex = visible ? String(1000 - Math.round(scale * 100)) : "0";
  t.el.classList.toggle("hidden", !visible);
}

const playingSet = new Set();
function play(i, hover = false) {
  const t = tiles[i];
  if (!t.video) {
    const v = document.createElement("video");
    v.muted = true; v.loop = true; v.playsInline = true; v.preload = "auto";
    v.src = segs[i].clip;
    v.addEventListener("playing", () => t.el.classList.add("playing"));
    t.el.insertBefore(v, t.el.querySelector(".score"));
    t.video = v;
  }
  t.video.play().catch(() => {});
  if (!hover) playingSet.add(i);
}
function stop(i) {
  const t = tiles[i];
  playingSet.delete(i);
  if (t.video) {
    t.video.pause();
    t.video.removeAttribute("src");
    t.video.load();
    t.video.remove();
    t.video = null;
  }
  t.el.classList.remove("playing");
}

// ------------------------------------------------------------------ layout

let rng = mulberry32(7);
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// idle wall: an even spread across all videos, so neighbours on the wall are not adjacent segments
const wallIds = Array.from({ length: WALL_SIZE }, (_, k) => Math.floor((k * segs.length) / WALL_SIZE));
const wallSet = new Set(wallIds);

function barRect(pad = 0) {
  const r = $("#searchbar").getBoundingClientRect();
  return { x: r.left - pad, y: r.top - pad, w: r.width + 2 * pad, h: r.height + 2 * pad };
}
const overlaps = (a, b, slack = 0) =>
  a.x + slack < b.x + b.w && b.x + slack < a.x + a.w && a.y + slack < b.y + b.h && b.y + slack < a.y + a.h;

let idleSlots = [];
function computeIdleSlots() {
  rng = mulberry32(7);
  const W = innerWidth, H = innerHeight;
  const bar = barRect(28);
  // cells roughly 3:2 so 16:9 tiles fill them; a few extra cells cover the ones under the search bar
  const n = WALL_SIZE * 1.06;
  const cols = Math.round(Math.sqrt((n * W) / (1.5 * H)));
  const rows = Math.ceil(n / cols);
  const cw = W / cols, ch = H / rows;
  const slots = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const w = cw * (0.78 + rng() * 0.36);
      const h = (w * 9) / 16;
      const x = c * cw + (cw - w) / 2 + (rng() - 0.5) * cw * 0.35;
      const y = r * ch + (ch - h) / 2 + (rng() - 0.5) * ch * 0.35;
      const rect = { x, y, w, h };
      if (!overlaps(rect, bar)) slots.push(rect);
    }
  }
  // shuffle so consecutive segments land far apart
  for (let k = slots.length - 1; k > 0; k--) {
    const j = Math.floor(rng() * (k + 1));
    [slots[k], slots[j]] = [slots[j], slots[k]];
  }
  idleSlots = slots;
}

function layoutIdle() {
  document.body.classList.remove("searching");
  for (const i of [...playingSet]) stop(i);
  let k = 0;
  for (const t of tiles) {
    if (wallSet.has(t.i) && k < idleSlots.length) {
      const s = idleSlots[k++];
      place(t, s.x, s.y, s.w / BASE_W, true, Math.floor(rng() * 120));
    } else {
      // park off-wall tiles somewhere plausible so they fly in from there later
      const s = idleSlots[t.i % idleSlots.length];
      place(t, s.x, s.y, (s.w / BASE_W) * 0.6, false);
    }
  }
}

// results: greedy packing along a golden-angle spiral around the search bar, best results nearest
function layoutResults(ranked, scores) {
  document.body.classList.add("searching");
  const W = innerWidth, H = innerHeight;
  const bar = barRect(14);
  const cx = W / 2, cy = H / 2;
  const top = ranked.slice(0, MAX_RESULTS);
  const M = top.length;
  const placed = [];
  const rects = [];
  const sizeFor = (r) => {
    const big = Math.min(250, W / 6.5);
    const small = Math.min(130, W / 12);
    const f = M <= 1 ? 0 : r / (M - 1);
    return big - (big - small) * Math.pow(f, 0.6) * (M > 12 ? 1 : M / 12);
  };
  let angle = rng() * Math.PI * 2;
  let radius = 60;
  for (let r = 0; r < M; r++) {
    const w = sizeFor(r), h = (w * 9) / 16;
    let ok = null;
    for (let tries = 0; tries < 900 && !ok; tries++) {
      angle += 2.39996; // golden angle
      radius += 1.1;
      const x = cx + Math.cos(angle) * radius * (W / H) * 0.8 - w / 2;
      const y = cy + Math.sin(angle) * radius - h / 2;
      const rect = { x, y, w, h };
      if (x < 6 || y < 6 || x + w > W - 6 || y + h > H - 34) continue;
      if (overlaps(rect, bar)) continue;
      if (rects.some((o) => overlaps(rect, o, Math.min(w, o.w) * 0.12))) continue;
      ok = rect;
    }
    if (!ok) break;
    rects.push(ok);
    placed.push([top[r], ok, r]);
    radius = Math.max(60, radius * 0.55); // pull back in so the next tile packs close to the bar
  }
  const shown = new Set();
  for (const [i, rect, r] of placed) {
    const t = tiles[i];
    t.el.querySelector(".score").textContent = scores[i].toFixed(2);
    t.el.classList.toggle("top", r < 12);
    place(t, rect.x, rect.y, rect.w / BASE_W, true, r * 7);
    shown.add(i);
  }
  for (const t of tiles) {
    if (!shown.has(t.i)) {
      // fade out and drift away from the centre
      const dx = t.x + (BASE_W * t.s) / 2 - cx, dy = t.y + (BASE_H * t.s) / 2 - cy;
      const d = Math.hypot(dx, dy) || 1;
      if (!t.el.classList.contains("hidden")) place(t, t.x + (dx / d) * 80, t.y + (dy / d) * 80, t.s * 0.85, false);
    }
  }
  const want = new Set(placed.slice(0, PLAYING).map(([i]) => i));
  for (const i of [...playingSet]) if (!want.has(i)) stop(i);
  for (const i of want) play(i);
}

// ------------------------------------------------------------------ search

let current = { q: "", result: null, live: null };
let qvecCache = new Map();
let embedQuery = null; // set once the embedding model loads

function renderChips(result, extra = "") {
  matched.innerHTML = "";
  if (!result) return;
  for (const c of result.clauses) {
    for (const { i } of c.concepts.slice(0, 2)) {
      const el = document.createElement("span");
      el.className = `chip ${C[i].kind}`;
      el.innerHTML = `<b>${c.neg ? "not " : ""}${C[i].kind}</b>${C[i].label}`;
      el.title = C[i].q;
      matched.appendChild(el);
    }
  }
  if (extra) matched.insertAdjacentHTML("beforeend", extra);
}

function runSearch() {
  const q = input.value;
  clearBtn.hidden = !q;
  const nq = norm(q);
  if (!nq) {
    current = { q: "", result: null, live: null };
    renderChips(null);
    layoutIdle();
    hudIdle();
    return;
  }
  const t0 = performance.now();
  const qvecs = {};
  for (const part of [nq, ...nq.split(/\s*(?:,|\band\b|\bwith\b|\bwhile\b|\bbut\b|\+)\s*/)]) {
    if (qvecCache.has(part)) qvecs[part] = qvecCache.get(part);
  }
  const result = searcher.search(q, qvecs);
  const ms = performance.now() - t0;
  current = { q: nq, result, live: null };
  if (!result.scores) {
    // nothing in the index matches (yet): keep whatever is on screen while the user keeps typing,
    // and offer the live search
    renderChips(result, `<span class="chip live"><b>enter ↵</b>ask Clef-omni live</span>`);
  } else {
    renderChips(result);
    layoutResults(result.ranked, result.scores);
  }
  if (result.scores) hudSearch(result.ranked.length, ms, result.clauses.reduce((n, c) => n + c.concepts.length, 0));

  // refine with embeddings for paraphrases the lexical matcher misses
  if (embedQuery) {
    const missing = [nq, ...nq.split(/\s*(?:,|\band\b|\bwith\b|\bwhile\b|\bbut\b|\+)\s*/)].filter((p) => p && !qvecCache.has(p));
    if (missing.length) {
      embedQuery(missing).then((vecs) => {
        missing.forEach((p, k) => qvecCache.set(p, vecs[k]));
        if (norm(input.value) === nq) runSearch();
      });
    }
  }
}

input.addEventListener("input", runSearch);
clearBtn.addEventListener("click", () => { input.value = ""; runSearch(); input.focus(); });
input.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { input.value = ""; runSearch(); }
  if (e.key === "Enter" && norm(input.value)) liveSearch(input.value);
});
addEventListener("resize", () => { computeIdleSlots(); runSearch(); });

// ------------------------------------------------------------------ live deep search (Enter)
// Asks Clef-omni the literal query, live, about the current candidates: the top indexed results,
// or the whole idle wall if the query matched nothing in the index. Results stream back as NDJSON.

async function liveSearch(q) {
  const nq = norm(q);
  const base = current.result && current.result.scores ? current.result.ranked.slice(0, 48) : [];
  const cand = base.length >= 12 ? base : [...new Set([...base, ...wallIds])].slice(0, 120);
  const live = new Float32Array(segs.length);
  const got = new Set();
  current.live = { q: nq, live, got };
  const t0 = performance.now();
  let n = 0, cachedN = 0, lastAt = t0;
  const draw = () => {
    const ranked = [...got].filter((i) => live[i] >= 0.5).sort((a, b) => live[b] - live[a]);
    const tag = cachedN && cachedN === n ? "cached" : "live";
    matched.innerHTML = `<span class="chip live"><b>${tag}</b>Clef-omni: “${escapeHtml(q)}” · ${n}/${cand.length} clips</span>`;
    layoutResults(ranked, live);
    hudSearch(ranked.length, lastAt - t0, cand.length, tag);
  };
  let pending = false;
  const schedule = () => { if (!pending) { pending = true; setTimeout(() => { pending = false; if (current.live && current.live.live === live) draw(); }, 120); } };
  draw();
  try {
    const res = await fetch("api/deep", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q, ids: cand.map((i) => segs[i].id) }),
    });
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    const byId = new Map(segs.map((s, i) => [s.id, i]));
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        const msg = JSON.parse(line);
        if (msg.done && msg.error && !n) {
          matched.innerHTML = `<span class="chip live"><b>live</b>${escapeHtml(msg.error)}</span>`;
          return;
        }
        if (msg.id && byId.has(msg.id)) {
          const i = byId.get(msg.id);
          live[i] = msg.p; got.add(i); n++;
          if (msg.cached) cachedN++;
          lastAt = performance.now();
          schedule();
        }
      }
    }
  } catch (err) {
    console.error(err);
  }
  if (current.live && current.live.live === live) draw();
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// ------------------------------------------------------------------ modal player

const modal = $("#modal"), player = $("#player");
function openModal(i) {
  const s = segs[i];
  const v = index.videos[s.video];
  player.src = `${v.raw}#t=${s.start}`;
  player.currentTime = s.start;
  player.muted = false;
  player.play().catch(() => {});
  $("#modal-title").textContent = v.title;
  const mm = Math.floor(s.start / 60), ss = String(Math.floor(s.start % 60)).padStart(2, "0");
  $("#modal-time").textContent = `${mm}:${ss} · segment ${s.id} · what Clef-omni saw, heard, and understood here:`;
  const row = index.p[i];
  const focus = new Set((current.result?.clauses || []).flatMap((c) => c.concepts.map((x) => x.i)));
  const yes = row.map((p, k) => [p, k]).filter(([p, k]) => p >= 800 || focus.has(k))
    .sort((a, b) => (focus.has(b[1]) - focus.has(a[1])) || b[0] - a[0]).slice(0, 18);
  $("#modal-why").innerHTML = yes.map(([p, k]) =>
    `<span class="chip ${C[k].kind}" title="${escapeHtml(C[k].q)}"><b>${C[k].kind}</b>${C[k].label} ${(p / 1000).toFixed(2)}</span>`).join("");
  modal.hidden = false;
}
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });
addEventListener("keydown", (e) => { if (e.key === "Escape" && !modal.hidden) closeModal(); });
function closeModal() { player.pause(); player.removeAttribute("src"); player.load(); modal.hidden = true; input.focus(); }

// ------------------------------------------------------------------ HUD

const totalMin = Math.round(Object.values(index.videos).reduce((a, v) => a + v.duration, 0) / 60);
function hudIdle() {
  hudL.innerHTML = `<b>${segs.length}</b> clips · <b>${totalMin}</b> min of video · <b>${stats.decisions.toLocaleString()}</b> Clef-omni decisions`;
  const took = stats.index_seconds ? `indexed in <b>${stats.index_seconds}s</b> for ` : "indexed for ";
  hudR.innerHTML = `${took}<b>$${stats.cost_usd}</b> · @cf/cloudflare/clef-omni on Workers AI`;
}
function hudSearch(n, ms, k, live = null) {
  hudL.innerHTML = `<b>${n}</b> matches of ${segs.length} clips`;
  if (live === "cached") hudR.innerHTML = `cached Clef-omni answers for ${k} clips`;
  else if (live) hudR.innerHTML = `asked Clef-omni about <b>${k}</b> clips in parallel · <b>${(ms / 1000).toFixed(1)}s</b>`;
  else hudR.innerHTML = `${k} concept${k === 1 ? "" : "s"} · search <b>${ms < 1 ? ms.toFixed(2) : ms.toFixed(1)} ms</b> · 0 API calls`;
}

// ------------------------------------------------------------------ boot

computeIdleSlots();
layoutIdle();
hudIdle();
requestAnimationFrame(() => document.body.classList.add("ready"));

// optional: semantic matching for paraphrases, fully in the browser (no API calls per keystroke)
(async () => {
  try {
    const worker = new Worker("embed-worker.js", { type: "module" });
    const waiting = new Map();
    let nextId = 0;
    worker.onmessage = ({ data }) => {
      const w = waiting.get(data.id);
      waiting.delete(data.id);
      if (w) data.error ? w.reject(new Error(data.error)) : w.resolve(data.vecs);
    };
    const embed = (texts) => new Promise((resolve, reject) => {
      const id = nextId++;
      waiting.set(id, { resolve, reject });
      worker.postMessage({ id, texts });
    });
    searcher.setEmbeddings(await embed(C.map((c) => searcher.embeddingText(c))));
    embedQuery = embed;
    console.log("embeddings ready");
    if (input.value) runSearch();
  } catch (err) {
    console.warn("embeddings unavailable, lexical search only", err);
  }
  autopilot();
})();

// ------------------------------------------------------------------ autopilot for recording
// ?demo=1 plays the default script; ?demo=hat|excited|!man wearing an orange cap plays a custom one.
// A leading "!" presses Enter at the end (live Clef-omni search). Start screen recording first;
// the script begins after a 3 s pause.

const DEMO = ["hat", "cloudflare shirt", "cloudflare mentioned", "excited", "durable objects",
  "code but no person", "carnival", "!man wearing an orange cap"];

async function autopilot() {
  const param = new URLSearchParams(location.search).get("demo");
  if (!param) return;
  const script = param === "1" ? DEMO : param.split("|");
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const typeText = async (text) => {
    for (const ch of text) {
      input.value += ch;
      runSearch();
      await sleep(85 + Math.random() * 70);
    }
  };
  const erase = async () => {
    while (input.value) {
      input.value = input.value.slice(0, -1);
      runSearch();
      await sleep(28);
    }
  };
  document.body.classList.add("demo");
  await sleep(3000);
  for (const item of script) {
    const live = item.startsWith("!");
    const q = live ? item.slice(1) : item;
    await typeText(q);
    if (live) {
      await sleep(600);
      liveSearch(q);
      await sleep(5500);
    } else {
      await sleep(2600);
    }
    await erase();
    await sleep(900);
  }
}
