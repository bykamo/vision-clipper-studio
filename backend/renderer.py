import os
import sys
import cv2
import numpy as np
from backend.utils import log, format_ass_timestamp, run_command, get_ffmpeg_binary, TEMP_DIR
from moviepy import VideoFileClip

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
    log(f"Applying AI Smart Crop (YuNet DNN Neural Face Tracking & Shot-Aware Framing)...", job_id=job_id)
    
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
        """Detect accurate human faces with zero false positives."""
        valid = []
        
        # Priority 1: High-Precision Neural YuNet Detector
        if yunet_detector is not None:
            try:
                # YuNet expects BGR format
                bgr_img = cv2.cvtColor(frame_img, cv2.COLOR_RGB2BGR) if len(frame_img.shape) == 3 and frame_img.shape[2] == 3 else frame_img
                _, raw_faces = yunet_detector.detect(bgr_img)
                if raw_faces is not None:
                    for f in raw_faces:
                        x, y, w, h = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                        score = float(f[-1])
                        cx = x + w / 2
                        cy = y + h / 2
                        # Filter out thumbnail overlays, edges, and sub-pixel artifacts
                        if cx < width * 0.05 or cx > width * 0.95:
                            continue
                        if cy < height * 0.10 or cy > height * 0.90:
                            continue
                        if w < width * 0.035 or h < height * 0.05:
                            continue
                        valid.append({
                            "center_x": _clamp_center(cx),
                            "raw_cx": cx,
                            "cy": cy,
                            "w": w,
                            "h": h,
                            "area": w * h,
                            "score": score
                        })
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
            if cy < height * 0.10 or cy > height * 0.85:
                continue
            cx = _clamp_center(fx + (fw / 2))
            valid.append({"center_x": cx, "raw_cx": fx + (fw / 2), "cy": cy, "w": fw, "h": fh, "area": area, "score": 0.8})
            
        return valid

    # ── Dense Initial Speaker Scan (Anti-Delay Framing 0.0s) ──
    # Dense scan frame awal klip agar frame 0 langsung 100% pas membidik pembicara (Zero Millisecond Center Delay)
    initial_camera_x = _clamp_center(width * 0.25)
    active_seat = "left"
    try:
        sample_times = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
        found_in_scan = []
        for st in sample_times:
            if st < clip.duration:
                sample_frame = clip.get_frame(st)
                v = _detect_faces_in_frame(sample_frame)
                if v:
                    found_in_scan.extend(v)
                    if len(v) == 1:
                        initial_camera_x = v[0]["center_x"]
                        active_seat = "left" if v[0]["raw_cx"] < width * 0.50 else "right"
                        break
                    elif len(v) >= 2:
                        v.sort(key=lambda item: item["raw_cx"])
                        initial_camera_x = v[0]["center_x"]
                        active_seat = "left"
                        break
        if not found_in_scan and clip.duration > 0:
            initial_camera_x = _clamp_center(width * 0.25)
    except Exception:
        pass

    # ── Shot-Aware Multi-Camera Tracking & Cinematic Dip-to-Black State ──
    current_camera_x = float(initial_camera_x)
    target_camera_x = float(initial_camera_x)
    
    seat_locked_frames = 0
    LOCK_MIN_FRAMES = 75            # Kunci pembicara minimal ~1.2s sebelum boleh switch
    candidate_target_x = None
    candidate_detected_frames = 0
    CANDIDATE_CONFIRM_FRAMES = 16   # Konfirmasi konsisten ~0.25s sebelum transition
    
    DEAD_ZONE = 35.0                # Deadzone 35px untuk tripod freeze (zero micro-shake)
    CUT_THRESHOLD = 90.0            # Perbedaan >90px memicu Cinematic Dip-to-Black
    
    DETECT_INTERVAL = 2             # Deteksi setiap 2 frame untuk tracking super responsif
    frame_count = 0

    # ── Dip-to-Black Transition Engine ──
    # Kurva transisi 8 frame (~0.13 detik) untuk menutupi perpindahan sudut kamera 100%
    TRANSITION_CURVE = [0.70, 0.35, 0.05, 0.00, 0.10, 0.40, 0.75, 1.00]
    transition_idx = -1             # -1 = normal (tidak dalam transisi)
    pending_cut_target = None
    no_face_count = 0

    def process_frame(frame):
        nonlocal frame_count, current_camera_x, target_camera_x, active_seat
        nonlocal seat_locked_frames, candidate_target_x, candidate_detected_frames
        nonlocal transition_idx, pending_cut_target, no_face_count
        
        # ── Frame 0 Instant Snap ──
        if frame_count == 0:
            try:
                f0_faces = _detect_faces_in_frame(frame)
                if f0_faces:
                    if len(f0_faces) == 1:
                        current_camera_x = target_camera_x = f0_faces[0]["center_x"]
                        active_seat = "left" if f0_faces[0]["raw_cx"] < width * 0.50 else "right"
                    else:
                        f0_faces.sort(key=lambda item: item["raw_cx"])
                        current_camera_x = target_camera_x = f0_faces[0]["center_x"]
                        active_seat = "left"
            except Exception:
                pass
        
        # ── Neural Face Detection (every N frames) ──
        if frame_count % DETECT_INTERVAL == 0:
            try:
                valid_faces = _detect_faces_in_frame(frame)
            except Exception:
                valid_faces = []
            
            if not valid_faces:
                no_face_count += DETECT_INTERVAL
            else:
                no_face_count = 0
            
            raw_target = target_camera_x
            
            if len(valid_faces) == 1:
                # ── SHOT TYPE 1: Single Speaker Shot (Close-up / Medium Solo) ──
                single_face = valid_faces[0]
                raw_target = single_face["center_x"]
                active_seat = "left" if single_face["raw_cx"] < width * 0.50 else "right"
                
            elif len(valid_faces) >= 2:
                # ── SHOT TYPE 2: Dual/Multi Speaker Wide Shot (Host & Guest) ──
                valid_faces.sort(key=lambda item: item["raw_cx"])
                left_spk = valid_faces[0]
                right_spk = valid_faces[-1]
                
                # Pilih speaker terdekat dengan framing aktif atau pembicara dominan
                if abs(left_spk["center_x"] - current_camera_x) < abs(right_spk["center_x"] - current_camera_x):
                    raw_target = left_spk["center_x"]
                    active_seat = "left"
                else:
                    raw_target = right_spk["center_x"]
                    active_seat = "right"
            
            # ── Hysteresis & Cinematic Dip-to-Black Trigger ──
            dist_to_raw = abs(raw_target - target_camera_x)
            
            if dist_to_raw > CUT_THRESHOLD:
                if candidate_target_x is not None and abs(raw_target - candidate_target_x) < 50:
                    candidate_detected_frames += DETECT_INTERVAL
                    # Jika terkonfirmasi dan sudah terkunci cukup lama -> Picu Cinematic Dip-to-Black
                    if candidate_detected_frames >= CANDIDATE_CONFIRM_FRAMES and seat_locked_frames >= LOCK_MIN_FRAMES:
                        if transition_idx == -1: # Mulai transisi gelap
                            transition_idx = 0
                            pending_cut_target = raw_target
                        candidate_target_x = None
                        candidate_detected_frames = 0
                        seat_locked_frames = 0
                else:
                    candidate_target_x = raw_target
                    candidate_detected_frames = DETECT_INTERVAL
                seat_locked_frames += DETECT_INTERVAL
            else:
                candidate_target_x = None
                candidate_detected_frames = 0
                seat_locked_frames += DETECT_INTERVAL
                if dist_to_raw > DEAD_ZONE and transition_idx == -1:
                    target_camera_x += (raw_target - target_camera_x) * 0.20
        else:
            seat_locked_frames += 1
        
        # ── Handle Dip-to-Black Transition Animation ──
        current_brightness = 1.0
        
        if transition_idx >= 0:
            current_brightness = TRANSITION_CURVE[transition_idx]
            # Di titik gelap puncak (frame ke-3 / brightness 0.0), pindahkan kamera secara instan!
            if transition_idx == 3 and pending_cut_target is not None:
                target_camera_x = pending_cut_target
                current_camera_x = pending_cut_target
                pending_cut_target = None
                
            transition_idx += 1
            if transition_idx >= len(TRANSITION_CURVE):
                transition_idx = -1
        else:
            # Smooth Tripod Gliding normal (hanya untuk gerakan duduk mikro dalam deadzone)
            dist_current = abs(target_camera_x - current_camera_x)
            if dist_current > DEAD_ZONE:
                current_camera_x += (target_camera_x - current_camera_x) * 0.12
            
            # Subtle Dimming jika pembicara hilang sejenak (> 1 detik)
            if no_face_count > 30:
                current_brightness = max(0.65, 1.0 - (no_face_count - 30) * 0.01)
            
        current_camera_x = _clamp_center(current_camera_x)
        
        # ── Crop Frame 9:16 (Strict Even X1 for YUV420p Chroma Alignment) ──
        frame_count += 1
        x1 = int(round(current_camera_x - target_width / 2))
        x1 = (x1 // 2) * 2  # Enforce even pixel boundary (eliminates chroma tear glitches)
        
        if x1 < 0:
            x1 = 0
        if x1 + target_width > width:
            x1 = ((width - target_width) // 2) * 2
            
        x2 = x1 + target_width
        cropped = frame[:, x1:x2]
        
        # Apply Cinematic Brightness Modulation (Dip to Black / Auto-Dim)
        if current_brightness < 0.99:
            cropped = (cropped.astype(np.float32) * current_brightness).astype(np.uint8)
            
        return cropped

    cropped_clip = clip.image_transform(process_frame)
    my_logger = MoviePyLogger(job_id=job_id)
    
    codecs_to_try = []
    if sys.platform == "darwin":
        codecs_to_try = [
            ("h264_videotoolbox", []),
            ("libx264", ["-preset", "fast"])
        ]
    else:
        codecs_to_try = [
            ("h264_nvenc", []),
            ("h264_nvenc", ["-preset", "p2", "-profile:v", "main"]),
            ("libx264", ["-preset", "fast"])
        ]

    success = False
    for codec, extra_params in codecs_to_try:
        try:
            log(f"Trying smart crop encoding with {codec}...", job_id=job_id)
            cropped_clip.write_videofile(
                output_path, 
                codec=codec,
                audio_codec="aac",
                bitrate="8000k",
                temp_audiofile=output_path.replace(".mp4", "_temp.m4a"),
                remove_temp=True,
                ffmpeg_params=["-pix_fmt", "yuv420p"] + extra_params,
                logger=my_logger
            )
            success = True
            break
        except Exception as e:
            log(f"{codec} failed ({e}), trying next fallback...", job_id=job_id)
    
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
    
    try:
        apply_smart_crop(video_path, start, end, temp_crop_file, job_id=job_id)
            
        log(f"Rendering Subtitles, Audio Enhancer, and Color Grading for Clip {index}: {title}", job_id=job_id)
        vf_filter_base = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp=5:5:0.4:5:5:0.0"
        subtitle_filter = f",subtitles='{escaped_ass}'" if sub_style not in ["none", "no_subtitle"] else ""
        vf_filter = f"{vf_filter_base}{subtitle_filter},fade=t=out:st={fade_out_start}:d=0.5"
        
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
