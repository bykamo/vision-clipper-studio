import os
import re
import sys
import math
import time
import json
import random
import subprocess
import cv2
import numpy as np
from backend.utils import (
    log,
    format_ass_timestamp,
    format_timestamp,
    run_command,
    get_ffmpeg_binary,
    get_ffprobe_binary,
    TEMP_DIR,
    FONTS_DIR,
)

# ── FONT EMOJI ──
# Mode warna: NotoColorEmoji.ttf (CBDT bitmap) dirender native oleh libass sehingga
# emoji tampil BERWARNA persis seperti emoji asli di HP. Mode fallback: NotoEmoji.ttf
# (monokrom) + tint warna EMOJI_COLORS, dipakai jika font warna tidak tersedia atau
# probe libass gagal merender bitmap warna.
EMOJI_FONT_COLOR = "Noto Color Emoji"
EMOJI_FONT_MONO = "Noto Emoji"
EMOJI_COLOR_FONT_FILE = "NotoColorEmoji.ttf"
EMOJI_MONO_FONT_FILE = "NotoEmoji.ttf"
# Override manual: "color" | "mono" | None (auto-detect via probe)
EMOJI_FONT_MODE_OVERRIDE = os.environ.get("EMOJI_FONT_MODE") or None


def _probe_color_emoji_support():
    """Cek apakah libass (bundled ffmpeg) mampu merender NotoColorEmoji (CBDT) berwarna.

    Render 1 frame ASS berisi emoji via bundled ffmpeg -> rawvideo gray+u/v analisis
    sederhana: frame di-render sebagai bgr24 lalu dicek saturasi kroma piksel emoji.
    Emoji berwarna -> ada piksel dengan saturasi tinggi. Tofu/monokrom -> abu-abu.
    Hasil di-cache di temp/.emoji_color_probe.json (key: path ffmpeg + mtime font).
    """
    global _COLOR_EMOJI_SUPPORTED
    if _COLOR_EMOJI_SUPPORTED is not None:
        return _COLOR_EMOJI_SUPPORTED

    cache_path = os.path.join(TEMP_DIR, ".emoji_color_probe.json")
    try:
        ffmpeg_bin = get_ffmpeg_binary()
    except Exception:
        ffmpeg_bin = "ffmpeg"
    font_path = os.path.join(FONTS_DIR, EMOJI_COLOR_FONT_FILE)
    if not os.path.exists(font_path):
        _COLOR_EMOJI_SUPPORTED = False
        return False
    try:
        font_key = f"{ffmpeg_bin}|{os.path.getmtime(font_path)}|{os.path.getmtime(ffmpeg_bin) if os.path.exists(ffmpeg_bin) else 0}"
    except OSError:
        font_key = None

    if font_key:
        try:
            with open(cache_path, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
            if cached.get("key") == font_key:
                _COLOR_EMOJI_SUPPORTED = bool(cached.get("supported"))
                return _COLOR_EMOJI_SUPPORTED
        except Exception:
            pass

    supported = False
    probe_ass = os.path.join(TEMP_DIR, ".emoji_probe.ass")
    try:
        with open(probe_ass, "w", encoding="utf-8") as fh:
            fh.write(
                "[Script Info]\nScriptType: v4.00+\nPlayResX: 320\nPlayResY: 180\n"
                "WrapStyle: 2\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                f"Style: Probe,{EMOJI_FONT_COLOR},48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,10,1\n"
                "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:00.00,0:00:05.00,Probe,,0,0,0,,\U0001F525\U0001F4B0\U0001F60E\n"
            )
        escaped_ass = _escape_filter_path(probe_ass)
        escaped_fonts = _escape_filter_path(FONTS_DIR)
        cmd = [
            ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=320x180:d=1",
            "-vf", f"subtitles='{escaped_ass}':fontsdir='{escaped_fonts}',format=bgr24",
            "-frames:v", "1", "-f", "rawvideo", "-",
        ]
        raw = subprocess.run(cmd, capture_output=True, timeout=30)
        buf = raw.stdout
        if raw.returncode == 0 and len(buf) >= 320 * 180 * 3:
            arr = np.frombuffer(buf[: 320 * 180 * 3], dtype=np.uint8).reshape(180, 320, 3)
            mx = arr.max(axis=2).astype(np.int16)
            mn = arr.min(axis=2).astype(np.int16)
            sat = mx - mn
            # Emoji CBDT berwarna menghasilkan banyak piksel saturasi tinggi;
            # tofu/monokrom hanya abu-abu (saturasi ~0).
            supported = bool((sat > 60).sum() > 200)
    except Exception:
        supported = False
    finally:
        try:
            if os.path.exists(probe_ass):
                os.remove(probe_ass)
        except Exception:
            pass

    _COLOR_EMOJI_SUPPORTED = supported
    if font_key:
        try:
            with open(cache_path, "w", encoding="utf-8") as fh:
                json.dump({"key": font_key, "supported": supported}, fh)
        except Exception:
            pass
    return supported


def _get_active_emoji_font():
    """Kembalikan nama family font emoji aktif: warna (CBDT) atau monokrom fallback."""
    # Baca env saat dipanggil (bukan saat import) agar mudah di-override test.
    mode = (os.environ.get("EMOJI_FONT_MODE") or "").strip().lower()
    if mode == "mono":
        return EMOJI_FONT_MONO
    if mode == "color":
        return EMOJI_FONT_COLOR
    color_file = os.path.join(FONTS_DIR, EMOJI_COLOR_FONT_FILE)
    if os.path.exists(color_file) and _probe_color_emoji_support():
        return EMOJI_FONT_COLOR
    return EMOJI_FONT_MONO


_COLOR_EMOJI_SUPPORTED = None


def _emoji_overlay_available():
    """Apakah emoji berwarna bisa ditempel sebagai overlay PNG?

    Butuh Pillow + fontTools + NotoColorEmoji.ttf. Jika tidak tersedia, pipeline
    otomatis memakai font emoji monokrom (fallback lama) supaya render tidak gagal.
    """
    if os.environ.get("EMOJI_OVERLAY", "").strip().lower() in {"0", "false", "no", "off"}:
        return False
    try:
        from backend.emoji_overlay import emoji_overlay_supported
        return emoji_overlay_supported(FONTS_DIR)
    except Exception:
        return False

try:
    from backend.utils import env_float, env_bool
except ImportError:
    def env_float(key, default=0.0, min_val=None, max_val=None):
        val_str = os.environ.get(key)
        if val_str is None or str(val_str).strip() == "":
            return default
        try:
            val = float(val_str)
            if min_val is not None:
                val = max(min_val, val)
            if max_val is not None:
                val = min(max_val, val)
            return val
        except (ValueError, TypeError):
            return default

    def env_bool(key, default=False):
        val_str = os.environ.get(key)
        if val_str is None or str(val_str).strip() == "":
            return default
        return str(val_str).strip().lower() in ("1", "true", "yes", "on", "y", "t")
from moviepy import VideoFileClip
from proglog import ProgressBarLogger

CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_frontalface_default.xml")
PROFILE_CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_profileface.xml")
YUNET_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_detection_yunet_2023mar.onnx")
YOLO_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolov8n.pt")

# ── SUBTITLE SAFE ZONE (video 9:16 = 1080x1920) ──
# Horizontal margin per side so subtitle text never touches the frame edge or
# collides with TikTok/Reels UI (right action rail, left text column).
# 120px ≈ 11% of the 1080px width per side -> text confined to the middle 78%.
SAFE_MARGIN_H = 120
# Vertical safe band (percent of height). Keeps text clear of the top header
# tabs (~12%) and the bottom caption + navigation bar (~20%).
SAFE_TOP_PCT = 12.0
SAFE_BOTTOM_PCT = 20.0
# WrapStyle 0 = smart word wrapping. Long lines wrap onto a second line inside
# the margins instead of overflowing past the frame edge (WrapStyle 1/2 clip).
SAFE_WRAP_STYLE = 0

# Per-style character budgets derived from the safe width (1080 - 2*120 = 840px)
# and each font's approximate average glyph width (~0.62 * font size).
STYLE_CHUNK_LIMITS = {
    "tiktok_viral": {"max_words": 2, "max_chars": 12},
    "classic_karaoke": {"max_words": 3, "max_chars": 12},
    "minimalist": {"max_words": 4, "max_chars": 16},
}

# ── MODE TERJEMAHAN (audio bahasa sumber, subtitle bahasa target) ──
# Subtitle terjemahan TIDAK memakai highlight per-kata: timing kata hasil
# terjemahan hanya proporsional terhadap panjang karakter (lihat
# transcriber.split_segment_into_words), sehingga highlight tidak pernah
# sinkron dengan audio aslinya. Mode ini menampilkan kalimat utuh dengan
# waktu baca minimum (reading-time floor).
TRANSLATION_CHUNK_MAX_WORDS = 7
TRANSLATION_CHUNK_MAX_CHARS = 34   # total 2 baris
TRANSLATION_LINE_CHARS = 17        # per baris (aman di 840px, font 66)
TRANSLATION_READ_CPS = 13.0        # karakter/detik untuk pembaca non-native
TRANSLATION_MIN_CUE = 1.2          # detik tampil minimum
TRANSLATION_MAX_CUE = 5.0
TRANSLATION_CUE_HOLD = 0.4         # tahan cue sampai jeda hening berikutnya
TRANSLATION_CHUNK_MAX_GAP = 0.6    # jeda antar kata -> batas cue baru
TRANSLATION_MAX_DRIFT = 1.4        # batas lag kumulatif akibat reading floor

STYLE_CHUNK_LIMITS["translation_read"] = {
    "max_words": TRANSLATION_CHUNK_MAX_WORDS,
    "max_chars": TRANSLATION_CHUNK_MAX_CHARS,
}

def _escape_ass_text(text: str) -> str:
    """Escape ASS/SSA control characters and strip raw newlines."""
    if not text:
        return ""
    # Replace backslash first, then curly braces to prevent style tag injection
    sanitized = str(text).replace("\\", "＼").replace("{", "｛").replace("}", "｝")
    sanitized = sanitized.replace("\r", " ").replace("\n", " ").strip()
    return sanitized

def _display_len(text: str) -> int:
    """Panjang teks yang benar-benar memakan lebar baris (emoji tidak dihitung).

    Emoji dirender lebih kecil daripada teks dan pada mode overlay digambar
    sebagai PNG, jadi menghitungnya sebagai karakter akan membuat baris
    terlihat jauh lebih panjang dari aslinya dan memicu pemenggalan dini.
    """
    if not text:
        return 0
    return len(_EMOJI_PATTERN.sub("", text).strip())

def _sanitize_word_timestamps(words, clip_start, clip_end, min_word_dur=0.18):
    """
    Sanitize and enforce strictly monotonic, non-overlapping timestamps.
    Clamps word relative start and end strictly within [0.0, clip_end - clip_start].
    Prevents subtitle overlapping, flickering, and jumbled text when speaker talks fast.
    """
    cleaned = []
    max_clip_dur = max(0.0, float(clip_end - clip_start))
    for w in words:
        w_start = max(0.0, min(max_clip_dur, float(w.get("start", 0.0)) - clip_start))
        w_end = max(0.0, min(max_clip_dur, float(w.get("end", 0.0)) - clip_start))
        text = _escape_ass_text(w.get("word", ""))
        if not text:
            continue
        if w_end <= w_start:
            w_end = min(max_clip_dur, w_start + min_word_dur)
        cleaned.append({"word": text, "start": w_start, "end": w_end})
        
    if not cleaned:
        return []
        
    cleaned.sort(key=lambda x: x["start"])
    
    # Monotonic clamping: ensure no word overlaps another
    sanitized = []
    for i, w in enumerate(cleaned):
        s = max(0.0, min(max_clip_dur, w["start"]))
        e = max(0.0, min(max_clip_dur, max(w["end"], s + min_word_dur)))
        
        if sanitized and s < sanitized[-1]["end"]:
            s = sanitized[-1]["end"]
            e = max(0.0, min(max_clip_dur, max(e, s + min_word_dur)))
            
        sanitized.append({"word": w["word"], "start": s, "end": e})
        
    return sanitized

# Kamus Kata Kunci Viral untuk Auto-Emoji Insertion.
# Setiap kata kunci punya BEBERAPA kandidat emoji yang cocok maknanya dengan kalimat;
# satu kandidat dipilih acak supaya subtitle tidak monoton. Kandidat pertama = default.
# WAJIB: semua emoji di sini harus ada di font backend/fonts/NotoEmoji.ttf,
# kalau tidak akan muncul kotak kosong (tofu). Diverifikasi oleh test_renderer.
EMOJI_KEYWORDS = {
    # Keuangan / Bisnis / Karier
    "uang": ("💰", "💵", "🤑"),
    "duit": ("💸", "💰", "💵"),
    "kaya": ("🤑", "💰", "💎"),
    "cuan": ("💵", "💰", "📈"),
    "bisnis": ("📈", "💼", "🏢"),
    "investasi": ("📊", "📈", "💹"),
    "modal": ("💵", "💰", "🏦"),
    "kerja": ("💼", "🛠️", "💪"),
    "gaji": ("💰", "💵", "🧾"),
    "karir": ("👔", "📈", "🎯"),
    "untung": ("📈", "💹", "🎉"),
    "rugi": ("📉", "💸", "😖"),
    "saham": ("📊", "📈", "💹"),
    "omset": ("💸", "📈", "💰"),
    "omzet": ("💸", "📈", "💰"),
    # Emosi & Reaksi
    "kaget": ("😱", "😲", "🤯"),
    "shock": ("🤯", "😱", "⚡"),
    "kecewa": ("😞", "😔", "💔"),
    "marah": ("😡", "🤬", "🔥"),
    "bahaya": ("⚠️", "🚨", "☠️"),
    "masalah": ("🚨", "⚠️", "🧩"),
    "takut": ("😨", "😰", "😱"),
    "hancur": ("💥", "🧨", "💔"),
    "stres": ("😫", "😖", "🌀"),
    "capek": ("😮‍💨", "😩", "🥱"),
    # Mindset & Inspirasi
    "otak": ("🧠", "💡", "⚙️"),
    "pikiran": ("🧠", "💭", "💡"),
    "mindset": ("💡", "🧠", "🎯"),
    "ide": ("💡", "✨", "🧠"),
    "fokus": ("🎯", "🔍", "🧘"),
    "sukses": ("🏆", "🚀", "🌟"),
    "menang": ("🥇", "🏆", "✌️"),
    "juara": ("👑", "🏆", "🥇"),
    "waktu": ("⏱️", "⏰", "⌛"),
    "disiplin": ("⚡", "⏰", "🎯"),
    "rahasia": ("🤫", "🔒", "🕵️"),
    "kunci": ("🔑", "🗝️", "🔓"),
    "target": ("🎯", "📌", "🏹"),
    "kebiasaan": ("🔄", "🔁", "♻️"),
    # Viral / Energetik
    "viral": ("🚀", "🔥", "📢"),
    "meledak": ("💥", "🧨", "🔥"),
    "api": ("🔥", "🚒", "💥"),
    "batu": ("🗿", "🪨", "💪"),
    "mati": ("💀", "⚰️", "🥀"),
    "keren": ("✨", "😎", "🔥"),
    "gila": ("🤯", "😵", "🌀"),
    "parah": ("💀", "😵", "🚨"),
    "bohong": ("🤥", "🚫", "🙊"),
    "salah": ("❌", "🚫", "🙅"),
    "benar": ("✅", "👍", "💯"),
    "stop": ("🛑", "✋", "🚫"),
    "mulai": ("🚀", "▶️", "🏁"),
}

def _inject_emojis_to_words(words, min_gap=4):
    """
    Suntikkan emoji kontekstual pada kata kunci viral dengan frekuensi terkontrol.
    Maksimal 1 emoji per min_gap kata untuk menjaga kerapian & estetika subtitle.
    Emoji dipilih acak dari kandidat yang cocok dengan makna kalimat.
    """
    if not words:
        return words

    decorated = []
    last_emoji_idx = -min_gap

    for i, w in enumerate(words):
        raw_word = re.sub(r"[^\w]", "", w.get("word", "").lower())
        matched_emoji = None
        if i - last_emoji_idx >= min_gap:
            for kw, candidates in EMOJI_KEYWORDS.items():
                if raw_word == kw or (len(raw_word) >= 4 and raw_word.startswith(kw)):
                    matched_emoji = random.choice(candidates)
                    break

        if matched_emoji:
            new_text = f"{w['word']} {matched_emoji}"
            last_emoji_idx = i
            decorated.append({**w, "word": new_text})
        else:
            decorated.append(w)

    return decorated

# Palet warna aksen ASS (&HAABBGGRR / &HBBGGRR&) kontras tinggi untuk variasi emoji viral
EMOJI_COLORS = {
    "🔥": "&H0070FF&",  # Api (Orange menyala)
    "🚀": "&HFFCC00&",  # Roket (Electric Cyan/Blue)
    "💡": "&H00FFFF&",  # Ide/Mindset (Kuning cerah)
    "💰": "&H00E676&",  # Cuan (Hijau Emerald)
    "💵": "&H00E676&",  # Uang (Hijau Emerald)
    "💸": "&H00E676&",  # Cash terbang (Hijau)
    "📈": "&H00D4FF&",  # Untung (Emas)
    "📉": "&H0000FF&",  # Rugi (Merah)
    "🏆": "&H00D4FF&",  # Juara (Emas)
    "👑": "&H00D4FF&",  # Mahkota (Emas)
    "🥇": "&H00D4FF&",  # Medali (Emas)
    "⚡": "&H00FFFF&",  # Petir (Kuning)
    "🧠": "&HFFB6C1&",  # Otak (Pink)
    "🎯": "&H0044FF&",  # Target (Merah-Orange)
    "🔑": "&H00D4FF&",  # Kunci (Emas)
    "🚨": "&H0033FF&",  # Sirine (Merah)
    "⚠️": "&H00BFFF&",  # Warning (Amber)
    "🛑": "&H0000FF&",  # Stop (Merah)
    "❌": "&H0000FF&",  # Salah (Merah)
    "✅": "&H00E676&",  # Benar (Hijau)
    "✨": "&H00FFFF&",  # Keren (Kuning bintang)
    "🗿": "&HE0E0E0&",  # Batu (Silver)
    "💀": "&HE0E0E0&",  # Tengkorak (Putih tulang)
    "😱": "&H00BFFF&",  # Kaget (Amber)
    "🤯": "&H00BFFF&",  # Shock (Amber)
    # --- Pelengkap kandidat acak (emoji tanpa entri memakai warna default amber) ---
    "💎": "&HFFCC00&",  # Berlian (Cyan terang)
    "🏦": "&H00D4FF&",  # Bank (Emas)
    "🏢": "&H00D4FF&",  # Kantor (Emas)
    "💹": "&H00E676&",  # Grafik naik (Hijau)
    "🎉": "&H00FFFF&",  # Perayaan (Kuning)
    "💔": "&H0000FF&",  # Patah hati (Merah)
    "☠️": "&H0000FF&",  # Bahaya (Merah)
    "🧨": "&H0000FF&",  # Petasan (Merah)
    "🔒": "&H00D4FF&",  # Terkunci (Emas)
    "🔓": "&H00E676&",  # Terbuka (Hijau)
    "🗝️": "&H00D4FF&",  # Kunci antik (Emas)
    "📌": "&H0044FF&",  # Pin (Merah-orange)
    "📅": "&H00D4FF&",  # Kalender (Emas)
    "⏰": "&H00D4FF&",  # Alarm (Emas)
    "⏱️": "&H00D4FF&",  # Stopwatch (Emas)
    "⌛": "&H00D4FF&",  # Hourglass (Emas)
    "✋": "&H0000FF&",  # Stop tangan (Merah)
    "⛔": "&H0000FF&",  # Dilarang (Merah)
    "💯": "&H00E676&",  # Seratus (Hijau)
    "👍": "&H00E676&",  # Jempol (Hijau)
    "😎": "&H00FFFF&",  # Keren (Kuning)
    "😪": "&H00D4FF&",  # Ngantuk (Emas)
    "🥱": "&H00D4FF&",  # Menguap (Emas)
    "💪": "&H00E676&",  # Kekuatan (Hijau)
    "🧘": "&H00FFFF&",  # Meditasi (Kuning)
    "🤓": "&H00FFFF&",  # Kutu buku (Kuning)
    "💭": "&H00FFFF&",  # Pikiran (Kuning)
    "🔍": "&H00D4FF&",  # Cari (Emas)
    "🔧": "&H00D4FF&",  # Kunci pas (Emas)
    "🧩": "&H00FFFF&",  # Puzzle (Kuning)
    "🧾": "&H00D4FF&",  # Struk (Emas)
    "🥀": "&H0000FF&",  # Bunga layu (Merah)
    "⚰️": "&HE0E0E0&",  # Peti (Silver)
    "⛰️": "&HE0E0E0&",  # Gunung (Silver)
    "🪨": "&HE0E0E0&",  # Batu (Silver)
    "🌟": "&H00FFFF&",  # Bintang (Kuning)
    "✌️": "&H00E676&",  # Victory (Hijau)
    "🏁": "&H00FFFF&",  # Finish (Kuning)
    "👻": "&H00FFFF&",  # Hantu (Kuning)
    "🙅": "&H0000FF&",  # Tidak (Merah)
    "🙊": "&H0000FF&",  # Tutup mulut (Merah)
    "🚫": "&H0000FF&",  # Dilarang (Merah)
    "🚒": "&H0000FF&",  # Pemadam (Merah)
    "😵": "&H00BFFF&",  # Pusing (Amber)
    "😖": "&H00BFFF&",  # Frustasi (Amber)
    "😔": "&H00BFFF&",  # Sedih (Amber)
    "😞": "&H00BFFF&",  # Kecewa (Amber)
    "😡": "&H0000FF&",  # Marah (Merah)
    "🤬": "&H0000FF&",  # Marah besar (Merah)
    "😨": "&H00BFFF&",  # Takut (Amber)
    "😰": "&H00BFFF&",  # Cemas (Amber)
    "😲": "&H00BFFF&",  # Terkejut (Amber)
    "😩": "&H00BFFF&",  # Lelah (Amber)
    "😫": "&H00BFFF&",  # Sangat lelah (Amber)
    "🤥": "&H0000FF&",  # Bohong (Merah)
    "🤫": "&H00D4FF&",  # Ssst (Emas)
    "🔄": "&H00FFFF&",  # Ulang (Kuning)
    "🔁": "&H00FFFF&",  # Repeat (Kuning)
    "♻️": "&H00E676&",  # Daur ulang (Hijau)
    "⚙️": "&H00D4FF&",  # Gear (Emas)
    "🛠️": "&H00D4FF&",  # Perkakas (Emas)
    "👔": "&H00D4FF&",  # Dasi (Emas)
    "🕵️": "&H00D4FF&",  # Detektif (Emas)
    "💼": "&H00D4FF&",  # Tas kerja (Emas)
    "📢": "&H00FFFF&",  # Megafon (Kuning)
    "📊": "&H00D4FF&",  # Bar chart (Emas)
    "🏹": "&H0044FF&",  # Panah (Merah-orange)
    "🎯": "&H0044FF&",  # Target (Merah-orange)
}

# Rentang karakter emoji yang tercakup oleh font Noto Emoji.
# PENTING: daftar ini harus lengkap. Emoji yang TIDAK cocok akan ditulis mentah dan
# dirender memakai font subtitle (Plus Jakarta Sans / Montserrat / Impact) yang tidak
# memiliki glyph-nya, sehingga muncul "kotak kosong" / tofu.
# Contoh nyata: ⏱ (U+23F1) pada kata kunci "waktu" ada di blok Misc Technical (U+2300),
# di luar rentang lama -> tampil sebagai kotak kosong.
_EMOJI_CHAR_RANGES = (
    r"\U0001F000-\U0001FAFF"      # emoticon, pictograph, transport, symbol, extended-A
    r"\u2190-\u21FF"              # panah (↔ ↕ ⇄)
    r"\u2300-\u23FF"              # misc technical (⌚ ⏰ ⏱ ⏲ ⏳)
    r"\u2460-\u24FF"              # enclosed alphanumerics (① Ⓜ)
    r"\u25A0-\u25FF"              # geometric shapes (▶ ◀ ● ■)
    r"\u2600-\u27BF"              # misc symbols & dingbats (⚠ ✨ ✂)
    r"\u2B00-\u2BFF"              # misc symbols and arrows (⭐ ⬛ ⬜)
    r"\u3030\u303D\u3297\u3299"   # CJK symbols (〰 〽 ㊗ ㊙)
    r"\u2122\u2139\u2049\u203C"   # ™ ℹ ‼ ⁉
)
_EMOJI_CHAR = f"[{_EMOJI_CHAR_RANGES}]"

# Satu "cluster" emoji: base + variation selector + skin tone + rangkaian ZWJ.
# Cluster diperlakukan sebagai satu kesatuan agar urutan seperti 😮‍💨 tidak terpotong
# oleh tag {\fn...} di tengahnya.
_EMOJI_CLUSTER = (
    r"[\U0001F1E6-\U0001F1FF]{2}"                                        # bendera (2 regional indicator)
    rf"|{_EMOJI_CHAR}[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?"
    rf"(?:\u200D{_EMOJI_CHAR}[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?)*"  # rangkaian ZWJ
    r"|\u20E3"                                                           # keycap
)
_EMOJI_PATTERN = re.compile(f"({_EMOJI_CLUSTER})")

# Saat True, emoji TIDAK digambar oleh libass melainkan diganti placeholder
# transparan; gambar emoji berwarna asli ditempel sebagai overlay PNG di atas
# video (lihat backend/emoji_overlay.py). Di-set oleh generate_ass_subtitles()
# agar seluruh style generator memakai perilaku yang sama.
_EMOJI_OVERLAY_MODE = False


def _format_ass_word(text, base_color="&HFFFFFF&", alpha_hide=False, uppercase=False):
    """
    Format kata agar karakter emoji memakai font emoji yang tepat.

    Tiga mode:
    - Overlay (``_EMOJI_OVERLAY_MODE``): emoji ditulis memakai Noto Emoji tapi
      100% transparan. libass tetap MENYISAKAN ruang selebar emoji tersebut,
      lalu PNG emoji berwarna asli ditempel persis di ruang itu oleh ffmpeg.
      Hasil akhir: emoji persis seperti di HP (warna penuh), tanpa tint.
    - Warna native (Noto Color Emoji): hanya jika libass benar-benar mampu
      merender bitmap CBDT (probe lolos).
    - Fallback monokrom (Noto Emoji): emoji di-tint warna aksen EMOJI_COLORS.
    """
    if not text:
        return text

    emoji_font = _get_active_emoji_font()
    color_mode = emoji_font == EMOJI_FONT_COLOR

    def _replace_emoji(match):
        em = match.group(1)
        if em in ("\ufe0e", "\ufe0f", "\u200d"):
            return ""
        # Font emoji tidak butuh variation selector
        em = em.replace("\ufe0e", "").replace("\ufe0f", "")
        if _EMOJI_OVERLAY_MODE:
            # Placeholder transparan: ruang tetap disisakan untuk overlay PNG.
            # Bila kata ini memang sedang disembunyikan (alpha_hide), jangan
            # sentuh alpha sama sekali supaya sisa kata tetap ikut tersembunyi.
            if alpha_hide:
                return f"{{\\fn{EMOJI_FONT_MONO}}}{em}{{\\fn}}"
            return f"{{\\fn{EMOJI_FONT_MONO}\\alpha&HFF&}}{em}{{\\fn\\alpha&H00&}}"
        if color_mode:
            # Warna asli dari bitmap CBDT font - tanpa tint
            return f"{{\\fn{emoji_font}}}{em}{{\\fn}}"
        color = (
            EMOJI_COLORS.get(em)
            or EMOJI_COLORS.get(f"{em}\ufe0f")
            or EMOJI_COLORS.get(em[:1])
            or "&H00D4FF&"
        )
        if alpha_hide:
            return f"{{\\fn{emoji_font}\\alpha&HFF&}}{em}{{\\fn\\alpha&H00&}}"
        return f"{{\\fn{emoji_font}\\c{color}}}{em}{{\\fn\\c{base_color}}}"

    if uppercase:
        parts = _EMOJI_PATTERN.split(text)
        new_parts = []
        for p in parts:
            m = _EMOJI_PATTERN.match(p)
            if m:
                new_parts.append(_replace_emoji(m))
            else:
                new_parts.append(p.upper())
        return "".join(new_parts)

    return _EMOJI_PATTERN.sub(_replace_emoji, text)

def _calc_margin_v(sub_position=68):
    """Konversi posisi persentase dari atas layar ke nilai ASS MarginV (dari bawah).

    Posisi di-clamp ke SAFE ZONE vertikal: subtitle tidak boleh masuk ke area
    header atas (SAFE_TOP_PCT) maupun area caption/navigation bawah
    (SAFE_BOTTOM_PCT). Karena style memakai Alignment 2 (bottom-anchored),
    ``pos`` merepresentasikan tepi BAWAH blok subtitle.
    """
    try:
        pos = float(sub_position)
    except (ValueError, TypeError):
        pos = 68.0
    min_pos = SAFE_TOP_PCT          # jangan sampai blok naik ke area header
    max_pos = 100.0 - SAFE_BOTTOM_PCT  # jangan sampai turun ke area caption/nav
    pos = max(min_pos, min(max_pos, pos))
    return int(1920 * ((100.0 - pos) / 100.0))

def _build_watermark_ass_section(clip_start, clip_end, source_watermark="", account_watermark=""):
    """Mengembalikan (styles_str, dialogues_list) untuk watermark glass badge (Dark Smoked Glass)."""
    clean_src = (source_watermark or "").strip().replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", " ")
    clean_acc = (account_watermark or "").strip().replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", " ")
    if clean_acc and not clean_acc.startswith("@"):
        clean_acc = f"@{clean_acc}"

    styles = []
    dialogues = []
    duration = max(0.1, clip_end - clip_start)
    start_ass = "0:00:00.00"
    end_ass = format_ass_timestamp(duration)

    if clean_src:
        # Style GlassSource: Top-Left (Alignment 7), margin_v=160, margin_l=55
        # BorderStyle 3 (Box/Pill), Outline 14 (padding), Shadow 3 (soft elevation)
        # Box &H70181412 (dark smoked glass), Shadow &H90000000, teks putih tajam
        styles.append("Style: GlassSource,Plus Jakarta Sans,32,&H00FFFFFF,&H000000FF,&H70181412,&H90000000,-1,0,0,0,100,100,0.5,0,3,14,3,7,55,55,160,1")
        dialogues.append(f"Dialogue: 0,{start_ass},{end_ass},GlassSource,,0,0,0,,▶  Source: {clean_src}")

    if clean_acc:
        # Style GlassAccount: Top-Right (Alignment 9), margin_v=160, margin_r=55
        # Warna teks &H004DF8FF (Amber/Gold), box &H70181412
        styles.append("Style: GlassAccount,Plus Jakarta Sans,34,&H004DF8FF,&H000000FF,&H70181412,&H90000000,-1,0,0,0,100,100,0.5,0,3,14,3,9,55,55,160,1")
        dialogues.append(f"Dialogue: 0,{start_ass},{end_ass},GlassAccount,,0,0,0,,{clean_acc}")

    return "\n".join(styles), dialogues


def _generate_standalone_watermark_ass(out_ass_path, clip_start, clip_end, source_watermark, account_watermark):
    """Menulis file .ass hanya berisi watermark glass badge (saat mode no_subtitle aktif)."""
    styles_str, dialogues = _build_watermark_ass_section(clip_start, clip_end, source_watermark, account_watermark)
    if not dialogues:
        return
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_str}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"

    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)


def generate_ass_subtitles(segments, out_ass_path, clip_start, clip_end, sub_style="tiktok_viral", sub_position=68, show_emoji=True, watermark_enabled=True, source_watermark="", account_watermark="", inject_emoji=False, emoji_overlay=None, translation_mode=False):
    """Generate .ass subtitle file for specified style with optional glass-effect watermark badges.

    ``emoji_overlay``: True = tulis emoji sebagai placeholder transparan supaya
    bisa ditimpa PNG emoji berwarna asli (lihat backend/emoji_overlay.py).
    None = deteksi otomatis (aktif bila Pillow + NotoColorEmoji.ttf tersedia).
    """
    global _EMOJI_OVERLAY_MODE
    if emoji_overlay is None:
        emoji_overlay = _emoji_overlay_available()
    previous_overlay_mode = _EMOJI_OVERLAY_MODE
    _EMOJI_OVERLAY_MODE = bool(emoji_overlay) and bool(show_emoji)

    try:
        _generate_ass_body(
            segments, out_ass_path, clip_start, clip_end, sub_style, sub_position,
            show_emoji, watermark_enabled, source_watermark, account_watermark, inject_emoji,
            translation_mode=translation_mode,
        )
    finally:
        _EMOJI_OVERLAY_MODE = previous_overlay_mode


def _generate_ass_body(segments, out_ass_path, clip_start, clip_end, sub_style, sub_position,
                       show_emoji, watermark_enabled, source_watermark, account_watermark,
                       inject_emoji, translation_mode=False):
    has_wm = watermark_enabled and bool((source_watermark or "").strip() or (account_watermark or "").strip())
    extra_styles, extra_dialogues = ("", [])
    if has_wm:
        extra_styles, extra_dialogues = _build_watermark_ass_section(clip_start, clip_end, source_watermark, account_watermark)

    if sub_style in ["none", "no_subtitle"]:
        if has_wm:
            _generate_standalone_watermark_ass(out_ass_path, clip_start, clip_end, source_watermark, account_watermark)
        return

    # Collect words from segments with strict word-level boundary checking
    words = []
    for seg in segments:
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", 0.0))
        if seg_end <= clip_start or seg_start >= clip_end:
            continue
        if "words" in seg and seg["words"]:
            for w in seg["words"]:
                w_start = float(w.get("start", 0.0))
                w_end = float(w.get("end", 0.0))
                if w_end > clip_start and w_start < clip_end:
                    words.append(w)
        else:
            words.append({"word": seg.get("text", ""), "start": seg_start, "end": seg_end})

    # Sanitize timestamps to guarantee clean, non-overlapping flow
    sanitized_words = _sanitize_word_timestamps(words, clip_start, clip_end)
    if not sanitized_words:
        if has_wm:
            _generate_standalone_watermark_ass(out_ass_path, clip_start, clip_end, source_watermark, account_watermark)
        return

    # Mode terjemahan: audio != subtitle, jadi highlight per-kata menyesatkan
    # (timing kata hasil terjemahan hanya proporsional terhadap panjang
    # karakter). Emoji TIDAK dimatikan: teks hasil terjemahan dari LLM hampir
    # tidak pernah mengandung emoji, jadi injeksi kata kunci adalah satu-satunya
    # sumber emoji pada mode ini.
    translation = bool(translation_mode) or sub_style == "translation_read"

    # Emoji asli dari transkrip dirender jika show_emoji aktif.
    # Injeksi emoji kata kunci (EMOJI_KEYWORDS) hanya jika inject_emoji=True
    # (opsional, default OFF - lihat flag --inject-emoji di worker).
    if inject_emoji and show_emoji:
        sanitized_words = _inject_emojis_to_words(sanitized_words)
    elif not show_emoji:
        # show_emoji=False: buang semua emoji dari teks subtitle
        sanitized_words = [
            {**w, "word": _EMOJI_PATTERN.sub("", w["word"]).strip()} for w in sanitized_words
        ]

    margin_v = _calc_margin_v(sub_position)

    cues = None
    if translation:
        chunks = _chunk_words(
            sanitized_words,
            max_words=TRANSLATION_CHUNK_MAX_WORDS,
            max_chars=TRANSLATION_CHUNK_MAX_CHARS,
            uppercase=False,
            break_on_comma=False,
            max_gap=TRANSLATION_CHUNK_MAX_GAP,
        )
        cues = _schedule_cues(chunks)

    if sub_style == "translation_read" or (
        translation and sub_style in ("tiktok_viral", "classic_karaoke", "word_pop")
    ):
        # Preset bergaya kata (viral/karaoke/word pop) tidak cocok untuk teks
        # terjemahan: otomatis dialihkan ke tampilan kalimat yang mudah dibaca.
        _generate_translation_read_style(cues, out_ass_path, clip_start, clip_end,
                                         margin_v=margin_v, extra_styles=extra_styles,
                                         extra_dialogues=extra_dialogues)
    elif sub_style == "minimalist":
        _generate_minimalist_style(sanitized_words, out_ass_path, clip_start, clip_end,
                                   margin_v=margin_v, extra_styles=extra_styles,
                                   extra_dialogues=extra_dialogues, cues=cues)
    elif sub_style == "classic_karaoke":
        _generate_classic_karaoke_style(sanitized_words, out_ass_path, clip_start, clip_end, margin_v=margin_v, extra_styles=extra_styles, extra_dialogues=extra_dialogues)
    elif sub_style == "word_pop":
        _generate_word_pop_style(sanitized_words, out_ass_path, clip_start, clip_end, margin_v=margin_v, extra_styles=extra_styles, extra_dialogues=extra_dialogues)
    else:
        _generate_tiktok_viral_style(sanitized_words, out_ass_path, clip_start, clip_end, margin_v=margin_v, extra_styles=extra_styles, extra_dialogues=extra_dialogues)


def _chunk_words(words, max_words=2, max_chars=14, uppercase=False,
                 break_on_comma=True, max_gap=None):
    """Split sanitized words into display chunks that fit the 9:16 safe width.

    The character budget is enforced BEFORE a word is added, so a chunk can
    never exceed ``max_chars`` (except when a single word is itself longer).
    Previously the limit was checked after appending, which produced over-long
    lines that spilled past the left/right safe-zone margins.

    ``break_on_comma=False`` dipakai mode terjemahan: koma di bahasa Indonesia
    sangat sering, memotong di koma menghasilkan fragmen seperti
    "Konsisten itu" / "lebih penting".

    ``max_gap`` (detik) memaksa cue baru saat ada jeda hening, sehingga batas
    cue mengikuti frasa alami pembicara, bukan sekadar hitungan karakter.
    """
    chunks, current_chunk, current_len = [], [], 0
    prev_end = None
    terminators = ".?!," if break_on_comma else ".?!"

    for word_info in words:
        text = word_info["word"].strip()
        if uppercase:
            text = text.upper()
        if not text:
            continue

        gap_break = (
            max_gap is not None
            and prev_end is not None
            and float(word_info["start"]) - prev_end >= max_gap
        )

        # +1 accounts for the joining space when the chunk already has content.
        # Emoji tidak dihitung: lebarnya kecil dan pada mode overlay digambar
        # sebagai PNG di luar alur teks.
        text_len = _display_len(text)
        projected = current_len + text_len + (1 if current_chunk else 0)
        if current_chunk and (
            gap_break or len(current_chunk) >= max_words or projected > max_chars
        ):
            chunks.append(current_chunk)
            current_chunk, current_len = [], 0
            projected = text_len

        current_chunk.append({"word": text, "start": word_info["start"], "end": word_info["end"]})
        current_len = projected
        prev_end = float(word_info["end"])

        # A sentence terminator naturally closes the current chunk.
        if text[-1] in terminators:
            chunks.append(current_chunk)
            current_chunk, current_len = [], 0

    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def _split_words_into_lines(words, max_line_chars=TRANSLATION_LINE_CHARS, max_lines=2):
    """Bagi satu cue jadi maksimal ``max_lines`` baris yang seimbang.

    Pemotongan HANYA di batas kata (tidak pernah memotong kata), dan dipilih
    titik yang mendekati panjang rata-rata supaya tidak ada satu kata
    menggantung sendirian di baris kedua.
    """
    if not words:
        return []
    if len(words) == 1:
        return [words]

    # Emoji tidak dihitung (digambar lebih kecil / sebagai PNG overlay).
    total_chars = _display_len(" ".join(w["word"] for w in words))
    if total_chars <= max_line_chars:
        # Sudah muat satu baris: jangan dipecah. Memaksa 2 baris pada cue
        # pendek menghasilkan tampilan janggal seperti "online" / "ini".
        return [words]

    target = total_chars / max(1, max_lines)

    lines, current, current_len = [], [], 0
    for w in words:
        word = w["word"]
        word_len = _display_len(word)
        projected = current_len + word_len + (1 if current else 0)
        over_budget = projected > max_line_chars
        balanced = len(lines) < max_lines - 1 and bool(current) and current_len >= target
        if current and (over_budget or balanced):
            lines.append(current)
            current, current_len = [], 0
            projected = word_len
        current.append(w)
        current_len = projected

    if current:
        lines.append(current)

    # Overflow (kata tunggal yang sangat panjang) digabung ke baris terakhir;
    # libass akan wrap sendiri karena WrapStyle: 0.
    if len(lines) > max_lines:
        head = lines[:max_lines - 1]
        tail = [w for line in lines[max_lines - 1:] for w in line]
        lines = head + [tail]
    return lines

def _schedule_cues(chunks, cps=TRANSLATION_READ_CPS, min_dur=TRANSLATION_MIN_CUE,
                   max_dur=TRANSLATION_MAX_CUE, hold=TRANSLATION_CUE_HOLD,
                   max_drift=TRANSLATION_MAX_DRIFT, gap=0.04):
    """Beri tiap cue waktu baca minimum tanpa pernah menabrak cue berikutnya.

    Durasi audio tidak bisa diulur, jadi lever yang dipakai:
    1. tahan cue lebih lama (reading-time floor = panjang teks / ``cps``),
    2. cue berikutnya baru muncul setelah cue sebelumnya selesai dibaca,
       sehingga subtitle boleh sedikit tertinggal dari audio,
    3. batasi lag kumulatif (``max_drift``) supaya subtitle tidak makin
       tertinggal jauh di bagian bicara cepat. Bila anggaran lag habis, cue
       dipangkas ke ``min_dur`` — lebih baik cepat daripada tidak sinkron.
    """
    if not chunks:
        return []

    cues = []
    cursor = 0.0
    for i, chunk in enumerate(chunks):
        text = " ".join(w["word"] for w in chunk)
        natural_start = float(chunk[0]["start"])
        natural_end = float(chunk[-1]["end"])
        next_natural = float(chunks[i + 1][0]["start"]) if i + 1 < len(chunks) else None

        # Tidak boleh tampil sebelum audionya, tidak boleh menabrak cue sebelumnya.
        start = max(natural_start, cursor)
        need = max(min_dur, len(text) / max(1.0, cps))
        end = min(max(natural_end, start + need), start + max_dur)

        # Batasi lag cue BERIKUTNYA, bukan cue ini: kalau cue ini terlalu lama
        # tampil, cue selanjutnya makin tertinggal dari audio.
        if next_natural is not None:
            end = min(end, max(start + min_dur, next_natural + max_drift - gap))
        else:
            end = min(end, natural_end + hold + max_drift)

        end = max(end, start + min_dur)

        cues.append({"words": chunk, "text": text, "start": start, "end": end})
        cursor = end + gap

    return cues


def _generate_tiktok_viral_style(words, out_ass_path, clip_start, clip_end, margin_v=600, extra_styles="", extra_dialogues=None):
    """🎬 TikTok Viral: Plus Jakarta Sans Bold + Outline Tipis Modern + Highlight Kuning Pop."""
    styles_block = f"Style: ViralStyle,Plus Jakarta Sans,84,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,2,2,{SAFE_MARGIN_H},{SAFE_MARGIN_H},{margin_v},1\n"
    if extra_styles:
        styles_block += f"{extra_styles}\n"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: {SAFE_WRAP_STYLE}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_block}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    limits = STYLE_CHUNK_LIMITS["tiktok_viral"]
    chunks = _chunk_words(words, max_words=limits["max_words"], max_chars=limits["max_chars"], uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        if extra_dialogues:
            for d in extra_dialogues:
                f.write(f"{d}\n")
        for chunk in chunks:
            for i in range(len(chunk)):
                start_ass = format_ass_timestamp(chunk[i]["start"])
                # Chunk end time matches next word start or chunk end
                next_start = chunk[i+1]["start"] if i + 1 < len(chunk) else chunk[-1]["end"]
                end_ass = format_ass_timestamp(max(chunk[i]["end"], next_start))
                display = []
                for j in range(len(chunk)):
                    raw_word = chunk[j]["word"]
                    if j < i: 
                        display.append(_format_ass_word(raw_word, base_color="&HFFFFFF&"))
                    elif j == i: 
                        pop_word = _format_ass_word(raw_word, base_color="&H0000FFFF&")
                        display.append(f"{{\\c&H0000FFFF&}}{{\\fs92}}{pop_word}{{\\fs84}}{{\\c&HFFFFFF&}}")
                    else: 
                        display.append(f"{{\\alpha&HFF&}}{_format_ass_word(raw_word, alpha_hide=True)}{{\\alpha&H00&}}")
                f.write(f"Dialogue: 0,{start_ass},{end_ass},ViralStyle,,0,0,0,,{' '.join(display)}\n")


def _generate_classic_karaoke_style(words, out_ass_path, clip_start, clip_end, margin_v=580, extra_styles="", extra_dialogues=None):
    """🎤 Classic Karaoke: Teks natural case dengan sapuan highlight Electric Cyan / Mint per kata sesuai preview."""
    styles_block = f"Style: KaraokeStyle,Montserrat,84,&H00FFFFFF,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,0,0,1,8,4,2,{SAFE_MARGIN_H},{SAFE_MARGIN_H},{margin_v},1\n"
    if extra_styles:
        styles_block += f"{extra_styles}\n"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: {SAFE_WRAP_STYLE}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_block}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # 2-3 words per chunk for readable karaoke phrasing (kept inside the safe width)
    limits = STYLE_CHUNK_LIMITS["classic_karaoke"]
    chunks = _chunk_words(words, max_words=limits["max_words"], max_chars=limits["max_chars"], uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        if extra_dialogues:
            for d in extra_dialogues:
                f.write(f"{d}\n")
        for chunk in chunks:
            for i in range(len(chunk)):
                start_ass = format_ass_timestamp(chunk[i]["start"])
                next_start = chunk[i+1]["start"] if i + 1 < len(chunk) else chunk[-1]["end"]
                end_ass = format_ass_timestamp(max(chunk[i]["end"], next_start))
                display = []
                for j in range(len(chunk)):
                    raw_word = chunk[j]["word"]
                    if j < i:
                        # Kata yang sudah lewat: Tetap putih bersih
                        display.append(f"{{\\c&H00FFFFFF&}}{_format_ass_word(raw_word, base_color='&H00FFFFFF&')}")
                    elif j == i:
                        # Kata aktif: Highlight Electric Cyan / Mint cerah (&H00D4F500&) dengan pop font
                        karaoke_word = _format_ass_word(raw_word, base_color="&H00D4F500&")
                        display.append(f"{{\\c&H00D4F500&}}{{\\fs94}}{karaoke_word}{{\\fs84}}{{\\c&H00FFFFFF&}}")
                    else:
                        # Kata mendatang: Putih solid
                        display.append(f"{{\\c&H00FFFFFF&}}{_format_ass_word(raw_word, base_color='&H00FFFFFF&')}")
                f.write(f"Dialogue: 0,{start_ass},{end_ass},KaraokeStyle,,0,0,0,,{' '.join(display)}\n")


def _write_static_cue_ass(cues, out_ass_path, style_line, style_name,
                          extra_styles="", extra_dialogues=None,
                          line_chars=TRANSLATION_LINE_CHARS, fade_ms=70):
    """Tulis .ass berisi cue kalimat statis (1-2 baris) tanpa animasi per kata."""
    styles_block = f"{style_line}\n"
    if extra_styles:
        styles_block += f"{extra_styles}\n"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: {SAFE_WRAP_STYLE}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_block}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for d in (extra_dialogues or []):
            f.write(f"{d}\n")
        for cue in cues:
            lines = _split_words_into_lines(cue["words"], line_chars)
            rendered = "\\N".join(
                " ".join(_format_ass_word(w["word"], base_color="&HFFFFFF&") for w in line)
                for line in lines
            )
            if fade_ms:
                # Fade halus: mata pembaca non-native butuh penanda "teks baru".
                rendered = f"{{\\fad({fade_ms},{fade_ms})}}{rendered}"
            f.write(
                f"Dialogue: 0,{format_ass_timestamp(cue['start'])},"
                f"{format_ass_timestamp(cue['end'])},{style_name},,0,0,0,,{rendered}\n"
            )

def _generate_translation_read_style(cues, out_ass_path, clip_start, clip_end, margin_v=600,
                                     extra_styles="", extra_dialogues=None):
    """📖 Terjemahan Mudah Dibaca: kalimat utuh 1-2 baris, tanpa highlight per kata.

    BorderStyle 3 (opaque box) dengan Outline sebagai padding memberi latar
    gelap tipis supaya teks tetap terbaca di atas footage yang ramai.
    """
    style_line = (
        "Style: ReadStyle,Plus Jakarta Sans,66,&H00FFFFFF,&H000000FF,&H78000000,&H80000000,"
        f"-1,0,0,0,100,100,0.4,0,3,12,2,2,{SAFE_MARGIN_H},{SAFE_MARGIN_H},{margin_v},1"
    )
    _write_static_cue_ass(
        cues, out_ass_path, style_line, "ReadStyle",
        extra_styles=extra_styles, extra_dialogues=extra_dialogues,
    )

def _generate_minimalist_style(words, out_ass_path, clip_start, clip_end, margin_v=560, extra_styles="", extra_dialogues=None, cues=None):
    """✨ Minimalist: Teks putih bersih statis, elegan dan tidak mengganggu konten podcast."""
    if cues is not None:
        # Mode terjemahan: pakai cue terjadwal + pemenggalan 2 baris.
        style_line = (
            "Style: MinimalStyle,Plus Jakarta Sans,74,&H00FFFFFF,&H000000FF,&H00151515,&HAA000000,"
            f"-1,0,0,0,100,100,0,0,1,5,3,2,{SAFE_MARGIN_H},{SAFE_MARGIN_H},{margin_v},1"
        )
        _write_static_cue_ass(
            cues, out_ass_path, style_line, "MinimalStyle",
            extra_styles=extra_styles, extra_dialogues=extra_dialogues, fade_ms=0,
        )
        return
    styles_block = f"Style: MinimalStyle,Plus Jakarta Sans,74,&H00FFFFFF,&H000000FF,&H00151515,&HAA000000,-1,0,0,0,100,100,0,0,1,5,3,2,{SAFE_MARGIN_H},{SAFE_MARGIN_H},{margin_v},1\n"
    if extra_styles:
        styles_block += f"{extra_styles}\n"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: {SAFE_WRAP_STYLE}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_block}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # 3-4 words per line for clean readability (kept inside the safe width)
    limits = STYLE_CHUNK_LIMITS["minimalist"]
    chunks = _chunk_words(words, max_words=limits["max_words"], max_chars=limits["max_chars"], uppercase=False)
    
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        if extra_dialogues:
            for d in extra_dialogues:
                f.write(f"{d}\n")
        for chunk in chunks:
            start_ass = format_ass_timestamp(chunk[0]["start"])
            end_ass = format_ass_timestamp(chunk[-1]["end"])
            text_line = " ".join([_format_ass_word(w["word"], base_color="&HFFFFFF&") for w in chunk])
            f.write(f"Dialogue: 0,{start_ass},{end_ass},MinimalStyle,,0,0,0,,{text_line}\n")


def _generate_word_pop_style(words, out_ass_path, clip_start, clip_end, margin_v=960, extra_styles="", extra_dialogues=None):
    """⚡ Word Pop (Reels): Menampilkan 1 kata besar per saat di posisi tengah."""
    styles_block = f"Style: WordPopStyle,Impact,108,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,12,6,2,{SAFE_MARGIN_H},{SAFE_MARGIN_H},{margin_v},1\n"
    if extra_styles:
        styles_block += f"{extra_styles}\n"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: {SAFE_WRAP_STYLE}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_block}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Safe usable width and an approximate per-glyph width for Impact (bold).
    usable_w = 1080 - 2 * SAFE_MARGIN_H
    glyph_ratio = 0.60
    base_fs = 108
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        if extra_dialogues:
            for d in extra_dialogues:
                f.write(f"{d}\n")
        for i, w in enumerate(words):
            start_ass = format_ass_timestamp(w["start"])
            next_start = words[i+1]["start"] if i + 1 < len(words) else w["end"]
            end_ass = format_ass_timestamp(max(w["end"], next_start))
            # Emoji harus lewat _format_ass_word agar dibungkus font Noto Emoji
            # (menulis teks mentah akan menghasilkan kotak kosong / tofu).
            text = _format_ass_word(w["word"], base_color="&HFFFFFF&", uppercase=True)
            # Auto-shrink long single words so they never spill past the safe width.
            word_len = max(1, len(w["word"].strip()))
            fit_fs = int(usable_w / (glyph_ratio * word_len))
            fs = max(44, min(base_fs, fit_fs))
            # Dynamic punchy scale effect on entry
            f.write(f"Dialogue: 0,{start_ass},{end_ass},WordPopStyle,,0,0,0,,{{\\fs{fs}}}{{\\t(0,60,\\fscx110\\fscy110)}}{{\\t(60,120,\\fscx100\\fscy100)}}{text}\n")

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
    try:
        width, height, _ = _probe_video_stream(video_path)
    except Exception:
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
    Main 16:9 video dinaikkan 5% ke atas (posisi seimbang & proporsional untuk subtitle).
    """
    log("Applying Fit 16:9 with Blurred Background (Video dinaikkan 5% untuk ruang subtitle)...", job_id=job_id)
    ffmpeg_bin = get_ffmpeg_binary()
    clip_dur = end_time - start_time

    # FFmpeg filter:
    # Background: scale to 1080x1920 crop, heavy blur & slight darken
    # Foreground: scale to 1080:-1 (approx 1080x608), dinaikkan 10% dari posisi tengah
    # Posisi tengah = (H-h)/2. Dinaikkan 10% (192px) = (H-h)/2 - (H*0.10)
    fc_filter = (
        f"[0:v]split=2[bg_in][fg_in];"
        f"[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.08[bg];"
        f"[fg_in]scale=1080:-1[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2-(H*0.05)[v]"
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

def _gaussian_smooth(arr, sigma=28):
    """Filter Gaussian 1D untuk menghasilkan pergerakan kamera sinematik/gimbal gliding."""
    radius = int(sigma * 3)
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.pad(arr, radius, mode='edge')
    smoothed = np.convolve(padded, kernel, mode='valid')
    return smoothed


# ═══════════════════════════════════════════════════════════════
# SCENE-CUT DETECTION (podcast multi-kamera)
# ═══════════════════════════════════════════════════════════════
# Skor = rata-rata selisih absolut piksel HSV antar frame (skala 0-255, ala PySceneDetect ContentDetector).
# Lebih andal daripada histogram untuk cut antar angle di studio yang warnanya mirip.
SCENE_CUT_DEFAULT_THRESHOLD = 27.0
SCENE_CUT_MIN_GAP_SEC = 0.4
SCENE_SIGNATURE_WIDTH = 160


def _frame_signature(frame):
    """Thumbnail HSV kecil (int16) untuk perbandingan antar frame yang murah."""
    h, w = frame.shape[:2]
    sig_h = max(2, int(round(h * SCENE_SIGNATURE_WIDTH / float(w))))
    small = cv2.resize(frame, (SCENE_SIGNATURE_WIDTH, sig_h), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2HSV).astype(np.int16)


class SceneCutDetector:
    """
    Deteksi hard cut secara streaming (kausal), sehingga deteksi wajah bisa dipaksa jalan
    tepat di frame pertama angle baru.
    Cut jika: skor >= threshold, ATAU skor >= 60% threshold dan >= 3x rata-rata skor ~1 detik terakhir
    (menangkap cut antar angle yang warnanya mirip tanpa sensitif terhadap gerakan biasa).
    """

    def __init__(self, fps, threshold=SCENE_CUT_DEFAULT_THRESHOLD, min_gap_sec=SCENE_CUT_MIN_GAP_SEC):
        from collections import deque
        self.threshold = float(threshold)
        self.min_gap_frames = max(1, int(round(min_gap_sec * fps)))
        self.recent_scores = deque(maxlen=max(4, int(round(fps))))
        self.prev_signature = None
        self.last_cut_frame = None
        self.cuts = []

    def update(self, frame_idx, frame):
        signature = _frame_signature(frame)
        prev = self.prev_signature
        self.prev_signature = signature
        if prev is None or prev.shape != signature.shape:
            return False

        diff = np.abs(signature - prev)
        # Hue OpenCV melingkar (0..179): merah/warna kulit di sekitar 0<->179 jangan dianggap beda jauh
        diff[..., 0] = np.minimum(diff[..., 0], 180 - diff[..., 0])
        score = float(np.mean(diff))
        baseline = float(np.mean(self.recent_scores)) if self.recent_scores else 0.0
        self.recent_scores.append(score)

        is_cut = score >= self.threshold or (
            score >= self.threshold * 0.6 and score >= 3.0 * max(baseline, 1.0)
        )
        if not is_cut:
            return False
        if self.last_cut_frame is not None and frame_idx - self.last_cut_frame < self.min_gap_frames:
            return False  # Flash/strobe: abaikan cut beruntun dalam < 0.4 detik

        self.last_cut_frame = frame_idx
        self.cuts.append(frame_idx)
        # Mulai baseline baru untuk shot baru
        self.recent_scores.clear()
        return True


def _build_shot_trajectory(total_frames, sample_indices, sample_values, cut_frames, deadzone_px, sigma, default_x):
    """
    Bangun posisi center-X per frame, diproses PER SHOT (dipisah oleh cut_frames):
    interpolasi + deadzone + Gaussian smoothing tidak pernah melewati batas cut, sehingga kamera
    langsung "snap" ke angle baru tanpa meluncur.

    sample_values boleh berisi None/NaN (deteksi gagal): di dalam shot posisi ditahan dari deteksi
    sebelumnya; shot tanpa deteksi sama sekali memakai posisi akhir shot sebelumnya (atau default_x).
    """
    total_frames = int(total_frames)
    if total_frames <= 0:
        return np.zeros(0, dtype=np.float64)

    idx = np.asarray(sample_indices, dtype=np.int64).reshape(-1)
    vals = np.asarray([np.nan if v is None else v for v in sample_values], dtype=np.float64).reshape(-1)
    order = np.argsort(idx, kind="stable")
    idx, vals = idx[order], vals[order]

    bounds = sorted({int(c) for c in cut_frames if 0 < int(c) < total_frames})
    starts = [0] + bounds
    ends = bounds + [total_frames]

    out = np.empty(total_frames, dtype=np.float64)
    prev_final = float(default_x)
    for s, e in zip(starts, ends):
        mask = (idx >= s) & (idx < e)
        shot_idx = idx[mask]
        shot_vals = vals[mask].copy()

        # Forward-fill deteksi gagal dengan deteksi terakhir DI DALAM shot ini saja
        last = np.nan
        for k in range(len(shot_vals)):
            if np.isnan(shot_vals[k]):
                shot_vals[k] = last
            else:
                last = shot_vals[k]
        valid = ~np.isnan(shot_vals)

        if not valid.any():
            seg = np.full(e - s, prev_final, dtype=np.float64)
        else:
            # np.interp menahan nilai di tepi -> deteksi pertama shot dipakai mundur ke awal shot
            seg = np.interp(np.arange(s, e), shot_idx[valid], shot_vals[valid])

            # Deadzone Filter (kunci tripod jika gerakan mikro di bawah toleransi), reset per shot
            anchor = seg[0]
            deadzoned = np.empty_like(seg)
            for i, value in enumerate(seg):
                if abs(value - anchor) > deadzone_px:
                    anchor = value
                deadzoned[i] = anchor

            # Gaussian Smoothing (kurva gimbal lembut), hanya di dalam shot
            seg = _gaussian_smooth(deadzoned, sigma=sigma) if len(deadzoned) > 1 else deadzoned

        out[s:e] = seg
        prev_final = float(seg[-1])
    return out


# ═══════════════════════════════════════════════════════════════
# AUDIO: COMPRESSOR + LOUDNORM 2-PASS (target LUFS platform short video)
# ═══════════════════════════════════════════════════════════════
AUDIO_SAMPLE_RATE = 48000
AUDIO_BITRATE = "192k"
DEFAULT_TARGET_LUFS = -14.0   # Standar normalisasi TikTok / Reels / YouTube Shorts
LOUDNORM_TRUE_PEAK = -1.5
LOUDNORM_LRA = 11.0
SILENCE_LUFS_FLOOR = -50.0    # Di bawah ini dianggap (hampir) sunyi -> jangan dinaikkan
_LOUDNORM_KEYS = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")


def get_audio_settings():
    return {
        "target_lufs": env_float("VC_TARGET_LUFS", DEFAULT_TARGET_LUFS, -30.0, -5.0),
        "denoise": env_bool("VC_AUDIO_DENOISE", False),
    }


def build_audio_pre_chain(denoise=False):
    """Rantai audio sebelum normalisasi: highpass ringan, (opsional) denoise, compressor halus."""
    parts = ["asetpts=PTS-STARTPTS", "highpass=f=80"]
    if denoise:
        parts.append("afftdn=nr=10:nf=-40")
    parts.append("acompressor=threshold=-18dB:ratio=3:attack=5:release=80:makeup=2dB")
    return ",".join(parts)


def _loudnorm_base(target_lufs):
    return f"loudnorm=I={target_lufs:g}:TP={LOUDNORM_TRUE_PEAK:g}:LRA={LOUDNORM_LRA:g}"


def _parse_loudnorm_json(text):
    """Ambil blok JSON hasil `loudnorm=print_format=json` dari stderr FFmpeg. Return dict float atau None."""
    if not text:
        return None
    blocks = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", text, re.S)
    if not blocks:
        return None
    try:
        data = json.loads(blocks[-1])
        return {key: float(data[key]) for key in _LOUDNORM_KEYS}
    except (ValueError, KeyError, TypeError):
        return None


def _measure_loudness(video_path, start, duration, pre_chain, target_lufs, job_id=None):
    """Pass ukur loudnorm (audio saja, tanpa decode video). Return dict hasil ukur atau None jika gagal."""
    cmd = [
        get_ffmpeg_binary(), "-hide_banner", "-nostats",
        "-ss", f"{float(start):.3f}", "-t", f"{float(duration):.3f}",
        "-i", video_path,
        "-vn", "-sn", "-map", "0:a:0",
        "-af", f"{pre_chain},{_loudnorm_base(target_lufs)}:print_format=json",
        "-f", "null", "-",
    ]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=max(60.0, float(duration) * 3), **kwargs)
    except Exception as e:
        log(f"Info: pengukuran loudness gagal ({e}), memakai loudnorm 1-pass.", job_id=job_id)
        return None
    if res.returncode != 0:
        return None
    return _parse_loudnorm_json(res.stderr)


def build_audio_filter(fade_out_start, pre_chain, target_lufs, measurement=None):
    """
    Return (filter_string, mode). mode:
      - "two_pass": loudnorm linear memakai hasil ukur (paling natural, tanpa pumping)
      - "single_pass": loudnorm dinamis (fallback jika pengukuran gagal)
      - "skip": klip (hampir) sunyi, tidak dinormalisasi agar noise tidak ikut dikeraskan
    """
    loudnorm = _loudnorm_base(target_lufs)
    mode = "single_pass"
    if measurement:
        values = [measurement.get(key) for key in _LOUDNORM_KEYS]
        finite = all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)
        if not finite or measurement["input_i"] < SILENCE_LUFS_FLOOR:
            loudnorm = None
            mode = "skip"
        else:
            loudnorm += (
                f":measured_I={measurement['input_i']:.2f}"
                f":measured_TP={measurement['input_tp']:.2f}"
                f":measured_LRA={measurement['input_lra']:.2f}"
                f":measured_thresh={measurement['input_thresh']:.2f}"
                f":offset={measurement['target_offset']:.2f}"
                f":linear=true"
            )
            mode = "two_pass"

    parts = [pre_chain]
    if loudnorm:
        parts.append(loudnorm)
    parts.append(f"afade=t=out:st={max(0.0, float(fade_out_start)):.3f}:d=0.5")
    return ",".join(parts), mode

_YOLO_MODEL_CACHE = {}

# Lebar maksimum frame untuk Pass 1 (deteksi). Deteksi tidak butuh resolusi penuh,
# jadi decode di resolusi kecil jauh lebih cepat, terutama untuk sumber 1440p/4K.
ANALYSIS_MAX_WIDTH = 960

# Fallback statis jika tracking gagal: kunci kursi pembicara (kiri ~28%), BUKAN tengah meja (50%).
STATIC_FALLBACK_CROP_CHAIN = (
    "setpts=PTS-STARTPTS,crop=ih*9/16:ih:iw*0.14:0,"
    "scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
)


def _get_yolo_model(job_id=None):
    """Load YOLOv8 sekali per proses lalu dipakai ulang untuk semua klip."""
    if "model" not in _YOLO_MODEL_CACHE:
        try:
            from ultralytics import YOLO
            _YOLO_MODEL_CACHE["model"] = YOLO(YOLO_MODEL_PATH)
        except Exception as e:
            log(f"Warning: YOLOv8 failed to load ({e}), falling back to YuNet Face Detector...", job_id=job_id)
            _YOLO_MODEL_CACHE["model"] = None
    return _YOLO_MODEL_CACHE["model"]


def _get_torch_device():
    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _probe_video_stream(video_path):
    """Return (width, height, fps) of the first video stream using ffprobe (supports H.264/VP9/AV1)."""
    ffprobe_bin = get_ffprobe_binary()
    cmd = [
        ffprobe_bin, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate",
        "-of", "json", video_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe gagal membaca video: {res.stderr.strip()[:200]}")
    streams = json.loads(res.stdout or "{}").get("streams", [])
    if not streams:
        raise RuntimeError(f"Tidak ada stream video di: {video_path}")

    stream = streams[0]
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Resolusi video tidak valid: {width}x{height}")

    fps = 0.0
    for key in ("avg_frame_rate", "r_frame_rate"):
        raw = str(stream.get(key) or "0/0")
        try:
            num, den = raw.split("/") if "/" in raw else (raw, "1")
            if float(num) > 0 and float(den) > 0:
                fps = float(num) / float(den)
                break
        except ValueError:
            continue
    if fps <= 0 or fps > 240:
        fps = 30.0
    return width, height, fps


def _iter_ffmpeg_frames(video_path, start_time, duration, fps, out_w, out_h):
    """
    Decode segmen video lewat FFmpeg (seek akurat + CFR) dan yield frame BGR berukuran out_w x out_h.
    Memakai decoder yang sama dengan render final sehingga trajektori crop sinkron dengan audio.
    """
    ffmpeg_bin = get_ffmpeg_binary()
    cmd = [
        ffmpeg_bin, "-v", "error",
        "-ss", f"{start_time:.3f}", "-t", f"{duration:.3f}",
        "-i", video_path,
        "-an", "-sn",
        "-vf", f"fps={fps:.6f},scale={out_w}:{out_h}:flags=area",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1",
    ]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000
    frame_bytes = out_w * out_h * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=frame_bytes * 2, **kwargs)
    try:
        while True:
            buf = proc.stdout.read(frame_bytes)
            if not buf or len(buf) < frame_bytes:
                break
            yield np.frombuffer(buf, dtype=np.uint8).reshape((out_h, out_w, 3)).copy()
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def compute_smart_crop_trajectory(video_path, start_time, end_time, job_id=None):
    """
    Pass 1 Turbo Cinema Clipper: scan narasumber (YOLOv8 person / YuNet face) di frame resolusi kecil,
    lalu hasilkan trajektori posisi crop 9:16 per frame (koordinat resolusi ASLI) yang sudah
    di-deadzone + Gaussian smoothing. Tidak ada encoding video di tahap ini.
    """
    orig_w, orig_h, fps = _probe_video_stream(video_path)
    duration = max(0.1, float(end_time) - float(start_time))
    total_clip_frames = max(1, int(round(duration * fps)))

    # Ukuran crop vertikal 9:16 di resolusi asli
    target_aspect_ratio = 9.0 / 16.0
    crop_h = orig_h
    crop_w = int(crop_h * target_aspect_ratio)
    if crop_w % 2 != 0: crop_w -= 1
    if crop_w > orig_w:
        crop_w = orig_w
        if crop_w % 2 != 0: crop_w -= 1
        crop_h = int(crop_w / target_aspect_ratio)
        if crop_h % 2 != 0: crop_h -= 1
    crop_y = max(0, ((orig_h - crop_h) // 2) // 2 * 2)

    # Resolusi analisis (downscaled)
    ana_w = min(orig_w, ANALYSIS_MAX_WIDTH)
    ana_w -= ana_w % 2
    ana_h = max(2, int(round(orig_h * ana_w / orig_w)))
    ana_h -= ana_h % 2
    scale_x = orig_w / float(ana_w)

    # Parameter berbasis WAKTU agar perilaku sama di 24/30/60 fps (di 30fps: stride=5, sigma=25)
    stride = max(1, int(round(fps / 6.0)))   # Jalankan AI ~6x per detik (memotong beban ~80%)
    smooth_sigma = max(1.0, fps * (25.0 / 30.0))  # ~0.83 detik kurva gimbal
    deadzone_ratio = 0.08  # 8% lebar layar = toleransi diam (kunci tripod)
    deadzone_px = orig_w * deadzone_ratio
    default_center_x = orig_w / 2.0
    scene_threshold = env_float("VC_SCENE_CUT_THRESHOLD", SCENE_CUT_DEFAULT_THRESHOLD, 5.0, 100.0)
    cut_detector = SceneCutDetector(fps, threshold=scene_threshold)

    device = _get_torch_device()
    yolo_model = _get_yolo_model(job_id=job_id)
    log(
        f"Applying Turbo Cinema Clipper (YOLOv8 [{device.upper()}] + Stride {stride} + Scene-Cut Aware Gaussian 9:16) | "
        f"Sumber {orig_w}x{orig_h} @ {fps:.2f}fps -> crop {crop_w}x{crop_h}",
        job_id=job_id,
    )
    if crop_w < 1080:
        log(f"Info: lebar crop {crop_w}px < 1080px, video akan di-upscale. Sumber resolusi lebih tinggi = hasil lebih tajam.", job_id=job_id)

    # Fallback detector (YuNet DNN) jika YOLOv8 tidak tersedia
    yunet_detector = None
    if yolo_model is None and os.path.exists(YUNET_MODEL_PATH) and hasattr(cv2, 'FaceDetectorYN'):
        try:
            yunet_detector = cv2.FaceDetectorYN.create(
                YUNET_MODEL_PATH, "", (ana_w, ana_h),
                score_threshold=0.55, nms_threshold=0.3
            )
        except Exception:
            yunet_detector = None

    # ═══════════════════════════════════════════════════════════════
    # PASS 1: TURBO SCANNING & TRAJECTORY INTERPOLATION
    # ═══════════════════════════════════════════════════════════════
    sample_indices = []
    sample_positions = []  # None = deteksi gagal (ditahan per shot oleh _build_shot_trajectory)
    frame_idx = 0
    start_pass1_time = time.time()
    last_log_time = 0

    log(f"[Pass 1/2] Fast Scanning narasumber (~{total_clip_frames} frames @ {ana_w}x{ana_h}, stride={stride})...", job_id=job_id)

    for frame in _iter_ffmpeg_frames(video_path, start_time, duration, fps, ana_w, ana_h):
        is_cut = cut_detector.update(frame_idx, frame)
        # Di frame cut, deteksi DIPAKSA jalan agar posisi wajah di angle baru langsung diketahui
        if is_cut or frame_idx % stride == 0:
            current_target_x = None
            detected_target = False

            # Priority 1: YOLOv8 Person Tracking (Downscaled 384px + GPU Acceleration)
            if yolo_model is not None:
                try:
                    results = yolo_model.predict(
                        source=frame,
                        classes=[0],
                        conf=0.30,
                        imgsz=384,
                        device=device,
                        verbose=False
                    )
                    if len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
                        boxes = results[0].boxes.xyxy.cpu().numpy()
                        best_box = None
                        max_area = 0

                        for box in boxes:
                            bx1, by1, bx2, by2 = box
                            bw = bx2 - bx1
                            bh = by2 - by1
                            area = bw * bh

                            if area > max_area and bw > (ana_w * 0.05):
                                max_area = area
                                best_box = box

                        if best_box is not None:
                            detected_target = True
                            bx1, by1, bx2, by2 = best_box
                            current_target_x = (bx1 + (bx2 - bx1) / 2.0) * scale_x
                            last_valid_x = current_target_x
                except Exception:
                    pass

            # Priority 2: YuNet Face Fallback
            if not detected_target and yunet_detector is not None:
                try:
                    _, raw_faces = yunet_detector.detect(frame)
                    if raw_faces is not None and len(raw_faces) > 0:
                        best_face = max(raw_faces, key=lambda f: float(f[2]) * float(f[3]))
                        fx, fy, fw, fh = float(best_face[0]), float(best_face[1]), float(best_face[2]), float(best_face[3])
                        if fw >= (ana_w * 0.04) and (fy + fh / 2) < ana_h * 0.75:
                            detected_target = True
                            current_target_x = (fx + (fw / 2.0)) * scale_x
                            last_valid_x = current_target_x
                except Exception:
                    pass

            sample_indices.append(frame_idx)
            sample_positions.append(current_target_x)

        frame_idx += 1

        curr_time = time.time()
        if curr_time - last_log_time >= 1.5:
            percent = min(100.0, (frame_idx / total_clip_frames) * 100)
            elapsed = curr_time - start_pass1_time
            eta = (elapsed / (percent / 100) - elapsed) if percent > 0 else 0
            eta_str = format_timestamp(eta).split('.')[0]
            log(f"Progress Pass 1 (Turbo Scan): {percent:.1f}% ({frame_idx}/{total_clip_frames}) | ETA: {eta_str}", job_id=job_id)
            last_log_time = curr_time

    if frame_idx == 0:
        raise RuntimeError(f"Gagal decode frame video untuk tracking: {video_path}")

    if not sample_indices:
        sample_indices = [0]
        sample_positions = [default_center_x]
    # Interpolasi + Deadzone + Gaussian Smoothing dihitung PER SHOT (tidak melewati cut kamera)
    cut_frames = list(cut_detector.cuts)
    if cut_frames:
        cut_times = ", ".join(f"{c / fps:.1f}s" for c in cut_frames[:12])
        more = " ..." if len(cut_frames) > 12 else ""
        log(f"Terdeteksi {len(cut_frames)} pergantian kamera -> {len(cut_frames) + 1} shot (di {cut_times}{more})", job_id=job_id)
    else:
        log("Tidak ada pergantian kamera terdeteksi (1 shot).", job_id=job_id)

    smooth_center_x = _build_shot_trajectory(
        frame_idx, sample_indices, sample_positions, cut_frames,
        deadzone_px=deadzone_px, sigma=smooth_sigma, default_x=default_center_x,
    )

    # Konversi target center ke sudut kiri atas (X1) & clamp batas video
    smooth_crop_x = smooth_center_x - (crop_w / 2.0)
    smooth_crop_x = np.clip(smooth_crop_x, 0, orig_w - crop_w)

    log(f"[Pass 1/2] Tracking selesai ({frame_idx} frames).", job_id=job_id)
    return {
        "fps": fps,
        "orig_w": orig_w,
        "orig_h": orig_h,
        "crop_w": crop_w,
        "crop_h": crop_h,
        "crop_y": crop_y,
        "positions": smooth_crop_x,
        "cut_frames": cut_frames,
    }


def _escape_filter_path(path):
    """Escape file path for use inside an FFmpeg filtergraph option value."""
    return path.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")


def _write_crop_commands(trajectory, cmd_path):
    """
    Tulis trajektori crop sebagai file sendcmd FFmpeg (hanya saat posisi berubah).
    Return posisi X awal untuk inisialisasi filter crop.
    """
    fps = float(trajectory["fps"])
    positions = trajectory["positions"]
    first_x = None
    last_x = None
    with open(cmd_path, "w", encoding="utf-8") as f:
        for i, x in enumerate(positions):
            xi = (int(round(float(x))) // 2) * 2
            if first_x is None:
                first_x = xi
            if xi == last_x:
                continue
            # Setengah frame lebih awal: pembulatan PTS tidak membuat crop telat 1 frame di titik cut
            t = 0.0 if i == 0 else max(0.0, (i - 0.5) / fps)
            f.write(f"{t:.4f} crop x {xi};\n")
            last_x = xi
    return first_x or 0


def build_smart_crop_chain(trajectory, cmd_path):
    """
    Bangun filter chain FFmpeg yang melakukan crop dinamis (via sendcmd) + scale ke 1080x1920.
    Semua dilakukan di dalam satu proses FFmpeg -> hanya 1x encode di render final.
    """
    x0 = _write_crop_commands(trajectory, cmd_path)
    return (
        f"setpts=PTS-STARTPTS,"
        f"sendcmd=f='{_escape_filter_path(cmd_path)}',"
        f"crop={trajectory['crop_w']}:{trajectory['crop_h']}:{x0}:{trajectory['crop_y']},"
        f"scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    )


def build_fit_blur_graph(finish_chain, out_label="v"):
    """
    Filtergraph Fit 16:9 + Blurred Background.
    Main 16:9 video dinaikkan 5% ke atas (posisi seimbang & proporsional untuk subtitle).
    """
    return (
        f"[0:v]setpts=PTS-STARTPTS,split=2[bg_in][fg_in];"
        f"[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.08[bg];"
        f"[fg_in]scale=1080:-2:flags=lanczos[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2-(H*0.05),{finish_chain}[{out_label}]"
    )


def build_split_screen_graph(video_path, start_time, end_time, finish_chain, job_id=None, out_label="v"):
    """
    Filtergraph Dual Stack Split-Screen (Top & Bottom 50:50).
    Top window: Left speaker / Host (1080x960)
    Bottom window: Right speaker / Guest (1080x960)
    Zero panning motion sickness, single-pass encode bersama finish_chain.
    """
    try:
        width, height, _ = _probe_video_stream(video_path)
    except Exception:
        width, height = 1920, 1080

    target_crop_w = int(height * 0.54)
    if target_crop_w % 2 != 0:
        target_crop_w -= 1

    anchors = detect_speaker_anchors(video_path, start_time, end_time, width, height, target_crop_w)
    left_cx = anchors.get("left_anchor", width * 0.25)
    right_cx = anchors.get("right_anchor", width * 0.75)

    top_x = max(0, min(int(left_cx - target_crop_w / 2), width - target_crop_w))
    bottom_x = max(0, min(int(right_cx - target_crop_w / 2), width - target_crop_w))

    top_x = (top_x // 2) * 2
    bottom_x = (bottom_x // 2) * 2

    return (
        f"[0:v]setpts=PTS-STARTPTS,split=2[vtop_in][vbot_in];"
        f"[vtop_in]crop={target_crop_w}:{height}:{top_x}:0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
        f"[vbot_in]crop={target_crop_w}:{height}:{bottom_x}:0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bot];"
        f"[top][bot]vstack=inputs=2[stacked];"
        f"[stacked]drawbox=x=0:y=958:w=1080:h=4:color=0x18181b@0.9:t=fill,{finish_chain}[{out_label}]"
    )


def apply_smart_crop(video_path, start_time, end_time, output_path, job_id=None):
    """
    Turbo Cinema Clipper standalone (tanpa subtitle/grading): tracking + crop 9:16 + audio
    dalam SATU kali encode FFmpeg (tidak ada file intermediate mp4v lagi).
    """
    clip_dur = end_time - start_time
    trajectory = compute_smart_crop_trajectory(video_path, start_time, end_time, job_id=job_id)
    cmd_path = os.path.join(TEMP_DIR, f"temp_cropcmd_{int(time.time()*1000)}.txt")
    try:
        chain = build_smart_crop_chain(trajectory, cmd_path)
        log(f"[Pass 2/2] Rendering Video 9:16 (1 pass encode)...", job_id=job_id)
        ffmpeg_cmd = [
            get_ffmpeg_binary(), "-y",
            "-ss", str(start_time),
            "-t", str(clip_dur),
            "-i", video_path,
            "-filter_complex", f"[0:v]{chain}[v]",
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        run_command(ffmpeg_cmd, "Rendering cinema video & audio...", job_id=job_id, duration=clip_dur)
    finally:
        if os.path.exists(cmd_path):
            try:
                os.remove(cmd_path)
            except Exception:
                pass

    log("Cinema Clipper selesai 100% dengan mulus.", job_id=job_id)
    return output_path

def _validate_rendered_video(file_path: str, min_duration: float = 0.5) -> bool:
    """Validate that rendered file exists, non-empty, contains video stream, and has valid duration."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) <= 1024:
        return False

    ffprobe_bin = get_ffprobe_binary()
    try:
        # Check stream video
        cmd_streams = [
            ffprobe_bin, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height",
            "-of", "json",
            file_path
        ]
        res_streams = subprocess.run(cmd_streams, capture_output=True, text=True)
        if res_streams.returncode != 0:
            return False
        stream_data = json.loads(res_streams.stdout)
        streams = stream_data.get("streams", [])
        if not streams or not streams[0].get("codec_name"):
            return False

        # Check format duration
        cmd_duration = [
            ffprobe_bin, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            file_path
        ]
        res_dur = subprocess.run(cmd_duration, capture_output=True, text=True)
        if res_dur.returncode != 0:
            return False
        dur_str = res_dur.stdout.strip()
        if not dur_str:
            return False
        dur = float(dur_str)
        if dur < min_duration:
            return False
        return True
    except Exception:
        return False

def extract_and_format_clip(video_path, clip_info, index, segments, out_dir, job_id=None, sub_style="tiktok_viral", framing_mode="smart_crop", sub_position=68, show_emoji=True, watermark_enabled=True, source_watermark="", account_watermark="", inject_emoji=False, translation_mode=False):
    start = max(0.0, float(clip_info.get("start", 0.0)) - 0.2)
    end = float(clip_info.get("end", 0.0)) + 1.2
    duration = end - start
    fade_out_start = max(0.0, duration - 0.5)
    
    title_options = clip_info.get("title_options", [clip_info.get("title", f"clip_{index}")])
    title = title_options[0] if isinstance(title_options, list) and title_options else title_options
    
    safe_title = "".join(c if c.isalnum() else "_" for c in title).strip("_")
    out_file = os.path.join(out_dir, f"{index:02d}_{safe_title}.mp4")
    part_out_file = out_file + ".part"
    caption_file = os.path.join(out_dir, f"{index:02d}_{safe_title}.txt")
    
    caption_text = clip_info.get("caption", title)
    hashtags = clip_info.get("hashtags", [])
    hashtags_text = " ".join(hashtags) if isinstance(hashtags, list) else hashtags
    titles_text = "\n".join([f"- {t}" for t in title_options]) if isinstance(title_options, list) else title_options
    
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(f"Title Options:\n{titles_text}\n\nCaption:\n{caption_text}\n\nHashtags:\n{hashtags_text}")
    
    ass_file = os.path.join(TEMP_DIR, f"temp_{index}.ass")
    if os.path.exists(ass_file):
        try:
            os.remove(ass_file)
        except Exception:
            pass
    # Emoji berwarna asli: libass tidak bisa merender font emoji berwarna, jadi
    # emoji ditulis sebagai placeholder transparan di ASS lalu ditempel sebagai
    # PNG berwarna lewat ffmpeg overlay (lihat backend/emoji_overlay.py).
    use_emoji_overlay = (
        show_emoji
        and sub_style not in ("none", "no_subtitle")
        and _emoji_overlay_available()
    )
    generate_ass_subtitles(
        segments,
        ass_file,
        start,
        end,
        sub_style=sub_style,
        sub_position=sub_position,
        show_emoji=show_emoji,
        watermark_enabled=watermark_enabled,
        source_watermark=source_watermark,
        account_watermark=account_watermark,
        inject_emoji=inject_emoji,
        emoji_overlay=use_emoji_overlay,
        translation_mode=translation_mode,
    )
    crop_cmd_file = os.path.join(TEMP_DIR, f"temp_cropcmd_{index}_{int(time.time()*1000)}.txt")
    
    escaped_ass = _escape_filter_path(ass_file)
    
    af_filter = f"asetpts=PTS-STARTPTS,highpass=f=100,acompressor=threshold=-20dB:ratio=4:attack=5:release=50:makeup=8dB,afade=t=out:st={fade_out_start}:d=0.5"
    # Audio Enhancer: highpass + compressor halus + loudnorm 2-pass ke target LUFS platform (default -14)
    audio_settings = get_audio_settings()
    audio_pre_chain = build_audio_pre_chain(denoise=audio_settings["denoise"])
    loudness = _measure_loudness(video_path, start, duration, audio_pre_chain, audio_settings["target_lufs"], job_id=job_id)
    af_filter, audio_mode = build_audio_filter(fade_out_start, audio_pre_chain, audio_settings["target_lufs"], loudness)
    if audio_mode == "two_pass":
        log(f"Audio: loudnorm 2-pass {loudness['input_i']:.1f} LUFS -> {audio_settings['target_lufs']:g} LUFS "
            f"(true peak {LOUDNORM_TRUE_PEAK:g} dBTP){' + denoise' if audio_settings['denoise'] else ''}", job_id=job_id)
    elif audio_mode == "skip":
        log("Audio: klip (hampir) sunyi, normalisasi volume dilewati.", job_id=job_id)
    else:
        log("Audio: pengukuran loudness gagal, memakai loudnorm 1-pass.", job_id=job_id)
    
    codecs_to_try = []
    tiktok_golden = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-g", "60", "-bf", "2", "-crf", "18", "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags", "+faststart"]
    nvenc_golden = ["-c:v", "h264_nvenc", "-preset", "slow", "-profile:v", "high", "-rc", "constqp", "-qp", "18", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_trc", "bt709", "-color_primaries", "bt709", "-g", "60", "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags", "+faststart"]
    
    if sys.platform == "darwin":
        codecs_to_try = [
            ("VideoToolbox (TikTok Golden)", ["-c:v", "h264_videotoolbox", "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "60", "-b:v", "10M", "-maxrate", "12M", "-bufsize", "20M", "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags", "+faststart"]),
            ("libx264 (TikTok Golden)", tiktok_golden)
        ]
    else:
        codecs_to_try = [
            ("NVENC (TikTok Golden)", nvenc_golden),
            ("Safer NVENC", ["-c:v", "h264_nvenc", "-preset", "p2", "-profile:v", "main", "-b:v", "8M", "-c:a", "aac", "-b:a", AUDIO_BITRATE]),
            ("libx264 (TikTok Golden)", tiktok_golden)
        ]

    # Grading + subtitle + fade diterapkan di filtergraph yang SAMA dengan crop/layout,
    # sehingga seluruh klip hanya di-encode satu kali (tanpa file intermediate).
    grade_chain = "eq=contrast=1.1:brightness=0.02:saturation=1.2,unsharp=5:5:0.4:5:5:0.0"
    has_subtitles = os.path.exists(ass_file) and os.path.getsize(ass_file) > 0
    escaped_fonts_dir = _escape_filter_path(FONTS_DIR) if (FONTS_DIR and os.path.exists(FONTS_DIR)) else ""
    fonts_opt = f":fontsdir='{escaped_fonts_dir}'" if escaped_fonts_dir else ""
    subtitle_filter = f",subtitles='{escaped_ass}'{fonts_opt}" if has_subtitles else ""
    subtitle_stage = f"{grade_chain}{subtitle_filter}"
    fade_filter = f"fade=t=out:st={fade_out_start}:d=0.5"

    # Emoji berwarna asli ditempel setelah subtitle, sebelum fade (agar ikut fade).
    emoji_overlays = []
    if use_emoji_overlay and has_subtitles:
        try:
            from backend.emoji_overlay import plan_emoji_overlays
            emoji_overlays = plan_emoji_overlays(
                ass_file, FONTS_DIR, play_res_x=1080, play_res_y=1920, job_id=job_id,
            )
        except Exception as exc:
            log(f"Emoji overlay dilewati (gagal menyiapkan): {exc}", job_id=job_id)
            emoji_overlays = []

    overlay_graph, overlay_inputs = "", []
    if emoji_overlays:
        from backend.emoji_overlay import build_overlay_graph
        overlay_graph, overlay_inputs, overlay_last = build_overlay_graph(emoji_overlays, "[vsub]")
        log(f"Emoji berwarna: {len(emoji_overlays)} overlay PNG ditempel ke klip {index}.", job_id=job_id)
    else:
        overlay_last = "[vsub]"

    def _assemble(prefix_graph):
        """Tempel overlay emoji + fade di belakang graph layout/crop/subtitle."""
        parts = [prefix_graph]
        if overlay_graph:
            parts.append(overlay_graph)
        parts.append(f"{overlay_last}{fade_filter}[v]")
        return ";".join(parts)

    ffmpeg_bin = get_ffmpeg_binary()

    def build_cmd(filter_graph, codec_params):
        return [
            ffmpeg_bin, "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", video_path,
            *overlay_inputs,
            "-filter_complex", filter_graph,
            "-map", "[v]",
            "-map", "0:a?",
            "-af", af_filter,
            "-ar", str(AUDIO_SAMPLE_RATE),  # Wajib: loudnorm internal 192kHz
            "-avoid_negative_ts", "make_zero",
            # Overlay PNG di-loop selamanya -> output harus dibatasi eksplisit.
            "-t", str(duration),
        ] + codec_params + ["-f", "mp4", part_out_file]

    def try_render(filter_graph, label):
        for name, codec_params in codecs_to_try:
            if os.path.exists(part_out_file):
                try:
                    os.remove(part_out_file)
                except Exception:
                    pass
            try:
                run_command(build_cmd(filter_graph, codec_params), f"{label} ({name})...", job_id=job_id, duration=duration)
                if _validate_rendered_video(part_out_file, min_duration=max(0.3, duration * 0.7)):
                    os.replace(part_out_file, out_file)
                    return True
                log(f"{name} produced an invalid or unreadable video file.", job_id=job_id)
            except Exception as e:
                log(f"{name} Encoding failed: {e}. Falling back to next codec...", job_id=job_id)
        return False

    render_success = False
    primary_graph = None
    # Semua graph layout berakhir di label [vsub] (hasil subtitle) supaya overlay
    # emoji berwarna + fade bisa disambung dari titik itu.
    try:
        if framing_mode == "fit_blur":
            log(f"Applying 16:9 Fit Blur Background for Clip {index} (Podcast/Live stream mode)...", job_id=job_id)
            primary_graph = _assemble(build_fit_blur_graph(subtitle_stage, out_label="vsub"))
        elif framing_mode == "split_screen":
            log(f"Applying Studio Dual-Stack Split-Screen (50:50 Host/Guest) for Clip {index}...", job_id=job_id)
            primary_graph = _assemble(
                build_split_screen_graph(video_path, start, end, subtitle_stage,
                                         job_id=job_id, out_label="vsub")
            )
        else:
            log(f"Applying AI Smart Face Tracking 9:16 for Clip {index}...", job_id=job_id)
            trajectory = compute_smart_crop_trajectory(video_path, start, end, job_id=job_id)
            primary_graph = _assemble(
                f"[0:v]{build_smart_crop_chain(trajectory, crop_cmd_file)},{subtitle_stage}[vsub]"
            )
    except Exception as e:
        log(f"Face tracking error, using intelligent Podcast Dual-Anchor fallback: {e}", job_id=job_id)
        primary_graph = None

    fallback_graph = _assemble(f"[0:v]{STATIC_FALLBACK_CROP_CHAIN},{subtitle_stage}[vsub]")

    try:
        if primary_graph:
            log(f"[Pass 2/2] Single-pass render (Crop + Subtitles + Audio Enhancer + Color Grading) for Clip {index}: {title}", job_id=job_id)
            render_success = try_render(primary_graph, "Rendering final clip")
            if not render_success:
                log(f"Render utama gagal untuk Clip {index}, mencoba Podcast Dual-Anchor fallback...", job_id=job_id)
        if not render_success:
            render_success = try_render(fallback_graph, f"Fallback processing for Clip {index}")
    finally:
        for tmp in [ass_file, crop_cmd_file, part_out_file]:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception as e:
                log(f"Warning: Could not remove temp file {tmp}: {e}", job_id=job_id)

    if not render_success or not os.path.exists(out_file):
        raise RuntimeError(f"All codecs failed to render clip {index} ('{title}'). Output file was not generated.")

    # Emit structured output marker for frontend / social integration
    clip_output_data = {
        "index": index,
        "title": title,
        "out_file": os.path.abspath(out_file),
        "caption": caption_text,
        "hashtags": hashtags if isinstance(hashtags, list) else [hashtags]
    }
    print(f"[CLIP_RENDERED]{json.dumps(clip_output_data)}", flush=True)

    return out_file
