import os
import tempfile
import time
import re
from backend.utils import log, run_command, format_timestamp, TEMP_DIR

_whisper_model = None

def split_segment_into_words(text, start, end):
    """
    Split a segment's text into individual words with proportional timestamps based on word length.
    """
    words_split = text.strip().split()
    if not words_split:
        return []
        
    duration = end - start
    total_chars = sum(len(w) for w in words_split)
    
    words_list = []
    current_time = start
    
    for word in words_split:
        word_len = len(word)
        word_dur = (word_len / total_chars) * duration if total_chars > 0 else (duration / len(words_split))
        words_list.append({
            "word": word,
            "start": current_time,
            "end": current_time + word_dur
        })
        current_time += word_dur
        
    return words_list

def extract_youtube_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def fetch_youtube_transcript(video_id, job_id=None):
    from youtube_transcript_api import YouTubeTranscriptApi
    
    log(f"Mencoba mengambil subtitle langsung dari InnerTube API untuk video ID: {video_id}...", job_id=job_id)
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
        
        try:
            # Prioritize Indonesian manual transcripts
            transcript_obj = transcript_list.find_transcript(['id'])
            transcript = transcript_obj.fetch()
        except Exception:
            # Fallback to generated Indonesian transcripts
            transcript_obj = transcript_list.find_generated_transcript(['id'])
            transcript = transcript_obj.fetch()
            
        segments = []
        for t in transcript:
            start = t['start']
            end = start + t['duration']
            text = t['text'].replace('\n', ' ')
            
            # Split segment into word-level timestamps proportionally
            segments.append({
                "start": start,
                "end": end,
                "text": text,
                "words": split_segment_into_words(text, start, end)
            })
            
        log("Berhasil mendapatkan subtitle dari InnerTube API! (0 detik transkripsi)", job_id=job_id)
        return segments
    except Exception as e:
        log(f"Gagal mengambil subtitle dari InnerTube API: {e}", job_id=job_id)
        return None

def fetch_ytdlp_subs(url, job_id=None):
    import yt_dlp
    import webvtt
    import uuid
    
    log("Mencoba mengambil subtitle via yt-dlp...", job_id=job_id)
    
    unique_id = uuid.uuid4().hex[:8]
    sub_base_name = f"temp_sub_{unique_id}"
    sub_path = os.path.join(TEMP_DIR, sub_base_name)
    
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['id'],
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
            if file.startswith(sub_base_name) and file.endswith(".vtt"):
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
                "words": split_segment_into_words(text, start, end)
            })
            
        try:
            os.remove(vtt_file)
        except Exception:
            pass
        
        if segments:
            log("Berhasil mendapatkan subtitle via yt-dlp!", job_id=job_id)
            return segments
        return None
        
    except Exception as e:
        log(f"Gagal mengambil subtitle via yt-dlp: {e}", job_id=job_id)
        return None

def transcribe_with_groq(audio_path, job_id=None):
    from backend.utils import GROQ_API_KEY, log
    import requests

    groq_key = (GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")).strip()
    if not groq_key or groq_key.startswith("gsk_xxxx"):
        raise ValueError("GROQ_API_KEY belum diatur di file .env! Dapatkan API Key gratis di https://console.groq.com lalu masukkan ke file .env.")

    log(f"Mengirim audio ke Groq Cloud Whisper API (whisper-large-v3-turbo)...", job_id=job_id)
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {groq_key}"
    }

    with open(audio_path, "rb") as f:
        files = [
            ("file", (os.path.basename(audio_path), f, "audio/mp3")),
            ("model", (None, "whisper-large-v3-turbo")),
            ("response_format", (None, "verbose_json")),
            ("language", (None, "id")),
            ("temperature", (None, "0.0")),
            ("timestamp_granularities[]", (None, "word")),
            ("timestamp_granularities[]", (None, "segment")),
        ]
        log("Menunggu respon dari Groq Cloud AI (estimasi: 2-8 detik)...", job_id=job_id)
        resp = requests.post(url, headers=headers, files=files, timeout=120)

    if resp.status_code != 200:
        raise RuntimeError(f"Groq API Error ({resp.status_code}): {resp.text}")

    result = resp.json()
    raw_segments = result.get("segments", [])
    raw_words = result.get("words", [])
    
    # Map words to segments accurately based on timestamp overlap
    segments = []
    word_idx = 0
    total_words = len(raw_words)

    for seg in raw_segments:
        text = seg.get("text", "").strip()
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))
        
        words = []
        # Ambil word timestamps langsung dari list kata asli Groq jika tersedia
        if raw_words:
            while word_idx < total_words:
                w_item = raw_words[word_idx]
                w_start = float(w_item.get("start", 0.0))
                w_end = float(w_item.get("end", 0.0))
                w_text = w_item.get("word", "").strip()
                
                # Masukkan kata ke dalam segmen ini jika berada dalam rentang waktu segmen
                if w_start <= end + 0.15:
                    words.append({
                        "word": w_text,
                        "start": w_start,
                        "end": w_end
                    })
                    word_idx += 1
                else:
                    break
        elif "words" in seg and seg["words"]:
            for w in seg["words"]:
                words.append({
                    "word": w.get("word", "").strip(),
                    "start": float(w.get("start", 0.0)),
                    "end": float(w.get("end", 0.0))
                })
        else:
            words = split_segment_into_words(text, start, end)

        segments.append({
            "start": start,
            "end": end,
            "text": text,
            "words": words
        })

    log(f"[SUCCESS] Transkripsi Groq selesai kilat! Ditemukan {len(segments)} segmen audio.", job_id=job_id)
    return segments

def transcribe_video(video_path, source_url=None, model_size="groq", job_id=None):
    is_youtube_url = source_url and ("youtube.com" in source_url or "youtu.be" in source_url)
    video_id = extract_youtube_id(source_url) if is_youtube_url else None
    
    if model_size == "youtube":
        if not is_youtube_url:
            raise ValueError("Model transkripsi YouTube dipilih, tetapi video sumber bukan video YouTube.")
            
        if not video_id:
            raise ValueError("Gagal mengekstrak ID video YouTube dari URL.")
            
        # Check local cache first
        from backend.utils import PROJECT_ROOT
        import json
        cache_dir = os.path.join(PROJECT_ROOT, "downloads", "transcripts")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{video_id}_youtube.json")
        
        if os.path.exists(cache_path):
            log(f"Memuat transkrip dari cache lokal: {cache_path}", job_id=job_id)
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    segments = json.load(f)
                return segments
            except Exception as e:
                log(f"Gagal memuat cache transkrip: {e}, melakukan fetch ulang...", job_id=job_id)
                
        # Step 1: InnerTube API
        segments = fetch_youtube_transcript(video_id, job_id=job_id)
        if segments:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, indent=2, ensure_ascii=False)
                log(f"Transkrip disimpan ke cache lokal: {cache_path}", job_id=job_id)
            except Exception as e:
                log(f"Gagal menyimpan cache transkrip: {e}", job_id=job_id)
            return segments
            
        # Step 2: yt-dlp Subs
        segments = fetch_ytdlp_subs(source_url, job_id=job_id)
        if segments:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, indent=2, ensure_ascii=False)
                log(f"Transkrip disimpan ke cache lokal: {cache_path}", job_id=job_id)
            except Exception as e:
                log(f"Gagal menyimpan cache transkrip: {e}", job_id=job_id)
            return segments
            
        raise RuntimeError("Gagal mendapatkan transkrip/subtitle Bahasa Indonesia dari YouTube (dan mode YouTube saja dipilih).")

    # Check local cache first
    if is_youtube_url and video_id:
        from backend.utils import PROJECT_ROOT
        import json
        cache_dir = os.path.join(PROJECT_ROOT, "downloads", "transcripts")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{video_id}_groq.json")
        
        if os.path.exists(cache_path):
            log(f"Memuat transkrip dari cache lokal: {cache_path}", job_id=job_id)
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    segments = json.load(f)
                return segments
            except Exception as e:
                log(f"Gagal memuat cache transkrip: {e}, melakukan fetch ulang...", job_id=job_id)

    # Groq Cloud Whisper (Default & Ultra Cepat)
    log("Mengekstrak audio terkompresi mono MP3 untuk Groq Whisper...", job_id=job_id)
    temp_audio_path = tempfile.mktemp(suffix=".mp3", dir=TEMP_DIR)
    # Ekstrak mono 48kbps 16kHz audio (ukuran file hanya ~15-20 MB untuk durasi 70+ menit)
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-b:a", "48k", "-ar", "16000", "-ac", "1",
        temp_audio_path
    ]
    try:
        run_command(extract_cmd, "Extracting lightweight audio for Groq", job_id=job_id)
        segments = transcribe_with_groq(temp_audio_path, job_id=job_id)
        
        # Simpan ke cache jika ada video_id
        if is_youtube_url and video_id and segments:
            try:
                from backend.utils import PROJECT_ROOT
                import json
                cache_dir = os.path.join(PROJECT_ROOT, "downloads", "transcripts")
                os.makedirs(cache_dir, exist_ok=True)
                cache_path = os.path.join(cache_dir, f"{video_id}_groq.json")
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        return segments
    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass

def build_transcript_text(segments):
    lines = []
    for seg in segments:
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"].strip()
        lines.append(f"[{start} --> {end}] {text}")
    return "\n".join(lines)
