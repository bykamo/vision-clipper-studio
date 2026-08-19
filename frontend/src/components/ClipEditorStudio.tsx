import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Volume2, 
  VolumeX, 
  Maximize2, 
  Smartphone, 
  Square, 
  Tv, 
  Flame, 
  Sparkles, 
  Copy, 
  Check, 
  Scissors, 
  Clock, 
  Type, 
  Share2, 
  CheckCircle2, 
  Smile, 
  Palette, 
  Layers,
  ChevronRight,
  Eye,
  Sliders,
  ShieldCheck
} from 'lucide-react';
import { GeneratedClip, SubtitleStyleConfig, AspectRatio, SocialPlatformId, SubtitleWord } from '../types';

interface ClipEditorStudioProps {
  clips: GeneratedClip[];
  activeClipId: string;
  onSelectClip: (clipId: string) => void;
  subtitleConfig: SubtitleStyleConfig;
  onUpdateSubtitleConfig: (config: SubtitleStyleConfig) => void;
  onOpenExportModal: (clipToExport?: GeneratedClip) => void;
}

export const ClipEditorStudio: React.FC<ClipEditorStudioProps> = ({
  clips,
  activeClipId,
  onSelectClip,
  subtitleConfig,
  onUpdateSubtitleConfig,
  onOpenExportModal
}) => {
  const activeClip = clips.find(c => c.id === activeClipId) || clips[0];
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0); // in seconds relative to clip start
  const [isMuted, setIsMuted] = useState(false);
  const [showSafeZone, setShowSafeZone] = useState(true);
  const [previewAspect, setPreviewAspect] = useState<AspectRatio>(activeClip?.aspectRatio || '9:16');
  const [selectedSocialTab, setSelectedSocialTab] = useState<SocialPlatformId>('tiktok');
  const [copiedCaption, setCopiedCaption] = useState(false);
  const [activeTab, setActiveTab] = useState<'subtitles' | 'social_copy' | 'style_quick'>('subtitles');

  // Video element ref
  const videoRef = useRef<HTMLVideoElement>(null);
  const duration = activeClip ? activeClip.duration : 30;

  // Auto loop/tick playback
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentTime(prev => {
          if (prev >= duration) {
            return 0; // loop
          }
          return prev + 0.1;
        });
      }, 100);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isPlaying, duration]);

  // Keep previewAspect in sync if clip changes
  useEffect(() => {
    if (activeClip) {
      setPreviewAspect(activeClip.aspectRatio);
      setCurrentTime(0);
      setIsPlaying(false);
    }
  }, [activeClipId]);

  if (!activeClip) {
    return (
      <div className="flex h-96 flex-col items-center justify-center rounded-2xl border border-neutral-800 bg-neutral-900/60 p-8 text-center text-neutral-400">
        <Scissors className="mb-3 h-10 w-10 text-neutral-600" />
        <h3 className="text-sm font-bold text-white">Belum Ada Klip yang Digenerate</h3>
        <p className="mt-1 text-xs">Jalankan proses AI Clipper di tab "Generate & Konfigurasi" terlebih dahulu.</p>
      </div>
    );
  }

  // Active Subtitle Line for current time
  const currentSubLine = activeClip.subtitles.find(
    s => currentTime >= s.start && currentTime <= s.end
  );

  const handleTogglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleCopySocialCaption = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCaption(true);
    setTimeout(() => setCopiedCaption(false), 2000);
  };

  const handleWordClick = (wordObj: SubtitleWord) => {
    // Toggle word highlight
    wordObj.highlight = !wordObj.highlight;
    // Force rerender by triggering small state change
    setCurrentTime(prev => prev + 0.001);
  };

  return (
    <div id="clip-editor-studio" className="space-y-6">
      
      {/* CLIP TABS SELECTOR */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
        {clips.map((clip, idx) => {
          const isCurrent = clip.id === activeClip.id;
          return (
            <button
              key={clip.id}
              id={`clip-tab-${clip.id}`}
              onClick={() => onSelectClip(clip.id)}
              className={`flex flex-shrink-0 items-center gap-3 rounded-xl border p-2.5 text-left transition-all ${
                isCurrent
                  ? 'border-amber-500 bg-amber-500/10 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500'
                  : 'border-neutral-800 bg-neutral-900/80 hover:border-neutral-700 hover:bg-neutral-800/60'
              }`}
            >
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg font-mono text-xs font-black ${
                isCurrent ? 'bg-amber-500 text-black' : 'bg-neutral-800 text-neutral-300'
              }`}>
                #{idx + 1}
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-neutral-100 line-clamp-1 max-w-[170px]">
                    {clip.title}
                  </span>
                  <span className="flex items-center gap-0.5 rounded bg-orange-500/20 px-1.5 py-0.2 text-[10px] font-black text-orange-400 border border-orange-500/30">
                    <Flame className="h-2.5 w-2.5 fill-orange-400" />
                    {clip.viralityScore}
                  </span>
                </div>
                <div className="text-[11px] text-neutral-400">
                  Durasi: {clip.duration}s • {clip.subtitles.length} Subtitle
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* MAIN STUDIO GRID */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        
        {/* LEFT / CENTER: VIDEO CANVAS PREVIEW (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          
          <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4 shadow-xl">
            
            {/* Viewport Header Controls */}
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white">Pratinjau Output Video:</span>
                <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-400 border border-amber-500/20">
                  {subtitleConfig.name}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {/* Safe Zone Toggle */}
                <button
                  id="btn-toggle-safezone"
                  onClick={() => setShowSafeZone(!showSafeZone)}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                    showSafeZone 
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' 
                      : 'bg-neutral-800 text-neutral-400 hover:text-white'
                  }`}
                  title="Tampilkan area aman UI TikTok / Instagram Reels"
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Safe Zone {showSafeZone ? 'ON' : 'OFF'}</span>
                </button>

                {/* Aspect Switcher */}
                <div className="flex rounded-lg border border-neutral-800 bg-neutral-950 p-0.5">
                  {(['9:16', '1:1', '4:5', '16:9'] as const).map(asp => (
                    <button
                      key={asp}
                      onClick={() => setPreviewAspect(asp)}
                      className={`px-2 py-0.5 text-[10px] font-bold transition-all rounded ${
                        previewAspect === asp ? 'bg-amber-500 text-black' : 'text-neutral-400 hover:text-white'
                      }`}
                    >
                      {asp}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* SIMULATED VERTICAL / SQUARE VIDEO CONTAINER */}
            <div className="relative mx-auto flex items-center justify-center overflow-hidden rounded-xl bg-neutral-950 border border-neutral-800 min-h-[460px] max-h-[560px]">
              
              {/* Aspect Ratio Frame Wrapper */}
              <div 
                className={`relative flex items-center justify-center overflow-hidden bg-neutral-900 transition-all duration-300 ${
                  previewAspect === '9:16' ? 'w-[290px] h-[515px]' :
                  previewAspect === '1:1' ? 'w-[400px] h-[400px]' :
                  previewAspect === '4:5' ? 'w-[340px] h-[425px]' :
                  'w-full max-w-[560px] h-[315px]'
                }`}
              >
                {/* Background Video Simulation / Image Visual */}
                <div className="absolute inset-0 bg-gradient-to-br from-neutral-900 via-neutral-800 to-stone-900">
                  {/* Dynamic Gradient / Speaker simulation graphics */}
                  <div className="absolute inset-0 opacity-40 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-amber-600/30 via-transparent to-black" />
                  
                  {/* Mock Speaker Visual Avatar / Stage */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <div className="relative mb-3 flex h-24 w-24 items-center justify-center rounded-full bg-neutral-800/80 border-2 border-amber-500/40 shadow-2xl shadow-amber-500/20">
                      <span className="font-['Outfit'] text-2xl font-black text-amber-400">
                        {activeClip.speakerName ? activeClip.speakerName.split(' ')[0][0] : 'AI'}
                      </span>
                      {isPlaying && (
                        <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex h-4 w-4 rounded-full bg-emerald-500"></span>
                        </span>
                      )}
                    </div>
                    <span className="rounded-full bg-black/60 px-3 py-1 text-[11px] font-bold text-neutral-200 backdrop-blur-md">
                      {activeClip.speakerName || 'Speaker'} • Face Tracked
                    </span>
                  </div>
                </div>

                {/* TIKTOK / REELS SAFE ZONE OVERLAYS */}
                {showSafeZone && previewAspect === '9:16' && (
                  <div className="pointer-events-none absolute inset-0 z-20">
                    {/* Top safe zone (Status bar) */}
                    <div className="absolute top-0 inset-x-0 h-10 border-b border-rose-500/20 bg-rose-500/5 px-2 pt-1 text-[9px] text-rose-400/60 flex justify-between">
                      <span>Header / Search bar safe zone</span>
                    </div>

                    {/* Right side interactions (Like, Comment, Share, Sound) */}
                    <div className="absolute right-2 bottom-20 flex flex-col items-center gap-3">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-black/50 text-[10px] text-white/70">❤️</div>
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-black/50 text-[10px] text-white/70">💬</div>
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-black/50 text-[10px] text-white/70">🔄</div>
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-black/50 text-[10px] text-white/70">🎵</div>
                    </div>

                    {/* Bottom username & audio caption safe zone */}
                    <div className="absolute bottom-0 inset-x-0 h-20 border-t border-rose-500/20 bg-rose-500/5 p-2 text-[9px] text-rose-400/60">
                      <span>@username • caption & audio safe zone</span>
                    </div>
                  </div>
                )}

                {/* DYNAMIC KINETIC SUBTITLE OVERLAY */}
                {currentSubLine && (
                  <div 
                    className="absolute inset-x-4 z-30 flex flex-col items-center justify-center text-center transition-all duration-150"
                    style={{
                      bottom: `${subtitleConfig.positionY}%`
                    }}
                  >
                    <div
                      className="inline-flex flex-wrap items-center justify-center gap-1.5 px-3 py-1.5"
                      style={{
                        fontFamily: subtitleConfig.fontFamily,
                        backgroundColor: subtitleConfig.backgroundBox ? subtitleConfig.backgroundColor : 'transparent',
                        borderRadius: subtitleConfig.backgroundBox ? '10px' : '0',
                      }}
                    >
                      {currentSubLine.words.map((w, wIdx) => {
                        const isWordActive = currentTime >= (currentSubLine.start + w.start) && currentTime <= (currentSubLine.start + w.end);
                        const isHighlighted = w.highlight || isWordActive;
                        
                        return (
                          <span
                            key={wIdx}
                            onClick={() => handleWordClick(w)}
                            className={`cursor-pointer transition-all duration-100 select-none ${
                              isWordActive && subtitleConfig.animationType === 'bounce' ? 'scale-125 -translate-y-1' :
                              isWordActive && subtitleConfig.animationType === 'word_pop' ? 'scale-115' :
                              isWordActive && subtitleConfig.animationType === 'glow_pulse' ? 'scale-110 drop-shadow-[0_0_12px_#38bdf8]' :
                              ''
                            }`}
                            style={{
                              fontSize: `${subtitleConfig.fontSize}px`,
                              color: isHighlighted ? subtitleConfig.highlightColor : subtitleConfig.primaryColor,
                              fontWeight: 900,
                              textTransform: subtitleConfig.allCaps ? 'uppercase' : 'none',
                              WebkitTextStroke: subtitleConfig.strokeWidth > 0 ? `${subtitleConfig.strokeWidth / 2}px ${subtitleConfig.strokeColor}` : 'none',
                              textShadow: subtitleConfig.shadow ? '0 2px 6px rgba(0,0,0,0.9)' : 'none',
                              padding: '0 2px'
                            }}
                          >
                            {w.word}
                            {subtitleConfig.showEmoji && w.emoji && (
                              <span className="ml-1 inline-block animate-bounce">{w.emoji}</span>
                            )}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

              </div>
            </div>

            {/* PLAYBACK CONTROLS & SCRUBBER */}
            <div className="mt-4 rounded-xl border border-neutral-800 bg-neutral-950 p-3">
              {/* Scrub Bar */}
              <div className="mb-2 flex items-center gap-3">
                <input
                  type="range"
                  min="0"
                  max={duration}
                  step="0.1"
                  value={currentTime}
                  onChange={(e) => {
                    setCurrentTime(parseFloat(e.target.value));
                    if (isPlaying) setIsPlaying(false);
                  }}
                  className="h-2 w-full appearance-none rounded-lg bg-neutral-800 accent-amber-500 cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    id="btn-play-pause"
                    onClick={handleTogglePlay}
                    className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500 text-neutral-950 font-bold shadow-md hover:bg-amber-400"
                  >
                    {isPlaying ? <Pause className="h-4 w-4 fill-black" /> : <Play className="h-4 w-4 fill-black ml-0.5" />}
                  </button>

                  <button
                    onClick={() => setCurrentTime(0)}
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-400 hover:bg-neutral-800 hover:text-white"
                    title="Ulangi dari Awal"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </button>

                  <div className="ml-2 font-mono text-xs text-neutral-300">
                    <span className="text-amber-400 font-bold">{currentTime.toFixed(1)}s</span>
                    <span className="text-neutral-500"> / {duration}s</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsMuted(!isMuted)}
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-400 hover:bg-neutral-800 hover:text-white"
                  >
                    {isMuted ? <VolumeX className="h-4 w-4 text-rose-400" /> : <Volume2 className="h-4 w-4" />}
                  </button>

                  <button
                    onClick={() => onOpenExportModal(activeClip)}
                    className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 px-3.5 py-1.5 text-xs font-extrabold text-neutral-950 shadow-md hover:from-amber-400 hover:to-orange-400"
                  >
                    <Share2 className="h-3.5 w-3.5" />
                    <span>Ekspor Klip Ini</span>
                  </button>
                </div>
              </div>
            </div>

          </div>

        </div>

        {/* RIGHT: SUBTITLE EDITOR & SOCIAL CAPTIONS TABS (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Virality Hook Analysis Card */}
          <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4 shadow-xl">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Flame className="h-4 w-4 text-orange-500" />
                <span className="text-xs font-bold text-white">AI Hook & Virality Rationale:</span>
              </div>
              <span className="rounded-full bg-orange-500/20 px-2.5 py-0.5 text-xs font-black text-orange-400 border border-orange-500/30">
                Score {activeClip.viralityScore}/100
              </span>
            </div>
            <p className="text-xs text-neutral-300 font-medium bg-neutral-950 p-2.5 rounded-xl border border-neutral-800">
              "{activeClip.viralityRationale}"
            </p>
          </div>

          {/* TAB BAR FOR RIGHT PANEL */}
          <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4 shadow-xl">
            
            <div className="mb-4 flex rounded-xl border border-neutral-800 bg-neutral-950 p-1">
              <button
                onClick={() => setActiveTab('subtitles')}
                className={`flex-1 rounded-lg py-1.5 text-xs font-bold transition-all ${
                  activeTab === 'subtitles' ? 'bg-amber-500 text-black' : 'text-neutral-400 hover:text-white'
                }`}
              >
                Transkrip Subtitle
              </button>
              <button
                onClick={() => setActiveTab('social_copy')}
                className={`flex-1 rounded-lg py-1.5 text-xs font-bold transition-all ${
                  activeTab === 'social_copy' ? 'bg-amber-500 text-black' : 'text-neutral-400 hover:text-white'
                }`}
              >
                Caption & Tagar Sosmed
              </button>
              <button
                onClick={() => setActiveTab('style_quick')}
                className={`flex-1 rounded-lg py-1.5 text-xs font-bold transition-all ${
                  activeTab === 'style_quick' ? 'bg-amber-500 text-black' : 'text-neutral-400 hover:text-white'
                }`}
              >
                Gaya Teks
              </button>
            </div>

            {/* TAB 1: SUBTITLE TRANSCRIPT LIST */}
            {activeTab === 'subtitles' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-[11px] text-neutral-400">
                  <span>Klik baris untuk melompat ke timestamp. Klik kata untuk highlight.</span>
                  <span className="text-amber-400 font-bold">{activeClip.subtitles.length} baris</span>
                </div>

                <div className="max-h-[380px] space-y-2.5 overflow-y-auto pr-1">
                  {activeClip.subtitles.map((sub, idx) => {
                    const isCurrent = currentTime >= sub.start && currentTime <= sub.end;
                    return (
                      <div
                        key={sub.id}
                        onClick={() => setCurrentTime(sub.start)}
                        className={`cursor-pointer rounded-xl border p-3 transition-all ${
                          isCurrent
                            ? 'border-amber-500 bg-amber-500/10 shadow-md ring-1 ring-amber-500'
                            : 'border-neutral-800 bg-neutral-950 hover:border-neutral-700'
                        }`}
                      >
                        <div className="mb-1.5 flex items-center justify-between">
                          <span className="font-mono text-[10px] text-neutral-500">
                            {sub.start.toFixed(1)}s - {sub.end.toFixed(1)}s
                          </span>
                          {isCurrent && (
                            <span className="rounded bg-amber-500 px-1.5 py-0.2 text-[9px] font-black text-black">
                              PLAYING
                            </span>
                          )}
                        </div>

                        {/* Words Tokens */}
                        <div className="flex flex-wrap gap-1.5">
                          {sub.words.map((w, wIdx) => (
                            <button
                              key={wIdx}
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleWordClick(w);
                              }}
                              className={`rounded px-1.5 py-0.5 text-xs font-bold transition-all ${
                                w.highlight
                                  ? 'bg-amber-400 text-black shadow'
                                  : 'bg-neutral-800 text-neutral-200 hover:bg-neutral-700'
                              }`}
                            >
                              {w.word}
                              {w.emoji && <span className="ml-1">{w.emoji}</span>}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* TAB 2: SOCIAL MEDIA CAPTIONS & HASHTAGS */}
            {activeTab === 'social_copy' && (
              <div className="space-y-4">
                
                {/* Platform selector */}
                <div className="grid grid-cols-5 gap-1">
                  {(['tiktok', 'instagram', 'youtube_shorts', 'twitter', 'linkedin'] as const).map(plat => (
                    <button
                      key={plat}
                      onClick={() => setSelectedSocialTab(plat)}
                      className={`rounded-lg py-1.5 text-[10px] font-bold uppercase transition-all ${
                        selectedSocialTab === plat
                          ? 'bg-amber-500 text-black shadow'
                          : 'border border-neutral-800 bg-neutral-950 text-neutral-400 hover:text-white'
                      }`}
                    >
                      {plat === 'youtube_shorts' ? 'Shorts' : plat}
                    </button>
                  ))}
                </div>

                {/* Content Box */}
                {activeClip.socialMetadata[selectedSocialTab] && (
                  <div className="space-y-3 rounded-xl border border-neutral-800 bg-neutral-950 p-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white capitalize">
                        Preset Metadata {selectedSocialTab.replace('_', ' ')}
                      </span>
                      <button
                        onClick={() => {
                          const meta = activeClip.socialMetadata[selectedSocialTab];
                          const copyText = `${meta.caption}\n\n${meta.hashtags.join(' ')}`;
                          handleCopySocialCaption(copyText);
                        }}
                        className="flex items-center gap-1 rounded bg-neutral-800 px-2 py-1 text-[10px] font-bold text-neutral-200 hover:bg-neutral-700 hover:text-white"
                      >
                        {copiedCaption ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        <span>{copiedCaption ? 'Tersalin!' : 'Salin Semua'}</span>
                      </button>
                    </div>

                    {activeClip.socialMetadata[selectedSocialTab].title && (
                      <div>
                        <label className="text-[10px] text-neutral-500 font-bold uppercase">Judul Video</label>
                        <p className="text-xs font-semibold text-neutral-200">
                          {activeClip.socialMetadata[selectedSocialTab].title}
                        </p>
                      </div>
                    )}

                    <div>
                      <label className="text-[10px] text-neutral-500 font-bold uppercase">Deskripsi & Caption</label>
                      <p className="text-xs text-neutral-300 leading-relaxed">
                        {activeClip.socialMetadata[selectedSocialTab].caption}
                      </p>
                    </div>

                    <div>
                      <label className="text-[10px] text-neutral-500 font-bold uppercase">Tagar Rekomendasi AI</label>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {activeClip.socialMetadata[selectedSocialTab].hashtags.map(t => (
                          <span key={t} className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-400 border border-amber-500/20">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

              </div>
            )}

            {/* TAB 3: QUICK STYLE ADJUSTMENTS */}
            {activeTab === 'style_quick' && (
              <div className="space-y-4 text-xs">
                <div>
                  <label className="mb-1.5 block font-bold text-neutral-300">Warna Highlight Aktif:</label>
                  <div className="flex gap-2">
                    {['#FACC15', '#4ADE80', '#38BDF8', '#F43F5E', '#C084FC'].map(hex => (
                      <button
                        key={hex}
                        onClick={() => onUpdateSubtitleConfig({ ...subtitleConfig, highlightColor: hex })}
                        className={`h-7 w-7 rounded-full border-2 transition-all ${
                          subtitleConfig.highlightColor === hex ? 'border-white scale-110' : 'border-transparent'
                        }`}
                        style={{ backgroundColor: hex }}
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <div className="mb-1 flex justify-between text-[11px] text-neutral-400">
                    <span>Posisi Subtitle (Y%):</span>
                    <span className="font-bold text-amber-400">{subtitleConfig.positionY}%</span>
                  </div>
                  <input
                    type="range"
                    min="15"
                    max="45"
                    value={subtitleConfig.positionY}
                    onChange={(e) => onUpdateSubtitleConfig({ ...subtitleConfig, positionY: parseInt(e.target.value) })}
                    className="h-1.5 w-full appearance-none rounded-lg bg-neutral-800 accent-amber-500"
                  />
                </div>

                <div className="flex items-center justify-between border-t border-neutral-800 pt-3">
                  <span>Emoji Otomatis:</span>
                  <button
                    onClick={() => onUpdateSubtitleConfig({ ...subtitleConfig, showEmoji: !subtitleConfig.showEmoji })}
                    className={`rounded-lg px-3 py-1 text-xs font-bold ${
                      subtitleConfig.showEmoji ? 'bg-amber-500 text-black' : 'bg-neutral-800 text-neutral-400'
                    }`}
                  >
                    {subtitleConfig.showEmoji ? 'AKTIF' : 'NONAKTIF'}
                  </button>
                </div>
              </div>
            )}

          </div>

        </div>

      </div>

    </div>
  );
};
