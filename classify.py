"""Ask Clef-omni (Workers AI) every concept in concepts.py about every segment.

Concepts are sent in chunks of 64 questions (the API maximum) per request. Every finished
request is appended to media/answers.jsonl, so the run can be stopped and resumed; editing a
concept only re-runs the chunk it is in. The search UI reads web/data/index.json.

Needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN (environment or .env). Set
CLOUDFLARE_AI_GATEWAY to route through an AI Gateway, e.g. to bill prepaid credits.

Usage:
  python classify.py                  # index everything that is missing, then build the index
  python classify.py --limit 6        # only the first N segments (spot checks)
  python classify.py --ids a_001,b_002
  python classify.py --build-only     # rebuild web/data/index.json from the cache
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from concepts import CONCEPTS

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "media" / "segments.json"
CACHE = ROOT / "media" / "answers.jsonl"
RUNS = ROOT / "media" / "index_runs.jsonl"  # wall-clock time of each indexing run
INDEX = ROOT / "web" / "data" / "index.json"
CHUNK = 64
PRICE_PER_M = 0.15
STATE = "An 8-second segment from a developer video. Judge only what is seen and heard in this segment."


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            k, _, v = line.strip().partition("=")
            if k and v and not k.startswith("#"):
                os.environ.setdefault(k, v)


def chunks() -> list[tuple[str, list[dict]]]:
    out = []
    for i in range(0, len(CONCEPTS), CHUNK):
        group = CONCEPTS[i : i + CHUNK]
        key = hashlib.sha1(json.dumps([(c["id"], c["q"]) for c in group]).encode()).hexdigest()[:12]
        out.append((key, group))
    return out


def load_cache() -> dict[tuple[str, str], dict]:
    done = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r["seg"], r["chunk"])] = r
    return done


class Client:
    MODEL = "@cf/cloudflare/clef-omni"

    def __init__(self):
        load_env()
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        token = os.environ.get("CLOUDFLARE_API_TOKEN")
        if not account or not token:
            raise SystemExit("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN (see .env.example)")
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{self.MODEL}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # Cloudflare's bot protection rejects the default python-requests user agent
            "User-Agent": "clef-omni-media-search/1.0",
        }
        gateway = os.environ.get("CLOUDFLARE_AI_GATEWAY")
        if gateway:
            # Workers AI REST calls are routed through AI Gateway by this header
            self.headers["cf-aig-gateway-id"] = gateway
        self.local = threading.local()

    def session(self) -> requests.Session:
        if not hasattr(self.local, "s"):
            self.local.s = requests.Session()
        return self.local.s

    def run(self, body: dict, timeout: float = 25.0, attempts: int = 6, backoff: float = 1.5) -> tuple[dict, float]:
        data = json.dumps(body)
        for attempt in range(attempts):
            t = time.perf_counter()
            try:
                r = self.session().post(self.url, data=data, headers=self.headers, timeout=timeout)
                if r.status_code == 200:
                    out = r.json()
                    if out.get("success"):
                        return out["result"], time.perf_counter() - t
                    err = out.get("errors")
                elif r.status_code in (429, 500, 502, 503, 504, 524):
                    err = f"HTTP {r.status_code}"
                else:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            except (requests.Timeout, requests.ConnectionError) as e:
                err = type(e).__name__
            if attempt < attempts - 1:
                time.sleep(min(30, backoff * 2**attempt) * (0.5 + random.random()))
        raise RuntimeError(f"gave up after {attempts} attempts: {err}")


def classify(limit: int | None, workers: int, ids: list[str] | None = None) -> None:
    manifest = json.loads(MANIFEST.read_text())
    segments = manifest["segments"][:limit] if limit else manifest["segments"]
    if ids:
        segments = [s for s in manifest["segments"] if s["id"] in ids]
    groups = chunks()
    done = load_cache()
    todo = [(s, key, group) for s in segments for key, group in groups if (s["id"], key) not in done]
    print(f"{len(segments)} segments x {len(groups)} chunks: {len(todo)} requests to run, {len(done)} cached")
    if not todo:
        return

    client = Client()
    video_cache: dict[str, str] = {}
    lock = threading.Lock()

    def video_b64(seg: dict) -> str:
        with lock:
            if seg["id"] not in video_cache:
                raw = (ROOT / "web" / seg["clip"]).read_bytes()
                video_cache[seg["id"]] = "data:video/mp4;base64," + base64.b64encode(raw).decode()
            return video_cache[seg["id"]]

    def job(seg, key, group):
        body = {
            "model": "clef-omni",
            "state": STATE,
            "videos": [video_b64(seg)],
            "questions": {c["id"]: {"type": "noul", "instructions": c["q"]} for c in group},
        }
        result, dt = client.run(body)
        answers = {cid: a["noul"] for cid, a in result["answers"].items()}
        return {"seg": seg["id"], "chunk": key, "answers": answers,
                "tokens": result.get("usage", {}).get("input_tokens", 0), "ms": round(dt * 1000)}

    t0 = time.perf_counter()
    n = tokens = failed = 0
    with CACHE.open("a") as f, ThreadPoolExecutor(workers) as ex:
        futures = [ex.submit(job, *t) for t in todo]
        for fut in as_completed(futures):
            try:
                rec = fut.result()
            except Exception as e:  # keep going; a re-run picks up whatever failed
                failed += 1
                print("  failed:", e)
                continue
            f.write(json.dumps(rec) + "\n")
            f.flush()
            n += 1
            tokens += rec["tokens"]
            if n % 50 == 0 or n == len(todo):
                el = time.perf_counter() - t0
                print(f"  {n}/{len(todo)}  {n / el:.1f} req/s  {tokens / 1e6:.2f}M tokens  ${tokens * PRICE_PER_M / 1e6:.2f}")
    elapsed = time.perf_counter() - t0
    print(f"done: {n} ok, {failed} failed in {elapsed:.0f}s")
    with RUNS.open("a") as f:
        f.write(json.dumps({"requests": n, "seconds": round(elapsed, 1), "tokens": tokens}) + "\n")


def build() -> None:
    manifest = json.loads(MANIFEST.read_text())
    groups = chunks()
    done = load_cache()
    keys = {key for key, _ in groups}

    # Segments not in the local cache keep their rows from the existing index (e.g. the precomputed
    # one shipped with the repo), as long as it was built from the same questions.
    old_rows, old_stats = {}, {}
    if INDEX.exists():
        old = json.loads(INDEX.read_text())
        if [(c["id"], c["q"]) for c in old["concepts"]] == [(c["id"], c["q"]) for c in CONCEPTS]:
            old_rows = {s["id"]: r for s, r in zip(old["segments"], old["p"])}
            old_stats = old.get("stats", {})

    segs, rows = [], []
    tokens = carried = 0
    for s in manifest["segments"]:
        recs = [done.get((s["id"], key)) for key in keys]
        if all(recs):
            answers = {}
            for r in recs:
                answers.update(r["answers"])
                tokens += r["tokens"]
            row = [round(answers[c["id"]] * 1000) for c in CONCEPTS]
        elif s["id"] in old_rows:
            row = old_rows[s["id"]]
            carried += 1
        else:
            continue
        segs.append({k: s[k] for k in ("id", "video", "start", "duration", "clip", "poster")})
        rows.append(row)

    seconds = sum(json.loads(l)["seconds"] for l in RUNS.read_text().splitlines() if l.strip()) if RUNS.exists() else 0
    if carried and old_stats.get("segments"):
        share = carried / old_stats["segments"]
        tokens += round(old_stats.get("tokens", 0) * share)
        seconds += (old_stats.get("index_seconds") or 0) * share
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    videos = {k: {f: v[f] for f in ("title", "url", "duration", "raw")} for k, v in manifest["videos"].items()}
    if carried:
        print(f"kept {carried} segments from the existing index (not in media/answers.jsonl)")
    INDEX.write_text(json.dumps({
        "model": "@cf/cloudflare/clef-omni",
        "segment_seconds": manifest["seconds"],
        "concepts": [{k: c[k] for k in ("id", "kind", "label", "syn", "q")} for c in CONCEPTS],
        "videos": videos,
        "segments": segs,
        "p": rows,  # p[segment][concept] = P(yes) * 1000
        "stats": {"segments": len(segs), "decisions": len(segs) * len(CONCEPTS),
                  "tokens": tokens, "cost_usd": round(tokens * PRICE_PER_M / 1e6, 2),
                  "index_seconds": round(seconds) or None},
    }, separators=(",", ":")))
    print(f"index: {len(segs)} segments x {len(CONCEPTS)} concepts -> {INDEX.relative_to(ROOT)} "
          f"({INDEX.stat().st_size / 1e3:.0f} KB), {tokens / 1e6:.2f}M tokens, ${tokens * PRICE_PER_M / 1e6:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--ids", help="comma-separated segment ids to index")
    ap.add_argument("--build-only", action="store_true")
    args = ap.parse_args()
    if not MANIFEST.exists():
        raise SystemExit("media/segments.json not found: run `python download.py` and `python ingest.py` first")
    if not args.build_only:
        classify(args.limit, args.workers, args.ids.split(",") if args.ids else None)
    build()


if __name__ == "__main__":
    main()
