# VisionClipper Studio (Combo Maut Edition)

VisionClipper Studio adalah *AI Pipeline* lengkap untuk memotong video panjang (podcast, interview, dll) menjadi klip vertikal pendek (TikTok, Reels, Shorts) secara otomatis. Versi terbaru ini menggunakan strategi **"Combo Maut"** untuk memaksimalkan retensi dan engangement.

## 🌟 Fitur Utama
1. **AI Video & Audio Enhancer**: Memotong video dengan *Cinematic Face Tracking* (AI Smart Crop), menjernihkan audio (*Highpass Filter*), dan menyeimbangkan volume (*Compressor*).
2. **CapCut-style Subtitles**: Pembuatan teks *subtitle* per kata secara otomatis menggunakan Whisper AI yang ditempel langsung (*burn-in*) pada video.
3. **Viral Segment Analysis (9Router LLM)**: Menemukan momen dengan *hook* paling menarik dan memotongnya secara pas.
4. **Clickbait Title Hook & SEO Metadata**: Membuat judul clickbait 1-detik pertama di layar, serta *generate* ide judul dan *hashtags* SEO-friendly.

---

## 🛠️ Instalasi Global (Sangat Disarankan)

Sekarang VisionClipper Studio bisa diinstal langsung ke sistem lo layaknya paket profesional (mirip `npm install -g`), sehingga lo cukup ngetik `vision-clipper` di terminal manapun untuk menjalankan Web Dashboard-nya!

### 1. Prasyarat Sistem
Pastikan komputer lo udah punya:
- **Python 3.8+**
- **FFmpeg**: Wajib terinstal dan masuk ke *System PATH*. Download di [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html).

### 2. Instalasi Paket
Buka terminal / CMD di dalam folder repo ini, lalu ketik perintah berikut:
```bash
pip install -e .
```
*(Perintah ini bakal mengunduh semua dependency yang dibutuhkan dan memasang perintah `vision-clipper` ke komputer lo).*

### 3. Konfigurasi API (.env)
Bikin/copy file bernama `.env` di folder *project* lo dan masukin kunci API-nya. Silakan lihat formatnya di file `.env.example`.

---

## 🚀 Cara Menjalankan

### Cara 1: Menggunakan Web Dashboard (GUI Terpadu)
Buka terminal di mana aja (bebas), lalu cukup ketik:
```bash
vision-clipper
```
Aplikasi bakal berjalan secara mandiri dan langsung ngebuka browser secara otomatis ke alamat `http://localhost:5000`. Lo tinggal klik-klik aja lewat tampilan web!

### Cara 2: Menjalankan Skrip Mentah via Terminal
Kalau lo lebih suka nge-hack via *command line interface*, lo juga bisa panggil skrip Python-nya langsung:

```bash
python vision_clipper/hook_cutter.py --file "video_podcast.mp4" --num-clips 5
```

---

## 📝 Catatan Tambahan
- Semua video hasil kliping bakal disimpen dalam folder `clips/` di *directory* tempat lo lagi menjalankan terminal.
- Karena file `.env` sudah diabaikan di `.gitignore`, API lo bakal tetep rahasia dan aman nggak akan ter-upload ke GitHub.
