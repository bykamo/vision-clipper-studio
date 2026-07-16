import os
import tempfile
import time
import re
from backend.utils import log, run_command, format_timestamp, TEMP_DIR

_whisper_model = None

def extract_youtube_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def fetch_youtube_transcript(video_id, job_id=None):
    from youtube_transcript_api import YouTubeTranscriptApi
    
    log(f"Mencoba mengambil subtitle langsung dari InnerTube API untuk video ID: {video_id}...", job_id=job_id)
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            # Prioritize Indonesian or English manual/auto transcripts
            transcript_obj = transcript_list.find_transcript(['id', 'en'])
            transcript = transcript_obj.fetch()
        except:
            # Fallback to generated translated or any available
            transcript_obj = transcript_list.find_generated_transcript(['id', 'en'])
            transcript = transcript_obj.fetch()
            
        segments = []
        for t in transcript:
            start = t['start']
            end = start + t['duration']
            text = t['text'].replace('\n', ' ')
            
            # Format to match Whisper segments array format
            segments.append({
                "start": start,
                "end": end,
                "text": text,
                "words": [{"word": text, "start": start, "end": end}]
            })
            
        log("Berhasil mendapatkan subtitle dari InnerTube API! (0 detik transkripsi)", job_id=job_id)
        return segments
    except Exception as e:
        log(f"Gagal mengambil subtitle dari InnerTube API: {e}", job_id=job_id)
        return None

def fetch_ytdlp_subs(url, job_id=None):
    import yt_dlp
    import webvtt
    
    log("Mencoba mengambil subtitle via yt-dlp...", job_id=job_id)
    
    sub_path = os.path.join(TEMP_DIR, "temp_sub")
    
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['id', 'en'],
        'outtmpl': sub_path,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # Find the downloaded .vtt file
        vtt_file = None
        for file in os.listdir(TEMP_DIR):
            if file.startswith("temp_sub") and file.endswith(".vtt"):
                vtt_file = os.path.join(TEMP_DIR, file)
                break
                
        if not vtt_file:
            log("yt-dlp tidak menemukan file subtitle (.vtt).", job_id=job_id)
            return None
            
        segments = []
        for caption in webvtt.read(vtt_file):
            # Parse webvtt timestamp: HH:MM:SS.mmm
            def parse_vtt_time(time_str):
                parts = time_str.replace(',', '.').split(':')
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                
            start = parse_vtt_time(caption.start)
            end = parse_vtt_time(caption.end)
            text = caption.text.replace('\n', ' ')
            
            segments.append({
                "start": start,
                "end": end,
                "text": text,
                "words": [{"word": text, "start": start, "end": end}]
            })
            
        os.remove(vtt_file)
        
        if segments:
            log("Berhasil mendapatkan subtitle via yt-dlp!", job_id=job_id)
            return segments
        return None
        
    except Exception as e:
        log(f"Gagal mengambil subtitle via yt-dlp: {e}", job_id=job_id)
        return None

def transcribe_video(video_path, source_url=None, model_size="small", job_id=None):
    # FALLBACK CHAIN: 1. InnerTube API -> 2. yt-dlp -> 3. Faster-Whisper
    if source_url and ("youtube.com" in source_url or "youtu.be" in source_url):
        video_id = extract_youtube_id(source_url)
        if video_id:
            # Step 1: InnerTube API
            segments = fetch_youtube_transcript(video_id, job_id=job_id)
            if segments: return segments
            
            # Step 2: yt-dlp Subs
            segments = fetch_ytdlp_subs(source_url, job_id=job_id)
            if segments: return segments
            
            log("Fallback ke transkripsi lokal (Faster-Whisper)...", job_id=job_id)

    # Step 3: Faster-Whisper
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
