# 🎬 VisionClipper Studio

**AI-Powered Viral Video Clipper — Combo Maut Edition**

> Potong video panjang (podcast, interview, dll) menjadi klip vertikal pendek (TikTok, Reels, Shorts) secara otomatis menggunakan kekuatan AI.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Web_Dashboard-009688?logo=fastapi&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-green?logo=ffmpeg)
![macOS / Windows](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?logo=apple&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Fitur Utama

| # | Fitur | Deskripsi |
|---|-------|-----------|
| 1 | **AI Smart Crop** | *Cinematic Face Tracking* otomatis — kamera mengikuti wajah speaker dan mengkrop video jadi format vertikal 9:16. |
| 2 | **Audio Enhancer** | Jernihin audio otomatis pakai *Highpass Filter* + *Compressor* untuk volume yang seimbang. |
| 3 | **CapCut-style Subtitles** | Generate subtitle per-kata menggunakan **Groq Cloud Whisper** (kilat ~3 detik) atau **Whisper AI**, langsung di-burn ke video. |
| 4 | **Viral Segment Analysis** | AI (via OpenRouter / OpenAI / 9Router LLM) menganalisa transkrip dan menemukan momen dengan *hook* paling menarik. |
| 5 | **Viral Metadata & SEO** | Auto-generate judul opsi, deskripsi caption viral, hashtags, serta ide title hook disimpan dalam file `.txt` terpisah untuk tiap klip. |
| 6 | **One-Click CLI & Clean Lifecycle** | Perintah CLI universal (`install`, `config`, `start`, `stop`, `status`, `uninstall`) dengan auto-isolated `.venv`. |
| 7 | **Web Dashboard (GUI)** | Kontrol semuanya lewat tampilan web premium berbasis **FastAPI** di `localhost:5050`. |

---

## 🗂️ Struktur Proyek (Modular Architecture)

```
vision-clipper-studio/
├── backend/                  # FastAPI Backend & Pipeline Logika
│   ├── main.py               # API Server & Endpoints
│   ├── cli.py                # Universal CLI Entry Point (`vision-clipper`)
│   ├── worker.py             # Background Worker Process (Subprocess)
│   ├── transcriber.py        # Logika Whisper AI Transcript
│   ├── analyzer.py           # Logika LLM Prompting
│   ├── renderer.py           # Rendering FFmpeg & Subtitle
│   ├── downloader.py         # Downloader & Validasi File
│   ├── database.py           # SQLite Session Manager
│   ├── utils.py              # Log Utilities
│   └── bg_server.py          # Background Server Launcher
├── frontend/                 # React 19 + Vite + Tailwind v4 Dashboard
│   ├── index.html            # Vite entry HTML
│   ├── package.json          # Dependencies & scripts (dev / build / lint)
│   ├── vite.config.ts        # Dev server :3000 + proxy ke backend :5050
│   ├── src/
│   │   ├── App.tsx           # Root component
│   │   ├── main.tsx          # React entry point
│   │   ├── index.css         # Tailwind + iOS mockup/transport styles
│   │   ├── components/       # Dashboard, PhonePreview, Settings, dll
│   │   ├── data/             # Preset subtitle
│   │   ├── lib/              # Helper (cn)
│   │   └── types/            # Shared TypeScript types
│   ├── public/               # Logo & mockup assets
│   └── dist/                 # Hasil build (dibuat oleh `npm run build`)
├── scripts/                  # Helper Scripts
│   ├── install_mac.sh        # macOS/Linux Installer
│   ├── uninstall_mac.sh      # macOS/Linux Clean Uninstaller
│   ├── configure_ai.sh       # macOS/Linux AI Wizard
│   ├── install.bat           # Windows Installer
│   ├── uninstall_windows.bat # Windows Clean Uninstaller
│   ├── configure_ai.bat      # Windows AI Wizard
│   └── vision-clipper.bat    # Windows CLI Launcher
├── .env.example              # Contoh Environment Config
├── setup.py                  # Package Setup
└── MANIFEST.in               # Package Manifest
```

---

## 🛠️ Instalasi & Setup

### Prasyarat Sistem
- **Python 3.10+** (Direkomendasikan)
- **FFmpeg** (Wajib terinstal di sistem)
  - *macOS*: `brew install ffmpeg` (atau otomatis dipasang via installer)
  - *Windows*: Download dari [ffmpeg.org](https://ffmpeg.org/download.html) atau via `winget install Gyan.FFmpeg`

---

### Cara Install

#### 🍎 macOS / 🐧 Linux
Buka terminal di folder project, lalu jalankan:
```bash
chmod +x scripts/install_mac.sh
./scripts/install_mac.sh
```
> Script ini otomatis membuat `.venv`, memasang semua dependency, menjalankan wizard konfigurasi AI, dan mendaftarkan perintah global `vision-clipper`.

#### 🪟 Windows
Buka CMD / PowerShell di folder project, lalu jalankan:
```cmd
scripts\install.bat
```
*(Atau jalankan: `scripts\vision-clipper.bat install`)*

---

## 🤖 Konfigurasi AI & Model

Anda dapat mengatur atau mengganti Provider AI, Model LLM, dan API Key kapan saja melalui dua cara:

### 1. Langsung dari Web Dashboard (Paling Mudah)
* Buka dashboard Studio (`http://localhost:5050`).
* Klik ikon **⚙️ Setup AI / Pengaturan AI** di header atas (atau klik banner jika belum dikonfigurasi).
* Pilih provider siap pakai (**OpenRouter**, **OpenAI**, **Groq**, **DeepSeek**, atau **Custom Endpoint / Ollama / 9Router**).
* Klik tombol **Uji Koneksi AI** untuk memastikan respon model bekerja.
* Klik **Simpan & Sambungkan ke Engine** — konfigurasi langsung aktif secara instan tanpa perlu restart server!

### 2. Melalui Terminal / CLI Interaktif
```bash
vision-clipper config
```

Tersedia preset siap pakai untuk:
1. **OpenRouter** (Rekomendasi - model gratis `google/gemini-2.0-flash-exp:free` / Claude / Llama)
2. **OpenAI Resmi** (`gpt-4o`, `gpt-4o-mini`)
3. **Groq LLM** (`llama-3.3-70b-versatile`)
4. **DeepSeek** (`deepseek-chat`, `deepseek-reasoner`)
5. **Custom Endpoint** (Local Ollama, 9Router, vLLM, dll)

---

## 🚀 Cara Menjalankan

### 🖥️ Web Dashboard (Rekomendasi)

Cukup buka terminal di mana saja, lalu ketik:

```bash
vision-clipper
```

* Server akan **berjalan di background** (tanpa popup jendela hitam) dan otomatis membuka browser ke `http://localhost:5050`.
* **Terminal bisa langsung ditutup** — server tetap berjalan sampai Anda hentikan sendiri.

---

### 🎮 Daftar Perintah Universal CLI

Perintah berikut berlaku sama di **macOS, Windows (CMD/PowerShell), dan Linux**:

| Perintah | Deskripsi |
|---|---|
| `vision-clipper` | Menjalankan server di background & membuka browser dashboard (auto-detect `.venv` & `.env`) |
| `vision-clipper install` | Install ulang dependencies & inisialisasi environment `.venv` terisolasi |
| `vision-clipper config` | Wizard interaktif untuk mengatur/mengganti API Key, Endpoint, dan Model AI |
| `vision-clipper status` | Mengecek apakah server background sedang aktif |
| `vision-clipper stop` | Menghentikan background server & proses engine |
| `vision-clipper uninstall` | **Clean Uninstall**: menghapus `.venv`, shortcut CLI, dan file cache tanpa menghapus hasil render video |
| `vision-clipper help` | Menampilkan menu bantuan perintah |

---

### 🛑 Cara Menghentikan Server

| Cara | Tindakan |
|---|---|
| **Dari Web Dashboard** | Klik tombol merah **"Shut Down Background Server"** di bagian bawah dashboard |
| **Dari Terminal / CMD** | Ketik: `vision-clipper stop` |

---

### ⌨️ Menjalankan CLI Worker Manual (Opsional)

Jika ingin memproses video langsung lewat terminal tanpa dashboard:

```bash
python -m backend.worker --file "video_podcast.mp4" --num-clips 5 --mode hook
```

---

## 🎛️ Mode Operasi

### 🎯 Hook Cutter
Mode utama — AI menganalisa transkrip video, menemukan momen-momen *hook* paling menarik, lalu memotong dan mengolahnya jadi klip vertikal siap upload (TikTok, Reels, Shorts).

### 🛒 Affiliate Clipper
Mode alternatif — Dioptimalkan untuk konten *affiliate/review*, memotong segmen pembahasan produk dan *call-to-action (CTA)* secara otomatis.

### 📂 Posting Ulang Hasil Render Lama

Klip yang sudah dirender sebelumnya dapat dibuka kembali langsung menggunakan dialog folder bawaan OS (Finder / File Explorer):

1. Pada bagian **Video Source**, klik tombol folder hijau (Folder Explorer bawaan OS). Dialog bawaan akan langsung mengarah ke folder `clips/`.
2. Pilih satu subfolder proyek render (misalnya: `clips/Judul_Video_...`) lalu klik **Pilih / Choose**.
3. Dashboard akan langsung masuk ke mode **Output Clips / Complete** dan memutar klip pertama di phone preview.
4. Anda dapat langsung mengklik tombol **YouTube** untuk posting langsung, **TikTok** untuk copy caption + buka TikTok Studio, atau **Preview** untuk memutar klip lain tanpa perlu render ulang.

> **Catatan**: Tombol kamera video di sebelahnya digunakan untuk memilih file video baru untuk proses clipping normal. Jika Anda memilih file video `.mp4` yang berada di dalam subfolder `clips/`, sistem juga akan otomatis mendeteksi dan memuat seluruh klip proyek tersebut. Metadata judul, caption, dan hashtag dibaca otomatis dari file `.txt` pasangan video jika tersedia.

---

## 📦 Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Web Framework | **FastAPI** + **Uvicorn** + Server-Sent Events (SSE) |
| Speech-to-Text | **Groq Cloud Whisper** (`whisper-large-v3-turbo`) / **Faster Whisper** |
| Video Processing | **FFmpeg** + **MoviePy** + **OpenCV Headless** |
| Subject Tracking | **YOLOv8 AI Person Tracker** + EMA Smooth Panning |
| AI Analysis | LLM via OpenRouter / OpenAI / Custom Provider |
| Database | **SQLite3** Session & Job Logging |

---

## 🔧 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `FFmpeg not found` | Pastikan FFmpeg sudah terinstal dan masuk ke System PATH. Restart terminal setelah instalasi. |
| `vision-clipper: command not found` | Muat ulang shell dengan `source ~/.zshrc` (Mac) atau buka terminal baru (Windows). |
| API Error / timeout | Jalankan `vision-clipper config` untuk memastikan Endpoint dan API Key sudah benar. |
| Port 5050 bentrok | Matikan instance sebelumnya dengan `vision-clipper stop`. |
| UI tampil kosong / fallback | `frontend/dist` belum ada. Jalankan `cd frontend && npm install && npm run build`. |

---

## 🧑‍💻 Development

```bash
# Backend (port 5050) — serve frontend/dist
.venv/bin/python -m backend.main

# Frontend dev server (port 3000, proxy /api -> :5050)
cd frontend && npm run dev

# Typecheck (strict TS) — jalankan sebelum commit
cd frontend && npm run lint

# Build produksi (wajib sebelum `pa`/`python -m backend.main` melayani UI baru)
cd frontend && npm run build

# Test backend (unittest, 136 test)
.venv/bin/python -m unittest discover -s backend -p "test_*.py"
```

---

## 📝 Catatan Penting

- **Output Folder (`clips/`)**: Hasil video yang dirender disimpan rapi dalam subfolder tersendiri berdasarkan nama video aslinya.
- **Isolasi Bersih (`.venv`)**: Semua library disimpan di dalam `.venv` lokal agar tidak mengotori Python sistem utama komputer Anda.
- **Keamanan Data**: File konfigurasi `.env` sudah masuk ke `.gitignore` sehingga API Key Anda aman dari kebocoran ke repository Git.

---

## 📄 Lisensi

MIT License — Silakan dipakai dan dimodifikasi sesuka hati.

---

<p align="center">
  <b>VisionClipper Studio</b> © 2026 — Built with ❤️ by <a href="https://github.com/kam2k-dev">kam2k-dev</a>
</p>
