# PUBLISH-LATEST.md — jadwal ulang klip yang 0 views + klip fresh

## Kenapa 0 views (diagosa 11 Nov)
- Publish di **05.31–05.48 WIB**: poros 05.00 paling buruk di 25 video (4/6 mati, median 3 views).
- Judul/hook/manual dari HP (bukan clipper), tanpa hook yang terbaca + metadata dikit.
- Bukti: batch 21 Sep yang sama dihasilkan 6.062 **dan** 17 views → isu bukan tema.

## Cara kerjanya sekarang (ingat: bukan re-upload file sama)
- Potongan baru dibuat dari window berbeda (mulai +2s, ekor +5s) dengan judul/hook baru → file baru (44s, 43s, 53s, 41s).
- Subtitle style tetap tiktok_viral, framing smart_crop.
- Nama: `01_Dr__Tirta_Mimpi_Dikejar_Raditya_Dika_Kepalanya_Dua_Personal_Branding_Hancur_Semalam.mp4` dsb.

## Jadwal (3–6/hari, jeda ≥30 menit, slot ramai)

### HARI INI — 2026-11-11 (WIB)
| jam | klip | judul (flat) |
|---|---|---|
| 11.00 | recut #4 (845-898s) | Udah Jadi Dokter Masih Ditanya Kapan S3? Standar Orang Tua Asia Gak Ada Habisnya #Shorts |
| 19.30 | recut #3 (472-515s) | Dibully Jangkung Sampai Jalan Bongkok, Tinggi Badan Gak Selalu Berkah #Shorts |
| 21.00 | recut #7 (3217-3258s) | Branding Dr. Tirta Hancur Gara-Gara Julukan Nyong Nyong #Shorts |

### HARI ESOK — 2026-11-12 (WIB)
| jam | klip | judul (flat) |
|---|---|---|
| 10.30 | recut #1 (33-77s) | Dr. Tirta Mimpi Dikejar Raditya Dika Kepalanya Dua, Personal Branding Hancur Semalam #Shorts |
| 19.00 | clip 02 (Tidak pernah tayang) | Mama Zaman Old: Tinggi Gak Laku, Dilarang Basket Sama Mamanya #Shorts |
| 20.00 | clip 05 (Tidak pernah tayang) | 4 Hal Perempuan Menurut Dr. Patricia: Cantik, Pintar, Kaya, Siap Jomblo #Shorts |
| 21.00 | clip 06 (Tidak pernah tayang) | Kok Inisialnya RD? Raditya Dika Panik, Cerita Tewang Kesetrum #Shorts |

## Peraturan publish
1. Upload **hanya lewat clipper** (endpoint /api/social/youtube/upload) — never hand-upload dari HP.
2. Setiap klip: judul lengkap + deskripsi (caption dari clipper) + hashtag 5–8.
3. Default privacy = **private**, baru `public` pas di-approve user (default publik kalau user bilang "publish").
4. Batalkan/privatasi video lama yang 0 views (01/03/04/07 asli) supaya nggak duplikat di channel.
5. Setelah publish, kinerja dievaluasi ulang; klip yang <20 views → rekompilasi + retest dengan packaging beda.

## State file
- Render: VPS /home/ubuntu/bykamo/vision-clipper-studio/clips/tirta_recut/ (sedang berjalan, haven't confirm finished)
- Upload-ready files: harus scopped dulu ke local `clips/tirta_recut/`, baru dijadwalkan di `queue_upload.py`.
- Token: local ~/.visionclipper_youtube_token.json (3 scope: youtube.upload + readonly + force-ssl).
