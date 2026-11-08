---
name: vision-clipper
description: Turn long videos (podcasts, interviews, YouTube URLs or local files) into short vertical 9:16 viral clips for TikTok, Reels and Shorts, with face-tracking smart crop, burned-in word-level subtitles, and AI-generated titles, captions and hashtags. Use when the user asks to clip, cut, or repurpose a long video into shorts, find viral or hook moments, make affiliate clips, re-render clips with another subtitle style or framing, or list and fetch metadata of previously rendered clips.
license: MIT
compatibility: Requires a local VisionClipper install (Python 3.10+, .venv, FFmpeg) with ROUTER_API_ENDPOINT, ROUTER_API_KEY and GROQ_API_KEY set in the project .env. Network access for Groq Whisper, the LLM endpoint and YouTube downloads.
metadata:
  author: kam2k-dev
  version: "1.0.0"
  homepage: https://github.com/kam2k-dev
---

# VisionClipper

VisionClipper is a local AI video clipper. Pipeline: download/resolve source → Groq Whisper transcription → LLM picks viral moments (two-pass, diversity-aware) → FFmpeg renders 9:16 clips with smart crop + subtitles → writes an `.mp4` and a `.txt` (titles, hook, caption, hashtags) per clip into `clips/<video name>/`.

Drive it through the helper script `scripts/vclip.py`. It prints **one JSON object on stdout**, progress logs on stderr, and exits `0` on success / `1` on failure (`"ok": false`, `"error"`, `"log_tail"`).

## Running the helper

```bash
python3 <skill-dir>/scripts/vclip.py <command> [options]
```

- `<skill-dir>` is the folder containing this file. The script auto-locates the project (follows symlinks) and re-uses the project `.venv` interpreter, so plain `python3` is fine.
- If the skill was **copied** (not symlinked) outside the repo, set `VISION_CLIPPER_HOME=/absolute/path/to/vision-clipper`.
- Add `--quiet` before the command to suppress progress logs, or `--verbose` to stream raw FFmpeg output.

## Workflow

1. **Check the environment first** (once per session):
   ```bash
   python3 scripts/vclip.py doctor
   ```
   If `ok` is false, report the `problems` list to the user. Never read, print or edit API keys yourself — ask the user to run `vision-clipper config`.

2. **Analyze** (transcribe + pick moments, no rendering, ~30 s–3 min):
   ```bash
   python3 scripts/vclip.py analyze --source "<path-or-youtube-url>" --num-clips 5 --mode hook --lang id
   ```
   Returns `analysis_id` and `clips[]` with `index`, `title`, `start`, `end`, `duration`, `viral_score`, `hook_line`, `reason`, `caption`, `hashtags`.

3. **Show candidates to the user** (title, timestamps, score, hook) and let them choose, unless they asked for a fully automatic run.

4. **Render** the chosen clips (slow: roughly 0.5–2× real-time per clip on CPU):
   ```bash
   python3 scripts/vclip.py render --analysis <analysis_id> --clips 1,3,4 --sub-style tiktok_viral --framing smart_crop
   ```
   Returns `rendered[]` with `video_path`, `metadata_path` and parsed `metadata` (`title_options`, `hook`, `caption`, `hashtags`).

5. **Report** the output paths plus the ready-to-post title, caption and hashtags.

Fully automatic (analyze + render everything selected):
```bash
python3 scripts/vclip.py auto --source "<path-or-url>" --num-clips 3
```

Re-render with another look without re-transcribing — reuse the same analysis:
```bash
python3 scripts/vclip.py render --analysis latest --clips all --sub-style word_pop --framing fit_blur
```

Browse existing renders:
```bash
python3 scripts/vclip.py clips                       # list projects in clips/
python3 scripts/vclip.py clips --project "<folder>"  # clips + metadata of one project
```

## Options

| Option | Commands | Values / default |
|---|---|---|
| `--source` | analyze, auto | Local video path or `http(s)://` YouTube URL (required) |
| `--num-clips` | analyze, auto | 1–10, default `5` |
| `--mode` | analyze, auto | `hook` (viral/emotional moments, default) · `affiliate` (product/selling moments) |
| `--lang` | analyze, auto | `id` (default) · `en` · `auto` — spoken language of the source |
| `--single-pass` | analyze, auto | Legacy one-call analysis: faster, less diverse |
| `--analysis` | render | `analysis_<digits>`, path to an analysis JSON, or `latest` (default) |
| `--clips` | render | `all` (default) or 1-based indices `1,3,4` |
| `--sub-style` | render, auto | `tiktok_viral` (default) · `classic_karaoke` · `minimalist` · `word_pop` · `no_subtitle` |
| `--framing` | render, auto | `smart_crop` (face tracking, default) · `fit_blur` (full frame + blurred bg) · `split_screen` (two speakers) |
| `--sub-position` | render, auto | Subtitle Y position, % from top, 30–85, default `68` |
| `--no-watermark` | render, auto | Disable the subtle source/account watermark |
| `--source-watermark` | render, auto | Credit text; auto-detected from the video/channel name if empty |
| `--account-watermark` | render, auto | Clipper handle, e.g. `@myclips` |

## Rules

- **One job at a time.** The worker is CPU/RAM heavy. Never run analyze/render commands in parallel, and do not run them while the user is processing a job in the web dashboard.
- Rendering is long-running. Run it in the foreground and wait for the JSON; do not poll or kill it early. If your harness has a command timeout, raise it (≥ 30 min for 5+ clips).
- Analysis files in `temp/` expire after ~24 h (cleaned when the server starts). If `render` reports "Analysis file not found", run `analyze` again — transcripts are cached in `downloads/transcripts/`, so it is fast.
- Prefer passing a local path when the user has one; YouTube downloads from datacenter IPs may need a `cookies.txt` in the project root (`doctor` → `cookies_txt`).
- Only upload or post clips when the user explicitly asks. YouTube upload needs OAuth, done once in the dashboard — see [references/http-api.md](references/http-api.md).
- Respect copyright: remind the user they need rights to repost third-party content when relevant.

## Troubleshooting

| Symptom (`error` / `log_tail`) | Fix |
|---|---|
| `Cannot locate the VisionClipper project` | Set `VISION_CLIPPER_HOME` to the repo root |
| `401` / `Invalid API key` / `PermanentLLMError` | Wrong key or model for the endpoint → user runs `vision-clipper config` |
| `GROQ` / transcription errors | `GROQ_API_KEY` missing or rate-limited; multiple comma-separated keys are supported |
| `Sign in to confirm you're not a bot` | Export YouTube cookies (Netscape format) to `cookies.txt` in the project root |
| `FFmpeg not found` | Install FFmpeg and make sure it is on `PATH` |
| `Seleksi keberagaman: 2/5 klip lolos` (log) | Not an error — the video had fewer distinct moments; result is still valid |

## Other interfaces

- **HTTP API** (when the dashboard server is running on `:5050`): SSE endpoints for analyze/render, YouTube upload, AI config. See [references/http-api.md](references/http-api.md).
- **Raw worker**: `python -m backend.worker --help` from the project root (same pipeline, plain-text logs).
- **Dashboard**: `vision-clipper` starts the web UI at `http://localhost:5050`; `vision-clipper stop` stops it.
