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

## Standing workflow with this user (jack profile)

The user's standing instruction (11 Nov 2026): *"begitu gw kirim link video yt ke sini lo langsung kerjain pake skill visionclipper ... jangan langsung upload kecuali udh gw approve mana aja yang oke"*.

- **A pasted YouTube link IS the request.** No further instruction needed — run `doctor` → `analyze` → `render` yourself and come back with the clip list. Don't ask what to do with the link.
- **NEVER upload to YouTube without per-clip approval.** Rendering is the deliverable; publishing is a separate step the user authorizes by naming which clips are OK. Approval for one clip is **not** approval for the next batch, and never pre-schedule or arm an upload queue on your own initiative.
- When clips are ready, present them compactly (number, title, `viral_score`, duration, size) and ask which to publish.
- After approval: upload via the clipper / `queue_upload.py` with title + description + hashtags complete (never a bare upload), default `private`. If the user vetoes a set of clips, add its project to `queue/exclude.txt` **the same turn**.
- Spread approved uploads across slots (3-6/day, >=30 min apart) — hygiene for per-clip feed testing, not a fix for anything.
- One job at a time: never run analyze/render in parallel with another render or with a dashboard job.
- YouTube downloads from this IP hit the bot check — **`cookies.txt` is already exported in the project root** (mode 600, from the logged-in Brave session) and `downloads`/`backend` pick it up automatically, so `doctor` reports `cookies_txt: true`. Refresh it with `yt-dlp --cookies-from-browser brave --cookies cookies.txt --skip-download <any-URL>` if downloads ever start failing again.

One-shot for a pasted link (analyze + render in a single call, then stop and report):

```bash
cd /home/kamo/dev/myapp/vision-clipper
python3 skills/vision-clipper/scripts/vclip.py auto --source "<URL>" --num-clips 5 --mode hook --lang id
```

Use `--mode affiliate` instead when the source is a selling/promo video. Runs 30 min+ for 5+ clips — raise the command timeout. Output lands in `clips/<video name>/` as `.mp4` + `.txt` (titles, hook, caption, hashtags); read the `.txt` files to build the approval list.

## MCP server

If you are an MCP-capable agent, VisionClipper is also available as an MCP
server exposing the same five operations (`doctor`, `analyze`, `render`,
`auto`, `clips`) as tools. Configure it with [`.vscode/mcp.json`](../../.vscode/mcp.json)
(in this repo) and follow [references/mcp.md](references/mcp.md) — the tool
descriptions and the rules in this file apply unchanged.

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
- Only upload or post clips when the user explicitly approves **that clip** — a pasted link authorizes clipping, never uploading. Approval for one clip is not approval for the next batch.
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

## Editing metadata & measuring results (use the Data API, never the Studio UI)

- `videos.update` (retitle/description/tags) needs the scope **`youtube.force-ssl`**. It is in `SCOPES` in `backend/youtube_uploader.py`; a token created before that change must be re-authorized once (dashboard → ⚙️ Settings → YouTube → "Hubungkan YouTube", or `bash auth-youtube.sh`, verify with `bash auth-youtube.sh --check`).
- **Do not automate the YouTube Studio editor.** Under browser automation the Save button never enables and many requests get blocked (Brave shields), so JS/mouse clicks silently do nothing while the API still reports the old title. Always write metadata through the Data API.
- Write metadata with a dry-run-first script: print `old title -> new title` for every video, back up the old values to JSON, then apply with `--apply`, and finally **re-read via the API** to confirm.
- `track_views.py` in the repo root snapshots every video's views/likes/comments into `analytics/views_history.csv` and prints the delta versus the previous snapshot — run it instead of guessing whether a change worked.
- For "why is this video stuck at 0 views", read facts, not vibes: `videos.list(part='fileDetails')` (owner only) gives width/height/codec/duration, `contentDetails.duration` the length, `statistics` the views. A video at literally 0 views was never tested in the Shorts feed — that is a distribution fact, not a quality verdict.
- Publish cadence is **not** what kills distribution. Minute-level `publishedAt` data shows clips uploaded minutes apart all performing (3 in 9 min -> all ~1.2k views), so never recommend 1/day or 6-hour gaps as a fix. What matters: publish every clip with title + description + hashtags (placeholder titles with empty descriptions cluster with 0 views), and pick clips on a strong first-3-seconds hook. When the user wants 3-6 clips/day, use `queue_upload.py` to spread them across slots with >=30 min gaps as hygiene, and say plainly that the gap is not the cause.

## Pitfalls seen on this machine

| Symptom | Cause / fix |
|---|---|
| `User location is not supported for the API use` on analyze | `ag/gemini-*` routes are geo-blocked from this network — use `ROUTER_LLM_MODEL=tip/deepseek-v-4.1-flash-1017` |
| Groq `403` (Cloudflare 1010) on transcription | Groq rejects a Python User-Agent; send a browser UA on those requests |
| JS `element.click()` does nothing on Google/YouTube pages | Trusted events required — drive the page with playwright-core over CDP (`connectOverCDP('http://127.0.0.1:9222')`) and real locator clicks; use the logged-in Brave session for OAuth consent |
| OAuth link "expired"/dead | Auth URLs live ~10 min and the dashboard mints a new one per click — regenerate immediately before using it |
| `skill_manage` cannot find `vision-clipper` | It is a symlink into the project; edit `<repo>/skills/vision-clipper/SKILL.md` directly |

## Other interfaces

- **MCP server** (for MCP-capable agents): same tools as this script — see [references/mcp.md](references/mcp.md).
- **HTTP API** (when the dashboard server is running on `:5050`): SSE endpoints for analyze/render, YouTube upload, AI config. See [references/http-api.md](references/http-api.md).
- **Raw worker**: `python -m backend.worker --help` from the project root (same pipeline, plain-text logs).
- **Dashboard**: `vision-clipper` starts the web UI at `http://localhost:5050`; `vision-clipper stop` stops it.
