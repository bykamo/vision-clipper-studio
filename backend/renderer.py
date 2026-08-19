import os
import sys
import cv2
import numpy as np
from backend.utils import log, format_ass_timestamp, run_command, get_ffmpeg_binary, TEMP_DIR
from moviepy import VideoFileClip
from proglog import ProgressBarLogger

CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_frontalface_default.xml")
PROFILE_CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_profileface.xml")
YUNET_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_detection_yunet_2023mar.onnx")

def _sanitize_word_timestamps(words, clip_start, clip_end, min_word_dur=0.18):
    """
    Sanitize and enforce strictly monotonic, non-overlapping timestamps.
    Prevents subtitle overlapping, flickering, and jumbled text when speaker talks fast.
    """
    cleaned = []
    for w in words:
        w_start = max(0.0, float(w.get("start", 0.0)) - clip_start)
        w_end = min(clip_end - clip_start, float(w.get("end", 0.0)) - clip_start)
        text = str(w.get("word", "")).strip()
        if not text:
            continue
        if w_end <= w_start:
            w_end = w_start + min_word_dur
        cleaned.append({"word": text, "start": w_start, "end": w_end})
        
    if not cleaned:
        return []
        
    cleaned.sort(key=lambda x: x["start"])
    
    # Monotonic clamping: ensure no word overlaps another
    sanitized = []
    for i, w in enumerate(cleaned):
        s = w["start"]
        e = max(w["end"], s + min_word_dur)
        
        if sanitized and s < sanitized[-1]["end"]:
            s = sanitized[-1]["end"]
            e = max(e, s + min_word_dur)
            
        sanitized.append({"word": w["word"], "start": s, "end": e})
        
    return sanitized

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

    # Sanitize timestamps to guarantee clean, non-overlapping flow
    sanitized_words = _sanitize_word_timestamps(words, clip_start, clip_end)

    if sub_style in ["karaoke", "classic_karaoke"]:
        _generate_karaoke_style(sanitized_words, out_ass_path, clip_start, clip_end)
    elif sub_style == "minimalist":
        _generate_minimalist_style(sanitized_words, out_ass_path, clip_start, clip_end)
    elif sub_style == "word_pop":
        _generate_word_pop_style(sanitized_words, out_ass_path, clip_start, clip_end)
    elif sub_style in ["none", "no_subtitle"]:
        pass
    else:
        _generate_tiktok_viral_style(sanitized_words, out_ass_path, clip_start, clip_end)


def _chunk_words(words, max_words=2, max_chars=14, uppercase=False):
    """Split sanitized words into display chunks (compact for mobile screens)."""
    chunks, current_chunk = [], []
    for word_info in words:
        text = word_info["word"].strip()
        if uppercase:
            text = text.upper()
        if not text: continue
        current_chunk.append({"word": text, "start": word_info["start"], "end": word_info["end"]})
        if len(current_chunk) >= max_words or sum(len(w["word"]) for w in current_chunk) > max_chars or text[-1] in ".?!,":
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk: chunks.append(current_chunk)
    return chunks


def _generate_tiktok_viral_style(words, out_ass_path, clip_start, clip_end):
    """🎬 TikTok Viral: Bold white + yellow highlight pop on active word (Mobile Safe-Zone)."""
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralStyle,Impact,88,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,10,5,2,100,100,600,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    chunks = _chunk_words(words, max_words=2, max_chars=14, uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for chunk in chunks:
            for i in range(len(chunk)):
                start_ass = format_ass_timestamp(chunk[i]["start"])
                # Chunk end time matches next word start or chunk end
                next_start = chunk[i+1]["start"] if i + 1 < len(chunk) else chunk[-1]["end"]
                end_ass = format_ass_timestamp(max(chunk[i]["end"], next_start))
                display = []
                for j in range(len(chunk)):
                    if j < i: 
                        display.append(chunk[j]["word"])
                    elif j == i: 
                        display.append(f"{{\\c&H0000FFFF&}}{{\\fs98}}{chunk[j]['word']}{{\\fs88}}{{\\c&HFFFFFF&}}")
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
Style: KaraokeStyle,Arial Black,68,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,100,100,600,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    chunks = _chunk_words(words, max_words=4, max_chars=22, uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for chunk in chunks:
            for i in range(len(chunk)):
                start_ass = format_ass_timestamp(chunk[i]["start"])
                next_start = chunk[i+1]["start"] if i + 1 < len(chunk) else chunk[-1]["end"]
                end_ass = format_ass_timestamp(max(chunk[i]["end"], next_start))
                display = []
                for j in range(len(chunk)):
                    if j < i:
                        display.append(chunk[j]["word"])
                    elif j == i:
                        display.append(f"{{\\c&H00FF00&}}{chunk[j]['word']}{{\\c&HFFFFFF&}}")
                    else:
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
Style: MinimalStyle,Arial Black,65,&H00FFFFFF,&H000000FF,&H50000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,100,100,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    chunks = _chunk_words(words, max_words=4, max_chars=22, uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for chunk in chunks:
            if not chunk: continue
            chunk_start = format_ass_timestamp(chunk[0]["start"])
            chunk_end = format_ass_timestamp(chunk[-1]["end"])
            text = " ".join(w["word"] for w in chunk)
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
Style: WordPop,Impact,110,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,10,5,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for word_info in words:
            start_ass = format_ass_timestamp(word_info["start"])
            end_ass = format_ass_timestamp(word_info["end"])
            text = word_info["word"].strip()
            if not text: continue
            f.write(f"Dialogue: 0,{start_ass},{end_ass},WordPop,,0,0,0,,{{\\fscx110\\fscy110\\t(0,80,\\fscx100\\fscy100)}}{text}\n")

def detect_speaker_anchors(video_path, start_time, end_time, width, height, target_width):
    """
    Scan the clip to find stable discrete speaker anchors (Left, Right, or Center).
    Prevents the camera from wandering into empty spaces or the center of tables.
    """
    yunet_detector = None
    if os.path.exists(YUNET_MODEL_PATH) and hasattr(cv2, 'FaceDetectorYN'):
        try:
            yunet_detector = cv2.FaceDetectorYN.create(
                YUNET_MODEL_PATH, "", (width, height),
                score_threshold=0.60, nms_threshold=0.3
            )
        except Exception:
            yunet_detector = None

    MIN_CENTER_X = target_width / 2
    MAX_CENTER_X = width - (target_width / 2)

    def _clamp(cx):
        return max(MIN_CENTER_X, min(cx, MAX_CENTER_X))

    sample_times = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    clip = None
    left_positions = []
    right_positions = []
    solo_positions = []

    try:
        clip = VideoFileClip(video_path).subclipped(start_time, min(end_time, start_time + 6.0))
        for st in sample_times:
            if st >= clip.duration: break
            frame = clip.get_frame(st)
            if yunet_detector is not None:
                bgr_img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) if len(frame.shape) == 3 and frame.shape[2] == 3 else frame
                _, raw_faces = yunet_detector.detect(bgr_img)
                if raw_faces is not None:
                    faces_in_frame = []
                    for f in raw_faces:
                        x, y, w, h = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                        cx = x + w / 2
                        cy = y + h / 2
                        if cx < width * 0.05 or cx > width * 0.95: continue
                        if cy < height * 0.10 or cy > height * 0.90: continue
                        if w < width * 0.035 or h < height * 0.05: continue
                        faces_in_frame.append(cx)
                    
                    if len(faces_in_frame) == 1:
                        solo_positions.append(faces_in_frame[0])
                        if faces_in_frame[0] < width * 0.50:
                            left_positions.append(faces_in_frame[0])
                        else:
                            right_positions.append(faces_in_frame[0])
                    elif len(faces_in_frame) >= 2:
                        faces_in_frame.sort()
                        left_positions.append(faces_in_frame[0])
                        right_positions.append(faces_in_frame[-1])
        clip.close()
    except Exception:
        if clip:
            try: clip.close()
            except Exception: pass

    # Compute median / average anchors
    left_anchor = _clamp(np.median(left_positions)) if left_positions else _clamp(width * 0.25)
    right_anchor = _clamp(np.median(right_positions)) if right_positions else _clamp(width * 0.75)
    solo_anchor = _clamp(np.median(solo_positions)) if solo_positions else left_anchor

    is_multi_speaker = bool(len(left_positions) >= 2 and len(right_positions) >= 2)

    return {
        "left_anchor": float(left_anchor),
        "right_anchor": float(right_anchor),
        "solo_anchor": float(solo_anchor),
        "is_multi_speaker": is_multi_speaker
    }

def apply_split_screen(video_path, start_time, end_time, output_path, anchors=None, job_id=None):
    """
    Render 9:16 vertical video using Stacked Split-Screen (Top & Bottom).
    Top window: Left speaker / Host (1080x960)
    Bottom window: Right speaker / Guest (1080x960)
    100% static framing, zero panning motion sickness.
    """
    log("Applying Studio Split-Screen (Top: Host / Bottom: Guest)...", job_id=job_id)
    ffmpeg_bin = get_ffmpeg_binary()
    clip_dur = end_time - start_time

    # Determine probe size
    temp_clip = VideoFileClip(video_path)
    width, height = temp_clip.size
    temp_clip.close()

    target_crop_w = int(height * 0.54) # 1:1 roughly or 9:8 ratio for 960h
    if target_crop_w % 2 != 0: target_crop_w -= 1
    
    if anchors is None:
        anchors = detect_speaker_anchors(video_path, start_time, end_time, width, height, target_crop_w)

    left_cx = anchors["left_anchor"]
    right_cx = anchors["right_anchor"]

    # Calculate crop offsets (clamped)
    top_x = max(0, min(int(left_cx - target_crop_w / 2), width - target_crop_w))
    bottom_x = max(0, min(int(right_cx - target_crop_w / 2), width - target_crop_w))

    top_x = (top_x // 2) * 2
    bottom_x = (bottom_x // 2) * 2

    # FFmpeg filter:
    # 1. Split into 2 streams
    # 2. Crop top speaker -> scale to 1080x960
    # 3. Crop bottom speaker -> scale to 1080x960
    # 4. Vertical Stack (vstack) with a sleek subtle border
    fc_filter = (
        f"[0:v]split=2[vtop_in][vbot_in];"
        f"[vtop_in]crop={target_crop_w}:{height}:{top_x}:0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
        f"[vbot_in]crop={target_crop_w}:{height}:{bottom_x}:0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bot];"
        f"[top][bot]vstack=inputs=2[stacked];"
        f"[stacked]drawbox=x=0:y=958:w=1080:h=4:color=0x18181b@0.9:t=fill[v]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-ss", str(start_time),
        "-t", str(clip_dur),
        "-i", video_path,
        "-filter_complex", fc_filter,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    run_command(cmd, "Rendering Split-Screen format...", job_id=job_id, duration=clip_dur)
    return output_path

def apply_fit_blur(video_path, start_time, end_time, output_path, job_id=None):
    """
    Render 9:16 vertical video using Fit + Blurred Background.
    Main 16:9 video centered with heavy Gaussian blur at top and bottom.
    """
    log("Applying Fit 16:9 with Blurred Background (Letterbox)...", job_id=job_id)
    ffmpeg_bin = get_ffmpeg_binary()
    clip_dur = end_time - start_time

    # FFmpeg filter:
    # Background: scale to 1080x1920 crop, heavy blur & slight darken
    # Foreground: scale to 1080:-1 (approx 1080x608), centered
    fc_filter = (
        f"[0:v]split=2[bg_in][fg_in];"
        f"[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.08[bg];"
        f"[fg_in]scale=1080:-1[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-ss", str(start_time),
        "-t", str(clip_dur),
        "-i", video_path,
        "-filter_complex", fc_filter,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    run_command(cmd, "Rendering Fit-Blur format...", job_id=job_id, duration=clip_dur)
    return output_path


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
    log(f"Applying AI Smart Crop (Shot-Based Multi-Camera Hard Cut Engine)...", job_id=job_id)
    
    clip = VideoFileClip(video_path).subclipped(start_time, end_time)
    
    width, height = clip.size
    target_width = int(height * 9 / 16)
    
    if target_width % 2 != 0: target_width -= 1
    if target_width > width:
        target_width = width
        if target_width % 2 != 0: target_width -= 1

    # ── Boundary limits for camera center ──
    MIN_CENTER_X = target_width / 2
    MAX_CENTER_X = width - (target_width / 2)

    def _clamp_center(cx):
        """Clamp camera center X within valid crop boundaries."""
        return max(MIN_CENTER_X, min(cx, MAX_CENTER_X))

    # Initialize YuNet Deep Neural Network Face Detector
    yunet_detector = None
    if os.path.exists(YUNET_MODEL_PATH) and hasattr(cv2, 'FaceDetectorYN'):
        try:
            yunet_detector = cv2.FaceDetectorYN.create(
                YUNET_MODEL_PATH, "", (width, height),
                score_threshold=0.65, nms_threshold=0.3
            )
        except Exception as e:
            log(f"YuNet init failed: {e}, falling back to Haar Cascades...", job_id=job_id)
            yunet_detector = None

    frontal_cascade = cv2.CascadeClassifier(CASCADE_PATH) if os.path.exists(CASCADE_PATH) else None
    profile_cascade = cv2.CascadeClassifier(PROFILE_CASCADE_PATH) if os.path.exists(PROFILE_CASCADE_PATH) else None

    def _detect_faces_in_frame(frame_img):
        """Detect accurate human faces with zero false positives on cups, microphones, and table items."""
        valid = []
        
        # Priority 1: High-Precision Neural YuNet Detector
        if yunet_detector is not None:
            try:
                # YuNet expects BGR format
                bgr_img = cv2.cvtColor(frame_img, cv2.COLOR_RGB2BGR) if len(frame_img.shape) == 3 and frame_img.shape[2] == 3 else frame_img
                _, raw_faces = yunet_detector.detect(bgr_img)
                if raw_faces is not None:
                    raw_candidates = []
                    for f in raw_faces:
                        x, y, w, h = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                        score = float(f[-1])
                        cx = x + w / 2
                        cy = y + h / 2
                        # ── Strict Face Zone ──
                        # Human head in interviews/podcasts is located in the upper/mid portion (10% to 68% height)
                        # Rejects images on cups/table items (which appear at bottom Y > 70%)
                        if cy < height * 0.10 or cy > height * 0.68:
                            continue
                        if cx < width * 0.05 or cx > width * 0.95:
                            continue
                        if w < width * 0.04 or h < height * 0.07:
                            continue
                        raw_candidates.append({
                            "center_x": _clamp_center(cx),
                            "raw_cx": cx,
                            "cy": cy,
                            "w": w,
                            "h": h,
                            "area": w * h,
                            "score": score
                        })
                    
                    if raw_candidates:
                        # Secondary filter: Suppress tiny secondary artifacts if a prominent main speaker face exists
                        max_area = max(c["area"] for c in raw_candidates)
                        for c in raw_candidates:
                            if max_area > 15000 and c["area"] < 0.20 * max_area:
                                continue
                            valid.append(c)
                    return valid
            except Exception:
                pass
                
        # Priority 2: Haar Cascades Fallback
        gray_img = cv2.cvtColor(frame_img, cv2.COLOR_RGB2GRAY) if len(frame_img.shape) == 3 else frame_img
        raw_faces = []
        if frontal_cascade and not frontal_cascade.empty():
            faces = frontal_cascade.detectMultiScale(
                gray_img, scaleFactor=1.10, minNeighbors=7,
                minSize=(int(width * 0.05), int(height * 0.07))
            )
            for (x, y, w, h) in faces:
                raw_faces.append((x, y, w, h, w * h))
        if profile_cascade and not profile_cascade.empty():
            faces_left = profile_cascade.detectMultiScale(
                gray_img, scaleFactor=1.10, minNeighbors=6,
                minSize=(int(width * 0.05), int(height * 0.07))
            )
            for (x, y, w, h) in faces_left:
                raw_faces.append((x, y, w, h, w * h))
            flipped = cv2.flip(gray_img, 1)
            faces_right = profile_cascade.detectMultiScale(
                flipped, scaleFactor=1.10, minNeighbors=6,
                minSize=(int(width * 0.05), int(height * 0.07))
            )
            for (x, y, w, h) in faces_right:
                orig_x = width - (x + w)
                raw_faces.append((orig_x, y, w, h, w * h))
                
        for (fx, fy, fw, fh, area) in raw_faces:
            aspect = float(fw) / float(fh) if fh > 0 else 0
            if aspect < 0.65 or aspect > 1.40:
                continue
            cy = fy + (fh / 2)
            if cy < height * 0.10 or cy > height * 0.68:
                continue
            cx = _clamp_center(fx + (fw / 2))
            valid.append({"center_x": cx, "raw_cx": fx + (fw / 2), "cy": cy, "w": fw, "h": fh, "area": area, "score": 0.8})
            
        return valid

    # ═══════════════════════════════════════════════════════════════
    # PASS 1: FULL-CLIP OPUS-STYLE SHOT & CLUSTER ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    SAMPLE_INTERVAL = 0.4            # 2.5 fps sampling untuk deteksi responsif
    HOLD_MIN = 7                     # ~2.8s wajib bertahan di pembicara aktif
    CONFIRM = 4                      # ~1.6s konfirmasi kandidat baru konsisten
    ABSENT_GRACE = 6                 # ~2.4s toleransi jika wajah tertutup sejenak
    SWITCH_COOLDOWN = 9              # ~3.6s larangan cut ulang setelah berganti
    MIN_SHOT_DURATION = 3.0          # Minimum durasi shot gaya Opus Clip

    clip_duration = clip.duration
    sample_count = max(1, int(clip_duration / SAMPLE_INTERVAL) + 1)
    samples = []                     # {"t", "cxs", "primary_cx"}
    all_detected_cxs = []

    for i in range(sample_count):
        t = i * SAMPLE_INTERVAL
        if t >= clip_duration:
            break
        try:
            frame = clip.get_frame(t)
            faces = _detect_faces_in_frame(frame)
        except Exception:
            faces = []

        if faces:
            # Sort faces by area descending (wajah paling dominan/besar di depan)
            faces.sort(key=lambda f: f["area"], reverse=True)
            cxs = [f["raw_cx"] for f in faces]
            primary_cx = faces[0]["raw_cx"]
            all_detected_cxs.extend(cxs)
        else:
            cxs = []
            primary_cx = None

        samples.append({"t": t, "cxs": cxs, "primary_cx": primary_cx})

    clip.close()

    # ── K-Means / Bimodal Cluster Analysis untuk Mendeteksi Speaker Asli ──
    # Mencegah pembagian kaku 50% layar yang sering salah anggap solo speaker sebagai dual speaker
    if len(all_detected_cxs) >= 8:
        sorted_cxs = sorted(all_detected_cxs)
        half = len(sorted_cxs) // 2
        left_med = float(np.median(sorted_cxs[:half]))
        right_med = float(np.median(sorted_cxs[half:]))
        
        # Hanya anggap Multi-Speaker jika ada dua kluster wajah dengan jarak signifikan (> 22% lebar video)
        if (right_med - left_med) > (width * 0.22):
            left_anchor = _clamp_center(left_med)
            right_anchor = _clamp_center(right_med)
            split_boundary_x = (left_anchor + right_anchor) / 2.0
            is_multi_speaker = True
        else:
            solo_med = float(np.median(sorted_cxs))
            left_anchor = right_anchor = _clamp_center(solo_med)
            split_boundary_x = solo_med
            is_multi_speaker = False
    else:
        solo_med = float(np.median(all_detected_cxs)) if all_detected_cxs else (width * 0.50)
        left_anchor = right_anchor = _clamp_center(solo_med)
        split_boundary_x = solo_med
        is_multi_speaker = False

    # Beri label seat pada setiap sampel berdasarkan batas kluster dinamis
    for s in samples:
        if s["primary_cx"] is None:
            s["seat"] = "absent"
        elif not is_multi_speaker:
            s["seat"] = "solo"
        else:
            s["seat"] = "left" if s["primary_cx"] < split_boundary_x else "right"

    log(f"Opus Face Engine: left_anchor={left_anchor:.0f}px right_anchor={right_anchor:.0f}px multi_speaker={is_multi_speaker}", job_id=job_id)

    shots = []
    if not is_multi_speaker:
        # ── Single Speaker Track: 100% Mengikuti Koordinat Wajah Asli ──
        solo_x = _clamp_center(float(np.median(all_detected_cxs))) if all_detected_cxs else _clamp_center(width * 0.50)
        shots = [{"seat": "solo", "t_start": 0.0, "t_end": clip_duration, "anchor_x": solo_x}]
    else:
        # ── Multi Speaker Track: State Machine Debounce ──
        active = None
        hold = 0
        candidate = None
        cand_streak = 0
        absent_streak = 0
        cooldown = 0
        shot_start = 0.0

        for s in samples:
            t, seat = s["t"], s["seat"]
            if cooldown > 0:
                cooldown -= 1

            if active is None:
                if seat != "absent":
                    active = seat
                    hold = 1
                    shot_start = t
                continue

            if seat == "absent":
                hold += 1
                absent_streak += 1
                cand_streak = 0
                candidate = None
            elif seat == active:
                hold += 1
                absent_streak = 0
                cand_streak = 0
                candidate = None
            else:
                hold += 1
                absent_streak = 0
                if candidate == seat:
                    cand_streak += 1
                else:
                    candidate = seat
                    cand_streak = 1

            should_switch = (hold >= HOLD_MIN and cooldown == 0 and
                             (cand_streak >= CONFIRM or absent_streak >= ABSENT_GRACE))
            if should_switch and candidate is not None and candidate != active:
                shots.append({"seat": active, "t_start": shot_start, "t_end": t})
                active = candidate
                hold = 0
                cand_streak = 0
                candidate = None
                absent_streak = 0
                cooldown = SWITCH_COOLDOWN
                shot_start = t

        if active is not None and shot_start < clip_duration - 0.05:
            shots.append({"seat": active, "t_start": shot_start, "t_end": clip_duration})

        if not shots:
            fallback_seat = "left" if left_anchor else "right"
            shots = [{"seat": fallback_seat, "t_start": 0.0, "t_end": clip_duration}]

        # Merge short shots (< MIN_SHOT_DURATION) agar pergantian kamera sangat tenang
        merged = []
        for sh in shots:
            if merged and (sh["t_end"] - sh["t_start"]) < MIN_SHOT_DURATION:
                merged[-1]["t_end"] = sh["t_end"]
            else:
                merged.append(sh)
        shots = merged

        # ── Kunci Anchor Per-Shot Berdasarkan Wajah Aktual di Dalam Rentang Waktu Tersebut ──
        # Mencegah kamera mengunci koordinat kursi kosong/benda saat angle video asli berubah
        for sh in shots:
            shot_actual_cxs = []
            for s in samples:
                if (sh["t_start"] - 0.05) <= s["t"] <= (sh["t_end"] + 0.05):
                    if s["primary_cx"] is not None:
                        shot_actual_cxs.append(s["primary_cx"])
            
            if shot_actual_cxs:
                sh["anchor_x"] = _clamp_center(float(np.median(shot_actual_cxs)))
            else:
                sh["anchor_x"] = left_anchor if sh["seat"] == "left" else right_anchor

    log(f"Opus Cut Sequence: {[{'start': round(s['t_start'],1), 'end': round(s['t_end'],1), 'speaker': s['seat'], 'anchor_x': round(s['anchor_x'])} for s in shots]}", job_id=job_id)

    # ═══════════════════════════════════════════════════════════════
    # PASS 2: SEAMLESS NATIVE FFMPEG FILTER GRAPH (ZERO GLITCH / FAST)
    # Merender seluruh shot dalam 1 kali run FFmpeg via filter complex
    # (trim + crop + concat filter). Mengeliminasi audio pop, frame drop,
    # dan lag sinkronisasi PTS secara total.
    # ═══════════════════════════════════════════════════════════════
    ffmpeg_bin = get_ffmpeg_binary()
    clip_dur = end_time - start_time

    if len(shots) == 1:
        # Single Shot Direct Crop
        x1 = int(round(shots[0]["anchor_x"] - target_width / 2))
        x1 = (x1 // 2) * 2
        x1 = max(0, min(x1, width - target_width))

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(start_time),
            "-t", str(clip_dur),
            "-i", video_path,
            "-vf", f"crop={target_width}:{height}:{x1}:0",
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "fast", "-crf", "17",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
        run_command(cmd, "Rendering Opus Static Solo Crop...", job_id=job_id, duration=clip_dur)
    else:
        # Multi-Shot Seamless Concat Filter (Single Encode Pass)
        # FFmpeg concat filter dengan v=1:a=1 mewajibkan urutan input berpasangan (interleaved):
        # [v0][a0][v1][a1]...[vN-1][aN-1]
        filter_parts = []
        concat_inputs = ""

        for idx, sh in enumerate(shots):
            rel_t0 = max(0.0, sh["t_start"])
            rel_t1 = min(clip_dur, sh["t_end"])
            
            x1 = int(round(sh["anchor_x"] - target_width / 2))
            x1 = (x1 // 2) * 2
            x1 = max(0, min(x1, width - target_width))

            filter_parts.append(
                f"[0:v]trim=start={rel_t0}:end={rel_t1},setpts=PTS-STARTPTS,crop={target_width}:{height}:{x1}:0[v{idx}];"
                f"[0:a]atrim=start={rel_t0}:end={rel_t1},asetpts=PTS-STARTPTS[a{idx}];"
            )
            concat_inputs += f"[v{idx}][a{idx}]"

        filter_complex_str = "".join(filter_parts) + f"{concat_inputs}concat=n={len(shots)}:v=1:a=1[outv][outa]"

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(start_time),
            "-t", str(clip_dur),
            "-i", video_path,
            "-filter_complex", filter_complex_str,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "17",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
        run_command(cmd, f"Rendering Opus Multi-Shot Video ({len(shots)} shots)...", job_id=job_id, duration=clip_dur)

    log("Opus Smart Crop Berhasil (Zero Glitch & Natural Cut).", job_id=job_id)
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
    out_file = os.path.join(out_dir, f"{index:02d}_{safe_title}.mp4")
    temp_crop_file = os.path.join(TEMP_DIR, f"temp_crop_{index}.mp4")
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
    
    codecs_to_try = []
    tiktok_golden = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-g", "60", "-bf", "2", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    nvenc_golden = ["-c:v", "h264_nvenc", "-preset", "slow", "-profile:v", "high", "-rc", "constqp", "-qp", "18", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_trc", "bt709", "-color_primaries", "bt709", "-g", "60", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    
    if sys.platform == "darwin":
        codecs_to_try = [
            ("VideoToolbox (TikTok Golden)", ["-c:v", "h264_videotoolbox", "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "60", "-b:v", "10M", "-maxrate", "12M", "-bufsize", "20M", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]),
            ("libx264 (TikTok Golden)", tiktok_golden)
        ]
    else:
        codecs_to_try = [
            ("NVENC (TikTok Golden)", nvenc_golden),
            ("Safer NVENC", ["-c:v", "h264_nvenc", "-preset", "p2", "-profile:v", "main", "-b:v", "8M", "-c:a", "aac", "-b:a", "192k"]),
            ("libx264 (TikTok Golden)", tiktok_golden)
        ]

    try:
        apply_smart_crop(video_path, start, end, temp_crop_file, job_id=job_id)
            
        log(f"Rendering Subtitles, Audio Enhancer, and Color Grading for Clip {index}: {title}", job_id=job_id)
        vf_filter_base = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp=5:5:0.4:5:5:0.0"
        subtitle_filter = f",subtitles='{escaped_ass}'" if sub_style not in ["none", "no_subtitle"] else ""
        vf_filter = f"{vf_filter_base}{subtitle_filter},fade=t=out:st={fade_out_start}:d=0.5"

        ffmpeg_bin = get_ffmpeg_binary()
        for name, codec_params in codecs_to_try:
            cmd = [
                ffmpeg_bin, "-y", 
                "-fflags", "+genpts", 
                "-i", temp_crop_file, 
                "-vf", vf_filter, 
                "-af", af_filter,
                "-avoid_negative_ts", "make_zero"
            ] + codec_params + [out_file]
            try:
                run_command(cmd, f"Burning subtitles ({name})...", job_id=job_id, duration=duration)
                break
            except Exception as e:
                log(f"{name} Encoding failed: {e}. Falling back to next codec...", job_id=job_id)
            
    except Exception as e:
        log(f"Face tracking error, using intelligent Podcast Dual-Anchor fallback: {e}", job_id=job_id)
        # Fallback Anti-Center: Kunci kursi pembicara (Kiri 28%), BUKAN tengah meja (50%)
        vf_filter_base = "crop=ih*9/16:ih:iw*0.14:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp=5:5:0.4:5:5:0.0"
        subtitle_filter = f",subtitles='{escaped_ass}'" if sub_style not in ["none", "no_subtitle"] else ""
        vf_filter = f"{vf_filter_base}{subtitle_filter},fade=t=out:st={fade_out_start}:d=0.5"
        
        ffmpeg_bin = get_ffmpeg_binary()
        def build_fallback_cmd(codec_params):
            return [
                ffmpeg_bin, "-y", "-ss", str(start), "-t", str(end - start), "-i", video_path,
                "-vf", vf_filter,
                "-af", af_filter
            ] + codec_params + [out_file]

        for name, codec_params in codecs_to_try:
            try:
                run_command(build_fallback_cmd(codec_params), f"Fallback processing for Clip {index} ({name})...", job_id=job_id, duration=duration)
                break
            except Exception as err:
                log(f"Fallback {name} failed, trying next... {err}", job_id=job_id)
    
    for tmp in [ass_file, temp_crop_file]:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception as e:
            log(f"Warning: Could not remove temp file {tmp}: {e}", job_id=job_id)
        
    return out_file
