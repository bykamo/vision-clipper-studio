# Hook-Cutter (hook_cutter.py)

Hook-Cutter adalah sebuah *script* Python otomatis yang berfungsi untuk mengunduh video dari YouTube (atau file lokal), mentranskripsinya, mencari bagian paling viral menggunakan kecerdasan buatan (LLM), dan memotong bagian tersebut menjadi video berformat vertikal (9:16) lengkap dengan *subtitle* kata-per-kata bergaya CapCut.

## 🌟 Fitur Utama
1. **Download Otomatis dari YouTube**: Cukup masukkan link URL video YouTube panjang.
2. **Auto-Crop 9:16 (Vertikal)**: Hasil pemotongan langsung cocok untuk TikTok, YouTube Shorts, atau Instagram Reels.
3. **CapCut-style Subtitles**: Pembuatan teks *subtitle* per kata secara otomatis menggunakan Whisper AI yang ditempel langsung (*burn-in*) pada video.
4. **Viral Segment Analysis**: Memanfaatkan LLM untuk menemukan momen dengan *hook* paling menarik dan retensi penonton yang diprediksi paling tinggi.

---

## 🛠️ Persyaratan Instalasi

Sebelum menggunakan skrip ini, pastikan Anda telah menginstal beberapa aplikasi dan *library* (pustaka) wajib:

### 1. Instalasi Aplikasi Pihak Ketiga
Sistem Anda **wajib** memiliki `ffmpeg` yang sudah terpasang dan bisa diakses via terminal (*System PATH*). 
- Download FFmpeg dari situs resminya: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
- Pastikan versi FFmpeg Anda mendukung pembuatan *subtitle* (`libass`).

### 2. Instalasi Pustaka Python
Buka terminal / Command Prompt (CMD), lalu jalankan perintah instalasi berikut:
```bash
pip install yt-dlp openai-whisper torch requests opencv-python
```

---

## 🚀 Cara Menjalankan Skrip

Skrip dijalankan melalui terminal/CMD. Anda dapat memilih sumber video, entah dari URL YouTube atau dari *file* yang ada di komputer Anda.

### A. Memotong Video dari YouTube
Gunakan parameter `--url` dan masukkan URL videonya.
```bash
python hook_cutter.py --url "https://www.youtube.com/watch?v=CONTOH_ID"
```

### B. Memotong Video dari File Lokal
Jika video sudah ada di laptop/komputer, gunakan parameter `--file`.
```bash
python hook_cutter.py --file "nama_video.mp4"
```

---

## ⚙️ Opsi Konfigurasi Lanjutan
Anda bisa menyesuaikan hasil potongan dengan berbagai tambahan parameter berikut:

| Parameter | Deskripsi | Default | Contoh Penggunaan |
|---|---|---|---|
| `--num-clips` | Jumlah klip viral yang ingin dihasilkan. | `3` | `--num-clips 5` |
| `--min-len` | Durasi minimal klip (detik). | `15` | `--min-len 30` |
| `--max-len` | Durasi maksimal klip (detik). | `60` | `--max-len 60` |
| `--model` | Ukuran model OpenAI Whisper (`tiny`, `base`, `small`, `medium`, `large`). Gunakan ukuran yang lebih besar untuk *subtitle* yang lebih akurat. | `base` | `--model small` |
| `--out-dir` | Folder tempat video hasil kliping akan disimpan. | `clips` | `--out-dir "D:/my_clips"` |

### 💡 Contoh Lengkap dengan Custom Parameter
Mencari 5 klip terbaik dari link YouTube, dengan durasi 30-45 detik, menggunakan whisper model *small*, dan disimpan di folder *output*:
```bash
python hook_cutter.py --url "https://www.youtube.com/watch?v=CONTOH_ID" --num-clips 5 --min-len 30 --max-len 45 --model small --out-dir "output"
```

---

## 📝 Catatan Tambahan
- Jika *subtitle* yang dihasilkan ada kata yang salah/terlewat, Anda disarankan menggunakan model whisper yang lebih tinggi seperti `--model medium` atau `--model large` (pastikan memori / RAM GPU komputer mencukupi).
- Semua video hasil potong otomatis tersimpan pada folder `clips` (atau folder kustom Anda).
