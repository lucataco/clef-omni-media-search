"""Cut media/raw/*.mp4 into fixed-length segments for indexing and the search wall.

For every raw video this writes:
  media/segments/<video>_<nnn>.mp4   480p, 15 fps, mono AAC (what Clef-omni sees, and what tiles play)
  web/media/posters/<video>_<nnn>.jpg   poster frame from the middle of the segment
and a manifest at media/segments.json.

Usage: python ingest.py [--seconds 8] [--jobs 3] [--force]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "media" / "raw"
SEGMENTS = ROOT / "web" / "media" / "segments"
POSTERS = ROOT / "web" / "media" / "posters"
MANIFEST = ROOT / "media" / "segments.json"
MIN_TAIL_SECONDS = 3.0  # drop a final segment shorter than this


def ffprobe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,r_frame_rate,color_transfer,color_primaries",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def duration(path: Path) -> float:
    return float(ffprobe(path)["format"]["duration"])


def cut(video: Path, seconds: float, force: bool) -> list[dict]:
    vid = video.stem
    existing = sorted(SEGMENTS.glob(f"{vid}_*.mp4"))
    if force or not existing:
        for p in existing:
            p.unlink()
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(video),
             "-vf", "scale=-2:480,fps=15",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
             "-force_key_frames", f"expr:gte(t,n_forced*{seconds})",
             "-c:a", "aac", "-ac", "1", "-ar", "22050", "-b:a", "48k",
             "-f", "segment", "-segment_time", str(seconds), "-reset_timestamps", "1",
             "-movflags", "+faststart",
             str(SEGMENTS / f"{vid}_%03d.mp4")],
            check=True,
        )
    existing_posters = sorted(POSTERS.glob(f"{vid}_*.jpg"))
    if force or not existing_posters:
        for p in existing_posters:
            p.unlink()
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", str(seconds / 2), "-i", str(video),
             "-vf", f"fps=1/{seconds},scale=384:-2", "-q:v", "4", "-start_number", "0",
             str(POSTERS / f"{vid}_%03d.jpg")],
            check=True,
        )

    info_path = RAW / f"{vid}.info.json"
    info = json.loads(info_path.read_text()) if info_path.exists() else {}
    records = []
    for i, seg in enumerate(sorted(SEGMENTS.glob(f"{vid}_*.mp4"))):
        d = duration(seg)
        if d < MIN_TAIL_SECONDS:
            seg.unlink()
            continue
        sid = seg.stem
        poster = POSTERS / f"{sid}.jpg"
        if not poster.exists():  # poster fps filter can come up one frame short at the end
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(d / 2), "-i", str(seg),
                            "-frames:v", "1", "-vf", "scale=384:-2", "-q:v", "4", str(poster)], check=True)
        records.append({
            "id": sid,
            "video": vid,
            "title": info.get("title", vid),
            "index": i,
            "start": round(i * seconds, 3),
            "duration": round(d, 3),
            "clip": f"media/segments/{seg.name}",
            "poster": f"media/posters/{sid}.jpg",
            "bytes": seg.stat().st_size,
        })
    return records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    SEGMENTS.mkdir(parents=True, exist_ok=True)
    POSTERS.mkdir(parents=True, exist_ok=True)

    raws = sorted(RAW.glob("*.mp4"))
    videos = {}
    for raw in raws:
        meta = ffprobe(raw)
        info_path = RAW / f"{raw.stem}.info.json"
        info = json.loads(info_path.read_text()) if info_path.exists() else {}
        vstream = next(s for s in meta["streams"] if s["codec_type"] == "video")
        videos[raw.stem] = {
            "id": raw.stem,
            "title": info.get("title", raw.stem),
            "url": info.get("webpage_url"),
            "upload_date": info.get("upload_date"),
            "duration": float(meta["format"]["duration"]),
            "width": vstream.get("width"),
            "height": vstream.get("height"),
            "raw": f"media/raw/{raw.name}",
        }

    with ThreadPoolExecutor(args.jobs) as ex:
        results = list(ex.map(lambda r: cut(r, args.seconds, args.force), raws))
    segments = [s for group in results for s in group]
    MANIFEST.write_text(json.dumps({"seconds": args.seconds, "videos": videos, "segments": segments}, indent=1))
    total_mb = sum(s["bytes"] for s in segments) / 1e6
    print(f"{len(segments)} segments from {len(raws)} videos, {total_mb:.0f} MB -> {MANIFEST.relative_to(ROOT)}")
    big = [s for s in segments if s["bytes"] > 12e6]
    if big:
        print("WARNING: segments over 12 MB:", [s["id"] for s in big])

    index = ROOT / "web" / "data" / "index.json"
    if index.exists():
        indexed = {s["id"] for s in json.loads(index.read_text())["segments"]}
        cut = {s["id"] for s in segments}
        if indexed == cut:
            print("segments match the precomputed web/data/index.json: `python serve.py` is ready")
        else:
            print(f"web/data/index.json covers {len(indexed & cut)} of these {len(cut)} segments "
                  f"({len(indexed - cut)} indexed segments are missing): run `python classify.py` to index them")


if __name__ == "__main__":
    main()
