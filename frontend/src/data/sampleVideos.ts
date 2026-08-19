import { SourceVideo, GeneratedClip } from '../types';

export const SAMPLE_VIDEOS: SourceVideo[] = [
  {
    id: 'sample-podcast-ai',
    title: 'Podcast Bisnis: Cara Creator Raih 100 Juta Pertama dari Konten AI',
    duration: 184, // 3 min 4s
    category: 'Podcast & Bisnis',
    speaker: 'Raka Pratama & Dina Sandra',
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    videoType: 'sample',
    originalAspect: '16:9',
    summary: 'Diskusi mendalam mengenai transformasi creator economy dengan AI clipper, strategi hook 3 detik pertama, dan monetisasi multi-platform.',
    transcriptSample: 'Banyak orang ngira bikin video pendek itu soal keberuntungan. Padahal ada pola hook 3 detik yang 99% pasti ditonton sampai habis...'
  },
  {
    id: 'sample-tech-insights',
    title: 'Tech Talk: Mengapa Video Vertikal Menguasai Algoritma 2026',
    duration: 142,
    category: 'Teknologi & Media',
    speaker: 'Arya Dev',
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    videoType: 'sample',
    originalAspect: '16:9',
    summary: 'Analisis teknis arsitektur rekomendasi TikTok, Instagram Reels, dan YouTube Shorts dalam memproses retensi video vertikal.',
    transcriptSample: 'Algoritma sekarang gak cuma baca hashtag, tapi transkrip suara real-time dan pacing visual frame per frame!'
  },
  {
    id: 'sample-mindset-finance',
    title: 'Mindset Finansial: Jebakan Gaji 2 Digit & Cara Keluar dari Rat Race',
    duration: 210,
    category: 'Pengembangan Diri',
    speaker: 'Coach Hendra',
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    videoType: 'sample',
    originalAspect: '16:9',
    summary: 'Strategi mengalokasikan arus kas untuk aset produktif daripada gaya hidup konsumtif.',
    transcriptSample: 'Kesalahan terbesar anak muda umur 20-an adalah mikir kenaikan gaji harus diiringi kenaikan cicilan!'
  }
];

export const INITIAL_GENERATED_CLIPS: GeneratedClip[] = [
  {
    id: 'clip-01',
    title: 'Pola Hook 3 Detik Pertama yang Bikin FYP Otomatis',
    hookSentence: 'Jangan pernah mulai video dengan kata "Halo guys"!',
    viralityScore: 98,
    viralityRationale: 'Hook sangat kuat dengan anti-cliché, tempo cepat, dan relevan tinggi untuk content creator.',
    startTime: 12,
    endTime: 38,
    duration: 26,
    aspectRatio: '9:16',
    speakerName: 'Raka Pratama',
    tags: ['#ContentCreator', '#TipsFYP', '#ShortsStrategy', '#DigitalMarketing'],
    subtitles: [
      {
        id: 'sub-1',
        start: 0,
        end: 4.2,
        text: 'Jangan pernah mulai video dengan kata halo guys!',
        words: [
          { word: 'JANGAN', start: 0.1, end: 0.8, highlight: true, emoji: '🚫' },
          { word: 'PERNAH', start: 0.9, end: 1.5, highlight: true },
          { word: 'MULAI', start: 1.6, end: 2.2 },
          { word: 'DENGAN', start: 2.3, end: 2.7 },
          { word: 'HALO GUYS!', start: 2.8, end: 4.1, highlight: true, emoji: '👋' }
        ]
      },
      {
        id: 'sub-2',
        start: 4.3,
        end: 9.0,
        text: '99% penonton bakal langsung scroll dalam 2 detik pertama.',
        words: [
          { word: '99%', start: 4.4, end: 5.2, highlight: true, emoji: '🔥' },
          { word: 'PENONTON', start: 5.3, end: 6.1 },
          { word: 'LANGSUNG', start: 6.2, end: 6.9 },
          { word: 'SCROLL', start: 7.0, end: 7.8, highlight: true, emoji: '📱' },
          { word: 'CEPAT!', start: 7.9, end: 8.9 }
        ]
      },
      {
        id: 'sub-3',
        start: 9.1,
        end: 15.5,
        text: 'Mulai dengan pertanyaan kontroversial atau data mengejutkan.',
        words: [
          { word: 'MULAI', start: 9.2, end: 10.0 },
          { word: 'DENGAN', start: 10.1, end: 10.6 },
          { word: 'PERTANYAAN', start: 10.7, end: 11.9, highlight: true, emoji: '❓' },
          { word: 'DATA', start: 12.0, end: 13.1, highlight: true, emoji: '📊' },
          { word: 'MENGEJUTKAN!', start: 13.2, end: 15.3, highlight: true, emoji: '🤯' }
        ]
      },
      {
        id: 'sub-4',
        start: 15.6,
        end: 22.0,
        text: 'Ini rahasia akun 0 follower bisa tembus 1 juta views dalam 7 hari.',
        words: [
          { word: 'INI', start: 15.7, end: 16.3 },
          { word: 'RAHASIA', start: 16.4, end: 17.5, highlight: true, emoji: '🤫' },
          { word: '1 JUTA', start: 17.6, end: 19.2, highlight: true, emoji: '🚀' },
          { word: 'VIEWS', start: 19.3, end: 20.3 },
          { word: '7 HARI!', start: 20.4, end: 21.8, highlight: true, emoji: '📅' }
        ]
      },
      {
        id: 'sub-5',
        start: 22.1,
        end: 26.0,
        text: 'Simpan video ini sebelum dihapus kompetitor kamu!',
        words: [
          { word: 'SIMPAN', start: 22.2, end: 23.2, highlight: true, emoji: '💾' },
          { word: 'VIDEO INI', start: 23.3, end: 24.5 },
          { word: 'SEKARANG!', start: 24.6, end: 25.8, highlight: true, emoji: '⚡' }
        ]
      }
    ],
    socialMetadata: {
      tiktok: {
        caption: 'Hentikan kesalahan fatal ini kalau mau views meledak di TikTok! 😱 Trik hook 3 detik yang wajib kamu coba.',
        hashtags: ['#tipsfyp', '#contentcreator', '#rahasiaforyou', '#belajarvideopendek', '#triktiktok'],
        recommendedAspect: '9:16',
        maxDurationSec: 60
      },
      instagram: {
        caption: 'Berapa detik waktu yang kamu butuhkan untuk menarik perhatian audiens di Reels? Ini rumusnya! ⚡ Simpan untuk konten berikutnya.',
        hashtags: ['#reelsgrowth', '#creatortips', '#digitalmarketingid', '#strategikonten'],
        recommendedAspect: '9:16',
        maxDurationSec: 90
      },
      youtube_shorts: {
        title: 'Jangan Awali Video Dengan "Halo Guys"! 🚫 Ini Hook Viral 2026 #Shorts',
        description: 'Pelajari formula hook pembuka video pendek yang terbukti meningkatkan retention rate hingga 85%.',
        hashtags: ['#Shorts', '#ViralTips', '#CreatorHub'],
        recommendedAspect: '9:16',
        maxDurationSec: 60
      },
      twitter: {
        caption: 'Rule #1 konten video pendek: Bunuh intro basi. Hook pembuka menentukan 90% algoritma distribusi.',
        hashtags: ['#CreatorEconomy', '#BuildInPublic'],
        recommendedAspect: '1:1',
        maxDurationSec: 140
      },
      linkedin: {
        caption: 'Di era rentang atensi 3 detik, bagaimana kita mengemas pesan esensial menjadi engaging tanpa clickbait murahan?',
        hashtags: ['#Leadership', '#DigitalContent', '#MarketingStrategy'],
        recommendedAspect: '4:5',
        maxDurationSec: 600
      }
    }
  },
  {
    id: 'clip-02',
    title: 'Kenapa Creator AI Bisa Bikin 30 Konten dalam 1 Jam',
    hookSentence: 'Kamu masih ngedit video manual 5 jam sehari? Kamu kalah cepat!',
    viralityScore: 94,
    viralityRationale: 'Membandingkan cara lama vs cara baru yang menciptakan FOMO dan solusi nyata.',
    startTime: 45,
    endTime: 78,
    duration: 33,
    aspectRatio: '9:16',
    speakerName: 'Dina Sandra',
    tags: ['#AITools', '#Productivity', '#AutomasiKonten'],
    subtitles: [
      {
        id: 'sub-201',
        start: 0,
        end: 5.0,
        text: 'Kamu masih ngedit manual lima jam sehari? Kamu kalah cepat!',
        words: [
          { word: 'MASIH', start: 0.1, end: 0.8 },
          { word: 'NGEDIT MANUAL', start: 0.9, end: 2.2, highlight: true },
          { word: '5 JAM?', start: 2.3, end: 3.4, highlight: true, emoji: '⏳' },
          { word: 'KALAH CEPAT!', start: 3.5, end: 4.8, highlight: true, emoji: '💨' }
        ]
      },
      {
        id: 'sub-202',
        start: 5.1,
        end: 11.5,
        text: 'Sekarang tinggal masukkan link podcast, AI otomatis potong momen terbaik.',
        words: [
          { word: 'MASUKKAN LINK', start: 5.2, end: 6.8, highlight: true, emoji: '🔗' },
          { word: 'AI OTOMATIS', start: 6.9, end: 8.5, highlight: true, emoji: '🤖' },
          { word: 'POTONG MOMEN', start: 8.6, end: 10.0 },
          { word: 'TERBAIK!', start: 10.1, end: 11.3, highlight: true, emoji: '✨' }
        ]
      },
      {
        id: 'sub-203',
        start: 11.6,
        end: 19.0,
        text: 'Subtitle gaya Hormozi, dynamic zoom, dan framing wajah sudah siap tayang.',
        words: [
          { word: 'SUBTITLE HORMOZI', start: 11.8, end: 13.8, highlight: true, emoji: '🟡' },
          { word: 'DYNAMIC ZOOM', start: 13.9, end: 15.6, highlight: true },
          { word: 'FRAMING WAJAH', start: 15.7, end: 17.2 },
          { word: 'SIAP TAYANG!', start: 17.3, end: 18.8, highlight: true, emoji: '🎯' }
        ]
      },
      {
        id: 'sub-204',
        start: 19.1,
        end: 25.0,
        text: 'Fokus kamu sekarang tinggal distribusi dan monetisasi.',
        words: [
          { word: 'FOKUS KAMU', start: 19.2, end: 20.8 },
          { word: 'DISTRIBUSI', start: 20.9, end: 22.4, highlight: true, emoji: '📈' },
          { word: 'MONETISASI!', start: 22.5, end: 24.7, highlight: true, emoji: '💰' }
        ]
      },
      {
        id: 'sub-205',
        start: 25.1,
        end: 33.0,
        text: 'Ketik AI di kolom komentar untuk coba tools ini sekarang juga!',
        words: [
          { word: 'KETIK "AI"', start: 25.2, end: 27.5, highlight: true, emoji: '💬' },
          { word: 'DI KOMENTAR', start: 27.6, end: 29.5 },
          { word: 'COBA SEKARANG!', start: 29.6, end: 32.7, highlight: true, emoji: '👇' }
        ]
      }
    ],
    socialMetadata: {
      tiktok: {
        caption: 'Workflow rahasia bikin 30 video per hari tanpa capek! 🤖 Simpan video ini dan komen "AI" sekarang.',
        hashtags: ['#aiclipper', '#automasikonten', '#tipsediting', '#produktivitas'],
        recommendedAspect: '9:16',
        maxDurationSec: 60
      },
      instagram: {
        caption: 'Tools yang bikin editor kerja 10x lebih cepat. Bukan menggantikan kreativitas, tapi membuang pekerjaan repetitif! 🔥',
        hashtags: ['#aiworkflows', '#videocreator', '#contentstrategy', '#futureofwork'],
        recommendedAspect: '9:16',
        maxDurationSec: 90
      },
      youtube_shorts: {
        title: 'Cara AI Mengubah 1 Podcast Jadi 10 Shorts Otomatis! ⚡ #AI',
        description: 'Workflow cerdas memotong video panjang menjadi klip viral berdurasi 30 detik lengkap dengan subtitle kinetik.',
        hashtags: ['#Shorts', '#AItools', '#TechTutorial'],
        recommendedAspect: '9:16',
        maxDurationSec: 60
      },
      twitter: {
        caption: 'Bukan siapa yang paling keras mengedit, tapi siapa yang paling konsisten mendistribusikan nilai.',
        hashtags: ['#AI', '#Productivity'],
        recommendedAspect: '1:1',
        maxDurationSec: 140
      },
      linkedin: {
        caption: 'Automasi konten bukanlah masa depan, ini adalah standar industri periklanan dan media hari ini.',
        hashtags: ['#Automation', '#AI', '#DigitalMedia'],
        recommendedAspect: '4:5',
        maxDurationSec: 600
      }
    }
  },
  {
    id: 'clip-03',
    title: 'Formula Retensi 80% di Video Pendek',
    hookSentence: 'Ada 1 aturan psikologi yang membuat mata audiens terkunci.',
    viralityScore: 91,
    viralityRationale: 'Insight mendalam tentang visual pacing, text highlighting, and auditory triggers.',
    startTime: 92,
    endTime: 120,
    duration: 28,
    aspectRatio: '9:16',
    speakerName: 'Raka Pratama',
    tags: ['#RetensiVideo', '#PsikologiKonten', '#Storytelling'],
    subtitles: [
      {
        id: 'sub-301',
        start: 0,
        end: 4.8,
        text: 'Ada satu aturan psikologi yang bikin mata audiens terkunci.',
        words: [
          { word: 'SATU ATURAN', start: 0.2, end: 1.5, highlight: true },
          { word: 'PSIKOLOGI', start: 1.6, end: 2.8, highlight: true, emoji: '🧠' },
          { word: 'MATA AUDIENS', start: 2.9, end: 3.8 },
          { word: 'TERKUNCI!', start: 3.9, end: 4.7, highlight: true, emoji: '🔒' }
        ]
      },
      {
        id: 'sub-302',
        start: 4.9,
        end: 10.5,
        text: 'Yaitu pergantian stimulus visual setiap 2.5 detik sekali.',
        words: [
          { word: 'PERGANTIAN', start: 5.0, end: 6.2 },
          { word: 'STIMULUS VISUAL', start: 6.3, end: 7.9, highlight: true, emoji: '👁️' },
          { word: 'SETIAP 2.5 DETIK', start: 8.0, end: 9.5, highlight: true, emoji: '⏱️' },
          { word: 'SEKALI!', start: 9.6, end: 10.4 }
        ]
      },
      {
        id: 'sub-303',
        start: 10.6,
        end: 17.5,
        text: 'Gunakan subtitle dengan warna aktif yang melompat mengikuti intonasi bicara.',
        words: [
          { word: 'SUBTITLE', start: 10.7, end: 12.0 },
          { word: 'WARNA AKTIF', start: 12.1, end: 13.8, highlight: true, emoji: '🎨' },
          { word: 'MELOMPAT', start: 13.9, end: 15.2, highlight: true, emoji: '🦘' },
          { word: 'IKUTI INTONASI!', start: 15.3, end: 17.3 }
        ]
      },
      {
        id: 'sub-304',
        start: 17.6,
        end: 23.0,
        text: 'Otak manusia dirancang untuk memperhatikan pergerakan kontras.',
        words: [
          { word: 'OTAK MANUSIA', start: 17.7, end: 19.3, highlight: true, emoji: '💡' },
          { word: 'DIRANCANG', start: 19.4, end: 20.6 },
          { word: 'PERGERAKAN', start: 20.7, end: 21.8 },
          { word: 'KONTRAS!', start: 21.9, end: 22.9, highlight: true }
        ]
      },
      {
        id: 'sub-305',
        start: 23.1,
        end: 28.0,
        text: 'Praktekkan ini dan tonton retensi video kamu melonjak!',
        words: [
          { word: 'PRAKTEKKAN', start: 23.2, end: 24.5, highlight: true },
          { word: 'RETENSI', start: 24.6, end: 25.8, highlight: true, emoji: '📊' },
          { word: 'MELONJAK!', start: 25.9, end: 27.8, highlight: true, emoji: '🚀' }
        ]
      }
    ],
    socialMetadata: {
      tiktok: {
        caption: 'Rahasia retensi 80% yang jarang dibocorkan agensi top! 🔥 Cek efek subtitle kata per kata.',
        hashtags: ['#videopsikologi', '#editinghacks', '#retensifyp'],
        recommendedAspect: '9:16',
        maxDurationSec: 60
      },
      instagram: {
        caption: 'Kenapa video kamu sepi penonton? Mungkin pacing visualnya terlalu lambat. Ini formula 2.5 detik! 💡',
        hashtags: ['#growthhack', '#reelsviral', '#contentediting'],
        recommendedAspect: '9:16',
        maxDurationSec: 90
      },
      youtube_shorts: {
        title: 'Formula Rahasia Retensi Video Pendek 2026! 📈 #Shorts',
        description: 'Trik psikologi visual untuk menjaga audiens tetap menonton video kamu hingga detik terakhir.',
        hashtags: ['#Shorts', '#AlgorithmTips'],
        recommendedAspect: '9:16',
        maxDurationSec: 60
      },
      twitter: {
        caption: 'Pergantian visual setiap 2.5 detik = retensi naik 40%.',
        hashtags: ['#CreatorTips'],
        recommendedAspect: '1:1',
        maxDurationSec: 140
      },
      linkedin: {
        caption: 'Membedah psikologi di balik video dengan performa engagement tinggi.',
        hashtags: ['#VisualMarketing', '#AudienceEngagement'],
        recommendedAspect: '4:5',
        maxDurationSec: 600
      }
    }
  }
];
