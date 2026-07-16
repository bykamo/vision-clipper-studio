import argparse
import os
import sys
from backend.downloader import get_video_file
from backend.transcriber import transcribe_video, build_transcript_text
from backend.analyzer import build_viral_prompt, call_llm_api, extract_json_block
from backend.renderer import extract_and_format_clip
from backend.utils import log, DEFAULT_LLM_MODEL, DEFAULT_ENDPOINT, DEFAULT_API_KEY, DEFAULT_OUT_DIR

def main():
    parser = argparse.ArgumentParser(description="Vision Clipper Worker")
    parser.add_argument("--file", type=str, required=True, help="Path to video file")
    parser.add_argument("--num-clips", type=int, default=5, help="Number of clips")
    parser.add_argument("--mode", type=str, default="hook", choices=["hook", "affiliate"], help="Analysis mode")
    parser.add_argument("--job-id", type=int, default=None, help="Job ID for DB logging")
    parser.add_argument("--min-len", type=int, default=15, help="Minimum clip length (seconds)")
    parser.add_argument("--max-len", type=int, default=60, help="Maximum clip length (seconds)")
    parser.add_argument("--model", type=str, default="base", help="Whisper model size")
    parser.add_argument("--out-dir", type=str, default=DEFAULT_OUT_DIR, help="Output directory")

    args = parser.parse_args()

    job_id = args.job_id
    if job_id:
        from backend.database import update_job_status
        update_job_status(job_id, "running")

    try:
        video_path = get_video_file(args.file, job_id=job_id)
        
        segments = transcribe_video(video_path, source_url=args.file, model_size=args.model, job_id=job_id)
        transcript_text = build_transcript_text(segments)
        
        prompt = build_viral_prompt(transcript_text, args.num_clips, args.min_len, args.max_len, mode=args.mode)
        
        max_retries = 3
        clips = []
        for attempt in range(max_retries):
            try:
                llm_response = call_llm_api(prompt, DEFAULT_LLM_MODEL, DEFAULT_ENDPOINT, DEFAULT_API_KEY, job_id=job_id)
                data = extract_json_block(llm_response, job_id=job_id)
                clips = data.get("clips", [])
                if clips:
                    break
            except Exception as e:
                log(f"LLM API or JSON parsing failed on attempt {attempt + 1}: {e}", job_id=job_id)
                if attempt == max_retries - 1:
                    log("Warning: Failed to get valid clips from LLM after 3 attempts!", job_id=job_id)
                    sys.exit(1)
        
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        safe_folder_name = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in video_basename]).strip()
        actual_out_dir = os.path.join(args.out_dir, safe_folder_name)
        os.makedirs(actual_out_dir, exist_ok=True)
        
        log(f"Extracting clips from {video_path}...", job_id=job_id)
        log(f"Outputs will be saved to: {actual_out_dir}", job_id=job_id)
        
        for i, clip in enumerate(clips, 1):
            log(f"--- Processing Clip {i}/{len(clips)} ---", job_id=job_id)
            titles = clip.get('title_options', [clip.get('title', 'Unknown Title')])
            log(f"Title: {titles[0] if isinstance(titles, list) and titles else titles}", job_id=job_id)
            log(f"Viral Reason: {clip.get('reason', clip.get('viral_reason'))}", job_id=job_id)
            log(f"Score: {clip.get('viral_score')}", job_id=job_id)
            
            try:
                extract_and_format_clip(video_path, clip, i, segments, actual_out_dir, job_id=job_id)
            except Exception as e:
                log(f"Failed to render clip {i}: {e}", job_id=job_id)
                
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
