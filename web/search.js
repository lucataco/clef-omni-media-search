// Query -> concepts -> ranked segments. Pure functions, no DOM, so it also runs under node for tests.
//
// A query is split into clauses ("hat and talking", "code but no person"). Each clause resolves to
// the 1-3 concepts whose label/synonyms match it best (lexically, plus embeddings when available).
// A segment's clause score is the best P(yes) among those concepts; clauses combine as a geometric
// mean (AND), and negated clauses use 1 - P.

const STOP = new Set(("a an the of in on is are was with someone something somebody video videos clip clips " +
  "segment segments show me where who that to for at by find any some there this it its from be being " +
  "person's guy's").split(" "));
const NEG = /^(no|not|without|nobody|noone|no one|non|never)\b\s*/;
const SPLIT = /\s*(?:,|\band\b|\bwith\b|\bwhile\b|\bbut\b|\+)\s*/;
// phrasing that says which sense should answer: "talks about X", "X on screen", "sound of X"
const HINTS = [
  { kind: "say", re: /^(?:(?:someone|people|they|he|she|speaker)\s+)?(?:talk(?:s|ing|ed)?|speak(?:s|ing)?|discuss(?:es|ing|ed)?|mention(?:s|ing|ed)?|say(?:s|ing)?|said)\s+(?:about\s+|the\s+word\s+)?/ },
  { kind: "say", re: /\s+(?:mentioned|mentions|discussed|talk|said|spoken)$/ },
  { kind: "hear", re: /^(?:(?:the\s+)?sound\s+of|hear(?:ing)?|audio\s+of)\s+/ },
  { kind: "hear", re: /\s+(?:sound|sounds|audio|noise)$/ },
  { kind: "see", re: /\s+(?:on\s+screen|visible|shown|in\s+frame)$/ },
  { kind: "see", re: /^(?:showing|shows|see|seeing)\s+/ },
];

export function norm(s) {
  return s.toLowerCase().replace(/[“”"]/g, "").replace(/[^a-z0-9.\-'/ ]+/g, " ").replace(/\s+/g, " ").trim();
}

function stem(w) {
  if (w.length > 4) return w.replace(/(ing|ers|er|ed|es|s)$/, "");
  return w;
}

function tokens(s) {
  return norm(s).split(" ").filter((w) => w && !STOP.has(w)).map(stem);
}

export class Searcher {
  constructor(index) {
    this.concepts = index.concepts;
    this.p = index.p;
    this.segments = index.segments;
    this.terms = this.concepts.map((c) => {
      const all = [c.label, ...c.syn].map(norm).filter(Boolean);
      return all.map((t) => ({ t, tok: tokens(t) }));
    });
    this.vecs = null; // Float32Array[] (unit vectors), set by setEmbeddings
  }

  setEmbeddings(vecs) {
    this.vecs = vecs;
  }

  embeddingText(c) {
    return `${c.label}: ${c.syn.slice(0, 8).join(", ")}`;
  }

  // -> [{i, m}] sorted by match strength m in [0, 1]
  match(q, qvec = null) {
    q = norm(q);
    if (!q) return [];
    const qtok = tokens(q);
    const out = [];
    for (let i = 0; i < this.concepts.length; i++) {
      let m = 0;
      for (const { t, tok } of this.terms[i]) {
        if (t === q) { m = 1; break; }
        if (q.length >= 2 && t.startsWith(q)) m = Math.max(m, 0.8 + 0.15 * (q.length / t.length));
        if (t.length >= 3 && (" " + q + " ").includes(" " + t + " ")) m = Math.max(m, 0.55 + 0.4 * (t.length / q.length));
        if (qtok.length && tok.length) {
          let inter = 0;
          for (const w of qtok) if (tok.includes(w)) inter++;
          if (inter) m = Math.max(m, 0.8 * inter / Math.max(qtok.length, tok.length));
        }
      }
      if (qvec && this.vecs) {
        let dot = 0;
        const v = this.vecs[i];
        for (let k = 0; k < v.length; k++) dot += v[k] * qvec[k];
        m = Math.max(m, 0.95 * Math.min(1, Math.max(0, (dot - 0.42) / 0.33)));
      }
      if (m > 0) out.push({ i, m });
    }
    out.sort((a, b) => b.m - a.m);
    return out;
  }

  resolveClause(text, qvec) {
    let neg = false;
    let t = norm(text);
    const nm = t.match(NEG);
    if (nm) { neg = true; t = t.slice(nm[0].length); }
    // exact concept label wins before hint stripping ("cloudflare mentioned" is itself a label)
    let cands = this.match(t, neg ? null : qvec);
    if (!(cands.length && cands[0].m === 1)) {
      for (const h of HINTS) {
        const stripped = t.replace(h.re, "");
        if (stripped !== t && stripped) {
          const kindOf = (i) => this.concepts[i].kind;
          cands = this.match(stripped, null)
            .map(({ i, m }) => ({ i, m: kindOf(i) === h.kind || kindOf(i) === "both" ? m : m * 0.55 }))
            .sort((a, b) => b.m - a.m);
          t = stripped;
          break;
        }
      }
    }
    const best = cands.length ? cands[0].m : 0;
    if (best < 0.45) return { text: t, neg, concepts: [] };
    const concepts = cands.filter((c) => c.m >= Math.max(0.45, best - 0.12)).slice(0, 3);
    return { text: t, neg, concepts };
  }

  // qvecs: optional {wholeQueryText: Float32Array} map of embeddings
  search(query, qvecs = {}) {
    const q = norm(query);
    const n = this.segments.length;
    if (!q) return { clauses: [], scores: null, ranked: [] };

    // whole query first: concept labels/synonyms can themselves contain "and"/"no" ("talking, no code")
    let clauses = [this.resolveClause(q, qvecs[q])];
    const whole = clauses[0];
    const wholeBest = whole.concepts.length ? whole.concepts[0].m : 0;
    const parts = q.split(SPLIT).filter(Boolean);
    if ((parts.length > 1 || NEG.test(q)) && wholeBest < 0.9) {
      const split = parts.map((p) => this.resolveClause(p, qvecs[norm(p)]));
      if (split.some((c) => c.concepts.length)) clauses = split;
    }
    const used = clauses.filter((c) => c.concepts.length);
    if (!used.length) return { clauses, scores: null, ranked: [] };

    const scores = new Float32Array(n);
    for (let s = 0; s < n; s++) {
      const row = this.p[s];
      let logsum = 0;
      for (const c of used) {
        const top = c.concepts[0].m;
        let v = 0;
        for (const { i, m } of c.concepts) v = Math.max(v, (row[i] / 1000) * Math.pow(m / top, 2));
        if (c.neg) v = 1 - v;
        logsum += Math.log(Math.max(v, 1e-4));
      }
      scores[s] = Math.exp(logsum / used.length);
    }
    const ranked = [];
    for (let s = 0; s < n; s++) if (scores[s] >= 0.5) ranked.push(s);
    ranked.sort((a, b) => scores[b] - scores[a]);
    return { clauses, scores, ranked };
  }
}
