import os
import urllib.request
from backend.utils import log, format_ass_timestamp, run_command, TEMP_DIR
from moviepy import VideoFileClip
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blaze_face_short_range.tflite")

def generate_ass_subtitles(segments, out_ass_path, clip_start, clip_end, title_hook=None, sub_style="tiktok_viral"):
    """Generate .ass subtitle file with the specified style."""
    
    # Collect words from segments
    words = []
    for seg in segments:
        if seg["end"] < clip_start or seg["start"] > clip_end: continue
        if "words" in seg: 
            words.extend(seg["words"])
        else: 
            words.append({"word": seg["text"], "start": seg["start"], "end": seg["end"]})

    if sub_style == "karaoke":
        _generate_karaoke_style(words, out_ass_path, clip_start, clip_end)
    elif sub_style == "minimalist":
        _generate_minimalist_style(words, out_ass_path, clip_start, clip_end)
    elif sub_style == "word_pop":
        _generate_word_pop_style(words, out_ass_path, clip_start, clip_end)
    else:
        _generate_tiktok_viral_style(words, out_ass_path, clip_start, clip_end)


def _chunk_words(words, clip_start, clip_end, max_words=3, max_chars=18, uppercase=False):
    """Split words into display chunks."""
    chunks, current_chunk = [], []
    for word_info in words:
        w_start = max(0, word_info["start"] - clip_start)
        w_end = min(clip_end - clip_start, word_info["end"] - clip_start)
        text = word_info["word"].strip()
        if uppercase:
            text = text.upper()
        if not text: continue
        current_chunk.append({"word": text, "start": w_start, "end": w_end})
        if len(current_chunk) >= max_words or sum(len(w["word"]) for w in current_chunk) > max_chars or text[-1] in ".?!,":
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk: chunks.append(current_chunk)
    return chunks


def _generate_tiktok_viral_style(words, out_ass_path, clip_start, clip_end):
    """🎬 TikTok Viral: Bold white + yellow highlight pop on active word."""
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralStyle,Impact,115,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,12,7,2,60,60,650,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    chunks = _chunk_words(words, clip_start, clip_end, uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
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


def _generate_karaoke_style(words, out_ass_path, clip_start, clip_end):
    """🎤 Classic Karaoke: Words appear cumulatively, active word highlighted green."""
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokeStyle,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,80,80,650,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Build sentence-level chunks (bigger groups for karaoke feel)
    chunks = _chunk_words(words, clip_start, clip_end, max_words=6, max_chars=35, uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for chunk in chunks:
            # Each word in chunk: show all previous words (white) + current word (green) 
            # Words accumulate and stay visible
            for i in range(len(chunk)):
                start_ass = format_ass_timestamp(chunk[i]["start"])
                end_ass = format_ass_timestamp(chunk[i]["end"])
                display = []
                for j in range(len(chunk)):
                    if j < i:
                        # Already spoken words — white
                        display.append(chunk[j]["word"])
                    elif j == i:
                        # Active word — highlighted green
                        display.append(f"{{\\c&H00FF00&}}{chunk[j]['word']}{{\\c&HFFFFFF&}}")
                    else:
                        # Future words — dim/semi-transparent
                        display.append(f"{{\\alpha&H80&}}{chunk[j]['word']}{{\\alpha&H00&}}")
                f.write(f"Dialogue: 0,{start_ass},{end_ass},KaraokeStyle,,0,0,0,,{' '.join(display)}\n")


def _generate_minimalist_style(words, out_ass_path, clip_start, clip_end):
    """📄 Minimalist: Clean static text, no animation, modern font."""
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MinimalStyle,Arial,75,&H00FFFFFF,&H000000FF,&H50000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,120,120,350,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Group into sentence-level chunks (longer groups, static display)
    chunks = _chunk_words(words, clip_start, clip_end, max_words=6, max_chars=35, uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for chunk in chunks:
            if not chunk: continue
            chunk_start = format_ass_timestamp(chunk[0]["start"])
            chunk_end = format_ass_timestamp(chunk[-1]["end"])
            text = " ".join(w["word"] for w in chunk)
            # Simple static text — no effects, no highlight
            f.write(f"Dialogue: 0,{chunk_start},{chunk_end},MinimalStyle,,0,0,0,,{text}\n")


def _generate_word_pop_style(words, out_ass_path, clip_start, clip_end):
    """💥 Word Pop (Reels): Single word pops in center, one at a time."""
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: WordPop,Impact,140,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,10,5,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for word_info in words:
            w_start = max(0, word_info["start"] - clip_start)
            w_end = min(clip_end - clip_start, word_info["end"] - clip_start)
            text = word_info["word"].strip()
            if not text: continue
            start_ass = format_ass_timestamp(w_start)
            end_ass = format_ass_timestamp(w_end)
            # Each word appears alone, centered, with slight scale-in effect
            f.write(f"Dialogue: 0,{start_ass},{end_ass},WordPop,,0,0,0,,{{\\fscx110\\fscy110\\t(0,80,\\fscx100\\fscy100)}}{text}\n")

def download_model(job_id=None):
    if not os.path.exists(MODEL_PATH):
        log("Downloading AI Face Detection model (BlazeFace)...", job_id=job_id)
        url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
        urllib.request.urlretrieve(url, MODEL_PATH)

from proglog import ProgressBarLogger

class MoviePyLogger(ProgressBarLogger):
    def __init__(self, job_id=None):
        super().__init__()
        self.job_id = job_id
        import time
        self.start_time = time.time()
        self.last_log_time = 0

    def bars_callback(self, bar, attr, value, old_value=None):
        import time
        current_time = time.time()
        if current_time - self.last_log_time < 1.0: return
        
        total = self.bars[bar]['total']
        if total > 0:
            percent = (value / total) * 100
            elapsed = current_time - self.start_time
            if percent > 0:
                eta = elapsed / (percent / 100) - elapsed
                from backend.utils import format_timestamp
                eta_str = format_timestamp(eta).split('.')[0]
                log(f"Progress Smart Crop: {percent:.1f}% | Sisa Waktu (ETA): {eta_str}", job_id=self.job_id)
                self.last_log_time = current_time

def apply_smart_crop(video_path, start_time, end_time, output_path, job_id=None):
    download_model(job_id=job_id)
    log(f"Applying AI Smart Crop (Cinematic Face Tracking v2)...", job_id=job_id)
    
    clip = VideoFileClip(video_path).subclipped(start_time, end_time)
    
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=0.65  # Filter weak/false detections
    )
    detector = vision.FaceDetector.create_from_options(options)

    width, height = clip.size
    target_width = int(height * 9 / 16)
    
    if target_width % 2 != 0: target_width -= 1
    if target_width > width:
        target_width = width
        if target_width % 2 != 0: target_width -= 1

    # ── Tracking State ──
    # Boundary limits for camera center
    MIN_CENTER_X = target_width / 2
    MAX_CENTER_X = width - (target_width / 2)
    
    # Double exponential smoothing (position + velocity)
    smoothed_x = width / 2          # Current smoothed camera position
    velocity_x = 0.0                # Current camera velocity (for momentum)
    target_x = width / 2            # Raw detection target
    
    # Tuning parameters
    DETECT_INTERVAL = 3             # Detect face every N frames (more responsive)
    POSITION_ALPHA = 0.06           # Position smoothing factor (lower = smoother)
    VELOCITY_ALPHA = 0.03           # Velocity damping factor (lower = more cinematic)
    DEAD_ZONE = width * 0.015       # Ignore movements smaller than 1.5% of width
    MAX_VELOCITY = width * 0.02     # Max camera speed per frame (2% of width)
    MIN_FACE_AREA = (width * 0.03) * (height * 0.03)  # Minimum face bounding box area to track
    
    # Face loss handling
    frames_since_detection = 0       # Counter since last successful detection
    FACE_LOSS_PATIENCE = 30          # Frames to wait before drifting to center
    CENTER_DRIFT_SPEED = 0.005       # Slow drift speed toward center when face is lost
    
    # Detection history for stability (rolling median)
    detection_history = []
    HISTORY_SIZE = 5                 # Number of recent detections to keep
    
    frame_count = 0

    def _clamp_center(cx):
        """Clamp camera center X within valid crop boundaries."""
        return max(MIN_CENTER_X, min(cx, MAX_CENTER_X))
    
    def _get_median(values):
        """Get median of a list of values for noise reduction."""
        if not values: return None
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        return sorted_vals[mid]

    def process_frame(frame):
        nonlocal frame_count, smoothed_x, velocity_x, target_x
        nonlocal frames_since_detection, detection_history
        
        # ── Face Detection (every N frames) ──
        if frame_count % DETECT_INTERVAL == 0:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            detection_result = detector.detect(mp_image)
            
            valid_faces = []
            if detection_result.detections:
                for detection in detection_result.detections:
                    # Filter by confidence score
                    score = detection.categories[0].score if detection.categories else 0
                    if score < 0.65:
                        continue
                    
                    bbox = detection.bounding_box
                    face_area = bbox.width * bbox.height
                    
                    # Filter tiny detections (noise/artifacts)
                    if face_area < MIN_FACE_AREA:
                        continue
                    
                    face_center_x = bbox.origin_x + (bbox.width / 2)
                    face_center_y = bbox.origin_y + (bbox.height / 2)
                    
                    # Filter faces that are outside reasonable vertical range
                    # (skip detections near very top/bottom edges — likely artifacts)
                    if face_center_y < height * 0.05 or face_center_y > height * 0.95:
                        continue
                    
                    valid_faces.append({
                        "center_x": face_center_x,
                        "area": face_area,
                        "score": score,
                        "distance": abs(face_center_x - smoothed_x)
                    })
            
            if valid_faces:
                # Score faces: prefer large faces close to current position
                # Weight: 60% proximity to current camera, 40% face area (larger = more important)
                max_area = max(f["area"] for f in valid_faces)
                max_dist = max(f["distance"] for f in valid_faces) or 1
                
                best_face = None
                best_score = -1
                
                for face in valid_faces:
                    proximity_score = 1.0 - (face["distance"] / max_dist) if max_dist > 0 else 1.0
                    area_score = face["area"] / max_area if max_area > 0 else 0
                    combined = (proximity_score * 0.6) + (area_score * 0.4)
                    
                    if combined > best_score:
                        best_score = combined
                        best_face = face
                
                if best_face:
                    raw_target = _clamp_center(best_face["center_x"])
                    
                    # Add to rolling history for temporal stability
                    detection_history.append(raw_target)
                    if len(detection_history) > HISTORY_SIZE:
                        detection_history.pop(0)
                    
                    # Use median of recent detections (removes outlier jitter)
                    median_target = _get_median(detection_history)
                    if median_target is not None:
                        target_x = median_target
                    
                    frames_since_detection = 0
            else:
                frames_since_detection += 1
        else:
            frames_since_detection += 1
        
        # ── Camera Movement Logic ──
        
        # If face has been lost for too long, slowly drift toward center
        if frames_since_detection > FACE_LOSS_PATIENCE:
            center_x = width / 2
            target_x = target_x + (center_x - target_x) * CENTER_DRIFT_SPEED
            # Clear detection history since face is lost
            detection_history.clear()
        
        # Calculate desired movement
        delta = target_x - smoothed_x
        
        # Apply dead zone — ignore micro-movements to prevent jitter
        if abs(delta) < DEAD_ZONE:
            delta = 0
        
        # Double exponential smoothing:
        # Update velocity with damping
        velocity_x = velocity_x * (1 - VELOCITY_ALPHA) + delta * POSITION_ALPHA * VELOCITY_ALPHA
        
        # Clamp velocity to prevent sudden jumps
        velocity_x = max(-MAX_VELOCITY, min(velocity_x, MAX_VELOCITY))
        
        # Update position with both smoothed delta and velocity (cinematic momentum)
        smoothed_x = smoothed_x + delta * POSITION_ALPHA + velocity_x
        
        # Ensure smoothed position stays within valid bounds
        smoothed_x = _clamp_center(smoothed_x)
        
        # ── Crop Frame ──
        frame_count += 1
        
        # Calculate crop coordinates with sub-pixel precision then round
        x1 = int(round(smoothed_x - target_width / 2))
        x2 = x1 + target_width
        
        # Safety clamp (should never trigger due to _clamp_center, but just in case)
        if x1 < 0:
            x1 = 0
            x2 = target_width
        if x2 > width:
            x2 = width
            x1 = width - target_width
        
        return frame[:, x1:x2]

    cropped_clip = clip.image_transform(process_frame)
    my_logger = MoviePyLogger(job_id=job_id)
    
    try:
        cropped_clip.write_videofile(
            output_path, 
            codec="h264_nvenc",
            audio_codec="aac",
            bitrate="8000k",
            temp_audiofile=output_path.replace(".mov", "_temp.m4a"),
            remove_temp=True,
            ffmpeg_params=["-pix_fmt", "yuv420p"],
            logger=my_logger
        )
    except Exception as e:
        log(f"NVENC failed ({e}), falling back to safer NVENC preset (p2)...", job_id=job_id)
        try:
            cropped_clip.write_videofile(
                output_path, 
                codec="h264_nvenc",
                audio_codec="aac",
                bitrate="8000k",
                temp_audiofile=output_path.replace(".mov", "_temp.m4a"),
                remove_temp=True,
                ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "p2", "-profile:v", "main"],
                logger=my_logger
            )
        except Exception as e2:
            log(f"Safer NVENC also failed ({e2}), falling back to CPU (libx264)...", job_id=job_id)
            cropped_clip.write_videofile(
                output_path, 
                codec="libx264",
                audio_codec="aac",
                bitrate="8000k",
                temp_audiofile=output_path.replace(".mov", "_temp.m4a"),
                remove_temp=True,
                ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "fast"],
                logger=my_logger
            )
    
    clip.close()
    cropped_clip.close()
    log("Progress Smart Crop: 100.0% | Sisa Waktu (ETA): 00:00:00 | Smart Crop Selesai.", job_id=job_id)
    return output_path

def extract_and_format_clip(video_path, clip_info, index, segments, out_dir, job_id=None, sub_style="tiktok_viral"):
    start = max(0.0, float(clip_info.get("start", 0.0)) - 0.2)
    end = float(clip_info.get("end", 0.0)) + 1.2
    duration = end - start
    fade_out_start = max(0.0, duration - 0.5)
    
    title_options = clip_info.get("title_options", [clip_info.get("title", f"clip_{index}")])
    title = title_options[0] if isinstance(title_options, list) and title_options else title_options
    title_hook = clip_info.get("title_hook", "")
    
    safe_title = "".join(c if c.isalnum() else "_" for c in title).strip("_")
    out_file = os.path.join(out_dir, f"{index:02d}_{safe_title}.mov")
    temp_crop_file = os.path.join(TEMP_DIR, f"temp_crop_{index}.mov")
    caption_file = os.path.join(out_dir, f"{index:02d}_{safe_title}.txt")
    
    caption_text = clip_info.get("caption", title)
    hashtags = clip_info.get("hashtags", [])
    hashtags_text = " ".join(hashtags) if isinstance(hashtags, list) else hashtags
    titles_text = "\n".join([f"- {t}" for t in title_options]) if isinstance(title_options, list) else title_options
    
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(f"Title Options:\n{titles_text}\n\nTitle Hook (0-1s): {title_hook}\n\nCaption:\n{caption_text}\n\nHashtags:\n{hashtags_text}")
    
    ass_file = os.path.join(TEMP_DIR, f"temp_{index}.ass")
    generate_ass_subtitles(segments, ass_file, start, end, title_hook=title_hook, sub_style=sub_style)
    
    escaped_ass = ass_file.replace('\\', '/').replace(':', '\\:')
    
    af_filter = f"highpass=f=100,acompressor=threshold=-20dB:ratio=4:attack=5:release=50:makeup=8dB,afade=t=out:st={fade_out_start}:d=0.5"
    
    try:
        apply_smart_crop(video_path, start, end, temp_crop_file, job_id=job_id)
            
        log(f"Rendering Subtitles, Audio Enhancer, and Color Grading for Clip {index}: {title}", job_id=job_id)
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
            run_command(cmd, f"Burning subtitles (NVENC)...", job_id=job_id, duration=duration)
        except Exception as e:
            log(f"NVENC Encoding failed: {e}. Falling back to safer NVENC preset...", job_id=job_id)
            cmd = [
                "ffmpeg", "-y", "-i", temp_crop_file,
                "-vf", vf_filter,
                "-af", af_filter,
                "-c:v", "h264_nvenc", "-preset", "p2", "-profile:v", "main", "-b:v", "8M",
                "-c:a", "aac", "-b:a", "192k",
                out_file
            ]
            try:
                run_command(cmd, f"Burning subtitles (Safer NVENC)...", job_id=job_id, duration=duration)
            except Exception as e2:
                log(f"Safer NVENC failed: {e2}. Falling back to libx264 (CPU)...", job_id=job_id)
                cmd = [
                    "ffmpeg", "-y", "-i", temp_crop_file,
                    "-vf", vf_filter,
                    "-af", af_filter,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k",
                    out_file
                ]
                run_command(cmd, f"Burning subtitles (libx264)...", job_id=job_id, duration=duration)
            
    except Exception as e:
        log(f"Face tracking error, using simple ffmpeg center crop: {e}", job_id=job_id)
        vf_filter = f"crop=ih*9/16:ih,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp,subtitles='{escaped_ass}',fade=t=out:st={fade_out_start}:d=0.5"
        
        def build_fallback_cmd(codec_params):
            return [
                "ffmpeg", "-y", "-ss", str(start), "-t", str(end - start), "-i", video_path,
                "-vf", vf_filter,
                "-af", af_filter
            ] + codec_params + [out_file]

        try:
            run_command(build_fallback_cmd(["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "18", "-b:v", "8M", "-c:a", "aac", "-b:a", "192k"]), f"Fallback processing for Clip {index} (NVENC)...", job_id=job_id, duration=duration)
        except Exception as err:
            log(f"Fallback NVENC failed, trying safer preset... {err}", job_id=job_id)
            try:
                run_command(build_fallback_cmd(["-c:v", "h264_nvenc", "-preset", "p2", "-profile:v", "main", "-b:v", "8M", "-c:a", "aac", "-b:a", "192k"]), f"Fallback processing for Clip {index} (Safer NVENC)...", job_id=job_id, duration=duration)
            except Exception as err2:
                log(f"Safer NVENC failed, trying libx264... {err2}", job_id=job_id)
                run_command(build_fallback_cmd(["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]), f"Fallback processing for Clip {index} (libx264)...", job_id=job_id, duration=duration)
    
    for tmp in [ass_file, temp_crop_file]:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception as e:
            log(f"Warning: Could not remove temp file {tmp}: {e}", job_id=job_id)
        
    return out_file
