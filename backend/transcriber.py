import os
import tempfile
import time
from backend.utils import log, run_command, format_timestamp, TEMP_DIR

_whisper_model = None

def transcribe_video(video_path, model_size="small", job_id=None):
    from faster_whisper import WhisperModel
    import torch
    global _whisper_model

    log("Extracting audio to .wav to prevent VRAM leak and speed up Whisper...", job_id=job_id)
    temp_audio_path = tempfile.mktemp(suffix=".wav", dir=TEMP_DIR)
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", 
        temp_audio_path
    ]
    try:
        run_command(extract_cmd, "Extracting Audio to WAV", job_id=job_id)
    except Exception as e:
        log(f"Audio extraction failed: {e}. Falling back to original video file.", job_id=job_id)
        temp_audio_path = video_path

    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"
    else:
        log("WARNING: GPU/CUDA tidak terdeteksi oleh sistem! Pytorch Anda mungkin versi CPU-only.", job_id=job_id)
        log("Memaksa beralih ke mode CPU (transkripsi akan berjalan lebih lambat).", job_id=job_id)
        device = "cpu"
        compute_type = "int8"
    
    log(f"Loading Faster-Whisper model '{model_size}' on device: {device} ({compute_type})", job_id=job_id)
    
    if _whisper_model is None:
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    
    log("Transcribing audio (extracting word-level timestamps with VAD)...", job_id=job_id)
    segments_generator, info = _whisper_model.transcribe(temp_audio_path, language="id", word_timestamps=True, vad_filter=True)

    log(f"Audio duration: {info.duration:.1f} seconds. Starting transcription...", job_id=job_id)
    segments = []
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
        
        percent = (segment.end / info.duration) * 100
        elapsed = time.time() - start_time
        if percent > 0:
            eta_seconds = elapsed / (percent / 100) - elapsed
            eta_str = format_timestamp(eta_seconds).split(".")[0]
        else:
            eta_str = "Menghitung..."
            
        log(f"Progress Transkripsi: {percent:.1f}% | Sisa Waktu (ETA): {eta_str} | ({segment.end:.1f}s / {info.duration:.1f}s)", job_id=job_id)

    log(f"Transcription complete. {len(segments)} segments found.", job_id=job_id)
    
    if temp_audio_path != video_path and os.path.exists(temp_audio_path):
        try:
            os.remove(temp_audio_path)
        except Exception as e:
            log(f"Warning: Could not remove temp audio {temp_audio_path}: {e}", job_id=job_id)
        
    return segments

def build_transcript_text(segments):
    lines = []
    for seg in segments:
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"].strip()
        lines.append(f"[{start} --> {end}] {text}")
    return "\n".join(lines)
