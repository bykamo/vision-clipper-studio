import os
import sys
import cv2
from backend.utils import log, format_ass_timestamp, run_command, get_ffmpeg_binary, TEMP_DIR
from moviepy import VideoFileClip

CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_frontalface_default.xml")
PROFILE_CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_profileface.xml")

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

    if sub_style == "karaoke":
        _generate_karaoke_style(sanitized_words, out_ass_path, clip_start, clip_end)
    elif sub_style == "minimalist":
        _generate_minimalist_style(sanitized_words, out_ass_path, clip_start, clip_end)
    elif sub_style == "word_pop":
        _generate_word_pop_style(sanitized_words, out_ass_path, clip_start, clip_end)
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
    log(f"Applying AI Smart Crop (Cinematic Face Tracking v3 - Dual Profile & Anchor)...", job_id=job_id)
    
    clip = VideoFileClip(video_path).subclipped(start_time, end_time)
    
    # Load frontal and profile cascade classifiers
    frontal_cascade = cv2.CascadeClassifier(CASCADE_PATH) if os.path.exists(CASCADE_PATH) else None
    profile_cascade = cv2.CascadeClassifier(PROFILE_CASCADE_PATH) if os.path.exists(PROFILE_CASCADE_PATH) else None

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

    # Podcast Dual Anchor Fallbacks (Host Kiri ~28% / Guest Kanan ~72%)
    ANCHOR_LEFT = _clamp_center(width * 0.28)
    ANCHOR_RIGHT = _clamp_center(width * 0.72)

    def _detect_faces_in_frame(gray_img):
        """Detect faces using both frontal and bilateral profile cascades."""
        raw_faces = []
        
        # 1. Frontal faces
        if frontal_cascade and not frontal_cascade.empty():
            faces = frontal_cascade.detectMultiScale(
                gray_img, scaleFactor=1.10, minNeighbors=7,
                minSize=(int(width * 0.05), int(height * 0.07))
            )
            for (x, y, w, h) in faces:
                raw_faces.append((x, y, w, h, w * h))
                
        # 2. Profile faces (Left)
        if profile_cascade and not profile_cascade.empty():
            faces_left = profile_cascade.detectMultiScale(
                gray_img, scaleFactor=1.10, minNeighbors=6,
                minSize=(int(width * 0.05), int(height * 0.07))
            )
            for (x, y, w, h) in faces_left:
                raw_faces.append((x, y, w, h, w * h))
                
            # 3. Profile faces (Right - flipped)
            flipped = cv2.flip(gray_img, 1)
            faces_right = profile_cascade.detectMultiScale(
                flipped, scaleFactor=1.10, minNeighbors=6,
                minSize=(int(width * 0.05), int(height * 0.07))
            )
            for (x, y, w, h) in faces_right:
                orig_x = width - (x + w)
                raw_faces.append((orig_x, y, w, h, w * h))
                
        valid = []
        for (fx, fy, fw, fh, area) in raw_faces:
            aspect = float(fw) / float(fh) if fh > 0 else 0
            if aspect < 0.65 or aspect > 1.40:
                continue
            cy = fy + (fh / 2)
            if cy < height * 0.10 or cy > height * 0.85:
                continue
            cx = _clamp_center(fx + (fw / 2))
            valid.append({"center_x": cx, "area": area, "raw_cx": fx + (fw / 2)})
            
        return valid

    # ── Initial Speaker Scan ──
    # Scan frame awal klip untuk menemukan wajah pembicara aktif
    initial_speaker_x = ANCHOR_LEFT
    try:
        sample_times = [0.0, 0.3, 0.6, 1.0, 1.5]
        found_faces = []
        for st in sample_times:
            if st < clip.duration:
                sample_frame = clip.get_frame(st)
                gray_sample = cv2.cvtColor(sample_frame, cv2.COLOR_RGB2GRAY)
                v = _detect_faces_in_frame(gray_sample)
                found_faces.extend(v)
        if found_faces:
            found_faces.sort(key=lambda x: x["area"], reverse=True)
            initial_speaker_x = found_faces[0]["center_x"]
    except Exception:
        pass

    # ── Initial Speaker Scan & Seat Clustering ──
    # Scan frame awal klip untuk memetakan kursi Host (Kiri) dan Guest (Kanan)
    detected_clusters = []
    try:
        sample_times = [0.0, 0.3, 0.6, 1.0, 1.5, 2.0]
        for st in sample_times:
            if st < clip.duration:
                sample_frame = clip.get_frame(st)
                gray_sample = cv2.cvtColor(sample_frame, cv2.COLOR_RGB2GRAY)
                v = _detect_faces_in_frame(gray_sample)
                for item in v:
                    detected_clusters.append((item["center_x"], item["area"]))
    except Exception:
        pass

    # Tentukan posisi kursi default
    left_faces = [pos for pos, area in detected_clusters if pos < (width * 0.50)]
    right_faces = [pos for pos, area in detected_clusters if pos >= (width * 0.50)]
    
    SEAT_LEFT = sum(left_faces) / len(left_faces) if left_faces else ANCHOR_LEFT
    SEAT_RIGHT = sum(right_faces) / len(right_faces) if right_faces else ANCHOR_RIGHT
    
    # Pilih pembicara pembuka klip
    if detected_clusters:
        detected_clusters.sort(key=lambda x: x[1], reverse=True)
        initial_speaker_x = SEAT_LEFT if detected_clusters[0][0] < (width * 0.50) else SEAT_RIGHT
    else:
        initial_speaker_x = SEAT_LEFT

    # ── Tracking State (OpusClip-Style Multi-Camera Instant Cut) ──
    current_camera_x = float(initial_speaker_x)
    active_seat = "left" if initial_speaker_x < (width * 0.50) else "right"
    
    seat_locked_frames = 0
    LOCK_MIN_FRAMES = 60            # Kunci pembicara minimal ~2 detik sebelum boleh switch
    candidate_seat = None
    candidate_detected_frames = 0
    CANDIDATE_CONFIRM_FRAMES = 18   # Konfirmasi konsisten ~0.6s sebelum Instant Cut
    
    DETECT_INTERVAL = 3
    frame_count = 0

    def process_frame(frame):
        nonlocal frame_count, current_camera_x, active_seat
        nonlocal seat_locked_frames, candidate_seat, candidate_detected_frames
        
        # ── Face Detection (every N frames) ──
        if frame_count % DETECT_INTERVAL == 0:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                valid_faces = _detect_faces_in_frame(gray)
            except Exception:
                valid_faces = []
            
            if valid_faces:
                # Cek apakah ada wajah di kursi lawan (Host vs Guest)
                detected_seats = set()
                for f in valid_faces:
                    if f["center_x"] < (width * 0.50):
                        detected_seats.add("left")
                    else:
                        detected_seats.add("right")
                
                other_seat = "right" if active_seat == "left" else "left"
                
                # Jika pembicara aktif masih di kursinya
                if active_seat in detected_seats:
                    seat_locked_frames += DETECT_INTERVAL
                    # Reset kandidat jika pembicara aktif masih dominan
                    candidate_seat = None
                    candidate_detected_frames = 0
                elif other_seat in detected_seats:
                    # Pembicara aktif tidak terlihat / diam, dan lawan bicara terdeteksi
                    if seat_locked_frames >= LOCK_MIN_FRAMES:
                        if candidate_seat == other_seat:
                            candidate_detected_frames += DETECT_INTERVAL
                            # Lakukan INSTANT CUT (Multi-Camera Switcher)
                            if candidate_detected_frames >= CANDIDATE_CONFIRM_FRAMES:
                                active_seat = other_seat
                                current_camera_x = SEAT_RIGHT if active_seat == "right" else SEAT_LEFT
                                seat_locked_frames = 0
                                candidate_seat = None
                                candidate_detected_frames = 0
                        else:
                            candidate_seat = other_seat
                            candidate_detected_frames = DETECT_INTERVAL
                    else:
                        seat_locked_frames += DETECT_INTERVAL
            else:
                # Wajah tidak terdeteksi sementara -> TETAP 100% DIAM di kursi aktif
                seat_locked_frames += DETECT_INTERVAL
        else:
            seat_locked_frames += 1
        
        # ── Multi-Camera True Static Framing (100% Diam / Zero Jitter) ──
        # Kamera terkunci statis di kursi pembicara aktif, tanpa gerakan geser
        x_center = SEAT_LEFT if active_seat == "left" else SEAT_RIGHT
        current_camera_x = _clamp_center(x_center)
        
        # ── Crop Frame ──
        frame_count += 1
        
        x1 = int(round(current_camera_x - target_width / 2))
        x2 = x1 + target_width
        
        if x1 < 0:
            x1 = 0
            x2 = target_width
        if x2 > width:
            x2 = width
            x1 = width - target_width
        
        return frame[:, x1:x2]

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
        subtitle_filter = f",subtitles='{escaped_ass}'" if sub_style != "none" else ""
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
            cmd = [ffmpeg_bin, "-y", "-i", temp_crop_file, "-vf", vf_filter, "-af", af_filter] + codec_params + [out_file]
            try:
                run_command(cmd, f"Burning subtitles ({name})...", job_id=job_id, duration=duration)
                break
            except Exception as e:
                log(f"{name} Encoding failed: {e}. Falling back to next codec...", job_id=job_id)
            
    except Exception as e:
        log(f"Face tracking error, using intelligent Podcast Dual-Anchor fallback: {e}", job_id=job_id)
        # Fallback Anti-Center: Kunci kursi pembicara (Kiri 28%), BUKAN tengah meja (50%)
        vf_filter_base = "crop=ih*9/16:ih:iw*0.14:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp=5:5:0.4:5:5:0.0"
        subtitle_filter = f",subtitles='{escaped_ass}'" if sub_style != "none" else ""
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
