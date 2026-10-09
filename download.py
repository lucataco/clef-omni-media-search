"""Download the source videos into media/raw/ with yt-dlp.

By default this fetches the 9 Cloudflare Developers videos the precomputed index was built from,
so `python ingest.py` reproduces the same 523 segments. Pass your own YouTube URLs or IDs to
build a library from other videos (then run `python classify.py` to index them).

Usage:
  python download.py                 # the 9 demo videos (~450 MB)
  python download.py <url-or-id> ... # your own videos
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "media" / "raw"

# The 9 most recent uploads on youtube.com/@CloudflareDevelopers as of October 2026
DEMO_VIDEOS = [
    "_BYvVd3teII",  # Cloudflare Artifacts Is in Open Beta: Here's What It Does
    "-F-fklPPiec",  # Meet cf (cli) and cloudflare.config.ts: A New Way to Build
    "tefsW9lgwTM",  # Cloudflare Worker Previews Are Here! Here's How They Work
    "m0c9SArzec0",  # How to Create an AI Powered Blog Writer with Flue
    "fUmK9yhDpHo",  # Real time Updates Using Workflows and Durable Objects
    "eTa8TPxkvMY",  # The Cloudflare API MCP in Under 3 Minutes
    "gO6eRAhzjss",  # Your Website Looks AI-Generated. Here's Why. Can Flue Agents Provide the Cure?
    "7CCoBvbluHA",  # Run your Python code in an isolate instead of a Container
    "mBb3GYR_nOk",  # Introducing Dial-a-Repo
]


def main() -> None:
    if not shutil.which("yt-dlp"):
        raise SystemExit("yt-dlp not found: install it with `brew install yt-dlp` or `pip install yt-dlp`")
    RAW.mkdir(parents=True, exist_ok=True)
    videos = sys.argv[1:] or DEMO_VIDEOS
    urls = [v if v.startswith("http") else f"https://www.youtube.com/watch?v={v}" for v in videos]
    subprocess.run(
        ["yt-dlp",
         "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b",
         "--merge-output-format", "mp4",
         "--write-info-json", "--no-playlist", "--no-progress",
         "-o", str(RAW / "%(id)s.%(ext)s"),
         *urls],
        check=True,
    )
    print(f"{len(list(RAW.glob('*.mp4')))} videos in {RAW.relative_to(ROOT)}; next: python ingest.py")


if __name__ == "__main__":
    main()
