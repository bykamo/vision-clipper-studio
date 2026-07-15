"""
Hook-Cutter
=================
A single-file, local-first pipeline that:
  1. Downloads a video from YouTube (or takes a local file)
  2. Transcribes it with OpenAI Whisper (GPU/CUDA if available), including word-level timestamps
  3. Sends the transcript to a local LLM endpoint (default: 9Router, OpenAI-compatible)
     for "viral segment" / watch-time analysis
  4. Generates CapCut-style viral subtitles (.ass format)
  5. Cuts the chosen segments out with ffmpeg, automatically crops to 9:16 vertical,
     and burns in the viral subtitles.

Requirements:
    pip install faster-whisper torch requests opencv-python yt-dlp

External requirements (must be installed separately and on PATH):
    - ffmpeg / ffprobe, built with libass support (needed for burned-in captions)
"""

import argparse
import json
import os
import subprocess
import sys
import re
import shutil
import tempfile
from datetime import datetime

import requests
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from moviepy import VideoFileClip
import urllib.request

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Load .env file — check project root first, then cwd
def _load_env():
    """Load .env from project root (where this script lives) or cwd."""
    # Project root = parent of vision_clipper/ folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    candidates = [
        os.path.join(project_root, ".env"),   # e.g. clip tools test/.env
        os.path.join(os.getcwd(), ".env"),     # fallback: current working dir
    ]
    
    for env_path in candidates:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            os.environ[parts[0].strip()] = parts[1].strip()
            break  # Only load the first .env found

_load_env()

DEFAULT_ENDPOINT = os.environ.get("ROUTER_API_ENDPOINT", "")
DEFAULT_OUT_DIR = os.path.join(os.getcwd(), "clips")
DEFAULT_API_KEY = os.environ.get("ROUTER_API_KEY", "")
DEFAULT_LLM_MODEL = "ag/gemini-3.5-flash-low"

# Output resolution untuk 9:16 vertical short-form
VERTICAL_WIDTH = 1080
VERTICAL_HEIGHT = 1920

# --------------------------------------------------------------------------- #
# Utility / shell helpers
# --------------------------------------------------------------------------- #

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    msg = f"[{timestamp}] {message}"
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'), flush=True)

def run_command(cmd_list, description=""):
    if description:
        log(description)
    log("Running: " + " ".join(str(c) for c in cmd_list))
    result = subprocess.run(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        log("Command failed with output:\n" + result.stdout)
        raise RuntimeError(f"Command failed: {' '.join(str(c) for c in cmd_list)}")
    return result.stdout

def check_dependencies():
    missing = []
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if shutil.which("ffprobe") is None:
        missing.append("ffprobe")

    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        missing.append("faster-whisper (pip install faster-whisper)")

    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        missing.append("yt-dlp (pip install yt-dlp)")

    try:
        import torch  # noqa: F401
    except ImportError:
        missing.append("torch (pip install torch)")

    if missing:
        log("Missing dependencies detected: " + ", ".join(missing))
        log("Please install the missing dependencies before running again.")
        sys.exit(1)

# --------------------------------------------------------------------------- #
# Step 1: Load Video
# --------------------------------------------------------------------------- #

def get_video_file(args):
    if not args.file:
        log("Error: You must provide --file")
        sys.exit(1)
        
    video_path = os.path.abspath(args.file)
    if not os.path.isfile(video_path):
        log(f"Error: Local file not found: {args.file}")
        sys.exit(1)
    
    return video_path

# --------------------------------------------------------------------------- #
# Step 2: Transcribe with Whisper (Word-Level)
# --------------------------------------------------------------------------- #

def transcribe_video(video_path, model_size="small"):
    from faster_whisper import WhisperModel
    import torch

    log("Extracting audio to .wav to prevent VRAM leak and speed up Whisper...")
    temp_audio_path = tempfile.mktemp(suffix=".wav")
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", 
        temp_audio_path
    ]
    try:
        run_command(extract_cmd, "Extracting Audio to WAV")
    except Exception as e:
        log(f"Audio extraction failed: {e}. Falling back to original video file.")
        temp_audio_path = video_path

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Using float16 if cuda is available, else int8
    compute_type = "float16" if device == "cuda" else "int8"
    
    log(f"Loading Faster-Whisper model '{model_size}' on device: {device} ({compute_type})")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    log("Transcribing audio (extracting word-level timestamps with VAD)...")
    # Using word_timestamps=True is critical for CapCut style subtitles
    segments_generator, info = model.transcribe(temp_audio_path, language="id", word_timestamps=True, vad_filter=True)

    log(f"Audio duration: {info.duration:.1f} seconds. Starting transcription...")
    segments = []
    
    import time
    start_time = time.time()
    
    for segment in segments_generator:
        words_list = []
        if segment.words:
            for word in segment.words:
                words_list.append({
                    "word": word.word,
                    "start": word.start,
                    "end": word.end
                })
        
        segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": words_list
        })
        
        # Cetak progress persentase dan ETA agar tidak terlihat 'stuck'
        percent = (segment.end / info.duration) * 100
        elapsed = time.time() - start_time
        if percent > 0:
            eta_seconds = elapsed / (percent / 100) - elapsed
            eta_str = format_timestamp(eta_seconds).split(".")[0] # Format HH:MM:SS
        else:
            eta_str = "Menghitung..."
            
        print(f"\rProgress Transkripsi: {percent:.1f}% | Sisa Waktu (ETA): {eta_str} | ({segment.end:.1f}s / {info.duration:.1f}s) ", end="", flush=True)

    print() # Pindah ke baris baru setelah selesai 100%
    log(f"Transcription complete. {len(segments)} segments found.")
    
    if temp_audio_path != video_path and os.path.exists(temp_audio_path):
        os.remove(temp_audio_path)
        
    return segments

def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"

def format_ass_timestamp(seconds):
    # ASS timestamp format: H:MM:SS.cc
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    # cap to 2 decimal places for ASS
    return f"{hrs}:{mins:02d}:{secs:05.2f}"

def build_transcript_text(segments):
    lines = []
    for seg in segments:
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"].strip()
        lines.append(f"[{start} --> {end}] {text}")
    return "\n".join(lines)

# --------------------------------------------------------------------------- #
# Step 3: Subtitle Generation (Viral CapCut Style)
# --------------------------------------------------------------------------- #

def generate_ass_subtitles(segments, out_ass_path, clip_start, clip_end, title_hook=None):
    # Setingan Viral: Font Impact/Montserrat-Black, Outline tebal, Shadow agak geser ke bawah
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralStyle,Impact,115,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,12,7,2,60,60,650,1
Style: TitleHookStyle,Impact,140,&H0000FFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,15,10,8,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        
        if title_hook and title_hook.strip():
            # Add the title hook for the first 1.5 seconds at the top (Alignment 8)
            safe_title_hook = title_hook.strip().upper().replace("\n", "\\N")
            f.write(f"Dialogue: 0,0:00:00.00,0:00:01.50,TitleHookStyle,,0,0,0,,{safe_title_hook}\n")
            
        words = []
        for seg in segments:
            if seg["end"] < clip_start or seg["start"] > clip_end: continue
            if "words" in seg: 
                words.extend(seg["words"])
            else: 
                words.append({"word": seg["text"], "start": seg["start"], "end": seg["end"]})

        chunks, current_chunk = [], []
        for word_info in words:
            w_start = max(0, word_info["start"] - clip_start)
            w_end = min(clip_end - clip_start, word_info["end"] - clip_start)
            
            # PAKSA HURUF BESAR SEMUA (Syarat mutlak konten viral)
            text = word_info["word"].strip().upper() 
            if not text: continue
            
            current_chunk.append({"word": text, "start": w_start, "end": w_end})
            
            # Jangan biarkan teks numpuk lebih dari 3-4 kata (biar cepat pergantiannya)
            if len(current_chunk) >= 3 or sum(len(w["word"]) for w in current_chunk) > 18 or text[-1] in ".?!,":
                chunks.append(current_chunk)
                current_chunk = []
        
        if current_chunk: chunks.append(current_chunk)
            
        for chunk in chunks:
            for i in range(len(chunk)):
                start_ass = format_ass_timestamp(chunk[i]["start"])
                end_ass = format_ass_timestamp(chunk[i]["end"])
                display = []
                for j in range(len(chunk)):
                    if j < i: 
                        display.append(chunk[j]["word"])
                    elif j == i: 
                        display.append(f"{{\\c&H0000FFFF&}}{{\\fs125}}{chunk[j]['word']}{{\\fs115}}{{\\c&HFFFFFF&}}")
                    else: 
                        display.append(f"{{\\alpha&HFF&}}{chunk[j]['word']}{{\\alpha&H00&}}")
                
                f.write(f"Dialogue: 0,{start_ass},{end_ass},ViralStyle,,0,0,0,,{' '.join(display)}\n")


# --------------------------------------------------------------------------- #
# Step 4: Viral Analysis via LLM
# --------------------------------------------------------------------------- #

def build_viral_prompt(transcript_text, num_clips, min_len, max_len):
    prompt = f"""
You are a top-tier viral content strategist for TikTok, YouTube Shorts, and Instagram Reels.
Your only goal is to maximize RETENTION, ENGAGEMENT, and VIRALITY.

Below is a timestamped transcript of a long-form video. Each line follows the format:
[HH:MM:SS.mmm --> HH:MM:SS.mmm] spoken text

Your task for EACH of the {num_clips} distinct clips:
- Identify exactly {num_clips} distinct segments with the HIGHEST VIRAL POTENTIAL.
- Look for: Controversial statements, mind-blowing facts, high emotional peaks, funny moments, or immediate strong hooks.
- Each segment MUST be between {min_len} and {max_len} seconds long.
- Segments must not overlap.
- SEO & VIRAL METADATA: Generate 3 highly engaging title options, 1 short clickbait text (`title_hook`) for the first second of the video, and 10 highly relevant SEO hashtags based on the video's niche.

Respond with ONLY valid JSON, no explanation, no markdown formatting.
Use exactly this schema:

{{
  "clips": [
    {{
      "start": 12.5,
      "end": 45.0,
      "title_options": ["Title Option 1", "Title Option 2", "Title Option 3"],
      "title_hook": "Teks clickbait 1 detik pertama",
      "reason": "Why this will go viral (hook, peak emotion, etc.)",
      "viral_score": 95,
      "caption": "A highly engaging TikTok/Reels caption with emojis",
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"]
    }}
  ]
}}

Transcript:
{transcript_text}
"""
    return prompt


def call_llm_api(prompt, model_name, endpoint, api_key):
    # Auto-append /chat/completions if the endpoint is just a base URL
    if not endpoint.rstrip('/').endswith('/chat/completions'):
        endpoint = endpoint.rstrip('/') + '/chat/completions'
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.7,
    }

    log(f"Sending transcript to '{model_name}' via {endpoint} for viral analysis...")
    response = requests.post(endpoint, json=payload, headers=headers, timeout=600)
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        log("Unexpected response shape from LLM endpoint: " + json.dumps(data)[:500])
        return ""


def extract_json_block(raw_text):
    text = raw_text.strip()
    
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        # Fallback: find the first { and last }
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx+1]
            
    # Remove trailing commas that break json.loads
    text = re.sub(r',\s*([\]}])', r'\1', text)
        
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        log("Failed to parse LLM output as JSON:")
        log(text)
        raise RuntimeError("LLM did not return valid JSON.") from e


# --------------------------------------------------------------------------- #
# Step 5: Render and Cut
# --------------------------------------------------------------------------- #

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blaze_face_short_range.tflite")

def download_model():
    if not os.path.exists(MODEL_PATH):
        log("Downloading AI Face Detection model (BlazeFace)...")
        url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
        urllib.request.urlretrieve(url, MODEL_PATH)

def apply_smart_crop(video_path, start_time, end_time, output_path):
    download_model()
    log(f"Applying AI Smart Crop (Tracking Face with Cinematic Gimbal)...")
    
    # Load the clip and get only the segment we want
    clip = VideoFileClip(video_path).subclipped(start_time, end_time)
    
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceDetectorOptions(base_options=base_options)
    detector = vision.FaceDetector.create_from_options(options)

    width, height = clip.size
    target_width = int(height * 9 / 16)
    
    if target_width % 2 != 0:
        target_width -= 1
    if target_width > width:
        target_width = width
        if target_width % 2 != 0:
            target_width -= 1

    CAMERA_SPEED = 0.05
    frame_count = 0
    last_center_x = width / 2
    smoothed_x = width / 2

    def process_frame(frame):
        nonlocal frame_count, last_center_x, smoothed_x
        
        # Skip frame optimization
        if frame_count % 5 == 0:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            detection_result = detector.detect(mp_image)
            
            if detection_result.detections:
                # Podcast Mode: Lock onto the face closest to the camera center
                best_face_center_x = None
                min_distance = float('inf')
                
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    face_center_x = bbox.origin_x + (bbox.width / 2)
                    distance = abs(face_center_x - smoothed_x)
                    if distance < min_distance:
                        min_distance = distance
                        best_face_center_x = face_center_x
                
                face_center_x = best_face_center_x
                min_x = target_width / 2
                max_x = width - (target_width / 2)
                last_center_x = max(min_x, min(face_center_x, max_x))
                
        frame_count += 1
        
        # EMA Camera Smoothing
        smoothed_x = smoothed_x + (last_center_x - smoothed_x) * CAMERA_SPEED
        
        x1 = int(smoothed_x - target_width / 2)
        x2 = int(smoothed_x + target_width / 2)
        
        x1 = max(0, x1)
        x2 = min(width, x1 + target_width)
        
        return frame[:, x1:x2]

    cropped_clip = clip.image_transform(process_frame)
    
    # Render intermediate crop (hardware accelerated with CPU fallback)
    try:
        cropped_clip.write_videofile(
            output_path, 
            codec="h264_nvenc",
            audio_codec="aac",
            bitrate="8000k", # Paksa bitrate tinggi untuk TikTok
            temp_audiofile=output_path.replace(".mov", "_temp.m4a"),
            remove_temp=True,
            ffmpeg_params=["-pix_fmt", "yuv420p"],
            logger="bar" # Tampilkan progress bar
        )
    except Exception as e:
        log(f"NVENC failed ({e}), falling back to safer NVENC preset (p2)...")
        try:
            cropped_clip.write_videofile(
                output_path, 
                codec="h264_nvenc",
                audio_codec="aac",
                bitrate="8000k",
                temp_audiofile=output_path.replace(".mov", "_temp.m4a"),
                remove_temp=True,
                ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "p2", "-profile:v", "main"],
                logger="bar"
            )
        except Exception as e2:
            log(f"Safer NVENC also failed ({e2}), falling back to CPU (libx264)...")
            cropped_clip.write_videofile(
                output_path, 
                codec="libx264",
                audio_codec="aac",
                bitrate="8000k", # Paksa bitrate tinggi untuk TikTok
                temp_audiofile=output_path.replace(".mov", "_temp.m4a"),
                remove_temp=True,
                ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "fast"],
                logger="bar" # Tampilkan progress bar
            )
    
    clip.close()
    cropped_clip.close()
    return output_path

def extract_and_format_clip(video_path, clip_info, index, segments, out_dir):
    # Tambahkan padding ekstra agar potongan tidak terputus tiba-tiba di akhir kalimat
    start = max(0.0, float(clip_info.get("start", 0.0)) - 0.2)
    end = float(clip_info.get("end", 0.0)) + 1.2
    duration = end - start
    fade_out_start = max(0.0, duration - 0.5)
    
    title_options = clip_info.get("title_options", [clip_info.get("title", f"clip_{index}")])
    title = title_options[0] if isinstance(title_options, list) and title_options else title_options
    title_hook = clip_info.get("title_hook", "")
    
    safe_title = "".join(c if c.isalnum() else "_" for c in title).strip("_")
    out_file = os.path.join(out_dir, f"{index:02d}_{safe_title}.mov")
    temp_crop_file = os.path.join(out_dir, f"temp_crop_{index}.mov")
    caption_file = os.path.join(out_dir, f"{index:02d}_{safe_title}.txt")
    
    # Simpan caption dan hashtag ke file teks
    caption_text = clip_info.get("caption", title)
    hashtags = clip_info.get("hashtags", [])
    hashtags_text = " ".join(hashtags) if isinstance(hashtags, list) else hashtags
    titles_text = "\n".join([f"- {t}" for t in title_options]) if isinstance(title_options, list) else title_options
    
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(f"Title Options:\n{titles_text}\n\nTitle Hook (0-1s): {title_hook}\n\nCaption:\n{caption_text}\n\nHashtags:\n{hashtags_text}")
    
    ass_file = os.path.join(out_dir, f"temp_{index}.ass")
    generate_ass_subtitles(segments, ass_file, start, end, title_hook=title_hook)
    
    escaped_ass = ass_file.replace('\\', '/').replace(':', '\\:')
    
    # Audio Enhancer (highpass filter + compressor) + Audio Fade Out
    af_filter = f"highpass=f=100,acompressor=threshold=-20dB:ratio=4:attack=5:release=50:makeup=8dB,afade=t=out:st={fade_out_start}:d=0.5"
    
    try:
        # TAHAP 1: AI Smart Crop (MediaPipe + MoviePy)
        apply_smart_crop(video_path, start, end, temp_crop_file)
            
        # TAHAP 2: Burn Subtitle, Color Grading & Video Fade Out (FFmpeg)
        log(f"Rendering Subtitles, Audio Enhancer, and Color Grading for Clip {index}: {title}")
        vf_filter = f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp,subtitles='{escaped_ass}',fade=t=out:st={fade_out_start}:d=0.5"
        
        cmd = [
            "ffmpeg", "-y", "-i", temp_crop_file,
            "-vf", vf_filter,
            "-af", af_filter,
            "-c:v", "h264_nvenc", "-preset", "p6", "-cq", "18", "-b:v", "8M",
            "-c:a", "aac", "-b:a", "192k",
            out_file
        ]
        
        try:
            run_command(cmd, f"Burning subtitles (NVENC)...")
        except Exception as e:
            log(f"NVENC Encoding failed: {e}. Falling back to safer NVENC preset...")
            cmd = [
                "ffmpeg", "-y", "-i", temp_crop_file,
                "-vf", vf_filter,
                "-af", af_filter,
                "-c:v", "h264_nvenc", "-preset", "p2", "-profile:v", "main", "-b:v", "8M",
                "-c:a", "aac", "-b:a", "192k",
                out_file
            ]
            try:
                run_command(cmd, f"Burning subtitles (Safer NVENC)...")
            except Exception as e2:
                log(f"Safer NVENC failed: {e2}. Falling back to libx264 (CPU)...")
                cmd = [
                    "ffmpeg", "-y", "-i", temp_crop_file,
                    "-vf", vf_filter,
                    "-af", af_filter,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k",
                    out_file
                ]
                run_command(cmd, f"Burning subtitles (libx264)...")
            
    except Exception as e:
        log(f"Face tracking error, using simple ffmpeg center crop: {e}")
        vf_filter = f"crop=ih*9/16:ih,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp,subtitles='{escaped_ass}',fade=t=out:st={fade_out_start}:d=0.5"
        
        def build_fallback_cmd(codec_params):
            return [
                "ffmpeg", "-y", "-ss", str(start), "-t", str(end - start), "-i", video_path,
                "-vf", vf_filter,
                "-af", af_filter
            ] + codec_params + [out_file]

        try:
            run_command(build_fallback_cmd(["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "18", "-b:v", "8M", "-c:a", "aac", "-b:a", "192k"]), f"Fallback processing for Clip {index} (NVENC)...")
        except Exception as err:
            log(f"Fallback NVENC failed, trying safer preset... {err}")
            try:
                run_command(build_fallback_cmd(["-c:v", "h264_nvenc", "-preset", "p2", "-profile:v", "main", "-b:v", "8M", "-c:a", "aac", "-b:a", "192k"]), f"Fallback processing for Clip {index} (Safer NVENC)...")
            except Exception as err2:
                log(f"Safer NVENC failed, trying libx264... {err2}")
                run_command(build_fallback_cmd(["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]), f"Fallback processing for Clip {index} (libx264)...")
    
    # Cleanup temp files
    if os.path.exists(ass_file):
        os.remove(ass_file)
    if os.path.exists(temp_crop_file):
        os.remove(temp_crop_file)
        
    return out_file

# --------------------------------------------------------------------------- #
# Main Execution
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="AI Viral Video Clipper")
    parser.add_argument("--file", type=str, help="Path to local video file", required=True)
    parser.add_argument("--num-clips", type=int, default=5, help="Number of clips to generate")
    parser.add_argument("--min-len", type=int, default=15, help="Minimum clip length (seconds)")
    parser.add_argument("--max-len", type=int, default=60, help="Maximum clip length (seconds)")
    parser.add_argument("--model", type=str, default="small", help="Whisper model size (tiny, base, small, medium, large)")
    parser.add_argument("--out-dir", type=str, default=DEFAULT_OUT_DIR, help="Output directory")
    
    args = parser.parse_args()
    
    try:
        check_dependencies()
        
        video_path = get_video_file(args)
        
        segments = transcribe_video(video_path, model_size=args.model)
        transcript_text = build_transcript_text(segments)
        
        prompt = build_viral_prompt(transcript_text, args.num_clips, args.min_len, args.max_len)
        
        # Auto-Retry Logic for LLM JSON
        max_retries = 3
        clips = []
        for attempt in range(max_retries):
            try:
                llm_response = call_llm_api(prompt, DEFAULT_LLM_MODEL, DEFAULT_ENDPOINT, DEFAULT_API_KEY)
                data = extract_json_block(llm_response)
                clips = data.get("clips", [])
                if clips:
                    break
            except Exception as e:
                log(f"LLM API or JSON parsing failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    log("Warning: Failed to get valid clips from LLM after 3 attempts!")
                    sys.exit(1)
        
        # Create a subfolder based on the video filename
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        safe_folder_name = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in video_basename]).strip()
        actual_out_dir = os.path.join(args.out_dir, safe_folder_name)
        os.makedirs(actual_out_dir, exist_ok=True)
        
        log(f"Extracting clips from {video_path}...")
        log(f"Outputs will be saved to: {actual_out_dir}")
        for i, clip in enumerate(clips, 1):
            log(f"--- Processing Clip {i}/{len(clips)} ---")
            titles = clip.get('title_options', [clip.get('title', 'Unknown Title')])
            log(f"Title: {titles[0] if isinstance(titles, list) and titles else titles}")
            log(f"Viral Reason: {clip.get('reason', clip.get('viral_reason'))}")
            log(f"Score: {clip.get('viral_score')}")
            
            try:
                extract_and_format_clip(video_path, clip, i, segments, actual_out_dir)
            except Exception as e:
                log(f"Failed to render clip {i}: {e}")
                
        log("All done! Check your output directory.")

    except Exception as e:
        log(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()