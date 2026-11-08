#!/usr/bin/env python3
"""VisionClipper agent helper.

Non-interactive, JSON-output wrapper around ``backend.worker`` so AI agents
(Claude, Hermes, GPT/Codex, Copilot, ...) can drive the clipper without the
web dashboard.

Contract:
  * stdout -> exactly ONE JSON object per invocation.
  * stderr -> progress logs (worker log lines by default; see --verbose/--quiet).
  * exit 0 on success, 1 on failure (JSON then has "ok": false + "error").

Commands: doctor | analyze | render | auto | clips
Run ``vclip.py <command> -h`` for options.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

RESULT_MARKER = "[ANALYSIS_RESULT]"
SUB_STYLES = ["tiktok_viral", "classic_karaoke", "minimalist", "word_pop", "no_subtitle", "none"]
FRAMING_MODES = ["smart_crop", "fit_blur", "split_screen"]
DEFAULT_LLM_MODEL = "google/gemini-2.0-flash-exp:free"
WORKER_LOG_RE = re.compile(r"^\[\d{2}:\d{2}:\d{2}\] ")
METADATA_HEADINGS = {
    "Title Options": "title_options",
    "Hook": "hook",
    "Caption": "caption",
    "Hashtags": "hashtags",
    "First Comment": "first_comment",
    "Series": "series",
}

LOG_MODE = "normal"  # normal | verbose | quiet


# ── Output helpers ──────────────────────────────────────────────────────────
def emit(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(code)


def fail(message: str, **extra) -> None:
    emit({"ok": False, "error": message, **extra}, 1)


def info(message: str) -> None:
    if LOG_MODE != "quiet":
        print(f"[vclip] {message}", file=sys.stderr, flush=True)


# ── Environment discovery ───────────────────────────────────────────────────
def project_root() -> Path:
    env_home = os.environ.get("VISION_CLIPPER_HOME")
    if env_home:
        root = Path(env_home).expanduser().resolve()
        if (root / "backend" / "worker.py").is_file():
            return root
        fail(f"VISION_CLIPPER_HOME={root} does not contain backend/worker.py")
    # resolve() follows symlinks, so a skill symlinked into ~/.claude/skills
    # still finds the real project.
    for parent in Path(__file__).resolve().parents:
        if (parent / "backend" / "worker.py").is_file():
            return parent
    fail(
        "Cannot locate the VisionClipper project. "
        "Set VISION_CLIPPER_HOME=/absolute/path/to/vision-clipper."
    )
    raise AssertionError  # unreachable


def python_exe(root: Path) -> str:
    for candidate in (root / ".venv" / "bin" / "python", root / ".venv" / "Scripts" / "python.exe"):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def read_env_file(root: Path) -> dict:
    values: dict = {}
    env_path = root / ".env"
    if not env_path.is_file():
        return values
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _is_real_secret(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip()
    return bool(v) and not v.startswith(("sk-xxxx", "gsk_xxxx"))


# ── Worker runner ───────────────────────────────────────────────────────────
def run_worker(root: Path, worker_args: list[str]) -> tuple[int, dict | None, list[str]]:
    cmd = [python_exe(root), "-u", "-m", "backend.worker", *worker_args]
    tail: deque = deque(maxlen=40)
    result = None
    proc = subprocess.Popen(
        cmd,
        cwd=str(root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\r\n")
            if not line:
                continue
            marker_at = line.find(RESULT_MARKER)
            if marker_at != -1:
                try:
                    result = json.loads(line[marker_at + len(RESULT_MARKER):])
                except json.JSONDecodeError as e:
                    tail.append(f"Failed to parse analysis JSON: {e}")
                continue
            tail.append(line)
            if LOG_MODE == "verbose" or (LOG_MODE == "normal" and WORKER_LOG_RE.match(line)):
                print(line, file=sys.stderr, flush=True)
        code = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        fail("Interrupted by user", log_tail=list(tail))
        raise AssertionError  # unreachable
    return code, result, list(tail)


# ── Analysis helpers ────────────────────────────────────────────────────────
def summarize_clip(clip: dict) -> dict:
    titles = clip.get("title_options") or [clip.get("title", "Untitled")]
    if not isinstance(titles, list):
        titles = [str(titles)]
    start = float(clip.get("start", 0) or 0)
    end = float(clip.get("end", 0) or 0)
    return {
        "index": clip.get("index"),
        "title": titles[0] if titles else clip.get("title"),
        "title_options": titles,
        "start": start,
        "end": end,
        "duration": clip.get("duration", round(end - start, 2)),
        "viral_score": clip.get("viral_score"),
        "hook_line": clip.get("hook_line"),
        "reason": clip.get("reason") or clip.get("viral_reason"),
        "caption": clip.get("caption"),
        "hashtags": clip.get("hashtags"),
    }


def resolve_analysis(root: Path, ref: str) -> Path:
    temp_dir = root / "temp"
    if ref == "latest":
        candidates = sorted(temp_dir.glob("analysis_*.json"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            fail("No analysis file found in temp/. Run `analyze` first.")
        return candidates[-1]
    if re.fullmatch(r"analysis_\d+", ref):
        path = temp_dir / f"{ref}.json"
    else:
        path = Path(ref).expanduser()
    if not path.is_file():
        fail(f"Analysis file not found: {path}")
    return path.resolve()


def parse_indices(raw: str, clip_count: int) -> list[int]:
    if raw.strip().lower() == "all":
        return list(range(1, clip_count + 1))
    try:
        indices = [int(v.strip()) for v in raw.split(",") if v.strip()]
    except ValueError:
        fail("--clips must be 'all' or comma-separated integers, e.g. 1,3,4")
    if not indices:
        fail("Select at least one clip index.")
    if len(set(indices)) != len(indices):
        fail("--clips must not contain duplicates.")
    bad = [i for i in indices if i < 1 or i > clip_count]
    if bad:
        fail(f"Clip indices out of range 1..{clip_count}: {bad}")
    return indices


def parse_metadata(txt_path: Path) -> dict:
    if not txt_path.is_file():
        return {}
    sections: dict = {}
    current = None
    for line in txt_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1] in METADATA_HEADINGS:
            current = METADATA_HEADINGS[stripped[:-1]]
            sections[current] = []
            continue
        if current:
            sections[current].append(line)
    out: dict = {key: "\n".join(lines).strip() for key, lines in sections.items()}
    if "title_options" in out:
        out["title_options"] = [
            l.strip().lstrip("-").strip() for l in out["title_options"].splitlines() if l.strip()
        ]
    if "hashtags" in out:
        out["hashtags"] = out["hashtags"].split()
    return out


def describe_clip_file(mp4: Path) -> dict:
    txt = mp4.with_suffix(".txt")
    return {
        "video_path": str(mp4.resolve()),
        "metadata_path": str(txt.resolve()) if txt.is_file() else None,
        "size_bytes": mp4.stat().st_size,
        "metadata": parse_metadata(txt),
    }


def collect_rendered(out_dir: Path, indices: list[int]) -> list[dict]:
    rendered = []
    for idx in indices:
        matches = [p for p in out_dir.glob(f"{idx:02d}_*.mp4") if p.is_file()]
        if not matches:
            rendered.append({"index": idx, "video_path": None})
            continue
        newest = max(matches, key=lambda p: p.stat().st_mtime)
        rendered.append({"index": idx, **describe_clip_file(newest)})
    return rendered


# ── Commands ────────────────────────────────────────────────────────────────
def cmd_doctor(args) -> None:
    root = project_root()
    env = read_env_file(root)

    def val(key: str) -> str | None:
        return env.get(key) or os.environ.get(key)

    py = python_exe(root)
    checks = {
        "project_root": str(root),
        "python": py,
        "venv": ".venv" in py,
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "env_file": (root / ".env").is_file(),
        "llm_endpoint_set": bool(val("ROUTER_API_ENDPOINT")),
        "llm_api_key_set": _is_real_secret(val("ROUTER_API_KEY")),
        "llm_model": val("ROUTER_LLM_MODEL") or DEFAULT_LLM_MODEL,
        "groq_api_key_set": _is_real_secret(val("GROQ_API_KEY")),
        "cookies_txt": (root / "cookies.txt").is_file(),
        "frontend_built": (root / "frontend" / "dist" / "index.html").is_file(),
    }
    problems = []
    if not checks["ffmpeg"]:
        problems.append("FFmpeg not found on PATH.")
    if not checks["venv"]:
        problems.append("No .venv found; run `vision-clipper install` (or scripts/install_*.sh).")
    if not checks["llm_endpoint_set"] or not checks["llm_api_key_set"]:
        problems.append("LLM endpoint/API key missing; ask the user to run `vision-clipper config`.")
    if not checks["groq_api_key_set"]:
        problems.append("GROQ_API_KEY missing; transcription will fail.")
    emit({"ok": not problems, "checks": checks, "problems": problems}, 0 if not problems else 1)


def do_analyze(root: Path, args) -> dict:
    if not 1 <= args.num_clips <= 10:
        fail("--num-clips must be between 1 and 10")
    worker_args = [
        "--file", args.source,
        "--num-clips", str(args.num_clips),
        "--mode", args.mode,
        "--source-lang", args.lang,
        "--analyze-only",
    ]
    if args.single_pass:
        worker_args.append("--single-pass")
    info(f"Analyzing {args.source} (mode={args.mode}, clips={args.num_clips}, lang={args.lang})")
    code, result, tail = run_worker(root, worker_args)
    if code != 0 or not result:
        fail("Analysis failed.", exit_code=code, log_tail=tail)

    analysis_id = f"analysis_{int(time.time() * 1000)}"
    result["analysis_id"] = analysis_id
    temp_dir = root / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = temp_dir / f"{analysis_id}.json"
    analysis_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    return {
        "ok": True,
        "analysis_id": analysis_id,
        "analysis_path": str(analysis_path),
        "video_path": result.get("video_path"),
        "output_dir": result.get("output_dir"),
        "mode": result.get("mode"),
        "clips": [summarize_clip(c) for c in result.get("clips", [])],
    }


def do_render(root: Path, analysis_path: Path, args) -> dict:
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    clips = analysis.get("clips") or []
    video_path = analysis.get("video_path")
    out_dir = analysis.get("output_dir")
    if not isinstance(clips, list) or not clips or not video_path or not out_dir:
        fail(f"Analysis file is invalid or empty: {analysis_path}")

    indices = parse_indices(args.clips, len(clips))
    sub_position = max(30, min(85, int(args.sub_position)))
    worker_args = [
        "--file", video_path,
        "--clips-json", str(analysis_path),
        "--render-indices", ",".join(str(i) for i in indices),
        "--sub-style", args.sub_style,
        "--framing-mode", args.framing,
        "--sub-position", str(sub_position),
        "--no-watermark" if args.no_watermark else "--watermark-enabled",
    ]
    if args.source_watermark:
        worker_args += ["--source-watermark", args.source_watermark]
    if args.account_watermark:
        worker_args += ["--account-watermark", args.account_watermark]

    info(f"Rendering clips {indices} -> {out_dir}")
    code, _, tail = run_worker(root, worker_args)
    rendered = collect_rendered(Path(out_dir), indices)
    payload = {
        "ok": code == 0,
        "analysis_path": str(analysis_path),
        "output_dir": out_dir,
        "rendered": rendered,
    }
    if code != 0:
        payload.update({"error": "Render failed for one or more clips.", "exit_code": code, "log_tail": tail})
    return payload


def cmd_analyze(args) -> None:
    emit(do_analyze(project_root(), args))


def cmd_render(args) -> None:
    root = project_root()
    payload = do_render(root, resolve_analysis(root, args.analysis), args)
    emit(payload, 0 if payload["ok"] else 1)


def cmd_auto(args) -> None:
    root = project_root()
    analysis = do_analyze(root, args)
    args.clips = "all"
    payload = do_render(root, Path(analysis["analysis_path"]), args)
    payload["analysis_id"] = analysis["analysis_id"]
    payload["clips"] = analysis["clips"]
    emit(payload, 0 if payload["ok"] else 1)


def cmd_clips(args) -> None:
    root = project_root()
    clips_dir = root / "clips"
    if args.project:
        project = Path(args.project).expanduser()
        if not project.is_absolute():
            project = clips_dir / args.project
        if not project.is_dir():
            fail(f"Project folder not found: {project}")
        files = sorted(p for p in project.glob("*.mp4") if p.is_file())
        emit({
            "ok": True,
            "project": str(project.resolve()),
            "clips": [describe_clip_file(p) for p in files],
        })
    projects = []
    if clips_dir.is_dir():
        for sub in sorted(clips_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if sub.is_dir():
                projects.append({
                    "name": sub.name,
                    "path": str(sub.resolve()),
                    "clip_count": sum(1 for p in sub.glob("*.mp4") if p.is_file()),
                })
    emit({"ok": True, "clips_dir": str(clips_dir), "projects": projects})


# ── CLI ─────────────────────────────────────────────────────────────────────
def _add_analyze_opts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--source", required=True, help="Local video path or YouTube URL")
    p.add_argument("--num-clips", type=int, default=5, help="Clips to select (1-10, default 5)")
    p.add_argument("--mode", choices=["hook", "affiliate"], default="hook")
    p.add_argument("--lang", choices=["id", "en", "auto"], default="id", help="Spoken language")
    p.add_argument("--single-pass", action="store_true", help="Legacy single LLM pass (faster, less diverse)")


def _add_render_opts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--sub-style", choices=SUB_STYLES, default="tiktok_viral")
    p.add_argument("--framing", choices=FRAMING_MODES, default="smart_crop")
    p.add_argument("--sub-position", type=int, default=68, help="Subtitle Y position %% from top (30-85)")
    p.add_argument("--no-watermark", action="store_true")
    p.add_argument("--source-watermark", default="", help="Source credit text (auto-detected if empty)")
    p.add_argument("--account-watermark", default="", help="Clipper account handle, e.g. @myclips")


def main() -> None:
    global LOG_MODE
    parser = argparse.ArgumentParser(prog="vclip", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("--verbose", action="store_true", help="Stream every worker line (incl. ffmpeg) to stderr")
    noise.add_argument("--quiet", action="store_true", help="No progress output on stderr")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Check FFmpeg, .venv and API keys (never prints secret values)") \
        .set_defaults(func=cmd_doctor)

    p_an = sub.add_parser("analyze", help="Transcribe + AI-select viral moments (no rendering)")
    _add_analyze_opts(p_an)
    p_an.set_defaults(func=cmd_analyze)

    p_re = sub.add_parser("render", help="Render selected clips from an analysis")
    p_re.add_argument("--analysis", default="latest", help="analysis_id, path to JSON, or 'latest'")
    p_re.add_argument("--clips", default="all", help="'all' or 1-based indices, e.g. 1,3,4")
    _add_render_opts(p_re)
    p_re.set_defaults(func=cmd_render)

    p_auto = sub.add_parser("auto", help="analyze + render all selected clips in one go")
    _add_analyze_opts(p_auto)
    _add_render_opts(p_auto)
    p_auto.set_defaults(func=cmd_auto)

    p_cl = sub.add_parser("clips", help="List rendered projects, or clips + metadata of one project")
    p_cl.add_argument("--project", default="", help="Folder name inside clips/ or absolute path")
    p_cl.set_defaults(func=cmd_clips)

    args = parser.parse_args()
    LOG_MODE = "verbose" if args.verbose else "quiet" if args.quiet else "normal"
    args.func(args)


if __name__ == "__main__":
    main()
