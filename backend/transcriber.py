import os
import tempfile
import time
import re
import math
import subprocess
from backend.utils import log, run_command, format_timestamp, TEMP_DIR

_whisper_model = None

def get_media_duration(file_path):
    """Mendapatkan total durasi media (dalam detik) secara akurat."""
    # Cara 1: OpenCV VideoCapture
    try:
        import cv2
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps and fps > 0 and frame_count and frame_count > 0:
                return float(frame_count / fps)
    except Exception:
        pass

    # Cara 2: FFmpeg stderr parse
    try:
        from backend.utils import get_ffmpeg_binary
        ffmpeg_bin = get_ffmpeg_binary()
        proc = subprocess.Popen([ffmpeg_bin, "-i", file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out, _ = proc.communicate()
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", out)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass

    return 0.0

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

_active_groq_key_idx = 0

def transcribe_with_groq(audio_path, job_id=None):
    global _active_groq_key_idx
    from backend.utils import get_groq_api_keys, log
    import requests

    keys = get_groq_api_keys()
    if not keys:
        raise ValueError("GROQ_API_KEY belum diatur di file .env! Dapatkan API Key gratis di https://console.groq.com lalu masukkan ke file .env.")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    # Coba request menggunakan key yang aktif, jika terkena 429 atau 401 otomatis rotate ke key berikutnya
    total_keys = len(keys)
    last_error = None

    for attempt in range(total_keys):
        current_key = keys[_active_groq_key_idx % total_keys]
        key_masked = f"{current_key[:6]}...{current_key[-4:]}"
        key_num = (_active_groq_key_idx % total_keys) + 1

        headers = {
            "Authorization": f"Bearer {current_key}"
        }

        log(f"Mengirim audio ke Groq Cloud Whisper API (whisper-large-v3-turbo) [Key #{key_num}: {key_masked}]...", job_id=job_id)

        try:
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
                resp = requests.post(url, headers=headers, files=files, timeout=120)

            if resp.status_code == 200:
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

                log(f"[SUCCESS] Transkripsi Groq selesai kilat! (Key #{key_num}) Ditemukan {len(segments)} segmen audio.", job_id=job_id)
                return segments

            # Jika terkena Rate Limit (429) atau Unauthorized (401)
            if resp.status_code in [429, 401]:
                err_msg = resp.text
                if total_keys > 1:
                    _active_groq_key_idx = (_active_groq_key_idx + 1) % total_keys
                    next_key_num = (_active_groq_key_idx % total_keys) + 1
                    log(f"⚠️ Groq Key #{key_num} mencapai batas kuota/rate limit ({resp.status_code}). Otomatis beralih ke API Key #{next_key_num}...", job_id=job_id)
                    time.sleep(1.0)
                    continue
                else:
                    raise RuntimeError(f"Groq API Error ({resp.status_code}): {err_msg}")
            else:
                raise RuntimeError(f"Groq API Error ({resp.status_code}): {resp.text}")

        except Exception as e:
            last_error = e
            if total_keys > 1 and ("429" in str(e) or "rate_limit" in str(e).lower() or "401" in str(e)):
                _active_groq_key_idx = (_active_groq_key_idx + 1) % total_keys
                next_key_num = (_active_groq_key_idx % total_keys) + 1
                log(f"⚠️ Error pada Groq Key #{key_num}: {e}. Mencoba beralih ke Key #{next_key_num}...", job_id=job_id)
                time.sleep(1.0)
                continue
            raise e

    raise last_error or RuntimeError("Semua Groq API Keys yang disediakan telah mencapai batas kuota/rate limit!")

def transcribe_long_audio_with_groq(video_path, total_duration, chunk_duration=900, job_id=None):
    """
    Membagi audio video panjang (1-3+ jam) menjadi potongan 15 menit (900 detik, ~4 MB),
    lalu mentranskripsikannya ke Groq Cloud API secara sekuensial dan menggabungkan timestamp-nya.
    """
    from backend.utils import get_ffmpeg_binary
    ffmpeg_bin = get_ffmpeg_binary()

    num_chunks = int(math.ceil(total_duration / chunk_duration))
    log(f"Video berdurasi panjang ({total_duration/60:.1f} menit). Mengaktifkan Groq Auto-Chunking ({num_chunks} part @ 15 menit)...", job_id=job_id)

    all_segments = []

    for i in range(num_chunks):
        start_sec = i * chunk_duration
        curr_dur = min(chunk_duration, total_duration - start_sec)
        
        start_min_str = f"{int(start_sec // 60):02d}:{int(start_sec % 60):02d}"
        end_min_sec = start_sec + curr_dur
        end_min_str = f"{int(end_min_sec // 60):02d}:{int(end_min_sec % 60):02d}"

        log(f"[Groq AI] Mengekstrak & Mentranskripsikan Part {i+1}/{num_chunks} (Menit {start_min_str} - {end_min_str})...", job_id=job_id)

        chunk_audio_path = tempfile.mktemp(suffix=f"_groq_part{i+1}.mp3", dir=TEMP_DIR)
        extract_chunk_cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(start_sec),
            "-t", str(curr_dur),
            "-i", video_path,
            "-vn", "-acodec", "libmp3lame", "-b:a", "48k", "-ar", "16000", "-ac", "1",
            chunk_audio_path
        ]

        try:
            run_command(extract_chunk_cmd, f"Extracting chunk {i+1}/{num_chunks}", job_id=job_id)
            
            # Retry loop per chunk
            max_retries = 3
            chunk_segments = None
            for attempt in range(max_retries):
                try:
                    chunk_segments = transcribe_with_groq(chunk_audio_path, job_id=job_id)
                    if chunk_segments:
                        break
                except Exception as e:
                    log(f"Groq Part {i+1} attempt {attempt + 1}/{max_retries} failed: {e}", job_id=job_id)
                    if attempt < max_retries - 1:
                        wait_sec = (attempt + 1) * 3
                        log(f"Mencoba kembali part {i+1} dalam {wait_sec} detik...", job_id=job_id)
                        time.sleep(wait_sec)
                    else:
                        raise e

            # Terapkan offset waktu ke timestamp
            if chunk_segments:
                for seg in chunk_segments:
                    seg["start"] += start_sec
                    seg["end"] += start_sec
                    for w in seg.get("words", []):
                        w["start"] += start_sec
                        w["end"] += start_sec
                    all_segments.append(seg)

            log(f"[Groq AI] Part {i+1}/{num_chunks} selesai transkripsi. Total segmen terakumulasi: {len(all_segments)}.", job_id=job_id)

            # Jeda singkat 0.5s antar request untuk menghormati rate limit Groq
            if i < num_chunks - 1:
                time.sleep(0.5)

        finally:
            if os.path.exists(chunk_audio_path):
                try:
                    os.remove(chunk_audio_path)
                except Exception:
                    pass

    log(f"[SUCCESS] Groq Multi-Part Transcription selesai 100%! Berhasil mengumpulkan total {len(all_segments)} segmen audio.", job_id=job_id)
    return all_segments

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

    # Groq Cloud Whisper (Default & Ultra Cepat dengan Retry & Cache Lokal)
    # Check local cache first berdasarkan nama file video
    import hashlib
    file_hash = hashlib.md5(os.path.basename(video_path).encode("utf-8")).hexdigest()[:12]
    from backend.utils import PROJECT_ROOT
    import json
    cache_dir = os.path.join(PROJECT_ROOT, "downloads", "transcripts")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{file_hash}_groq.json")

    if os.path.exists(cache_path):
        log(f"Memuat transkrip dari cache lokal: {cache_path}", job_id=job_id)
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                segments = json.load(f)
            return segments
        except Exception as e:
            log(f"Gagal memuat cache transkrip: {e}, melakukan transkripsi ulang...", job_id=job_id)

    # Deteksi total durasi video untuk penanganan otomatis file panjang
    total_dur = get_media_duration(video_path)
    
    # Jika video > 20 menit (1200 detik), gunakan Auto-Chunking (potongan per 15 menit)
    if total_dur > 1200:
        segments = transcribe_long_audio_with_groq(video_path, total_dur, chunk_duration=900, job_id=job_id)
        if segments:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, indent=2, ensure_ascii=False)
                log(f"Transkrip disimpan ke cache lokal: {cache_path}", job_id=job_id)
            except Exception:
                pass
        return segments

    log("Mengekstrak audio terkompresi mono MP3 untuk Groq Whisper...", job_id=job_id)
    from backend.utils import get_ffmpeg_binary
    ffmpeg_bin = get_ffmpeg_binary()
    temp_audio_path = tempfile.mktemp(suffix=".mp3", dir=TEMP_DIR)
    extract_cmd = [
        ffmpeg_bin, "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-b:a", "48k", "-ar", "16000", "-ac", "1",
        temp_audio_path
    ]
    try:
        run_command(extract_cmd, "Extracting lightweight audio for Groq", job_id=job_id)

        # Cek jika ukuran file audio yang diekstrak melebihi batas 24 MB
        file_size_mb = os.path.getsize(temp_audio_path) / (1024 * 1024) if os.path.exists(temp_audio_path) else 0
        if file_size_mb >= 24.0 and total_dur > 0:
            log(f"Ukuran audio ({file_size_mb:.1f} MB) mendekati limit 25 MB Groq. Beralih ke Auto-Chunking...", job_id=job_id)
            segments = transcribe_long_audio_with_groq(video_path, total_dur, chunk_duration=900, job_id=job_id)
            if segments:
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(segments, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass
            return segments
        
        # Retry loop dengan exponential backoff jika terjadi kendala jaringan/DNS sesaat
        max_retries = 3
        segments = None
        for attempt in range(max_retries):
            try:
                segments = transcribe_with_groq(temp_audio_path, job_id=job_id)
                if segments:
                    break
            except Exception as e:
                log(f"Groq API call attempt {attempt + 1}/{max_retries} failed: {e}", job_id=job_id)
                if attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 3
                    log(f"Mencoba kembali dalam {wait_sec} detik...", job_id=job_id)
                    time.sleep(wait_sec)
                else:
                    raise e
        
        if segments:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, indent=2, ensure_ascii=False)
                log(f"Transkrip disimpan ke cache lokal: {cache_path}", job_id=job_id)
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
