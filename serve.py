"""Local server for the media-search demo.

  GET  /                 the search UI (web/)
  GET  /media/raw/...    full source videos for the player (with Range support for seeking)
  POST /api/deep         live Clef-omni search: {"q": "...", "ids": [segment ids]} -> NDJSON stream

Typed search runs entirely in the browser against web/data/index.json. Only the live search
(press Enter) calls Clef-omni, and it needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN.

Usage: python serve.py [--port 8790]
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from classify import Client

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
RAW = ROOT / "media" / "raw"
MANIFEST = ROOT / "media" / "segments.json"
DEEP_CACHE = ROOT / "media" / "deep.jsonl"
DEADLINE = 6.0        # seconds; stragglers after this are dropped from a live search
REQUEST_TIMEOUT = 4.5
WORKERS = 48

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("video/mp4", ".mp4")

if not MANIFEST.exists():
    raise SystemExit("media/segments.json not found: run `python download.py` and `python ingest.py` first")
segments = {s["id"]: s for s in json.loads(MANIFEST.read_text())["segments"]}
try:
    client = Client()
except SystemExit as e:
    client = None
    print(f"live search disabled: {e}", flush=True)
pool = ThreadPoolExecutor(WORKERS)
b64_cache: dict[str, str] = {}
deep_cache: dict[tuple[str, str], float] = {}
lock = threading.Lock()
if DEEP_CACHE.exists():
    for line in DEEP_CACHE.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            deep_cache[(r["q"], r["id"])] = r["p"]


def video_b64(sid: str) -> str:
    with lock:
        if sid not in b64_cache:
            raw = (WEB / segments[sid]["clip"]).read_bytes()
            b64_cache[sid] = "data:video/mp4;base64," + base64.b64encode(raw).decode()
        return b64_cache[sid]


def ask(q: str, sid: str) -> float:
    body = {
        "model": "clef-omni",
        "state": "An 8-second segment from a developer video. Judge only what is seen and heard in this segment.",
        "videos": [video_b64(sid)],
        "questions": {"match": {
            "type": "noul",
            "instructions": f"Does this segment match the search query \"{q}\"? Consider what is shown on screen, "
                            "what can be heard, and what is said.",
        }},
    }
    result, _ = client.run(body, timeout=REQUEST_TIMEOUT, attempts=2, backoff=0.25)
    return result["answers"]["match"]["noul"]


class Handler(BaseHTTPRequestHandler):
    server_version = "clef-media-search"

    def log_message(self, fmt, *args):
        if not self.path.startswith(("/media/", "/data/")):
            super().log_message(fmt, *args)

    # ---------------------------------------------------------------- static
    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            path = "/index.html"
        base, rel = (RAW, path[len("/media/raw/"):]) if path.startswith("/media/raw/") else (WEB, path.lstrip("/"))
        file = (base / rel).resolve()
        if not str(file).startswith(str(base.resolve())) or not file.is_file():
            self.send_error(404)
            return
        size = file.stat().st_size
        ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        m = re.match(r"bytes=(\d*)-(\d*)", rng or "")
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start, end = size - int(m.group(2)), size - 1
            end = min(end, size - 1)
            if start > end:
                self.send_error(416)
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            start, end = 0, size - 1
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache" if file.suffix in (".html", ".js", ".css", ".json") else "max-age=3600")
        self.end_headers()
        try:
            with file.open("rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---------------------------------------------------------------- live search
    def do_POST(self):
        if urlparse(self.path).path != "/api/deep":
            self.send_error(404)
            return
        # Live search spends API credits, so only accept it from this page: a JSON content type forces
        # a CORS preflight (which this server never approves) for cross-site requests, and the Host
        # check blocks DNS rebinding.
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host not in ("127.0.0.1", "localhost", self.server.server_address[0]) or \
                not (self.headers.get("Content-Type") or "").startswith("application/json"):
            self.send_error(403)
            return
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        q = " ".join(str(req.get("q", "")).split())[:200]
        ids = [i for i in req.get("ids", []) if i in segments][:200]
        if not q or not ids:
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def emit(obj):
            self.wfile.write((json.dumps(obj) + "\n").encode())
            self.wfile.flush()

        t0 = time.perf_counter()
        key = q.lower()
        try:
            todo = []
            for sid in ids:
                if (key, sid) in deep_cache:
                    emit({"id": sid, "p": deep_cache[(key, sid)], "cached": True})
                else:
                    todo.append(sid)
            ok = dropped = 0
            n_cached = len(ids) - len(todo)
            first_error = None
            if client is None and todo:
                first_error = "live search needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN"
                dropped, todo = len(todo), []
            futures = {pool.submit(ask, q, sid): sid for sid in todo}
            with DEEP_CACHE.open("a") as log:
                try:
                    for fut in as_completed(futures, timeout=max(0.5, DEADLINE - (time.perf_counter() - t0))):
                        sid = futures[fut]
                        try:
                            p = fut.result()
                        except Exception as e:
                            dropped += 1
                            first_error = first_error or f"{type(e).__name__}: {e}"[:300]
                            continue
                        deep_cache[(key, sid)] = p
                        log.write(json.dumps({"q": key, "id": sid, "p": p}) + "\n")
                        emit({"id": sid, "p": p})
                        ok += 1
                except TimeoutError:
                    dropped += sum(1 for f in futures if not f.done())
            emit({"done": True, "ok": ok, "cached": n_cached, "dropped": dropped,
                  "seconds": round(time.perf_counter() - t0, 2), "error": first_error})
            self.log_message("live %r: %d asked, %d cached, %d dropped, %.2fs %s", q, len(todo), n_cached,
                             dropped, time.perf_counter() - t0, first_error or "")
        except (BrokenPipeError, ConnectionResetError):
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8790)
    args = ap.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
