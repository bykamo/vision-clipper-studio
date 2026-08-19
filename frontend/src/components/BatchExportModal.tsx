import React, { useState } from 'react';
import { 
  X, 
  Share2, 
  Download, 
  Check, 
  Sparkles, 
  Film, 
  Smartphone, 
  Square, 
  Layers, 
  HardDrive, 
  RefreshCw, 
  CheckCircle2,
  FileText,
  Copy,
  Flame
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { GeneratedClip, SocialPlatformId, ExportSettings } from '../types';

interface BatchExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  clips: GeneratedClip[];
  initialSelectedClip?: GeneratedClip;
}

export const BatchExportModal: React.FC<BatchExportModalProps> = ({
  isOpen,
  onClose,
  clips,
  initialSelectedClip
}) => {
  const [selectedClipIds, setSelectedClipIds] = useState<string[]>(
    initialSelectedClip ? [initialSelectedClip.id] : clips.map(c => c.id)
  );

  const [selectedPlatforms, setSelectedPlatforms] = useState<SocialPlatformId[]>([
    'tiktok',
    'instagram',
    'youtube_shorts'
  ]);

  const [resolution, setResolution] = useState<'1080p' | '4k' | '720p'>('1080p');
  const [framerate, setFramerate] = useState<30 | 60>(60);
  const [codec, setCodec] = useState<'h264' | 'hevc' | 'webm'>('h264');
  const [burnSubtitles, setBurnSubtitles] = useState(true);
  const [includeMetadata, setIncludeMetadata] = useState(true);

  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportStage, setExportStage] = useState('');
  const [exportCompleted, setExportCompleted] = useState(false);

  if (!isOpen) return null;

  const togglePlatform = (plat: SocialPlatformId) => {
    if (selectedPlatforms.includes(plat)) {
      if (selectedPlatforms.length > 1) {
        setSelectedPlatforms(selectedPlatforms.filter(p => p !== plat));
      }
    } else {
      setSelectedPlatforms([...selectedPlatforms, plat]);
    }
  };

  const toggleClip = (id: string) => {
    if (selectedClipIds.includes(id)) {
      if (selectedClipIds.length > 1) {
        setSelectedClipIds(selectedClipIds.filter(i => i !== id));
      }
    } else {
      setSelectedClipIds([...selectedClipIds, id]);
    }
  };

  const handleStartExport = () => {
    setIsExporting(true);
    setExportProgress(5);
    setExportStage('Inisialisasi Hardware Encoder (GPU NVENC)...');

    const totalClips = selectedClipIds.length;
    const stages = [
      'Render frame video & dynamic zoom...',
      'Burn-in kinetic animated subtitles...',
      'Encoding MP4 H.264 1080x1920 60fps...',
      'Mengemas format TikTok, Reels, & Shorts...',
      'Membuat file metadata caption & tagar...',
      'Finalisasi file ZIP export siap unduh...'
    ];

    let currentIdx = 0;
    const interval = setInterval(() => {
      currentIdx++;
      if (currentIdx < stages.length) {
        setExportStage(stages[currentIdx]);
        setExportProgress(Math.min(95, currentIdx * 18 + Math.floor(Math.random() * 8)));
      } else {
        clearInterval(interval);
        setExportProgress(100);
        setExportStage('Ekspor Selesai!');
        setIsExporting(false);
        setExportCompleted(true);

        try {
          confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 }
          });
        } catch (e) {
          // ignore if canvas not supported
        }
      }
    }, 600);
  };

  const handleDownloadZip = () => {
    // Trigger virtual file download
    const element = document.createElement("a");
    const file = new Blob([
      `ClipForge AI - Auto Export Package\nTotal Klip: ${selectedClipIds.length}\nPlatform: ${selectedPlatforms.join(', ')}\nResolusi: ${resolution} ${framerate}fps\n\nSemua video & metadata telah dikemas otomatis.`
    ], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `ClipForge_AI_Export_Clips_${Date.now()}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const platformInfo: Record<SocialPlatformId, { name: string; aspect: string; color: string; desc: string }> = {
    tiktok: { name: 'TikTok', aspect: '9:16 (1080x1920)', color: '#00F2FE', desc: 'Optimal untuk FYP vertical algorithm' },
    instagram: { name: 'Instagram Reels', aspect: '9:16 (1080x1920)', color: '#E1306C', desc: 'Audio sync & caption visual' },
    youtube_shorts: { name: 'YouTube Shorts', aspect: '9:16 (1080x1920)', color: '#FF0000', desc: 'Max 60 detik with title metadata' },
    twitter: { name: 'X / Twitter', aspect: '1:1 / 16:9', color: '#1DA1F2', desc: 'High bitrate auto-play feed' },
    linkedin: { name: 'LinkedIn', aspect: '4:5 / 1:1', color: '#0A66C2', desc: 'Professional short summary format' },
  };

  return (
    <div id="batch-export-modal" className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900 shadow-2xl">
        
        {/* HEADER */}
        <div className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500 to-orange-500 text-black">
              <Share2 className="h-5 w-5 stroke-[2.5]" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-white">
                Auto-Export Multi-Format Media Sosial
              </h3>
              <p className="text-xs text-neutral-400">
                Render otomatis resolusi tinggi dan format siap upload ke semua platform
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-400 hover:bg-neutral-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* BODY */}
        <div className="max-h-[75vh] space-y-5 overflow-y-auto p-6 text-xs">
          
          {/* STEP 1: TARGET PLATFORMS */}
          <div>
            <label className="mb-2 flex items-center justify-between font-bold text-neutral-200">
              <span className="flex items-center gap-1.5">
                <Smartphone className="h-4 w-4 text-amber-400" />
                1. Pilih Target Platform Sosial Media:
              </span>
              <span className="text-[11px] text-amber-400 font-semibold">
                {selectedPlatforms.length} Platform Dipilih
              </span>
            </label>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {(Object.keys(platformInfo) as SocialPlatformId[]).map((plat) => {
                const isSelected = selectedPlatforms.includes(plat);
                const info = platformInfo[plat];
                return (
                  <button
                    key={plat}
                    onClick={() => togglePlatform(plat)}
                    className={`flex flex-col rounded-xl border p-3 text-left transition-all ${
                      isSelected
                        ? 'border-amber-500 bg-amber-500/10 ring-1 ring-amber-500'
                        : 'border-neutral-800 bg-neutral-950/60 opacity-60 hover:opacity-100'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white">{info.name}</span>
                      {isSelected && <Check className="h-3.5 w-3.5 text-amber-400 stroke-[3]" />}
                    </div>
                    <span className="mt-0.5 text-[10px] text-neutral-400">{info.aspect}</span>
                    <span className="mt-1 text-[9px] text-neutral-500">{info.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* STEP 2: SELECT CLIPS TO EXPORT */}
          <div>
            <div className="mb-2 flex items-center justify-between font-bold text-neutral-200">
              <span className="flex items-center gap-1.5">
                <Film className="h-4 w-4 text-amber-400" />
                2. Pilih Klip yang Mau Diekspor:
              </span>
              <button
                onClick={() => {
                  if (selectedClipIds.length === clips.length) {
                    setSelectedClipIds([clips[0].id]);
                  } else {
                    setSelectedClipIds(clips.map(c => c.id));
                  }
                }}
                className="text-[11px] text-amber-400 hover:underline"
              >
                {selectedClipIds.length === clips.length ? 'Pilih 1 Saja' : 'Pilih Semua'}
              </button>
            </div>

            <div className="space-y-2">
              {clips.map((clip, idx) => {
                const isSelected = selectedClipIds.includes(clip.id);
                return (
                  <div
                    key={clip.id}
                    onClick={() => toggleClip(clip.id)}
                    className={`flex cursor-pointer items-center justify-between rounded-xl border p-3 transition-all ${
                      isSelected
                        ? 'border-amber-500/80 bg-amber-500/10'
                        : 'border-neutral-800 bg-neutral-950/50 hover:bg-neutral-800/40'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`flex h-6 w-6 items-center justify-center rounded text-[11px] font-bold ${
                        isSelected ? 'bg-amber-500 text-black' : 'bg-neutral-800 text-neutral-400'
                      }`}>
                        #{idx + 1}
                      </div>
                      <div>
                        <div className="font-bold text-white line-clamp-1">{clip.title}</div>
                        <div className="text-[10px] text-neutral-400">Durasi: {clip.duration}s • Virality Score: {clip.viralityScore}/100</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="rounded bg-orange-500/20 px-2 py-0.5 text-[10px] font-bold text-orange-400 border border-orange-500/30">
                        {clip.viralityScore} Score
                      </span>
                      <div className={`flex h-4 w-4 items-center justify-center rounded border ${
                        isSelected ? 'border-amber-500 bg-amber-500 text-black' : 'border-neutral-700'
                      }`}>
                        {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* STEP 3: ENCODING & QUALITY SETTINGS */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 p-4 space-y-3">
            <div className="font-bold text-neutral-200 flex items-center gap-1.5">
              <HardDrive className="h-4 w-4 text-amber-400" />
              3. Format & Kualitas Rendering:
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[10px] text-neutral-500 font-bold block mb-1">RESOLUSI</label>
                <select
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value as any)}
                  className="w-full rounded-lg border border-neutral-800 bg-neutral-900 p-2 text-neutral-200 focus:border-amber-500"
                >
                  <option value="1080p">1080p FHD (1080x1920)</option>
                  <option value="4k">4K Ultra (2160x3840)</option>
                  <option value="720p">720p HD (Ringan)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-neutral-500 font-bold block mb-1">FRAMERATE</label>
                <select
                  value={framerate}
                  onChange={(e) => setFramerate(parseInt(e.target.value) as any)}
                  className="w-full rounded-lg border border-neutral-800 bg-neutral-900 p-2 text-neutral-200 focus:border-amber-500"
                >
                  <option value={60}>60 FPS (Super Smooth)</option>
                  <option value={30}>30 FPS (Standar)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-neutral-500 font-bold block mb-1">CODEC</label>
                <select
                  value={codec}
                  onChange={(e) => setCodec(e.target.value as any)}
                  className="w-full rounded-lg border border-neutral-800 bg-neutral-900 p-2 text-neutral-200 focus:border-amber-500"
                >
                  <option value="h264">MP4 (H.264 Universal)</option>
                  <option value="hevc">MP4 (H.265 / HEVC)</option>
                  <option value="webm">WebM VP9</option>
                </select>
              </div>
            </div>

            {/* Checkboxes */}
            <div className="flex flex-wrap gap-4 pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-neutral-300">
                <input
                  type="checkbox"
                  checked={burnSubtitles}
                  onChange={(e) => setBurnSubtitles(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
                />
                <span>Burn-in Subtitle Kinetik ke Video</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-neutral-300">
                <input
                  type="checkbox"
                  checked={includeMetadata}
                  onChange={(e) => setIncludeMetadata(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
                />
                <span>Sertakan File Caption & Tagar (.txt)</span>
              </label>
            </div>
          </div>

          {/* EXPORT PROGRESS / STATUS */}
          {isExporting && (
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 animate-pulse">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-amber-400">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>{exportStage}</span>
                </div>
                <span className="font-mono font-bold text-white">{exportProgress}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-800">
                <div 
                  className="h-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-300"
                  style={{ width: `${exportProgress}%` }}
                />
              </div>
            </div>
          )}

          {exportCompleted && (
            <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500 text-black">
                  <CheckCircle2 className="h-6 w-6 stroke-[2.5]" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Semua Video Siap Diunduh!</h4>
                  <p className="text-neutral-300 text-[11px]">
                    {selectedClipIds.length} klip video telah di-render dengan format {selectedPlatforms.join(', ')}.
                  </p>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* FOOTER ACTIONS */}
        <div className="flex items-center justify-between border-t border-neutral-800 bg-neutral-950 px-6 py-4">
          <div className="text-neutral-400 text-[11px]">
            Estimasi Ukuran: <strong className="text-neutral-200">~{(selectedClipIds.length * 18.5).toFixed(1)} MB</strong>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="rounded-xl border border-neutral-800 bg-neutral-900 px-4 py-2 text-xs font-semibold text-neutral-300 hover:bg-neutral-800 hover:text-white"
            >
              Tutup
            </button>

            {exportCompleted ? (
              <button
                onClick={handleDownloadZip}
                className="flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2 text-xs font-extrabold text-black shadow-lg shadow-emerald-500/20 hover:bg-emerald-400"
              >
                <Download className="h-4 w-4" />
                <span>Unduh Paket ZIP ({selectedClipIds.length} Video)</span>
              </button>
            ) : (
              <button
                onClick={handleStartExport}
                disabled={isExporting || selectedClipIds.length === 0}
                className={`flex items-center gap-2 rounded-xl px-6 py-2 text-xs font-extrabold transition-all ${
                  isExporting
                    ? 'cursor-wait bg-neutral-800 text-neutral-500'
                    : 'bg-gradient-to-r from-amber-500 to-orange-500 text-black shadow-lg shadow-orange-500/20 hover:from-amber-400 hover:to-orange-400'
                }`}
              >
                <Sparkles className="h-4 w-4 fill-black" />
                <span>{isExporting ? 'Merender...' : `Mulai Ekspor Otomatis (${selectedClipIds.length} Klip)`}</span>
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
