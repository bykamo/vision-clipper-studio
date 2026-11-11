# PILAR byKamo — payung tema & aturan seleksi klip

Dibuat 2026-11-11 dari analisis 25 video channel byKamo (23.930 views) + branding channel via YouTube Data API.
Sumber data: `~/.hermes/profiles/jack/cache/scratch/yt/channel_report_fresh.json`.

## Pertanyaan yang dijawab

"Klip Shorts acak dari video influencer rame — boleh bebas gak, kan belum ada niche?"

**Jawaban dari data channel sendiri: boleh luas, tapi jangan tanpa payung.**
Tidak ada satu pun bukti di 25 video ini yang bilang tema acak bikin video mati.
Sebaliknya, batch yang di-upload tanpa metadata yang mati 4/4.

## Bukti 1 — nasib ditentukan per batch/cara upload, bukan per tema

| tanggal upload | n | rata2 views | tembus | mati | catatan |
|---|---|---|---|---|---|
| 2026-11-11 | 4 | 1 | 0/4 | **4/4** | naik dari HP, judul tanggal → **mati semua** |
| 2026-11-08 | 3 | 1.234 | 3/3 | 0 | lewat clipper, metadata lengkap |
| 2026-10-29 | 2 | 1.199 | 2/2 | 0 | idem |
| 2026-09-21 | 6 | 1.273 | 2/6 | 3/6 | satu batch berisi 6.062 **dan** 17 **dan** 27 |
| 2026-09-05 | 2 | 1.702 | 2/2 | 0 | |
| 2026-08-26 | 5 | 769 | 3/5 | 2/5 | |

Klip nomor satu channel (6.062) dan klip mati 17 views **naik di batch & hari yang sama** → tema/tanggal bukan penentu.

## Bukti 2 — tema kembar, hasil beda jauh

| judul | views |
|---|---|
| Kenapa Orang Miskin Sering Benci Lihat Orang Kaya? | 1.260 |
| Kenapa Orang Miskin Gengsinya Lebih Tinggi? | **17** |

Tema praktis sama. Yang beda: packaging + apakah klipnya dapet tes di feed.
→ Kalau klip mati, **jangan buang temanya** — perbaiki potongan & judulnya, coba lagi.

## Bukti 3 — nama influencer terkenal bukan jaminan

| | n | rata2 views | tembus |
|---|---|---|---|
| judul menyebut nama terkenal | 4 | 726 | 1/4 |
| judul tanpa nama | 21 | 1.001 | 12/21 |

Nama besar = bonus buat klik, bukan syarat lolos feed. Channel ini punya 0-view yang judulnya Raditya Dika & Dokter Tirta.

## Bukti 4 — hit rate per klaster tema (label manual dari 25 judul)

| klaster | n | rata2 | tembus | mati |
|---|---|---|---|---|
| UANG & KELAS SOSIAL | 6 | 1.079 | **5/6 (83%)** | 1/6 |
| BISNIS & KONTEN KREATOR | 4 | 926 | **3/4 (75%)** | 1/4 |
| CARA MIKIR / BELAJAR / IQ | 11 | 985 | 4/11 (36%) | 5/11 |
| ORANG TERKENAL / DIBICARAKAN | 4 | 726 | 1/4 (25%) | 2/4 |

Rata-rata semua klaster mirip (726–1.079) → **plafonnya sama, yang beda cuma peluang lolos tes feed.**

## Bukti 5 — pola judul pemenang

10 dari 13 video tembus pakai pola celah rasa penasaran (`Kenapa…`, `Tanda…`, `Rahasia…`, `Cara…`, `Jangan…`, `3 Trik…`), vs 4 dari 9 yang mati.

## Risiko kalau benar-benar tanpa payung

1. **Klasifikasi channel kosong.** `topicCategories` channel byKamo kosong di API — YouTube belum tahu channel ini soal apa, jadi rekomendasi lintas-video lemah.
2. **Reused content.** Channel berisi repost klip orang lain tanpa payung + nilai tambah bisa ditolak monetisasi YPP. Transformasi (crop vertikal, subtitle, hook, pemilihan momen) + kredit sumber + tema konsisten = pertahanan.
3. **Nggak bisa belajar.** Tanpa payung, tiap video jadi undian baru — nggak ada yang bisa ditarik jadi pelajaran.

## Payung byKamo (lebar, tapi satu janji)

> **"Cara orang Indonesia mikir soal uang, kerja, dan naik kelas."**

Di dalam payung ini influencer apa pun masuk — Dennies/Coach Tom (bisnis, affiliate), Coki & Raditya Dika (konten kreator/showbiz), motivator/psikologi/IQ — **selama potongannya soal uang, cara mikir, atau naik kelas.** Bukan prank, bukan drama, bukan gaming.

## 3 pilar + porsi

| pilar | porsi | sumber klip | dasar |
|---|---|---|---|
| 1. Uang & naik kelas | 50–70% | Dennies, Coach Tom, klip soal kaya/miskin/negosiasi/gengsi | hit rate 83% |
| 2. Cara mikir, belajar & IQ | 20–30% | motivator, psikologi, IQ, edukasi | hit rate 36% tapi pemegang juara 6.062 |
| 3. Bisnis & konten kreator (praktis) | 10–20% | affiliate, copywriting, kreator | hit rate 75% |

Eksperimen di luar payung: maksimal 1 dari 10 klip, dan catat hasilnya.

## 3 saringan sebelum upload

1. **Masuk salah satu pilar?** (kalau tidak → tahan, kecuali kuota eksperimen 1/10)
2. **Judul punya celah rasa penasaran atau klaim spesifik?** Bukan kalimat datar/berita.
3. **3 detik pertama ada tensi?** Kalau tidak ada, klip itu belum layak naik.

Kalau klip gagal saringan tapi momennya bagus → potong ulang dari titik lain, jangan upload apa adanya.

## Aturan upload (tetap berlaku)

- Upload **hanya lewat clipper** dengan judul + deskripsi + hashtag lengkap — bukan dari HP.
- 3–6 klip/hari, disebar (jeda ≥30 menit), slot 11.00–13.00 / 15.00–17.00 / 19.00–21.00 WIB.
- Default `private` sampai di-approve user.
- Klip yang mati (<20 views) → catat, coba paket ulang, jangan dihapus.
