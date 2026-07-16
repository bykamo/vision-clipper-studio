import os
import urllib.request
from backend.utils import log, format_ass_timestamp, run_command, TEMP_DIR
from moviepy import VideoFileClip
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blaze_face_short_range.tflite")

def generate_ass_subtitles(segments, out_ass_path, clip_start, clip_end, title_hook=None):
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
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        
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
            
            text = word_info["word"].strip().upper() 
            if not text: continue
            
            current_chunk.append({"word": text, "start": w_start, "end": w_end})
            
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
    log(f"Applying AI Smart Crop (Tracking Face with Cinematic Gimbal)...", job_id=job_id)
    
    clip = VideoFileClip(video_path).subclipped(start_time, end_time)
    
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceDetectorOptions(base_options=base_options)
    detector = vision.FaceDetector.create_from_options(options)

    width, height = clip.size
    target_width = int(height * 9 / 16)
    
    if target_width % 2 != 0: target_width -= 1
    if target_width > width:
        target_width = width
        if target_width % 2 != 0: target_width -= 1

    CAMERA_SPEED = 0.05
    frame_count = 0
    last_center_x = width / 2
    smoothed_x = width / 2

    def process_frame(frame):
        nonlocal frame_count, last_center_x, smoothed_x
        
        if frame_count % 5 == 0:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            detection_result = detector.detect(mp_image)
            
            if detection_result.detections:
                best_face_center_x = None
                min_distance = float('inf')
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    face_center_x = bbox.origin_x + (bbox.width / 2)
                    distance = abs(face_center_x - smoothed_x)
                    if distance < min_distance:
                        min_distance = distance
                        best_face_center_x = face_center_x
                
                if best_face_center_x is not None:
                    min_x = target_width / 2
                    max_x = width - (target_width / 2)
                    last_center_x = max(min_x, min(best_face_center_x, max_x))
                
        frame_count += 1
        smoothed_x = smoothed_x + (last_center_x - smoothed_x) * CAMERA_SPEED
        
        x1 = int(smoothed_x - target_width / 2)
        x2 = int(smoothed_x + target_width / 2)
        
        x1 = max(0, x1)
        x2 = min(width, x1 + target_width)
        
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
    return output_path

def extract_and_format_clip(video_path, clip_info, index, segments, out_dir, job_id=None):
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
    generate_ass_subtitles(segments, ass_file, start, end, title_hook=title_hook)
    
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
