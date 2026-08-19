import React from 'react';
import { 
  Type, 
  Sparkles, 
  Palette, 
  Layers, 
  Eye, 
  Check, 
  Sliders,
  Smile,
  ShieldCheck,
  MoveVertical
} from 'lucide-react';
import { SubtitleStyleConfig, SubtitlePresetId, SubtitleAnimation } from '../types';
import { SUBTITLE_PRESETS } from '../data/subtitlePresets';

interface SubtitleCustomizerProps {
  subtitleConfig: SubtitleStyleConfig;
  onChange: (config: SubtitleStyleConfig) => void;
}

export const SubtitleCustomizer: React.FC<SubtitleCustomizerProps> = ({
  subtitleConfig,
  onChange
}) => {
  const handleSelectPreset = (preset: SubtitleStyleConfig) => {
    onChange({ ...preset });
  };

  const updateField = <K extends keyof SubtitleStyleConfig>(key: K, value: SubtitleStyleConfig[K]) => {
    onChange({
      ...subtitleConfig,
      [key]: value
    });
  };

  const animationTypes: { id: SubtitleAnimation; label: string; desc: string }[] = [
    { id: 'word_pop', label: 'Word Pop ⚡', desc: 'Kata yang sedang dibaca membesar & berubah warna' },
    { id: 'bounce', label: 'Bounce Jump 🦘', desc: 'Efek memantul energetik ala MrBeast' },
    { id: 'karaoke', label: 'Karaoke Fill 🎤', desc: 'Warna terisi mulus dari kiri ke kanan' },
    { id: 'glow_pulse', label: 'Cyber Glow ✨', desc: 'Pendaran neon bercahaya dinamis' },
    { id: 'slide_up', label: 'Smooth Slide 🌊', desc: 'Transisi naik vertikal yang elegan' },
    { id: 'none', label: 'Statis (Tanpa Gerak)', desc: 'Teks subtitle standar' },
  ];

  const fontOptions = [
    { id: 'Montserrat', label: 'Montserrat (Hormozi Classic)' },
    { id: 'Rubik', label: 'Rubik (MrBeast Style)' },
    { id: 'Anton', label: 'Anton (Impact Heavy)' },
    { id: 'Bebas Neue', label: 'Bebas Neue (Tall Condensed)' },
    { id: 'Outfit', label: 'Outfit (Modern Tech)' },
    { id: 'Plus Jakarta Sans', label: 'Plus Jakarta Sans (Clean Minimal)' },
  ];

  const colorPalette = [
    { label: 'Kuning Hormozi', hex: '#FACC15' },
    { label: 'Hijau Neon', hex: '#4ADE80' },
    { label: 'Biru Cyan', hex: '#38BDF8' },
    { label: 'Merah Rose', hex: '#F43F5E' },
    { label: 'Ungu Elektrik', hex: '#C084FC' },
    { label: 'Putih Bersih', hex: '#FFFFFF' },
  ];

  return (
    <div id="subtitle-customizer" className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-5 shadow-xl">
      <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h2 className="flex items-center gap-2 text-base font-bold text-white">
            <Type className="h-4 w-4 text-amber-400" />
            <span>3. Pilihan Desain & Gaya Subtitle Viral</span>
          </h2>
          <p className="text-xs text-neutral-400">
            Pilih template subtitle kinetik kreator ternama atau kustomisasi tipografi, warna, dan animasi
          </p>
        </div>
      </div>

      {/* SUBTITLE PRESETS GRID */}
      <div className="mb-6">
        <label className="mb-2.5 block text-xs font-bold text-neutral-300">
          Template Subtitle Populer:
        </label>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {SUBTITLE_PRESETS.map((preset) => {
            const isSelected = subtitleConfig.presetId === preset.presetId;
            return (
              <button
                key={preset.presetId}
                id={`preset-btn-${preset.presetId}`}
                type="button"
                onClick={() => handleSelectPreset(preset)}
                className={`group relative flex flex-col justify-between rounded-xl border p-3 text-left transition-all ${
                  isSelected
                    ? 'border-amber-500 bg-amber-500/10 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500'
                    : 'border-neutral-800 bg-neutral-950/60 hover:border-neutral-700 hover:bg-neutral-800/40'
                }`}
              >
                {/* Mini Preview Box */}
                <div 
                  className="mb-2.5 flex h-14 w-full items-center justify-center rounded-lg bg-neutral-900 px-1 text-center font-bold"
                  style={{
                    fontFamily: preset.fontFamily,
                    backgroundColor: preset.backgroundBox ? preset.backgroundColor : '#0c0a09'
                  }}
                >
                  <span
                    style={{
                      color: preset.primaryColor,
                      fontSize: '13px',
                      textShadow: preset.strokeWidth > 0 ? `0 0 ${preset.strokeWidth}px ${preset.strokeColor}` : 'none',
                      textTransform: preset.allCaps ? 'uppercase' : 'none'
                    }}
                  >
                    RAHASIA{' '}
                    <span style={{ color: preset.highlightColor }}>
                      VIRAL!
                    </span>
                  </span>
                </div>

                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-neutral-100 group-hover:text-amber-300">
                    <span className="truncate">{preset.name}</span>
                    {isSelected && <Check className="h-3 w-3 text-amber-400 flex-shrink-0" />}
                  </div>
                  <div className="text-[10px] text-neutral-400 capitalize">
                    {preset.animationType.replace('_', ' ')}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* LIVE SUBTITLE CANVAS PREVIEW */}
      <div className="mb-6 rounded-xl border border-neutral-800 bg-neutral-950 p-4">
        <div className="mb-2 flex items-center justify-between text-xs text-neutral-400">
          <span className="flex items-center gap-1.5 font-bold text-neutral-300">
            <Eye className="h-3.5 w-3.5 text-amber-400" />
            Pratinjau Live Render Subtitle:
          </span>
          <span className="text-[11px] text-neutral-500">
            Posisi Y: {subtitleConfig.positionY}% dari bawah
          </span>
        </div>

        <div className="relative flex h-28 w-full items-center justify-center overflow-hidden rounded-lg bg-gradient-to-b from-neutral-900 to-neutral-950">
          {/* Mock Safe Zone overlay lines */}
          <div className="absolute inset-x-4 bottom-2 border-b border-dashed border-red-500/30 text-[9px] text-red-400/50">
            TikTok Bottom Safe Zone
          </div>
          
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 transition-all text-center"
            style={{
              fontFamily: subtitleConfig.fontFamily,
              backgroundColor: subtitleConfig.backgroundBox ? subtitleConfig.backgroundColor : 'transparent',
              borderRadius: subtitleConfig.backgroundBox ? '8px' : '0',
            }}
          >
            <span
              style={{
                fontSize: `${subtitleConfig.fontSize}px`,
                color: subtitleConfig.primaryColor,
                fontWeight: 900,
                textTransform: subtitleConfig.allCaps ? 'uppercase' : 'none',
                WebkitTextStroke: subtitleConfig.strokeWidth > 0 ? `${subtitleConfig.strokeWidth / 2}px ${subtitleConfig.strokeColor}` : 'none',
                filter: subtitleConfig.shadow ? 'drop-shadow(0 2px 4px rgba(0,0,0,0.8))' : 'none',
              }}
            >
              JANGAN PERNAH
            </span>
            <span
              className="animate-pulse"
              style={{
                fontSize: `${subtitleConfig.fontSize * 1.1}px`,
                color: subtitleConfig.highlightColor,
                fontWeight: 900,
                textTransform: subtitleConfig.allCaps ? 'uppercase' : 'none',
                WebkitTextStroke: subtitleConfig.strokeWidth > 0 ? `${subtitleConfig.strokeWidth / 2}px ${subtitleConfig.strokeColor}` : 'none',
                filter: subtitleConfig.shadow ? 'drop-shadow(0 2px 8px rgba(250,204,21,0.4))' : 'none',
              }}
            >
              MULAI {subtitleConfig.showEmoji && '🚫'}
            </span>
          </div>
        </div>
      </div>

      {/* DETAILED CUSTOMIZATION CONTROLS */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        
        {/* FONT & TYPOGRAPHY */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-3.5 space-y-3">
          <label className="flex items-center gap-1.5 text-xs font-bold text-neutral-200">
            <Type className="h-3.5 w-3.5 text-amber-400" />
            <span>Jenis Font & Ukuran:</span>
          </label>

          <div>
            <select
              value={subtitleConfig.fontFamily}
              onChange={(e) => updateField('fontFamily', e.target.value)}
              className="w-full rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs text-neutral-100 focus:border-amber-500 focus:outline-none"
            >
              {fontOptions.map(font => (
                <option key={font.id} value={font.id}>{font.label}</option>
              ))}
            </select>
          </div>

          <div>
            <div className="flex justify-between text-[11px] text-neutral-400 mb-1">
              <span>Ukuran Font:</span>
              <span className="font-bold text-amber-400">{subtitleConfig.fontSize}px</span>
            </div>
            <input
              type="range"
              min="16"
              max="36"
              value={subtitleConfig.fontSize}
              onChange={(e) => updateField('fontSize', parseInt(e.target.value))}
              className="h-1.5 w-full appearance-none rounded-lg bg-neutral-800 accent-amber-500"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex cursor-pointer items-center gap-2 text-xs text-neutral-300">
              <input
                type="checkbox"
                checked={subtitleConfig.allCaps}
                onChange={(e) => updateField('allCaps', e.target.checked)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
              />
              <span>HURUF BESAR (ALL CAPS)</span>
            </label>
          </div>
        </div>

        {/* COLORS & OUTLINES */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-3.5 space-y-3">
          <label className="flex items-center gap-1.5 text-xs font-bold text-neutral-200">
            <Palette className="h-3.5 w-3.5 text-amber-400" />
            <span>Warna Highlight Kata Aktif:</span>
          </label>

          <div className="flex flex-wrap gap-2">
            {colorPalette.map(c => (
              <button
                key={c.hex}
                type="button"
                onClick={() => updateField('highlightColor', c.hex)}
                className={`flex h-7 w-7 items-center justify-center rounded-full border-2 transition-all ${
                  subtitleConfig.highlightColor === c.hex ? 'border-white scale-110' : 'border-transparent hover:scale-105'
                }`}
                style={{ backgroundColor: c.hex }}
                title={c.label}
              >
                {subtitleConfig.highlightColor === c.hex && (
                  <Check className="h-3 w-3 text-black stroke-[3]" />
                )}
              </button>
            ))}
          </div>

          <div>
            <div className="flex justify-between text-[11px] text-neutral-400 mb-1">
              <span>Ketebalan Stroke Outline:</span>
              <span className="font-bold text-amber-400">{subtitleConfig.strokeWidth}px</span>
            </div>
            <input
              type="range"
              min="0"
              max="8"
              value={subtitleConfig.strokeWidth}
              onChange={(e) => updateField('strokeWidth', parseInt(e.target.value))}
              className="h-1.5 w-full appearance-none rounded-lg bg-neutral-800 accent-amber-500"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex cursor-pointer items-center gap-2 text-xs text-neutral-300">
              <input
                type="checkbox"
                checked={subtitleConfig.backgroundBox}
                onChange={(e) => updateField('backgroundBox', e.target.checked)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
              />
              <span>Kotak Latar Hitam (Badge Box)</span>
            </label>
          </div>
        </div>

        {/* ANIMATION & POSITION */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-3.5 space-y-3">
          <label className="flex items-center gap-1.5 text-xs font-bold text-neutral-200">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span>Animasi & Posisi Vertikal:</span>
          </label>

          <div>
            <select
              value={subtitleConfig.animationType}
              onChange={(e) => updateField('animationType', e.target.value as any)}
              className="w-full rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs text-neutral-100 focus:border-amber-500 focus:outline-none"
            >
              {animationTypes.map(anim => (
                <option key={anim.id} value={anim.id}>{anim.label}</option>
              ))}
            </select>
          </div>

          <div>
            <div className="flex justify-between text-[11px] text-neutral-400 mb-1">
              <span className="flex items-center gap-1">
                <MoveVertical className="h-3 w-3" />
                Posisi dari Bawah Layar:
              </span>
              <span className="font-bold text-amber-400">{subtitleConfig.positionY}%</span>
            </div>
            <input
              type="range"
              min="15"
              max="45"
              value={subtitleConfig.positionY}
              onChange={(e) => updateField('positionY', parseInt(e.target.value))}
              className="h-1.5 w-full appearance-none rounded-lg bg-neutral-800 accent-amber-500"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex cursor-pointer items-center gap-2 text-xs text-neutral-300">
              <input
                type="checkbox"
                checked={subtitleConfig.showEmoji}
                onChange={(e) => updateField('showEmoji', e.target.checked)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
              />
              <Smile className="h-3.5 w-3.5 text-amber-400" />
              <span>Sertakan Emoji Auto-Sticker</span>
            </label>
          </div>
        </div>

      </div>

    </div>
  );
};
