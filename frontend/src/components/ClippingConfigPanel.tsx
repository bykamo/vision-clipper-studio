import React from 'react';
import { 
  Sliders, 
  Flame, 
  Smartphone, 
  Square, 
  Tv, 
  ScanFace, 
  Sparkles,
  Zap,
  Timer,
  Hash,
  SmilePlus,
  Minus,
  Plus
} from 'lucide-react';
import { ClipGenerationConfig, AspectRatio, ViralityFocus, FramingMode } from '../types';

interface ClippingConfigPanelProps {
  config: ClipGenerationConfig;
  onChange: (newConfig: ClipGenerationConfig) => void;
  onStartGeneration: () => void;
  isProcessing: boolean;
}

export const ClippingConfigPanel: React.FC<ClippingConfigPanelProps> = ({
  config,
  onChange,
  onStartGeneration,
  isProcessing
}) => {
  const updateField = <K extends keyof ClipGenerationConfig>(key: K, value: ClipGenerationConfig[K]) => {
    onChange({
      ...config,
      [key]: value
    });
  };

  const handleClipCountChange = (delta: number) => {
    const nextVal = Math.min(10, Math.max(1, config.clipCount + delta));
    updateField('clipCount', nextVal);
  };

  const viralityOptions: { id: ViralityFocus; label: string; desc: string; icon: string }[] = [
    { 
      id: 'hook_first', 
      label: 'Hook 3 Detik Pertama', 
      desc: 'Mencari kalimat pembuka mengejutkan yang memancing rasa penasaran.',
      icon: '🎣'
    },
    { 
      id: 'key_insights', 
      label: 'Insight & Daging', 
      desc: 'Mengekstrak poin-poin pelajaran paling bernilai tanpa basa-basi.',
      icon: '💡'
    },
    { 
      id: 'high_energy', 
      label: 'Puncak Energi & Reaksi', 
      desc: 'Momen tawa, debat panas, atau intonasi suara paling bersemangat.',
      icon: '⚡'
    },
    { 
      id: 'qa_format', 
      label: 'Format Tanya-Jawab', 
      desc: 'Pertanyaan punchy diikuti jawaban tajam dari speaker.',
      icon: '❓'
    }
  ];

  const aspectOptions: { id: AspectRatio; label: string; sub: string; icon: React.ReactNode }[] = [
    { 
      id: '9:16', 
      label: '9:16 Vertikal', 
      sub: 'TikTok, Reels, Shorts',
      icon: <Smartphone className="h-4 w-4" />
    },
    { 
      id: '1:1', 
      label: '1:1 Persegi', 
      sub: 'Feed IG, Twitter / X',
      icon: <Square className="h-4 w-4" />
    },
    { 
      id: '4:5', 
      label: '4:5 Portrait', 
      sub: 'Instagram, LinkedIn',
      icon: <Smartphone className="h-4 w-4 rotate-12" />
    },
    { 
      id: '16:9', 
      label: '16:9 Landscape', 
      sub: 'YouTube Widescreen',
      icon: <Tv className="h-4 w-4" />
    }
  ];

  const framingOptions: { id: FramingMode; label: string; desc: string }[] = [
    { 
      id: 'auto_face_track', 
      label: 'Auto Face Tracking', 
      desc: 'AI memusatkan kamera secara dinamis ke wajah speaker yang sedang berbicara.'
    },
    { 
      id: 'split_screen', 
      label: 'Split Screen (2 Speaker)', 
      desc: 'Membagi layar atas & bawah untuk podcast 2 orang atau gameplay react.'
    },
    { 
      id: 'fit_blur', 
      label: 'Fit + Blurred Background', 
      desc: 'Mempertahankan rasio asli dengan latar belakang blur artistik.'
    }
  ];

  return (
    <div id="clipping-config-panel" className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-5 shadow-xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-base font-bold text-white">
            <Sliders className="h-4 w-4 text-amber-400" />
            <span>2. Pengaturan Auto-Clipper AI</span>
          </h2>
          <p className="text-xs text-neutral-400">
            Tentukan jumlah klip, durasi target, algoritma hook, dan rasio format video
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        
        {/* LEFT COLUMN: Clip Count & Duration */}
        <div className="space-y-4">
          
          {/* JUMLAH CLIP YANG MAU DIBUAT */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-4">
            <div className="mb-2 flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-xs font-bold text-neutral-200">
                <Hash className="h-3.5 w-3.5 text-amber-400" />
                <span>Jumlah Clip yang Mau Dibuat:</span>
              </label>
              <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-black text-amber-400">
                {config.clipCount} Klip Video
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                id="btn-decrement-clips"
                type="button"
                onClick={() => handleClipCountChange(-1)}
                className="flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-800 bg-neutral-900 text-neutral-300 hover:border-neutral-700 hover:bg-neutral-800 hover:text-white"
              >
                <Minus className="h-4 w-4" />
              </button>

              <input
                id="input-clip-count-slider"
                type="range"
                min="1"
                max="10"
                value={config.clipCount}
                onChange={(e) => updateField('clipCount', parseInt(e.target.value))}
                className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-neutral-800 accent-amber-500"
              />

              <button
                id="btn-increment-clips"
                type="button"
                onClick={() => handleClipCountChange(1)}
                className="flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-800 bg-neutral-900 text-neutral-300 hover:border-neutral-700 hover:bg-neutral-800 hover:text-white"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>

            {/* Quick Presets */}
            <div className="mt-3 flex gap-1.5">
              {[1, 3, 5, 8, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => updateField('clipCount', num)}
                  className={`flex-1 rounded-md py-1 text-[11px] font-bold transition-all ${
                    config.clipCount === num
                      ? 'bg-amber-500 text-neutral-950'
                      : 'border border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-white'
                  }`}
                >
                  {num} Klip
                </button>
              ))}
            </div>
          </div>

          {/* TARGET DURASI KLIP */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-4">
            <label className="mb-2.5 flex items-center gap-1.5 text-xs font-bold text-neutral-200">
              <Timer className="h-3.5 w-3.5 text-amber-400" />
              <span>Target Durasi Setiap Klip:</span>
            </label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                { id: '15_30', label: '15 - 30s', tag: 'Fast Bite' },
                { id: '30_60', label: '30 - 60s', tag: 'Standar FYP' },
                { id: '60_90', label: '60 - 90s', tag: 'Deep Dive' },
                { id: 'auto', label: 'Auto AI', tag: 'Optimal Retention' },
              ].map((dur) => (
                <button
                  key={dur.id}
                  type="button"
                  onClick={() => updateField('targetDuration', dur.id as any)}
                  className={`flex flex-col items-center justify-center rounded-lg border p-2.5 text-center transition-all ${
                    config.targetDuration === dur.id
                      ? 'border-amber-500 bg-amber-500/10 text-white ring-1 ring-amber-500'
                      : 'border-neutral-800 bg-neutral-900 text-neutral-400 hover:border-neutral-700 hover:text-white'
                  }`}
                >
                  <span className="text-xs font-extrabold">{dur.label}</span>
                  <span className="text-[10px] text-neutral-400">{dur.tag}</span>
                </button>
              ))}
            </div>
          </div>

          {/* FOKUS VIRALITY AI */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-4">
            <label className="mb-2.5 flex items-center gap-1.5 text-xs font-bold text-neutral-200">
              <Flame className="h-3.5 w-3.5 text-orange-500" />
              <span>Fokus Algoritma Hook Viral AI:</span>
            </label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {viralityOptions.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => updateField('viralityFocus', opt.id)}
                  className={`flex flex-col rounded-lg border p-2.5 text-left transition-all ${
                    config.viralityFocus === opt.id
                      ? 'border-amber-500 bg-amber-500/10 text-white ring-1 ring-amber-500'
                      : 'border-neutral-800 bg-neutral-900 text-neutral-400 hover:border-neutral-700 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-neutral-100">
                    <span>{opt.icon}</span>
                    <span>{opt.label}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-neutral-400 leading-tight">
                    {opt.desc}
                  </p>
                </button>
              ))}
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: Aspect Ratio, Framing, & AI Helpers */}
        <div className="space-y-4">
          
          {/* RASIO ASPEK VIDEO */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-4">
            <label className="mb-2.5 flex items-center gap-1.5 text-xs font-bold text-neutral-200">
              <Smartphone className="h-3.5 w-3.5 text-amber-400" />
              <span>Rasio Format Video Output:</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {aspectOptions.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => updateField('aspectRatio', opt.id)}
                  className={`flex items-center gap-2.5 rounded-lg border p-2.5 text-left transition-all ${
                    config.aspectRatio === opt.id
                      ? 'border-amber-500 bg-amber-500/10 text-white ring-1 ring-amber-500'
                      : 'border-neutral-800 bg-neutral-900 text-neutral-400 hover:border-neutral-700 hover:text-white'
                  }`}
                >
                  <div className={`flex h-7 w-7 items-center justify-center rounded-md ${
                    config.aspectRatio === opt.id ? 'bg-amber-500 text-black' : 'bg-neutral-800 text-neutral-400'
                  }`}>
                    {opt.icon}
                  </div>
                  <div>
                    <div className="text-xs font-bold text-neutral-100">{opt.label}</div>
                    <div className="text-[10px] text-neutral-400">{opt.sub}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* AI AUTO FRAMING MODE */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-4">
            <label className="mb-2.5 flex items-center gap-1.5 text-xs font-bold text-neutral-200">
              <ScanFace className="h-3.5 w-3.5 text-amber-400" />
              <span>AI Auto-Framing & Reframing Wajah:</span>
            </label>
            <div className="space-y-2">
              {framingOptions.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => updateField('framingMode', f.id)}
                  className={`flex w-full flex-col rounded-lg border p-2.5 text-left transition-all ${
                    config.framingMode === f.id
                      ? 'border-amber-500 bg-amber-500/10 text-white ring-1 ring-amber-500'
                      : 'border-neutral-800 bg-neutral-900 text-neutral-400 hover:border-neutral-700 hover:text-white'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-bold text-neutral-100">
                    <span>{f.label}</span>
                    {config.framingMode === f.id && (
                      <span className="rounded bg-amber-500 px-1.5 py-0.5 text-[9px] font-black text-black">
                        AKTIF
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-[11px] text-neutral-400">
                    {f.desc}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* TOGGLE EXTRAS */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-neutral-800 bg-neutral-950/70 p-3">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-neutral-300">
              <input
                type="checkbox"
                checked={config.autoEmojis}
                onChange={(e) => updateField('autoEmojis', e.target.checked)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
              />
              <SmilePlus className="h-3.5 w-3.5 text-amber-400" />
              <span>Auto Tambahkan Emoji Dinamis</span>
            </label>

            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-neutral-300">
              <input
                type="checkbox"
                checked={config.includeCaptions}
                onChange={(e) => updateField('includeCaptions', e.target.checked)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
              />
              <Zap className="h-3.5 w-3.5 text-amber-400" />
              <span>Auto-Generate Caption Sosmed</span>
            </label>
          </div>

        </div>

      </div>

      {/* START GENERATION BUTTON */}
      <div className="mt-6 flex flex-col items-center justify-between gap-3 border-t border-neutral-800 pt-5 sm:flex-row">
        <div className="flex items-center gap-2 text-xs text-neutral-400">
          <Sparkles className="h-4 w-4 text-amber-400" />
          <span>
            Memproses dengan model <strong className="text-white">Whisper v3</strong> + <strong className="text-white">Gemini Virality AI</strong>
          </span>
        </div>

        <button
          id="btn-start-clipping"
          type="button"
          onClick={onStartGeneration}
          disabled={isProcessing}
          className={`flex w-full items-center justify-center gap-2.5 rounded-xl px-8 py-3.5 text-sm font-extrabold transition-all sm:w-auto ${
            isProcessing
              ? 'cursor-wait bg-neutral-800 text-neutral-400'
              : 'bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 text-neutral-950 shadow-xl shadow-orange-500/25 hover:from-amber-400 hover:to-rose-400 hover:shadow-orange-500/40 active:scale-[0.98]'
          }`}
        >
          <Sparkles className="h-4 w-4 fill-neutral-950" />
          <span>
            {isProcessing ? 'Sedang Memproses AI...' : `Mulai AI Clipper (${config.clipCount} Klip)`}
          </span>
        </button>
      </div>

    </div>
  );
};
