import os
import sys
import cv2
from backend.utils import log, format_ass_timestamp, run_command, get_ffmpeg_binary, TEMP_DIR
from moviepy import VideoFileClip

CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_frontalface_default.xml")

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


def _chunk_words(words, clip_start, clip_end, max_words=2, max_chars=14, uppercase=False):
    """Split words into display chunks (compact for mobile screens)."""
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
    chunks = _chunk_words(words, clip_start, clip_end, max_words=2, max_chars=14, uppercase=False)
    
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
    # Build compact sentence chunks
    chunks = _chunk_words(words, clip_start, clip_end, max_words=4, max_chars=22, uppercase=False)
    
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
    chunks = _chunk_words(words, clip_start, clip_end, max_words=4, max_chars=22, uppercase=False)
    
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
    log(f"Applying AI Smart Crop (Cinematic Face Tracking v2)...", job_id=job_id)
    
    clip = VideoFileClip(video_path).subclipped(start_time, end_time)
    
    # Load universal OpenCV Cascade Face Detector dari model lokal yang terverifikasi
    if os.path.exists(CASCADE_PATH):
        face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    else:
        cascade_default = getattr(cv2.data, 'haarcascades', '') + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_default)

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

    # ── Initial Speaker Scan (Anti-Sorot Tengah Kosong) ──
    # Scan frame awal klip untuk langsung mengunci posisi pembicara utama dari detik 0.00
    initial_speaker_x = width / 2
    try:
        sample_times = [0.0, 0.5, 1.0, 1.5]
        found_faces = []
        for st in sample_times:
            if st < clip.duration:
                sample_frame = clip.get_frame(st)
                gray_sample = cv2.cvtColor(sample_frame, cv2.COLOR_RGB2GRAY)
                raw_faces = face_cascade.detectMultiScale(
                    gray_sample,
                    scaleFactor=1.12,
                    minNeighbors=7,
                    minSize=(int(width * 0.06), int(height * 0.08))
                )
                for (fx, fy, fw, fh) in raw_faces:
                    aspect_ratio = float(fw) / float(fh) if fh > 0 else 0
                    if 0.75 <= aspect_ratio <= 1.30:
                        found_faces.append((fw * fh, _clamp_center(fx + (fw / 2))))
        if found_faces:
            # Ambil wajah terbesar / paling dominan di awal klip
            found_faces.sort(key=lambda x: x[0], reverse=True)
            initial_speaker_x = found_faces[0][1]
    except Exception:
        pass

    # ── Tracking State ──
    smoothed_x = initial_speaker_x  # Frame 0 langsung berada di posisi pembicara
    target_x = initial_speaker_x
    
    active_speaker_x = initial_speaker_x
    speaker_locked_frames = 0
    LOCK_MIN_FRAMES = 75            # Kunci pembicara minimal ~2.5 detik sebelum boleh switch
    candidate_speaker_x = None
    candidate_detected_frames = 0
    CANDIDATE_CONFIRM_FRAMES = 15   # Butuh ~0.5 detik konfirmasi konsisten untuk pindah
    
    # Tuning parameters (Tripod Lock Mode)
    DETECT_INTERVAL = 3
    PAN_SMOOTH_FACTOR = 0.035       # Kecepatan transisi kamera lambat & sinematik
    TRIPOD_DEAD_ZONE = width * 0.08 # Freeze Tripod: Abaikan gerakan kepala kecil di bawah 8% lebar layar
    MAX_PAN_STEP = width * 0.006    # Panning lembut bertahap per frame
    MIN_FACE_AREA = (width * 0.06) * (height * 0.08)
    
    frame_count = 0

    def process_frame(frame):
        nonlocal frame_count, smoothed_x, target_x
        nonlocal active_speaker_x, speaker_locked_frames
        nonlocal candidate_speaker_x, candidate_detected_frames
        
        # ── Face Detection (every N frames) ──
        if frame_count % DETECT_INTERVAL == 0:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                detected_faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.12,
                    minNeighbors=8,
                    minSize=(int(width * 0.06), int(height * 0.08))
                )
            except Exception:
                detected_faces = ()
            
            valid_faces = []
            if len(detected_faces) > 0:
                for (fx, fy, fw, fh) in detected_faces:
                    aspect_ratio = float(fw) / float(fh) if fh > 0 else 0
                    if aspect_ratio < 0.75 or aspect_ratio > 1.30:
                        continue
                    
                    face_area = fw * fh
                    if face_area < MIN_FACE_AREA:
                        continue
                    
                    face_center_x = fx + (fw / 2)
                    face_center_y = fy + (fh / 2)
                    
                    if face_center_y < height * 0.10 or face_center_y > height * 0.85:
                        continue
                    
                    valid_faces.append({
                        "center_x": _clamp_center(face_center_x),
                        "area": face_area,
                        "dist_to_active": abs(face_center_x - active_speaker_x)
                    })
            
            if valid_faces:
                # Cari wajah yang paling dekat dengan pembicara yang sedang aktif
                active_match = min(valid_faces, key=lambda f: f["dist_to_active"])
                
                # Jika pembicara aktif masih di kursinya (toleransi < 18% lebar video)
                if active_match["dist_to_active"] < (width * 0.18):
                    active_speaker_x = active_match["center_x"]
                    speaker_locked_frames += DETECT_INTERVAL
                    candidate_speaker_x = None
                    candidate_detected_frames = 0
                else:
                    # Ada wajah pembicara kedua di posisi lain (podcast guest/host)
                    largest_other = max(valid_faces, key=lambda f: f["area"])
                    
                    if speaker_locked_frames >= LOCK_MIN_FRAMES:
                        if candidate_speaker_x is None or abs(largest_other["center_x"] - candidate_speaker_x) > (width * 0.12):
                            candidate_speaker_x = largest_other["center_x"]
                            candidate_detected_frames = DETECT_INTERVAL
                        else:
                            candidate_detected_frames += DETECT_INTERVAL
                            if candidate_detected_frames >= CANDIDATE_CONFIRM_FRAMES:
                                active_speaker_x = candidate_speaker_x
                                speaker_locked_frames = 0
                                candidate_speaker_x = None
                                candidate_detected_frames = 0
                    else:
                        speaker_locked_frames += DETECT_INTERVAL
                
                target_x = active_speaker_x
            else:
                # Jika wajah tidak terdeteksi sementara, TETAP KUNCI posisi terakhir (Tripod Lock)
                # JANGAN pernah drift ke tengah ruangan kosong
                speaker_locked_frames += DETECT_INTERVAL
                target_x = active_speaker_x
        else:
            speaker_locked_frames += 1
        
        # ── Tripod Stationary Logic & Smooth Pan ──
        delta = target_x - smoothed_x
        
        # Tripod Mode: Kunci total (0 gerakan) jika kepala pembicara hanya goyang mikro
        if abs(delta) < TRIPOD_DEAD_ZONE:
            delta = 0
        
        step = delta * PAN_SMOOTH_FACTOR
        step = max(-MAX_PAN_STEP, min(step, MAX_PAN_STEP))
        smoothed_x = _clamp_center(smoothed_x + step)
        
        # ── Crop Frame ──
        frame_count += 1
        
        x1 = int(round(smoothed_x - target_width / 2))
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
        log(f"Face tracking error, using simple ffmpeg center crop: {e}", job_id=job_id)
        vf_filter_base = "crop=ih*9/16:ih,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp=5:5:0.4:5:5:0.0"
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
