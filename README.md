# 🎬 VisionClipper Studio

**AI-Powered Viral Video Clipper — Combo Maut Edition**

> Potong video panjang (podcast, interview, dll) menjadi klip vertikal pendek (TikTok, Reels, Shorts) secara otomatis menggunakan kekuatan AI.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Web_Dashboard-009688?logo=fastapi&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-green?logo=ffmpeg)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Fitur Utama

| # | Fitur | Deskripsi |
|---|-------|-----------|
| 1 | **AI Smart Crop** | *Cinematic Face Tracking* otomatis — kamera mengikuti wajah speaker dan mengkrop video jadi format vertikal 9:16. |
| 2 | **Audio Enhancer** | Jernihin audio otomatis pakai *Highpass Filter* + *Compressor* untuk volume yang seimbang. |
| 3 | **CapCut-style Subtitles** | Generate subtitle per-kata menggunakan **Whisper AI**, langsung di-burn ke video. |
| 4 | **Viral Segment Analysis** | AI (via 9Router/OpenRouter LLM) menganalisa transkrip dan menemukan momen dengan *hook* paling menarik. |
| 5 | **Viral Metadata & SEO** | Auto-generate judul opsi, deskripsi caption viral, hashtags, serta ide title hook disimpan dalam file `.txt` terpisah untuk tiap klip. |
| 6 | **Web Dashboard (GUI)** | Kontrol semuanya lewat tampilan web yang premium dengan **FastAPI** di `localhost:5000`. |

---

## 🗂️ Struktur Proyek (Modular Architecture)

```
vision-clipper-studio/
├── backend/               # FastAPI Backend & Pipeline Logika
│   ├── main.py            # API Server & Endpoints
│   ├── cli.py             # CLI Entry Point (`vision-clipper`)
│   ├── worker.py          # Background Worker Process (Subprocess)
│   ├── transcriber.py     # Logika Whisper AI Transcript
│   ├── analyzer.py        # Logika LLM Prompting
│   ├── renderer.py        # Rendering FFmpeg & Subtitle
│   ├── downloader.py      # Downloader & Validasi File
│   ├── database.py        # SQLite Session Manager
│   ├── utils.py           # Log Utilities
│   └── bg_server.py       # Background Server Launcher
├── frontend/              # HTML/JS/CSS Assets
│   ├── index.html         # Dashboard HTML
│   ├── app.js             # Client-side Logic (SSE)
│   └── styles.css         # CSS UI Design
├── scripts/               # Helper Scripts
│   ├── install.bat        # Windows Installer
│   └── vision-clipper.bat # Fallback CLI Launcher
├── .env.example           # Contoh Environment Config
├── setup.py               # Package Setup
└── MANIFEST.in            # Package Manifest
```

---

## 🛠️ Instalasi

### Prasyarat Sistem
Pastikan komputer lo udah punya:
- **Python 3.8+** — [Download Python](https://www.python.org/downloads/)
- **FFmpeg** — Wajib terinstal dan masuk ke *System PATH*. [Download FFmpeg](https://ffmpeg.org/download.html)

### Cara Install

**Opsi 1: Pakai Installer (Windows)**
```bash
# Buka folder `scripts/` dan jalankan:
scripts\install.bat
```

**Opsi 2: Manual via Terminal**
```bash
# Buka terminal di root folder project ini
pip install -e .
```

> Perintah ini akan mengunduh semua dependency dan mendaftarkan perintah `vision-clipper` ke sistem lo secara global.

### Konfigurasi API Key

1. Copy file `.env.example` jadi `.env`
2. Isi API key lo:

```env
# AI Provider Endpoint (e.g., 9Router, OpenRouter, OpenAI)
ROUTER_API_ENDPOINT=https://api.example.com/v1/chat/completions

# Your API Key
ROUTER_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🚀 Cara Menjalankan

### 🖥️ Cara 1 — Web Dashboard (Recommended)

Buka terminal di mana saja, lalu ketik perintah CLI ini:

```bash
vision-clipper
```

Server akan **berjalan di background** dan browser otomatis terbuka ke `http://localhost:5000`. **Lo bisa langsung tutup terminal** — server tetap jalan sampai lo sendiri yang matiin!

#### Menghentikan Server

| Cara | Perintah |
|------|----------|
| Dari **Web Dashboard** | Klik tombol merah **"Shut Down Background Server"** di bagian bawah halaman |
| Dari **Terminal/CMD** | `vision-clipper --stop` |

#### Perintah CLI Tambahan

```bash
vision-clipper              # Jalankan server di background
vision-clipper --stop       # Hentikan server yang sedang berjalan
vision-clipper --status     # Cek apakah server masih aktif
vision-clipper --help       # Tampilkan bantuan
```

Dashboard menyediakan:
- 📂 **File browser** — pilih video langsung dari GUI
- 🔄 **Tab switching** — pilih mode *Hook Cutter* atau *Affiliate Clipper*
- 📊 **Live processing log** — pantau proses secara real-time (teks kuning!)
- ⏹️ **Cancel/Stop** — hentikan proses kapan saja

### ⌨️ Cara 2 — Command Line Worker

Jika lo mau menjalankan secara manual tanpa Dashboard GUI, lo bisa langsung panggil *worker* file:

```bash
python -m backend.worker --file "video_podcast.mp4" --num-clips 5 --mode hook
```

---

## 🎛️ Mode Operasi

### 🎯 Hook Cutter
Mode utama — AI menganalisa transkrip video, menemukan momen-momen *hook* paling menarik, lalu memotong dan mengolahnya jadi klip vertikal siap upload.

### 🛒 Affiliate Clipper
Mode alternatif — Dioptimalkan untuk konten *affiliate/review*, memotong segmen produk dan *call-to-action* secara otomatis.

---

## 📦 Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Web Server | **FastAPI** + **Uvicorn** + Server-Sent Events (SSE) |
| Speech-to-Text | Faster Whisper |
| Video Processing | FFmpeg + MoviePy + OpenCV |
| Face Detection | MediaPipe (BlazeFace) |
| AI Analysis | LLM via 9Router / OpenRouter API |
| Database Storage | SQLite3 |

---

## 🔧 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `FFmpeg not found` | Pastikan FFmpeg sudah terinstal dan masuk ke System PATH. Restart terminal setelah instalasi. |
| `vision-clipper` command not found | Jalankan ulang `pip install -e .` dan pastikan Python Scripts folder ada di PATH. |
| Proses macet / freeze | Klik tombol **STOP** di dashboard, atau tekan `Ctrl+C` di terminal. |
| API Error / timeout | Cek file `.env` — pastikan endpoint dan API key sudah benar. |
| Server gagal startup | Cek apakah Port 5000 sudah dipakai oleh program lain. |

---

## 📝 Catatan Penting

- **Output Folder (`clips/`)**: Folder output sekarang digenerate secara otomatis dengan rapi berdasarkan nama video aslinya.
- **SQLite Database (`vision_clipper.db`)**: Database ini menyimpan status dan log agar sistem dapat berjalan di latar belakang (background worker) tanpa masalah jika web UI dimatikan/direfresh.
- File `.env` sudah masuk `.gitignore` — API key lo aman dan nggak akan ter-upload ke GitHub.
- Dashboard web berjalan di `localhost:5000` secara default.

---

## 📄 Lisensi

MIT License — Silakan dipakai dan dimodifikasi sesuka hati.

---

<p align="center">
  <b>VisionClipper Studio</b> © 2026 — Built with ❤️ by <a href="https://github.com/kam2k-dev">kam2k-dev</a>
</p>
