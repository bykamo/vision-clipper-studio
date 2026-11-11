"""VisionClipper MCP server.

Exposes the same pipeline as ``skills/vision-clipper/scripts/vclip.py``
(doctor / analyze / render / auto / clips) as MCP tools so any MCP-capable AI
agent (Claude Desktop, Codex CLI, Copilot, Cline, ...) can drive the clipper
without the web dashboard.

Contract (mirrors vclip.py):
  * Each tool returns a JSON-serializable object with an ``ok`` boolean,
    and on failure an ``error`` string plus a ``log_tail`` list.
  * Everything is executed synchronously inside a subprocess, so the tools
    inherit VisionClipper's "one job at a time" rule. Rendering is
    long-running; callers should set a generous timeout.

The actual work is delegated to ``skills/vision-clipper/scripts/vclip.py`` so
there is exactly one implementation of the pipeline to maintain. The helper is
advantageous here because it already:
  * auto-locates the project root (follows symlinks),
  * reuses the project ``.venv`` interpreter,
  * prints one JSON object on stdout and progress on stderr,
  * exits 0/1 with a stable ``ok``/``error`` envelope.

Run:
    python -m backend.mcp_server          # stdio transport (default)
    python -m backend.mcp_server --http   # Streamable HTTP on localhost:5055
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The 'mcp' package is not installed. Install it with:\n"
        "  .venv/bin/pip install 'vision-clipper[mcp]'\n"
        "or: pip install mcp"
    ) from exc

mcp = FastMCP(
    "vision-clipper",
    instructions=(
        "Drive the VisionClipper AI video clipper: check the environment "
        "(doctor), transcribe + pick viral moments (analyze), render 9:16 "
        "clips (render), do both at once (auto), and browse renders (clips). "
        "Run only one pipeline job at a time; rendering is slow."
    ),
)

HOME = Path(__file__).resolve().parent.parent
VCLIP = HOME / "skills" / "vision-clipper" / "scripts" / "vclip.py"


def _python() -> str:
    for candidate in (HOME / ".venv" / "bin" / "python", HOME / ".venv" / "Scripts" / "python.exe"):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _run(*args: str) -> dict[str, Any]:
    """Run ``vclip.py`` and return its JSON envelope."""
    cmd = [_python(), "-u", str(VCLIP), *args]
    proc = subprocess.run(
        cmd,
        cwd=str(HOME),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = proc.stdout.strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "error": "vclip.py did not return valid JSON.",
            "stdout": stdout[-2000:],
        }
    if not isinstance(payload, dict):
        payload = {"ok": False, "error": "Unexpected vclip.py output.", "stdout": json.dumps(payload)}
    # Surface the tail of progress logs when the job failed, for debugging.
    if not payload.get("ok") and proc.stderr.strip():
        payload.setdefault("log_tail", proc.stderr.strip().splitlines()[-40:])
    return payload


@mcp.tool()
def doctor() -> dict[str, Any]:
    """Check the VisionClipper environment: FFmpeg, ffprobe, venv, LLM endpoint/API key,
    GROQ_API_KEY, cookies.txt and frontend build. Never returns secret values.
    Returns {"ok": bool, "checks": {...}, "problems": [...]}."""
    return _run("--quiet", "doctor")


@mcp.tool()
def analyze(
    source: str,
    num_clips: int = 5,
    mode: str = "hook",
    lang: str = "id",
    single_pass: bool = False,
) -> dict[str, Any]:
    """Transcribe a video and let the LLM pick viral moments (no rendering).

    Args:
        source: Local video path or YouTube URL.
        num_clips: Clips to select (1-10, default 5).
        mode: "hook" (viral/emotional moments) or "affiliate" (selling moments).
        lang: Spoken language: "id", "en" or "auto".
        single_pass: True for the legacy single-call analysis (faster, less diverse).

    Returns clips[] with index, title, start, end, duration, viral_score,
    hook_line, reason, caption and hashtags, plus an analysis_id to feed render."""
    if lang not in ("id", "en", "auto"):
        return {"ok": False, "error": "lang must be id, en or auto"}
    if mode not in ("hook", "affiliate"):
        return {"ok": False, "error": "mode must be hook or affiliate"}
    num_clips = max(1, min(10, int(num_clips)))
    args = ["--quiet", "analyze", "--source", source, "--num-clips", str(num_clips),
            "--mode", mode, "--lang", lang]
    if single_pass:
        args.append("--single-pass")
    return _run(*args)


@mcp.tool()
def render(
    analysis: str = "latest",
    clips: str = "all",
    sub_style: str = "tiktok_viral",
    framing: str = "smart_crop",
    sub_position: int = 68,
    no_watermark: bool = False,
    source_watermark: str = "",
    account_watermark: str = "",
) -> dict[str, Any]:
    """Render selected clips from a previous analysis into vertical 9:16 videos.

    Args:
        analysis: an analysis_id (analysis_<digits>), path to a JSON, or "latest".
        clips: "all" or comma-separated 1-based indices, e.g. "1,3,4".
        sub_style: tiktok_viral, classic_karaoke, minimalist, word_pop or no_subtitle.
        framing: smart_crop (face tracking), fit_blur or split_screen.
        sub_position: Subtitle Y position, % from top (30-85).
        no_watermark: True to disable the source/account watermark.
        source_watermark: Optional credit text.
        account_watermark: Optional clipper handle, e.g. @myclips.

    Returns rendered[] with video_path, metadata_path and parsed metadata."""
    sub_position = max(30, min(85, int(sub_position)))
    args = ["--quiet", "render", "--analysis", analysis, "--clips", clips,
            "--sub-style", sub_style, "--framing", framing,
            "--sub-position", str(sub_position)]
    if no_watermark:
        args.append("--no-watermark")
    if source_watermark:
        args += ["--source-watermark", source_watermark]
    if account_watermark:
        args += ["--account-watermark", account_watermark]
    return _run(*args)


@mcp.tool()
def auto(
    source: str,
    num_clips: int = 3,
    mode: str = "hook",
    lang: str = "id",
    single_pass: bool = False,
    sub_style: str = "tiktok_viral",
    framing: str = "smart_crop",
    sub_position: int = 68,
    no_watermark: bool = False,
) -> dict[str, Any]:
    """Analyze a source and render every selected clip in one go.

    This is the fully automatic pipeline: transcribe -> pick moments -> render.
    Returns the rendered[] clips plus the underlying clips[] selection."""
    if lang not in ("id", "en", "auto"):
        return {"ok": False, "error": "lang must be id, en or auto"}
    if mode not in ("hook", "affiliate"):
        return {"ok": False, "error": "mode must be hook or affiliate"}
    num_clips = max(1, min(10, int(num_clips)))
    sub_position = max(30, min(85, int(sub_position)))
    args = ["--quiet", "auto", "--source", source, "--num-clips", str(num_clips),
            "--mode", mode, "--lang", lang,
            "--sub-style", sub_style, "--framing", framing,
            "--sub-position", str(sub_position)]
    if single_pass:
        args.append("--single-pass")
    if no_watermark:
        args.append("--no-watermark")
    return _run(*args)


@mcp.tool()
def clips(project: str = "") -> dict[str, Any]:
    """List rendered projects in clips/, or the clips + metadata of one project.

    Args:
        project: Optional folder name inside clips/ (or an absolute path).

    When project is empty, returns projects[] with name, path and clip_count.
    Otherwise returns clips[] with video_path, metadata_path, size_bytes and
    parsed metadata (title_options, hook, caption, hashtags)."""
    args = ["--quiet", "clips"]
    if project:
        args += ["--project", project]
    return _run(*args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http", action="store_true",
                        help="Serve over Streamable HTTP on localhost:5055 instead of stdio")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()