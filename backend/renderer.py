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
    """
    M1 Native Smart Face Tracker & Auto-Clipper.
    Combines OpenCV Face Detection + Exponential Moving Average (EMA) smoothing for seamless 9:16 cinematic panning.
    """
    log(f"Applying M1 Smart Face Tracker (EMA Smooth Panning 9:16)...", job_id=job_id)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Gagal membuka video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    start_frame = max(0, int(start_time * fps))
    end_frame = int(end_time * fps)
    total_clip_frames = max(1, end_frame - start_frame)

    # Set posisi frame awal
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    # Dimensi crop vertikal 9:16
    target_aspect_ratio = 9.0 / 16.0
    crop_h = orig_h
    crop_w = int(crop_h * target_aspect_ratio)
    if crop_w % 2 != 0: crop_w -= 1
    if crop_w > orig_w:
        crop_w = orig_w
        if crop_w % 2 != 0: crop_w -= 1
        crop_h = int(crop_w / target_aspect_ratio)

    smoothing_factor = 0.08
    min_face_size_ratio = 0.04
    min_pixel_size = int(orig_w * min_face_size_ratio)

    default_center_x = (orig_w - crop_w) / 2.0
    curr_crop_x = default_center_x

    # Inisialisasi Face Detector (YuNet DNN jika ada, fallback ke Haar Cascade)
    yunet_detector = None
    if os.path.exists(YUNET_MODEL_PATH) and hasattr(cv2, 'FaceDetectorYN'):
        try:
            yunet_detector = cv2.FaceDetectorYN.create(
                YUNET_MODEL_PATH, "", (orig_w, orig_h),
                score_threshold=0.55, nms_threshold=0.3
            )
        except Exception:
            yunet_detector = None

    cascade_path = CASCADE_PATH if os.path.exists(CASCADE_PATH) else (getattr(cv2.data, 'haarcascades', '') + 'haarcascade_frontalface_default.xml')
    face_cascade = cv2.CascadeClassifier(cascade_path) if os.path.exists(cascade_path) else None

    temp_video_path = os.path.join(TEMP_DIR, f"temp_m1_video_{int(time.time()*1000)}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (crop_w, crop_h))

    frame_count = 0
    start_proc_time = time.time()
    last_log_time = 0

    try:
        while cap.isOpened() and (start_frame + frame_count) < end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            target_center_x = orig_w / 2.0
            detected_valid_face = False

            # Priority 1: YuNet DNN (Faster & more accurate)
            if yunet_detector is not None:
                try:
                    _, raw_faces = yunet_detector.detect(frame)
                    if raw_faces is not None and len(raw_faces) > 0:
                        best_face = max(raw_faces, key=lambda f: float(f[2]) * float(f[3]))
                        fx, fy, fw, fh = int(best_face[0]), int(best_face[1]), int(best_face[2]), int(best_face[3])
                        if fw >= min_pixel_size and (fy + fh / 2) < orig_h * 0.75:
                            detected_valid_face = True
                            face_center_x = fx + (fw / 2.0)
                            target_center_x = face_center_x
                except Exception:
                    pass

            # Priority 2: Haar Cascade Fallback
            if not detected_valid_face and face_cascade and not face_cascade.empty():
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.15,
                    minNeighbors=5,
                    minSize=(min_pixel_size, min_pixel_size)
                )
                if len(faces) > 0:
                    best_face = max(faces, key=lambda b: b[2] * b[3])
                    fx, fy, fw, fh = best_face
                    if fw >= min_pixel_size and (fy + fh / 2) < orig_h * 0.75:
                        detected_valid_face = True
                        face_center_x = fx + (fw / 2.0)
                        target_center_x = face_center_x

            # Hitung target crop X
            target_crop_x = target_center_x - (crop_w / 2.0)

            # Jika tidak ada wajah valid -> smooth drift ke center
            if not detected_valid_face:
                target_crop_x = default_center_x

            # Clamping batas layar
            target_crop_x = max(0, min(orig_w - crop_w, target_crop_x))

            # Smoothing Exponential Moving Average (EMA)
            curr_crop_x = curr_crop_x + smoothing_factor * (target_crop_x - curr_crop_x)

            # Slicing frame
            x1 = int(round(curr_crop_x))
            x2 = x1 + crop_w
            y1 = int((orig_h - crop_h) / 2)
            y2 = y1 + crop_h

            cropped_frame = frame[y1:y2, x1:x2]
            out.write(cropped_frame)

            # Periodic Progress Log
            curr_time = time.time()
            if (curr_time - last_log_time >= 1.5) or (frame_count == total_clip_frames):
                percent = min(100.0, (frame_count / total_clip_frames) * 100)
                elapsed = curr_time - start_proc_time
                eta = (elapsed / (percent / 100) - elapsed) if percent > 0 else 0
                from backend.utils import format_timestamp
                eta_str = format_timestamp(eta).split('.')[0]
                log(f"Progress Smart Face Tracker: {percent:.1f}% ({frame_count}/{total_clip_frames} frames) | ETA: {eta_str}", job_id=job_id)
                last_log_time = curr_time

    finally:
        cap.release()
        out.release()

    # Muxing audio asli dengan FFmpeg
    ffmpeg_bin = get_ffmpeg_binary()
    clip_dur = end_time - start_time
    log("Menggabungkan audio asli ke video hasil crop...", job_id=job_id)
    
    ffmpeg_cmd = [
        ffmpeg_bin, "-y",
        "-i", temp_video_path,
        "-ss", str(start_time),
        "-t", str(clip_dur),
        "-i", video_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-avoid_negative_ts", "make_zero",
        output_path
    ]
    run_command(ffmpeg_cmd, "Muxing final smart crop audio...", job_id=job_id, duration=clip_dur)

    if os.path.exists(temp_video_path):
        try:
            os.remove(temp_video_path)
        except Exception:
            pass

    log("Smart Face Tracker selesai dengan mulus.", job_id=job_id)
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
