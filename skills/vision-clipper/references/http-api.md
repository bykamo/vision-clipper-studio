# VisionClipper HTTP API (for agents)

Use this only when the dashboard server is already running (`vision-clipper status`) or when you need a feature the helper script does not cover (YouTube upload, AI config). For clipping itself, prefer `scripts/vclip.py`.

Base URL: `http://localhost:5050` (VPS behind SSH tunnel: same URL locally).

## Session cookie (required)

Every `/api/*`, `/stream`, `/cancel` and `/shutdown` request needs the `vc_session_token` cookie. Bootstrap it once:

```bash
JAR=$(mktemp)
curl -s -c "$JAR" http://localhost:5050/api/session          # 204, sets cookie
curl -s -b "$JAR" http://localhost:5050/api/social/youtube/status
```

POST requests must not send a foreign `Origin`/`Referer` (curl sends none by default).

## Only one worker at a time

`/api/analyze`, `/api/render-selected` and `/stream` return **HTTP 409** while another job runs. Wait or call `POST /cancel`.

## Analyze — `GET /api/analyze` (SSE)

Query: `source` (path or URL, required), `num_clips` (1–10), `mode` (`hook`|`affiliate`), `source_lang` (`id`|`en`|`auto`).

```bash
curl -sN -b "$JAR" --get http://localhost:5050/api/analyze \
  --data-urlencode "source=/abs/path/video.mp4" -d num_clips=5 -d mode=hook -d source_lang=id
```

Stream lines are `data: <log line>`. The result arrives as `data: [ANALYSIS_RESULT]{json}` containing `analysis_id`, `video_path`, `output_dir`, `clips[]`. The stream ends with `data: [PROCESS_COMPLETE]` or `data: [PROCESS_FAILED]`.

## Render — `POST /api/render-selected` (SSE)

```bash
curl -sN -b "$JAR" -H 'Content-Type: application/json' http://localhost:5050/api/render-selected -d '{
  "analysis_id": "analysis_1794106709844",
  "clip_indices": [1, 3],
  "sub_style": "tiktok_viral",
  "framing_mode": "smart_crop",
  "sub_position": 68,
  "watermark_enabled": true,
  "source_watermark": "",
  "account_watermark": "@myclips"
}'
```

Ends with `[PROCESS_COMPLETE]` / `[PROCESS_FAILED]`. Outputs: `<output_dir>/NN_<Title>.mp4` + `.txt`.

## Other endpoints

| Method & path | Purpose |
|---|---|
| `GET /api/analysis-clip-words?analysis_id=…&index=N` | Word-level transcript of one analysed clip |
| `POST /api/rendered-clips/load` `{"path": "<clips/project dir>"}` | List rendered clips + parsed metadata |
| `GET /api/social/youtube/status` | `{connected, channel}` |
| `GET /api/social/youtube/auth-url` | OAuth URL — the **user** must open it in a browser |
| `POST /api/social/youtube/upload` `{video_path, title, description, tags[], privacy}` | Upload a clip (must be inside `clips/`). `privacy`: `private` (default) · `unlisted` · `public` |
| `GET /api/youtube/cookies/status` | Whether `cookies.txt` exists |
| `GET /api/ai-config` | Current provider/model (secrets masked) |
| `POST /api/ai-config/test` | Test the LLM connection |
| `POST /cancel` | Stop the running job |

Do not call `POST /shutdown` or `POST /api/ai-config` (overwrites keys) unless the user explicitly asks. Always upload as `private` unless the user specifies otherwise.
