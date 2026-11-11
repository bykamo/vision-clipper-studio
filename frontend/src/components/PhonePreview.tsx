import React, { useState, useRef, useEffect } from 'react';
import {
  PlayIcon,
  PauseIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
} from '@heroicons/react/24/solid';
import type { SmartCropTrajectory } from '../types';

/** Satu kata transkrip (detik absolut terhadap file video sumber). */
export interface PreviewWord {
  word: string;
  start: number;
  end: number;
}

interface PhonePreviewProps {
  framingMode: 'smart_crop' | 'fit_blur' | 'split_screen';
  selectedPresetId: string;
  videoSource?: string;
  previewClip?: { start: number; end: number } | null;
  clipTitle?: string;
  /** Kata-kata transkrip di dalam klip yang sedang dipreview (sinkron dengan video). */
  clipWords?: PreviewWord[];
  /** Trajektori smart crop (sama dengan render) bila framing smart_crop aktif. */
  smartCropTrajectory?: SmartCropTrajectory | null;
  isRenderedClip?: boolean;
  isProcessing?: boolean;
  subPosition?: number;
  watermarkEnabled?: boolean;
  sourceWatermark?: string;
  accountWatermark?: string;
}

export const PhonePreview: React.FC<PhonePreviewProps> = ({
  framingMode,
  selectedPresetId,
  videoSource,
  previewClip,
  clipTitle,
  clipWords,
  smartCropTrajectory,
  isRenderedClip = false,
  isProcessing = false,
  subPosition = 68,
  watermarkEnabled = true,
  sourceWatermark = '',
  accountWatermark = '',
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [hasLoadedMetadata, setHasLoadedMetadata] = useState(false);
  const [mediaError, setMediaError] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [showPlayPulse, setShowPlayPulse] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  // Panel kedua untuk mode Dual Stack (split_screen): menampilkan sisi kanan
  // video sambil mengikuti waktu & status putar panel utama.
  const secondaryVideoRef = useRef<HTMLVideoElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  // Container layar konten (tempat video dirender) untuk menghitung skala crop.
  const screenContentRef = useRef<HTMLDivElement | null>(null);
  // Tracks whether the current mute state was forced by the browser autoplay
  // policy (not an explicit user choice). When true, the first user gesture
  // should restore sound instead of toggling playback.
  const autoplayMutedRef = useRef(false);
  const [scale, setScale] = useState<number>(0.62);
  const [screenContentWidth, setScreenContentWidth] = useState<number>(0);

  // Dynamically calculate scale factor to fit exactly within the available preview column stage
  useEffect(() => {
    const updateScale = () => {
      if (!stageRef.current) return;
      const rect = stageRef.current.getBoundingClientRect();
      const availW = Math.max(100, rect.width - 8);
      const availH = Math.max(100, rect.height - 8);
      const sX = availW / 389;
      const sY = availH / 800;
      const nextScale = Math.min(sX, sY);
      const clamped = Math.max(0.35, Math.min(1, Number(nextScale.toFixed(3))));
      setScale(clamped);
    };

    updateScale();

    const observer = new ResizeObserver(() => {
      updateScale();
    });

    if (stageRef.current) {
      observer.observe(stageRef.current);
    }

    window.addEventListener('resize', updateScale);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', updateScale);
    };
  }, []);

  // Lebar layar konten (px CSS, BELUM kena transform scale) dipakai untuk
  // menghitung ukuran video saat smart crop aktif. Screen-nya fixed 356px.
  // PENTING: pakai offsetWidth (bukan getBoundingClientRect) karena lebar
  // getBoundingClientRect sudah menyertakan transform scale dari wrapper
  // iPhone (mis. 356 * 0.62 = 221px), sedangkan style video ditulis dalam
  // koordinat lokal sebelum di-scale. Mencampur keduanya membuat video jadi
  // lebih kecil / melenceng dari layar (preview terlihat "hancur").
  useEffect(() => {
    const el = screenContentRef.current;
    if (!el) return;
    const measure = () => setScreenContentWidth(el.offsetWidth || 0);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Check if source is a local playable video file path
  const isLocalFile = Boolean(
    videoSource && !videoSource.startsWith('http://') && !videoSource.startsWith('https://'),
  );
  const videoStreamUrl =
    isLocalFile && videoSource
      ? `/api/video-stream?path=${encodeURIComponent(videoSource.trim())}`
      : '';

  // Attempts to start playback with sound. If the browser blocks audible
  // autoplay (no user gesture yet), it falls back to muted playback and marks
  // the mute as "forced" so the next user gesture can restore sound.
  const startPlayback = (video: HTMLVideoElement, withSound: boolean) => {
    video.muted = withSound ? false : true;
    if (withSound) video.volume = 1;
    return video
      .play()
      .then(() => {
        setIsPlaying(true);
        if (withSound) {
          setIsMuted(false);
          autoplayMutedRef.current = false;
        }
        return true;
      })
      .catch(() => {
        if (withSound) {
          // Browser blocked audible autoplay -> retry muted.
          video.muted = true;
          autoplayMutedRef.current = true;
          setIsMuted(true);
          return video
            .play()
            .then(() => {
              setIsPlaying(true);
              return true;
            })
            .catch(() => {
              setIsPlaying(false);
              return false;
            });
        }
        setIsPlaying(false);
        return false;
      });
  };

  // Auto-seek and loop within clip range when previewClip is set or when switching to rendered clip
  useEffect(() => {
    if (!videoRef.current || !videoStreamUrl) return;

    if (isRenderedClip) {
      videoRef.current.currentTime = 0;
      void startPlayback(videoRef.current, !isMuted);
    } else if (previewClip) {
      videoRef.current.currentTime = previewClip.start;
      void startPlayback(videoRef.current, !isMuted);
    }
    // `isMuted` is intentionally excluded: it is only the *initial* mute state
    // for a newly loaded source. Re-running on mute changes would re-seek the
    // video back to the clip start every time the user taps the mute button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewClip?.start, previewClip?.end, videoStreamUrl, isRenderedClip]);

  // Enforce clip end boundary
  const handleTimeUpdateWithClip = () => {
    handleTimeUpdate();
    if (isRenderedClip) return;
    if (previewClip && videoRef.current) {
      if (videoRef.current.currentTime >= previewClip.end) {
        videoRef.current.currentTime = previewClip.start;
      }
    }
  };

  // Reset transport readout whenever the source changes so the bar clearly
  // falls back to the "no playback" state until new metadata arrives.
  // Adjusting state during render (instead of in an effect) avoids a frame
  // where the old timecode is still shown against the new source.
  const [prevStreamUrl, setPrevStreamUrl] = useState(videoStreamUrl);
  if (prevStreamUrl !== videoStreamUrl) {
    setPrevStreamUrl(videoStreamUrl);
    setCurrentTime(0);
    setDuration(0);
    setHasLoadedMetadata(false);
    setMediaError(false);
    setIsPlaying(false);
  }

  // Ref writes must not happen during render, so clear the autoplay-forced mute
  // flag in an effect that also fires when the source changes.
  useEffect(() => {
    autoplayMutedRef.current = false;
  }, [videoStreamUrl]);

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || 0);
      setHasLoadedMetadata(true);
      setMediaError(false);
      // Respect any browser-forced autoplay mute; otherwise sync with user state.
      videoRef.current.muted = autoplayMutedRef.current ? true : isMuted;
      videoRef.current.volume = 1;
      if (isRenderedClip) {
        videoRef.current.currentTime = 0;
      } else if (previewClip) {
        videoRef.current.currentTime = previewClip.start;
      }
    }
  };

  // A failed stream (missing file / unsupported codec) also counts as "no playback".
  const handleMediaError = () => {
    setMediaError(true);
    setHasLoadedMetadata(false);
    setDuration(0);
    setCurrentTime(0);
    setIsPlaying(false);
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime || 0);
    }
  };

  // ── SMART CROP LIVE PREVIEW ──
  // Aktif hanya saat framing smart_crop, ada klip range (belum rendered), dan
  // trajektori sudah ter-fetch. Posisi frame dihitung dari waktu klip-relatif.
  const smartCropActive =
    framingMode === 'smart_crop' &&
    !isRenderedClip &&
    Boolean(previewClip) &&
    Boolean(smartCropTrajectory) &&
    (smartCropTrajectory?.positions?.length ?? 0) > 0;

  const smartCropFrameIndex = (() => {
    if (!smartCropActive || !previewClip || !smartCropTrajectory) return 0;
    const tc = (currentTime || 0) - previewClip.start;
    const fps = smartCropTrajectory.fps || 30;
    const idx = Math.round(tc * fps);
    const maxIndex = smartCropTrajectory.positions.length - 1;
    return Math.max(0, Math.min(maxIndex, idx));
  })();

  // Style video eksplisit: skala video sumber ke crop 9:16 lalu geser kiri/atas
  // mengikuti `positions[frame]`. Menggantikan `object-cover` center statis.
  const smartCropVideoStyle = (() => {
    if (!smartCropActive || !smartCropTrajectory) return null;
    const { orig_w, orig_h, crop_w, crop_h, crop_y, positions } = smartCropTrajectory;
    const containerW = screenContentWidth || 356;
    // Layar konten iPhone: lebar 356, tinggi 772. Gunakan rasio fixed bila tinggi belum terukur.
    const containerH = containerW * (772 / 356);
    // Cover-scale: crop 9:16 diisi penuh ke layar (tinggi layar dominan lebih sempit).
    const s = Math.max(containerW / crop_w, containerH / crop_h);
    const x = (positions[smartCropFrameIndex] ?? 0) * s;
    const y = crop_y * s;
    return {
      position: 'absolute' as const,
      top: `${-y}px`,
      left: `${-x}px`,
      width: `${orig_w * s}px`,
      height: `${orig_h * s}px`,
      // Tailwind preflight menetapkan `video { max-width: 100% }`, yang akan
      // membatasi width eksplisit kita ke lebar layar (356px) padahal height
      // tetap skala penuh -> video jadi sempit & melenceng. Nonaktifkan.
      maxWidth: 'none',
    };
  })();

  // Panel kedua (mode Dual Stack) mengikuti panel utama: waktu, play/pause,
  // dan selalu tanpa suara supaya tidak ada audio ganda.
  useEffect(() => {
    const secondary = secondaryVideoRef.current;
    const primary = videoRef.current;
    if (!secondary || !primary) return;
    if (Math.abs((secondary.currentTime || 0) - (primary.currentTime || 0)) > 0.15) {
      try {
        secondary.currentTime = primary.currentTime;
      } catch {
        // metadata belum siap
      }
    }
    if (primary.paused && !secondary.paused) secondary.pause();
    if (!primary.paused && secondary.paused) void secondary.play().catch(() => undefined);
  }, [currentTime, isPlaying, framingMode]);

  const togglePlay = async () => {
    const video = videoRef.current;
    if (!video) return;

    setShowPlayPulse(true);
    setTimeout(() => setShowPlayPulse(false), 500);

    // Already playing but silent only because of the autoplay policy:
    // this user gesture should simply restore sound, not pause.
    if (!video.paused && autoplayMutedRef.current) {
      video.muted = false;
      video.volume = 1.0;
      autoplayMutedRef.current = false;
      setIsMuted(false);
      return;
    }

    if (video.paused) {
      // A click/keypress is a user gesture, so browsers allow audible playback.
      // If the mute was only forced by the autoplay policy, try to restore sound.
      const wantSound = !isMuted || autoplayMutedRef.current;
      try {
        video.muted = !wantSound;
        if (wantSound) {
          video.volume = 1.0;
          autoplayMutedRef.current = false;
        }
        await video.play();
        setIsMuted(!wantSound);
        setIsPlaying(true);
      } catch {
        try {
          video.muted = true;
          autoplayMutedRef.current = true;
          setIsMuted(true);
          await video.play();
          setIsPlaying(true);
        } catch {
          setIsPlaying(false);
        }
      }
      return;
    }

    video.pause();
    setIsPlaying(false);
  };

  const handlePreviewKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    void togglePlay();
  };

  const handleSeek = (time: number) => {
    const video = videoRef.current;
    // Ignore seeks while there is no playback source / metadata yet.
    if (!video || !hasLoadedMetadata) return;

    // The transport timeline is clip-relative while a clip range is being previewed.
    const offset = previewClip && !isRenderedClip ? previewClip.start : 0;
    const absolute = offset + time;
    const nextTime = previewClip
      ? Math.min(previewClip.end, Math.max(previewClip.start, absolute))
      : absolute;

    setCurrentTime(nextTime);
    video.currentTime = nextTime;
    if (secondaryVideoRef.current) {
      try {
        secondaryVideoRef.current.currentTime = nextTime;
      } catch {
        // metadata belum siap
      }
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const nextMuted = !videoRef.current.muted;
    videoRef.current.muted = nextMuted;
    if (!nextMuted) {
      videoRef.current.volume = 1.0;
      autoplayMutedRef.current = false;
    }
    setIsMuted(nextMuted);
  };

  const handleRateChange = () => {
    const nextRate = playbackRate === 1.0 ? 1.5 : playbackRate === 1.5 ? 2.0 : 1.0;
    setPlaybackRate(nextRate);
    if (videoRef.current) {
      videoRef.current.playbackRate = nextRate;
    }
  };

  // ── SUBTITLE PREVIEW (teks transkrip asli, sinkron dengan posisi video) ──
  // Batas kata/karakter per gaya harus sama dengan backend (STYLE_CHUNK_LIMITS)
  // supaya preview benar-benar mencerminkan hasil render (aturan CapCut: frasa 3-4 kata horizontal).
  const SUBTITLE_LIMITS: Record<string, { maxWords: number; maxChars: number }> = {
    tiktok_viral: { maxWords: 4, maxChars: 22 },
    classic_karaoke: { maxWords: 4, maxChars: 22 },
    minimalist: { maxWords: 5, maxChars: 24 },
    word_pop: { maxWords: 1, maxChars: 12 },
  };

  /** Indeks kata yang sedang diucapkan pada `time` (detik absolut). */
  const findActiveWordIndex = (time: number) => {
    if (!clipWords || clipWords.length === 0) return -1;
    for (let i = 0; i < clipWords.length; i += 1) {
      const w = clipWords[i];
      if (time >= w.start && time < w.end) return i;
    }
    // Di antara dua kata (jeda hening): tahan kata terakhir yang sudah lewat.
    let last = -1;
    for (let i = 0; i < clipWords.length; i += 1) {
      if (clipWords[i].start <= time) last = i;
      else break;
    }
    return last;
  };

  /** Potong transkrip jadi chunk tampilan, sama seperti backend `_chunk_words`. */
  const chunkWords = (words: PreviewWord[], maxWords: number, maxChars: number) => {
    const chunks: PreviewWord[][] = [];
    let current: PreviewWord[] = [];
    let currentLen = 0;
    for (const w of words) {
      const text = w.word.trim();
      if (!text) continue;
      const projected = currentLen + text.length + (current.length ? 1 : 0);
      if (current.length && (current.length >= maxWords || projected > maxChars)) {
        chunks.push(current);
        current = [];
        currentLen = 0;
      }
      current.push({ ...w, word: text });
      currentLen += text.length + (current.length > 1 ? 1 : 0);
      // Hard sentence break on .?!, but for commas only break if the phrase already has >= 3 words
      // so it never creates tiny awkward 1-2 word fragments (CapCut phrase rule).
      if (/[.?!]$/.test(text) || (/,$/.test(text) && current.length >= 3)) {
        chunks.push(current);
        current = [];
        currentLen = 0;
      }
    }
    if (current.length) chunks.push(current);
    return chunks;
  };

  const activeWordIndex = findActiveWordIndex(currentTime);
  const subtitleLimit = SUBTITLE_LIMITS[selectedPresetId] ?? SUBTITLE_LIMITS.tiktok_viral;

  // Chunk yang memuat kata aktif. Bila belum ada kata aktif (video di awal klip),
  // tampilkan chunk pertama supaya gaya caption tetap terlihat.
  const activeChunk = (() => {
    if (!clipWords || clipWords.length === 0) return null;
    const chunks = chunkWords(clipWords, subtitleLimit.maxWords, subtitleLimit.maxChars);
    if (chunks.length === 0) return null;
    if (activeWordIndex < 0) return chunks[0];
    const active = clipWords[activeWordIndex];
    const found = chunks.find((chunk) =>
      chunk.some((w) => w.start === active.start && w.end === active.end),
    );
    return found ?? chunks[chunks.length - 1];
  })();

  /** Kata di dalam chunk aktif yang sedang di-highlight (null = tidak ada). */
  const activeChunkWord =
    activeChunk && activeWordIndex >= 0
      ? (activeChunk.find(
          (w) =>
            w.start === clipWords?.[activeWordIndex]?.start &&
            w.end === clipWords?.[activeWordIndex]?.end,
        ) ?? null)
      : null;

  // Teks contoh dipakai hanya saat belum ada transkrip (sebelum analisis).
  const hasRealTranscript = Boolean(activeChunk && activeChunk.length > 0);

  // Dynamic Subtitle text sample styled matching viral TikTok kinetic format
  const getSubtitleSample = () => {
    switch (selectedPresetId) {
      case 'classic_karaoke': {
        const words = activeChunk ?? [
          { word: 'Konsisten', start: 0, end: 0 },
          { word: 'itu', start: 0, end: 0 },
          { word: 'lebih', start: 0, end: 0 },
        ];
        return (
          <div className="flex flex-wrap items-center justify-center gap-x-1.5 font-['Montserrat',_sans-serif] font-extrabold text-center select-none leading-tight drop-shadow-[0_2px_6px_rgba(0,0,0,0.95)]">
            {words.map((w, i) => {
              const isActive =
                activeChunkWord !== null &&
                w.start === activeChunkWord.start &&
                w.end === activeChunkWord.end;
              return (
                <span
                  key={`${w.word}-${i}`}
                  style={{
                    WebkitTextStroke: '1.5px #000000',
                    paintOrder: 'stroke fill',
                  }}
                  className={`inline-block text-[15.5px] sm:text-[16.5px] tracking-[0.015em] font-extrabold transition-all duration-100 ${
                    isActive ? 'text-[#00F5D4] scale-105' : 'text-white'
                  }`}
                >
                  {w.word}
                </span>
              );
            })}
            {!hasRealTranscript && (
              <span
                style={{
                  WebkitTextStroke: '1.5px #000000',
                  paintOrder: 'stroke fill',
                }}
                className="text-white text-[15.5px] sm:text-[16.5px] tracking-[0.015em] font-extrabold"
              >
                dari motivasi
              </span>
            )}
          </div>
        );
      }
      case 'minimalist': {
        const text = activeChunk?.map((w) => w.word).join(' ') ?? 'Konsisten itu lebih penting';
        return (
          <div
            style={{
              WebkitTextStroke: '1.1px #0a0a0a',
              paintOrder: 'stroke fill',
            }}
            className="font-['Plus_Jakarta_Sans',_sans-serif] font-bold text-[14px] text-white tracking-[0.01em] text-center drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)] select-none leading-snug"
          >
            <span>{text}</span>
          </div>
        );
      }
      case 'word_pop': {
        const word = activeChunk?.[0]?.word.toUpperCase() ?? 'KONSISTEN!';
        return (
          <div
            style={{
              WebkitTextStroke: '2px #000000',
              paintOrder: 'stroke fill',
            }}
            className="flex flex-col items-center justify-center font-['Impact',_sans-serif] font-black uppercase text-[28px] text-white tracking-wider text-center drop-shadow-[0_4px_8px_rgba(0,0,0,0.95)] select-none leading-none"
          >
            <span>{word}</span>
          </div>
        );
      }
      case 'no_subtitle':
      case 'none':
        return null;
      case 'tiktok_viral':
      default: {
        const words =
          activeChunk && activeChunk.length > 0
            ? activeChunk
            : [
                { word: 'Konsisten', start: 0, end: 0 },
                { word: 'itu', start: 0, end: 0 },
                { word: 'lebih', start: 0, end: 0 },
                { word: 'penting', start: 0, end: 0 },
              ];
        return (
          <div className="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-1 font-['Montserrat',_'Plus_Jakarta_Sans',_sans-serif] font-extrabold text-center select-none max-w-[92%] mx-auto leading-normal">
            {words.map((w, i) => {
              const isActive =
                activeChunkWord !== null &&
                w.start === activeChunkWord.start &&
                w.end === activeChunkWord.end;
              const isHighlighted = hasRealTranscript ? isActive : i === 0;
              return (
                <span
                  key={`${w.word}-${i}`}
                  style={{
                    WebkitTextStroke: '1.4px #000000',
                    paintOrder: 'stroke fill',
                  }}
                  className={`inline-block text-[15px] sm:text-[16px] tracking-[0.015em] font-extrabold transition-all duration-100 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)] ${
                    isHighlighted ? 'text-[#34D399] scale-105' : 'text-white'
                  }`}
                >
                  {w.word}
                </span>
              );
            })}
          </div>
        );
      }
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // ── ADAPTIVE TRANSPORT TIMELINE ──
  // The transport bar reacts to three states:
  //   1. No playback  -> nothing loaded yet (no source / metadata pending) => placeholder "--:--"
  //   2. Paused       -> media ready but not playing => real times, dim status dot
  //   3. Playing      -> real times, glowing emerald status dot
  // While previewing a clip range, the timeline is clip-relative instead of source-relative.
  const hasVideoSource = Boolean(videoStreamUrl);
  const mediaDuration = Number.isFinite(duration) && duration > 0 ? duration : 0;

  const isClipRange = Boolean(previewClip && !isRenderedClip);
  const clipStart = isClipRange && previewClip ? previewClip.start : 0;
  const clipDuration =
    isClipRange && previewClip ? Math.max(0, previewClip.end - previewClip.start) : 0;

  const timelineDuration = isClipRange ? clipDuration : mediaDuration;
  const timelineCurrent = isClipRange
    ? Math.min(timelineDuration, Math.max(0, currentTime - clipStart))
    : Math.min(mediaDuration, Math.max(0, currentTime));

  // Timeline is only interactive once we actually know the media length.
  const isTimelineReady =
    hasVideoSource && hasLoadedMetadata && !mediaError && timelineDuration > 0;
  // Playback controls are only blocked when there is truly nothing to play.
  const isTransportDisabled = !hasVideoSource || mediaError;

  const playbackProgress = isTimelineReady
    ? Math.min(100, Math.max(0, (timelineCurrent / timelineDuration) * 100))
    : 0;
  const remainingTime = Math.max(0, timelineDuration - timelineCurrent);

  return (
    <div className="flex flex-col h-full max-lg:h-auto w-full rounded-2xl bg-[#090d13] border border-slate-800/80 shadow-xl overflow-hidden">
      {/* PERSISTENT TERMINAL HEADER (Video Preview) */}
      <div className="flex h-8 items-center justify-between px-3.5 border-b border-slate-800/80 bg-[#161b22] flex-shrink-0">
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f56]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
          <span
            className={`h-2.5 w-2.5 rounded-full ${isProcessing ? 'bg-[#27c93f] animate-pulse' : 'bg-[#27c93f]'}`}
          />
        </div>
        {clipTitle && (
          <span
            className="text-[11px] font-mono text-slate-400 truncate max-w-[200px] ml-2"
            title={clipTitle}
          >
            {clipTitle}
          </span>
        )}
      </div>

      <div className="flex-1 min-h-0 flex flex-col p-3 sm:p-3.5 max-sm:p-2.5 overflow-hidden">
        {/* ─────────────────────────────────────────────────────────────
            CENTER STAGE: PHOTOREALISTIC WEBMOBILEFIRST iPHONE 17 PRO (2-LAYER COMPOSITE)
            - True 1:1 Apple Viewport Underneath (.iphone-screen: 354px × 771px)
            - Transparent Official iPhone 17 Pro Overlay (.iphone-frame-overlay: 389px × 800px)
            - Dynamically auto-scaled to fit 100% of available column viewport
           ───────────────────────────────────────────────────────────── */}
      <div
        ref={stageRef}
        className="flex flex-1 min-h-0 w-full items-center justify-center p-1 overflow-hidden relative select-none max-lg:flex-none max-lg:min-h-[460px]"
      >
        {/* Subtle Ambient Radial Lighting Floor */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-white/[0.02] via-transparent to-transparent pointer-events-none -z-10" />

        {/* ─────────────────────────────────────────────────────────
            1:1 PHOTOREALISTIC iPHONE 17 PRO AUTO-SCALED WRAPPER
           ───────────────────────────────────────────────────────── */}
        <div
          className="relative shrink-0 flex items-center justify-center select-none"
          style={{
            width: `${Math.round(389 * scale)}px`,
            height: `${Math.round(800 * scale)}px`,
          }}
        >
          <div
            style={{
              width: '389px',
              height: '800px',
              transform: `scale(${scale})`,
              transformOrigin: '0 0',
            }}
            className="absolute top-0 left-0"
          >
            {/* ─────────────────────────────────────────────────────────
                1. UNDERNEATH LAYER (.iphone-screen): Exact Apple Viewport
                - 354px width × 771px height
                - top: 14px, left: 18px
                - border-radius: 46px
                - overflow: hidden
               ───────────────────────────────────────────────────────── */}
            <div className="iphone-screen bg-[#07090e] absolute top-[14px] left-[17px] w-[356px] h-[772px] rounded-[46px] overflow-hidden shadow-2xl flex flex-col z-10">
              {/* Front Screen Diagonal Glass Reflection Highlight */}
              <div className="pointer-events-none absolute inset-0 z-20 bg-gradient-to-tr from-transparent via-white/[0.015] to-white/[0.04] rounded-[46px]" />

              {/* ── AUTHENTIC iOS 26 STATUS BAR (Apple HIG) ──
                  - Time kiri: SF Pro Text Semibold, tracking rapat
                  - Kanan: Cellular (4 bar rounded, naik kiri→kanan) + Battery
                  - Tanpa Wi-Fi, mengikuti tata letak nukilan iOS terbaru. */}
              <div className="absolute top-[8px] inset-x-0 h-[27px] pl-[30px] pr-[16px] z-25 flex items-center justify-between text-white pointer-events-none select-none">
                {/* Left Flank: Time (9:41, SF Pro Semibold, tight tracking) */}
                <div className="flex items-center">
                  <span
                    className="text-[16px] font-semibold text-white/70 antialiased"
                    style={{
                      fontFamily:
                        "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Helvetica Neue', Helvetica, sans-serif",
                      letterSpacing: '-0.4px',
                      textShadow: '0 1px 2px rgba(0, 0, 0, 0.35)',
                    }}
                  >
                    9:41
                  </span>
                </div>

                {/* Right Flank: Cellular (4 rounded bars, ascending left→right) + Battery */}
                <div className="flex items-center gap-[7px] pr-0.5">
                  {/* Cellular Signal */}
                  <svg
                    className="w-[18px] h-[12.5px] text-white/70 shrink-0"
                    viewBox="0 0 18 12.5"
                    fill="currentColor"
                    style={{ filter: 'drop-shadow(0 1px 1px rgba(0, 0, 0, 0.35))' }}
                  >
                    <rect x="0" y="8.2" width="2.7" height="4.3" rx="0.9" />
                    <rect x="5" y="5.3" width="2.7" height="7.2" rx="0.9" />
                    <rect x="10" y="2.4" width="2.7" height="10.1" rx="0.9" />
                    <rect x="15" y="0" width="2.7" height="12.5" rx="0.9" />
                  </svg>

                  {/* Battery (rounded capsule + fill + right terminal nub) */}
                  <svg
                    className="w-[26px] h-[12px] text-white/70 shrink-0"
                    viewBox="0 0 26 12"
                    fill="none"
                    style={{ filter: 'drop-shadow(0 1px 1px rgba(0, 0, 0, 0.35))' }}
                  >
                    <rect
                      x="0.7"
                      y="0.7"
                      width="20.4"
                      height="10.6"
                      rx="3.4"
                      stroke="currentColor"
                      strokeWidth="1"
                      strokeOpacity="0.45"
                    />
                    <rect x="2.1" y="2.1" width="14" height="7.8" rx="1.9" fill="currentColor" />
                    <path
                      d="M22.6 3.9C23.5 3.9 24 4.4 24 5.1V6.9C24 7.6 23.5 8.1 22.6 8.1"
                      stroke="currentColor"
                      strokeWidth="1"
                      strokeOpacity="0.45"
                      strokeLinecap="round"
                      fill="none"
                    />
                  </svg>
                </div>
              </div>

              {/* OLED Screen Content Container */}
              <div
                ref={screenContentRef}
                className={`relative w-full h-full bg-slate-950 overflow-hidden flex items-center justify-center ${
                  videoStreamUrl ? 'cursor-pointer' : ''
                }`}
                onClick={videoStreamUrl ? () => void togglePlay() : undefined}
                onKeyDown={videoStreamUrl ? handlePreviewKeyDown : undefined}
                role={videoStreamUrl ? 'button' : undefined}
                tabIndex={videoStreamUrl ? 0 : undefined}
                aria-label={
                  videoStreamUrl
                    ? isPlaying
                      ? 'Pause video preview'
                      : 'Putar video preview'
                    : undefined
                }
                title={
                  videoStreamUrl ? (isPlaying ? 'Klik untuk pause' : 'Klik untuk putar') : undefined
                }
              >
                {/* ── REAL VIDEO STREAM PLAYBACK IF AVAILABLE ── */}
                {videoStreamUrl ? (
                  <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
                    {/* Background Blurred Stream for Fit/16:9 mode */}
                    {framingMode === 'fit_blur' && (
                      <video
                        src={videoStreamUrl}
                        className="absolute inset-0 w-full h-full object-cover filter blur-xl scale-125 opacity-50 pointer-events-none"
                        muted
                        loop
                      />
                    )}

                    {/* Dual Stack (split_screen): dua panel 50:50, kiri host & kanan guest */}
                    {!isRenderedClip && framingMode === 'split_screen' ? (
                      <div className="relative z-10 flex h-full w-full flex-col">
                        <div className="relative h-1/2 w-full overflow-hidden bg-black">
                          <video
                            ref={videoRef}
                            src={videoStreamUrl}
                            onLoadedMetadata={handleLoadedMetadata}
                            onError={handleMediaError}
                            onTimeUpdate={handleTimeUpdateWithClip}
                            onPlay={() => setIsPlaying(true)}
                            onPause={() => setIsPlaying(false)}
                            onEnded={() => setIsPlaying(false)}
                            muted={isMuted}
                            className="h-full w-full object-cover object-left"
                            playsInline
                          />
                        </div>
                        <div className="h-[3px] w-full bg-slate-900/90" />
                        <div className="relative h-1/2 w-full overflow-hidden bg-black">
                          <video
                            ref={secondaryVideoRef}
                            src={videoStreamUrl}
                            muted
                            className="h-full w-full object-cover object-right"
                            playsInline
                          />
                        </div>
                      </div>
                    ) : (
                      /* Main Video Screen */
                      <video
                        ref={videoRef}
                        src={videoStreamUrl}
                        onLoadedMetadata={handleLoadedMetadata}
                        onError={handleMediaError}
                        onTimeUpdate={handleTimeUpdateWithClip}
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                        onEnded={() => setIsPlaying(false)}
                        muted={isMuted}
                        className={`relative z-10 transition-all duration-300 ${
                          !isRenderedClip && framingMode === 'fit_blur'
                            ? 'w-full h-auto max-h-full object-contain'
                            : smartCropVideoStyle
                              ? ''
                              : 'w-full h-full object-cover'
                        }`}
                        style={smartCropVideoStyle ?? undefined}
                        playsInline
                      />
                    )}

                    {/* Play / Pause Tap Feedback Pulse */}
                    {showPlayPulse && (
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-30">
                        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-black/60 backdrop-blur-md text-white shadow-2xl border border-white/20 animate-scale-in">
                          {isPlaying ? (
                            <PauseIcon className="h-7 w-7 text-white fill-white" />
                          ) : (
                            <PlayIcon className="h-7 w-7 text-white fill-white ml-0.5" />
                          )}
                        </div>
                      </div>
                    )}

                    {/* Center Play Button Overlay when Paused */}
                    {!isPlaying && !showPlayPulse && (
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20 bg-black/20">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/25 backdrop-blur-md text-white shadow-xl border border-white/30 group-hover:scale-105 transition-transform">
                          <PlayIcon className="h-6 w-6 text-white fill-white ml-0.5" />
                        </div>
                      </div>
                    )}

                    {/* Tap-for-Sound hint: shown while playing muted (browser autoplay policy) */}
                    {isPlaying && isMuted && !isProcessing && (
                      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-30 pointer-events-none">
                        <div className="flex items-center gap-1.5 rounded-full border border-white/20 bg-black/70 px-3 py-1.5 text-white shadow-lg backdrop-blur-md animate-pulse">
                          <SpeakerXMarkIcon className="h-3.5 w-3.5 text-amber-300" />
                          <span className="text-[10px] font-semibold tracking-wide">
                            Ketuk untuk nyalakan suara
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Processing Overlay */}
                    {isProcessing && (
                      <div className="absolute inset-0 bg-black/80 z-40 flex flex-col items-center justify-center gap-3 text-center p-4">
                        <div className="h-9 w-9 animate-spin rounded-full border-3 border-emerald-500 border-t-transparent" />
                        <p className="font-['Outfit',_sans-serif] text-xs font-bold text-white tracking-wide">
                          Rendering 9:16 Klip AI...
                        </p>
                        <p className="text-[10px] font-mono text-emerald-400">
                          Smart Face Framing Active
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  // ── EMPTY STATE: NO SOURCE VIDEO SELECTED ──
                  <div className="relative w-full h-full flex flex-col items-center justify-center gap-6 px-6 text-center bg-[radial-gradient(ellipse_at_50%_38%,_#122032_0%,_#0a0f16_55%,_#05070a_100%)] select-none">
                    <div className="relative">
                      <div className="absolute inset-0 scale-150 rounded-full bg-emerald-500/20 blur-2xl" />
                      <img
                        src="/images/logo-icon-transparent.png"
                        alt="VisionClipper Studio"
                        draggable={false}
                        className="relative h-[128px] w-[128px] object-contain opacity-90 drop-shadow-[0_8px_34px_rgba(16,185,129,0.45)]"
                      />
                    </div>
                    <div className="space-y-2.5">
                      <p className="font-['Outfit',_sans-serif] text-[26px] font-bold tracking-wide text-white/90">
                        Belum ada video
                      </p>
                      <p className="mx-auto max-w-[300px] text-[14.5px] leading-relaxed text-slate-400">
                        Pilih video sumber atau folder klip di panel kiri untuk melihat preview di
                        sini.
                      </p>
                    </div>
                    <span className="px-4 py-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 text-[11.5px] font-bold uppercase tracking-wider font-mono text-emerald-300">
                      {framingMode === 'smart_crop'
                        ? 'Smart Follow · 9:16'
                        : framingMode === 'fit_blur'
                          ? '16:9 Fit Blur'
                          : 'Dual Stack · 50:50'}
                    </span>
                  </div>
                )}

                {/* ── SUBTITLE STYLE PREVIEW (only when a video source is loaded,
                    so placeholder caption doesn't float over the empty state) ── */}
                {/* Mirrors the backend safe zone: bottom-anchored at subPosition% with
                    ~11% horizontal margins so text never touches the frame edge. */}
                {!isRenderedClip && selectedPresetId !== 'no_subtitle' && videoStreamUrl && (
                  <div
                    className="absolute z-20 inset-x-0 px-[11%] flex justify-center pointer-events-none transition-all duration-200"
                    style={{ bottom: `${Math.max(4, 100 - subPosition)}%` }}
                  >
                    {getSubtitleSample()}
                  </div>
                )}

                {/* ── LIVE LIQUID GLASS WATERMARK (Top Safe Zone — No Background) ── */}
                {/* Parent hanya mengaktifkan `watermarkEnabled` setelah step
                    Branding terbuka (pre-render), jadi badge tidak muncul di
                    tahap config awal. */}
                {watermarkEnabled && !isRenderedClip && (
                  <div className="absolute top-12 inset-x-4 flex items-center justify-between pointer-events-none z-30">
                    <span className="liquid-glass-text text-[10px] font-semibold tracking-wide truncate max-w-[58%]">
                      Source: {sourceWatermark || 'Nama Channel'}
                    </span>

                    <span className="liquid-glass-text text-[10.5px] font-bold font-mono tracking-tight">
                      {accountWatermark
                        ? accountWatermark.startsWith('@')
                          ? accountWatermark
                          : `@${accountWatermark}`
                        : '@akun_kamu'}
                    </span>
                  </div>
                )}

                {/* Video Scrubber Bar on Phone Screen (no track — it drew a stray line under the home swipe) */}
                <div className="absolute bottom-0 inset-x-0 h-1 z-30 pointer-events-none">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-100"
                    style={{ width: `${playbackProgress}%` }}
                  />
                </div>
              </div>

              {/* ─────────────────────────────────────────────────────
                  AUTHENTIC iOS HOME INDICATOR BAR
                  - 134pt wide @ 393pt screen => 121px @ 356px, 5px tall, 9px from bottom
                 ───────────────────────────────────────────────────── */}
              <div className="absolute bottom-[9px] left-1/2 -translate-x-1/2 h-[5px] w-[121px] rounded-full bg-white/85 shadow-sm pointer-events-none z-40" />
            </div>

            {/* ─────────────────────────────────────────────────────────────
                2. OVERLAY LAYER (.iphone-frame-overlay): 1:1 Transparent Photorealistic iPhone 17 Pro PNG
                - Official WebMobileFirst transparent mockup
                - Real titanium metallic sheen, antenna bands, tactile hardware buttons
                - Opaque Dynamic Island with real camera lens glass reflections
                - 389px width × 800px height, pointer-events-none, z-30
               ───────────────────────────────────────────────────────────── */}
            <img
              src="/images/mockup-apple-iphone-17-pro-2025-transparent.png"
              onError={(e) => {
                e.currentTarget.src =
                  'https://www.webmobilefirst.com/img/mockups/mockup-apple-iphone-17-pro-2025-transparent.png';
              }}
              alt="Apple iPhone 17 Pro Frame"
              className="iphone-frame-overlay absolute inset-0 w-[389px] h-[800px] pointer-events-none z-30 object-contain select-none"
              draggable={false}
            />
          </div>
        </div>
      </div>

      {/* ── STUDIO TRANSPORT BAR ── */}
      <div
        className={`ios26-glass w-full max-w-[480px] px-3.5 py-2 flex items-center gap-3 select-none flex-shrink-0 mt-3 transition-opacity duration-200 ${
          isTransportDisabled ? 'opacity-70' : ''
        }`}
      >
        {/* Primary Transport Play/Pause */}
        <button
          type="button"
          onClick={togglePlay}
          disabled={isTransportDisabled}
          className={`ios26-play flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-white transition ${
            isTransportDisabled ? 'cursor-not-allowed opacity-40 saturate-50' : 'active:scale-95'
          }`}
          aria-label={
            isTransportDisabled
              ? 'Belum ada video untuk diputar'
              : isPlaying
                ? 'Jeda preview'
                : 'Putar preview'
          }
          title={
            isTransportDisabled
              ? 'Belum ada video untuk diputar'
              : isPlaying
                ? 'Jeda preview'
                : 'Putar preview'
          }
        >
          {isPlaying ? (
            <PauseIcon className="h-4 w-4 text-white" />
          ) : (
            <PlayIcon className="h-4 w-4 ml-0.5 text-white" />
          )}
        </button>

        {/* Timeline and Time Readout */}
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between text-[11px] font-mono">
            {isTimelineReady ? (
              <>
                {/* Playback in progress / paused at a known position */}
                <span className="flex items-center gap-1.5 text-white font-semibold tabular-nums">
                  <span
                    aria-hidden
                    className={`h-1.5 w-1.5 rounded-full transition-colors duration-200 ${
                      isPlaying
                        ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.85)]'
                        : 'bg-white/30'
                    }`}
                  />
                  {formatTime(timelineCurrent)}
                </span>
                <span
                  className={`tabular-nums transition-colors duration-200 ${isPlaying ? 'text-white/55' : 'text-white/35'}`}
                >
                  {formatTime(timelineDuration)}
                </span>
              </>
            ) : (
              <>
                {/* No playback: no source selected or media metadata not loaded yet */}
                <span className="text-white/25">--:--</span>
                <span className="text-white/20">--:--</span>
              </>
            )}
          </div>
          <input
            type="range"
            min={0}
            max={isTimelineReady ? timelineDuration : 1}
            step={isTimelineReady ? 0.1 : 1}
            value={isTimelineReady ? Math.min(timelineCurrent, timelineDuration) : 0}
            onChange={(e) => handleSeek(Number(e.target.value))}
            disabled={!isTimelineReady}
            className={`ios-media-scrubber block w-full ${
              isTimelineReady ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
            }`}
            style={{ '--ios-scrubber-progress': `${playbackProgress}%` } as React.CSSProperties}
            aria-label={
              isTimelineReady
                ? isClipRange
                  ? 'Posisi di dalam klip'
                  : 'Posisi video'
                : 'Belum ada video untuk diposisikan'
            }
            title={
              isTimelineReady
                ? remainingTime > 0
                  ? `Sisa ${formatTime(remainingTime)}`
                  : 'Posisi video'
                : 'Belum ada video'
            }
          />
        </div>

        {/* Secondary Controls: Mute + Playback Rate */}
        <div className="flex flex-shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={toggleMute}
            disabled={isTransportDisabled}
            className={`ios26-glass-btn flex h-7 w-7 items-center justify-center text-white/70 hover:text-white ${
              isTransportDisabled ? 'cursor-not-allowed opacity-40' : ''
            }`}
            title={
              isTransportDisabled ? 'Belum ada audio' : isMuted ? 'Nyalakan suara' : 'Matikan suara'
            }
          >
            {isMuted ? (
              <SpeakerXMarkIcon className="h-3.5 w-3.5 text-rose-400" />
            ) : (
              <SpeakerWaveIcon className="h-3.5 w-3.5" />
            )}
          </button>

          <button
            type="button"
            onClick={handleRateChange}
            disabled={isTransportDisabled}
            className={`ios26-glass-btn h-7 min-w-8 px-1.5 text-[10.5px] font-mono font-semibold text-white/80 hover:text-white ${
              isTransportDisabled ? 'cursor-not-allowed opacity-40' : ''
            }`}
            title={isTransportDisabled ? 'Belum ada video' : 'Kecepatan pemutaran'}
          >
            {playbackRate}x
          </button>
        </div>
      </div>
      </div>
    </div>
  );
};

export const IPhoneSocialPreview = PhonePreview;
