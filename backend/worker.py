import argparse
import json
import os
import sys
import time
from backend.downloader import get_video_file, get_video_source_name
from backend.transcriber import transcribe_video, build_transcript_text, build_compact_transcript_text, get_media_duration
from backend.analyzer import (
    build_viral_prompt,
    build_candidate_discovery_prompt,
    build_clip_enrichment_prompt,
    build_transcript_slice,
    select_diverse_clips,
    call_llm_api,
    extract_json_block,
    PermanentLLMError,
)
from backend.content_rules import apply_content_rules, MAX_DURATION
from backend.renderer import extract_and_format_clip
from backend.utils import (
    log,
    DEFAULT_LLM_MODEL,
    DEFAULT_ENDPOINT,
    DEFAULT_API_KEY,
    DEFAULT_OUT_DIR,
    parse_timestamp_to_seconds,
)


def _serialize_segments(segments):
    """Convert segment objects to JSON-safe dicts."""
    out = []
    for seg in segments:
        s = {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
        if "words" in seg:
            s["words"] = [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in seg["words"]]
        out.append(s)
    return out


def _parse_render_indices(raw_indices, clip_count):
    """Parse and validate one-based clip indexes passed to render mode."""
    try:
        indices = [int(value.strip()) for value in raw_indices.split(",") if value.strip()]
    except ValueError as e:
        raise ValueError("Render indices must be comma-separated integers.") from e

    if not indices:
        raise ValueError("Select at least one clip to render.")
    if len(set(indices)) != len(indices):
        raise ValueError("Render indices must not contain duplicates.")
    if any(index < 1 or index > clip_count for index in indices):
        raise ValueError(f"Render indices must be between 1 and {clip_count}.")
    return indices


def _llm_json_with_retries(prompt, compact_prompt, llm_endpoint, llm_key, llm_model, job_id=None, label="analisis"):
    """Call the LLM with retries + compact-transcript fallback; return parsed JSON dict.

    PermanentLLMError (bad key / blocked model) is re-raised immediately —
    retrying cannot help.

    Retry strategy: attempt 1 uses the full transcript. If it fails for ANY
    reason (timeout, truncated JSON, gateway 5xx), the next attempt switches to
    the compact transcript instead of resending the same oversized payload that
    just failed. This turns a ~3x repeated 2-minute timeout into one fast retry.
    """
    last_error = None
    use_compact = False
    for attempt in range(3):
        active_prompt = compact_prompt if (use_compact and compact_prompt) else prompt
        try:
            log(f"Memanggil AI ({label}, percobaan {attempt + 1}/3)...", job_id=job_id)
            llm_response = call_llm_api(
                active_prompt, llm_model, llm_endpoint, llm_key,
                job_id=job_id, compact_prompt=compact_prompt,
            )
            data = extract_json_block(llm_response, job_id=job_id)
            if isinstance(data, dict) and data:
                return data
            last_error = "LLM mengembalikan JSON kosong."
            log(f"Percobaan {attempt + 1}: LLM merespons tapi JSON kosong.", job_id=job_id)
        except PermanentLLMError:
            raise
        except Exception as e:
            last_error = str(e)
            log(f"LLM gagal ({label}) percobaan {attempt + 1}: {e}", job_id=job_id)
        # Next attempt: shrink the payload if we have a compact version.
        if compact_prompt:
            use_compact = True
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError(
        f"Gagal mendapatkan JSON valid dari LLM ({label}) setelah 3 percobaan: {last_error}"
    )


def main():
    parser = argparse.ArgumentParser(description="Vision Clipper Worker")
    parser.add_argument("--file", type=str, required=True, help="Path to video file")
    parser.add_argument("--num-clips", type=int, default=5, help="Number of clips")
    parser.add_argument("--mode", type=str, default="hook", choices=["hook", "affiliate"], help="Analysis mode")
    parser.add_argument("--max-candidates", type=int, default=15, help="Pass-1 candidate pool size (two-pass mode)")
    parser.add_argument("--min-clip-gap", type=float, default=60.0, help="Min seconds between selected clips (two-pass mode)")
    parser.add_argument("--diversity-threshold", type=float, default=0.55, help="Topic similarity 0-1 above which a candidate is rejected as duplicate (two-pass mode)")
    parser.add_argument("--single-pass", action="store_true", help="Use legacy single-pass analysis instead of two-pass")
    parser.add_argument("--job-id", type=int, default=None, help="Job ID for DB logging")
    parser.add_argument("--model", type=str, default="groq", choices=["groq"], help="Transcription provider (Groq Whisper Cloud)")
    parser.add_argument("--out-dir", type=str, default=DEFAULT_OUT_DIR, help="Output directory")
    parser.add_argument("--sub-style", type=str, default="tiktok_viral", choices=["tiktok_viral", "classic_karaoke", "minimalist", "word_pop", "no_subtitle", "none"], help="Subtitle style")
    parser.add_argument("--framing-mode", type=str, default="smart_crop", choices=["smart_crop", "fit_blur", "split_screen"], help="Video layout framing mode")
    parser.add_argument("--sub-position", type=int, default=68, help="Subtitle vertical position percentage from top (30-85)")
    # Watermark flags
    parser.add_argument("--watermark-enabled", action="store_true", default=True, help="Burn-in subtle glass-effect watermarks")
    parser.add_argument("--no-watermark", action="store_false", dest="watermark_enabled", help="Disable watermarks")
    parser.add_argument("--source-watermark", type=str, default="", help="Custom or auto source credit watermark text")
    parser.add_argument("--account-watermark", type=str, default="", help="Custom clipper account handle or name")
    # Language flags
    parser.add_argument("--source-lang", type=str, default="id", choices=["id", "en", "auto"], help="Source audio language (id, en, auto)")
    # Phase-split flags
    parser.add_argument("--analyze-only", action="store_true", help="Only transcribe + LLM analyze, output JSON, no rendering")
    parser.add_argument("--clips-json", type=str, default=None, help="Path to analysis JSON file (skip transcribe+LLM)")
    parser.add_argument("--render-indices", type=str, default=None, help="Comma-separated clip indices to render (e.g. 1,3,4)")

    args, unknown = parser.parse_known_args()

    if bool(args.clips_json) != bool(args.render_indices):
        parser.error("--clips-json and --render-indices must be used together")

    job_id = args.job_id
    if job_id:
        from backend.database import update_job_status
        update_job_status(job_id, "running")

    # ── RENDER-ONLY MODE: Load from saved analysis JSON ──
    if args.clips_json and args.render_indices:
        try:
            with open(args.clips_json, "r", encoding="utf-8") as f:
                analysis = json.load(f)

            video_path = analysis["video_path"]
            clips = analysis["clips"]
            segments = analysis["segments"]
            actual_out_dir = analysis["output_dir"]
            if not isinstance(clips, list) or not isinstance(segments, list):
                raise ValueError("Analysis file has invalid clip or transcript data.")
            os.makedirs(actual_out_dir, exist_ok=True)

            resolved_source_wm = (args.source_watermark or analysis.get("source_name") or get_video_source_name(video_path) or "").strip()
            resolved_account_wm = (args.account_watermark or "").strip()

            indices = _parse_render_indices(args.render_indices, len(clips))
            log(f"Render mode: rendering {len(indices)} selected clips from analysis.", job_id=job_id)
            log(f"Outputs will be saved to: {actual_out_dir}", job_id=job_id)

            failed_indices = []
            for idx in indices:
                clip = clips[idx - 1]  # 1-based index
                log(f"--- Rendering Clip {idx}/{len(clips)} ---", job_id=job_id)
                titles = clip.get('title_options', [clip.get('title', 'Unknown Title')])
                log(f"Title: {titles[0] if isinstance(titles, list) and titles else titles}", job_id=job_id)
                if clip.get("hook_line"):
                    log(f"Hook: {clip['hook_line']}", job_id=job_id)
                try:
                    extract_and_format_clip(
                        video_path, clip, idx, segments, actual_out_dir,
                        job_id=job_id,
                        sub_style=args.sub_style,
                        framing_mode=args.framing_mode,
                        sub_position=args.sub_position,
                        watermark_enabled=args.watermark_enabled,
                        source_watermark=resolved_source_wm,
                        account_watermark=resolved_account_wm,
                    )
                except Exception as e:
                    log(f"Failed to render clip {idx}: {e}", job_id=job_id)
                    failed_indices.append(idx)

            if failed_indices:
                raise RuntimeError(f"Failed to render selected clips: {failed_indices}")
            log("All done! Check your output directory.", job_id=job_id)
            if job_id:
                update_job_status(job_id, "completed")
            os._exit(0)
        except Exception as e:
            import traceback
            log(f"Error in render mode: {e}", job_id=job_id)
            log(traceback.format_exc(), job_id=job_id)
            if job_id:
                update_job_status(job_id, "failed")
            sys.exit(1)

    # ── NORMAL / ANALYZE-ONLY MODE ──
    try:
        log(f"Memulai analisis video: {args.file}", job_id=job_id)
        video_path = get_video_file(args.file, job_id=job_id)

        segments = transcribe_video(
            video_path,
            source_url=args.file,
            model_size=args.model,
            source_lang=args.source_lang,
            job_id=job_id
        )
        transcript_text = build_transcript_text(segments)

        llm_endpoint = os.environ.get("ROUTER_API_ENDPOINT") or DEFAULT_ENDPOINT
        llm_key = os.environ.get("ROUTER_API_KEY") or DEFAULT_API_KEY
        llm_model = os.environ.get("ROUTER_LLM_MODEL") or DEFAULT_LLM_MODEL
        total_video_dur = get_media_duration(video_path)
        # Compact fallback transcript (merged timestamp blocks) used when a
        # model rejects the full transcript for exceeding its token budget.
        compact_transcript = build_compact_transcript_text(segments)
        has_compact = bool(compact_transcript and compact_transcript != transcript_text)

        clips = []
        if args.single_pass:
            # ── LEGACY single-pass: one LLM call returns exactly N clips ──
            prompt = build_viral_prompt(transcript_text, args.num_clips, mode=args.mode)
            compact_prompt = (
                build_viral_prompt(compact_transcript, args.num_clips, mode=args.mode)
                if has_compact else None
            )
            log("Mencari bagian video paling viral menggunakan AI (single-pass). Estimasi waktu: ~10-25 detik...", job_id=job_id)
            data = _llm_json_with_retries(
                prompt, compact_prompt, llm_endpoint, llm_key, llm_model,
                job_id, label="single-pass",
            )
            clips = data.get("clips", []) if isinstance(data, dict) else []
            if not clips:
                raise RuntimeError("Single-pass: LLM tidak mengembalikan klip.")
        else:
            # ── TWO-PASS ──
            # Pass 1: LLM scouts a POOL of candidates (more than needed).
            discovery_prompt = build_candidate_discovery_prompt(
                transcript_text, args.max_candidates, mode=args.mode
            )
            compact_discovery = (
                build_candidate_discovery_prompt(
                    compact_transcript, args.max_candidates, mode=args.mode
                )
                if has_compact else None
            )
            log(f"Tahap 1/2: AI memindai hingga {args.max_candidates} kandidat momen viral...", job_id=job_id)
            data = _llm_json_with_retries(
                discovery_prompt, compact_discovery, llm_endpoint, llm_key, llm_model,
                job_id, label="tahap-1 discovery",
            )
            candidates = data.get("candidates", []) if isinstance(data, dict) else []
            video_summary = ((data.get("video_summary") or "") if isinstance(data, dict) else "").strip()
            if not candidates:
                raise RuntimeError("Tahap 1: LLM tidak mengembalikan kandidat momen.")
            log(f"Tahap 1 selesai: {len(candidates)} kandidat ditemukan.", job_id=job_id)

            # Validate candidate boundaries before selection.
            valid_candidates = []
            for raw in candidates:
                try:
                    s = parse_timestamp_to_seconds(raw.get("start", 0.0))
                    e = parse_timestamp_to_seconds(raw.get("end", 0.0))
                    if total_video_dur > 0:
                        e = min(total_video_dur, e)
                        s = min(total_video_dur, s)
                    if e <= s or (e - s) < 5.0:
                        continue
                    raw["start"] = round(s, 2)
                    raw["end"] = round(e, 2)
                    valid_candidates.append(raw)
                except (TypeError, ValueError):
                    continue
            if not valid_candidates:
                raise RuntimeError("Tahap 1: semua kandidat punya timestamp tidak valid.")

            # Pass 1.5: deterministic diversity-aware pick (no LLM call).
            clips = select_diverse_clips(
                valid_candidates,
                num_clips=args.num_clips,
                min_gap_sec=args.min_clip_gap,
                diversity_threshold=args.diversity_threshold,
            )
            if not clips:
                raise RuntimeError("Seleksi: tidak ada kandidat yang lolos filter keberagaman.")
            if len(clips) < args.num_clips:
                log(
                    f"Seleksi keberagaman: {len(clips)}/{args.num_clips} klip lolos "
                    f"(sisanya terlalu mirip topiknya atau terlalu dempetan) — lanjut dengan yang terbaik.",
                    job_id=job_id,
                )
            for c in clips:
                log(
                    f"  → Klip #{c['index']}: {c.get('title', '?')} "
                    f"(skor {c.get('viral_score', '?')}, {c['start']}s–{c['end']}s)",
                    job_id=job_id,
                )

            # Pass 2: enrich ONLY the selected clips (caption/hashtag/titles).
            enrich_items = [
                {
                    "index": c["index"],
                    "start": c["start"],
                    "end": c["end"],
                    "title": c.get("title", ""),
                    "transcript": build_transcript_slice(segments, c["start"], c["end"]),
                }
                for c in clips
            ]
            enrich_prompt = build_clip_enrichment_prompt(enrich_items, video_summary, mode=args.mode)
            log("Tahap 2/2: AI menulis caption & hashtag untuk klip terpilih...", job_id=job_id)
            enriched = _llm_json_with_retries(
                enrich_prompt, None, llm_endpoint, llm_key, llm_model,
                job_id, label="tahap-2 enrichment",
            )
            by_index = {
                item.get("index"): item
                for item in (enriched.get("clips", []) if isinstance(enriched, dict) else [])
                if isinstance(item, dict)
            }
            for c in clips:
                extra = by_index.get(c["index"], {})
                for key in ("title_options", "caption", "hashtags"):
                    if extra.get(key):
                        c[key] = extra[key]
                if not c.get("title_options"):
                    c["title_options"] = [c.get("title", "Untitled")]

        # ── VALIDASI & BOUNDARY CLAMPING KANDIDAT KLIP ──
        # (total_video_dur sudah dihitung sebelum tahap analisis di atas)
        valid_clips = []
        for raw_clip in clips:
            try:
                c_start = parse_timestamp_to_seconds(raw_clip.get("start", 0.0))
                c_end = parse_timestamp_to_seconds(raw_clip.get("end", 0.0))
                if total_video_dur > 0:
                    c_end = min(total_video_dur, c_end)
                    c_start = min(total_video_dur, c_start)
                if c_end <= c_start:
                    continue
                # Minimal durasi 5 detik agar tidak menghasilkan glitch video
                if (c_end - c_start) < 5.0:
                    continue
                raw_clip["start"] = round(c_start, 2)
                raw_clip["end"] = round(c_end, 2)
                valid_clips.append(raw_clip)
            except (ValueError, TypeError):
                continue

        if not valid_clips:
            raise RuntimeError("Semua kandidat klip yang dihasilkan LLM memiliki durasi tidak valid.")
        clips = valid_clips

        # ── DETERMINISTIC CONTENT RULES (durasi, caption, hashtag, duplikat) ──
        # LLM bagus untuk menemukan momen, tapi tidak konsisten untuk hal mekanis
        # yang paling menentukan performa (completion rate, hashtag hygiene,
        # closing question). Aturan ini dijalankan di kode supaya hasilnya sama
        # terlepas dari model mana yang menjawab.
        before_rules = len(clips)
        clips = apply_content_rules(clips, segments, mode=args.mode)
        if not clips:
            raise RuntimeError("Tidak ada kandidat klip yang lolos aturan kualitas konten.")
        if len(clips) < before_rules:
            log(
                f"{before_rules - len(clips)} klip dibuang karena tumpang tindih dengan klip lain.",
                job_id=job_id,
            )

        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        safe_folder_name = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in video_basename]).strip()
        actual_out_dir = os.path.join(args.out_dir, safe_folder_name)

        resolved_source_wm = (args.source_watermark or get_video_source_name(video_path) or get_video_source_name(args.file) or "").strip()
        resolved_account_wm = (args.account_watermark or "").strip()

        # ── ANALYZE-ONLY: emit JSON result and exit ──
        if args.analyze_only:
            # Add index to each clip for frontend reference
            for i, clip in enumerate(clips, 1):
                clip["index"] = i
                clip["duration"] = round(float(clip.get("end", 0)) - float(clip.get("start", 0)), 2)

            result = {
                "status": "analyzed",
                "video_path": video_path,
                "source_name": resolved_source_wm,
                "source_lang": args.source_lang,
                "mode": args.mode,
                "clips": clips,
                "segments": _serialize_segments(segments),
                "output_dir": actual_out_dir
            }
            # Print with marker so SSE parser can detect it
            print(f"[ANALYSIS_RESULT]{json.dumps(result)}", flush=True)
            if job_id:
                from backend.database import update_job_status
                update_job_status(job_id, "completed")
            os._exit(0)

        os.makedirs(actual_out_dir, exist_ok=True)
        log(f"Extracting clips from {video_path}...", job_id=job_id)
        log(f"Outputs will be saved to: {actual_out_dir}", job_id=job_id)

        for i, clip in enumerate(clips, 1):
            log(f"--- Processing Clip {i}/{len(clips)} ---", job_id=job_id)
            titles = clip.get('title_options', [clip.get('title', 'Unknown Title')])
            log(f"Title: {titles[0] if isinstance(titles, list) and titles else titles}", job_id=job_id)
            log(f"Viral Reason: {clip.get('reason', clip.get('viral_reason'))}", job_id=job_id)
            log(f"Score: {clip.get('viral_score')}", job_id=job_id)
            if clip.get("hook_line"):
                log(f"Hook line: {clip['hook_line']}", job_id=job_id)

            try:
                extract_and_format_clip(
                    video_path, clip, i, segments, actual_out_dir,
                    job_id=job_id,
                    sub_style=args.sub_style,
                    framing_mode=args.framing_mode,
                    sub_position=args.sub_position,
                    watermark_enabled=args.watermark_enabled,
                    source_watermark=resolved_source_wm,
                    account_watermark=resolved_account_wm,
                )
            except Exception as e:
                log(f"Failed to render clip {i}: {e}", job_id=job_id)
                raise RuntimeError(f"Fail-fast aborted: Failed to render clip {i} ({e})") from e

        log("All done! Check your output directory.", job_id=job_id)
        if job_id:
            update_job_status(job_id, "completed")

        # Force hard exit to prevent CTranslate2 destructor segfault during interpreter shutdown
        os._exit(0)

    except Exception as e:
        import traceback
        log(f"Error: {e}", job_id=job_id)
        log(traceback.format_exc(), job_id=job_id)
        if job_id:
            update_job_status(job_id, "failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
