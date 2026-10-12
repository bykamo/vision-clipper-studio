import React, { useState, useRef, useEffect } from 'react';
import {
  PlayIcon,
  PauseIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ArrowsPointingOutIcon,
  ViewfinderCircleIcon,
  SparklesIcon,
  UserIcon
} from '@heroicons/react/24/solid';

interface PhonePreviewProps {
  framingMode: 'smart_crop' | 'fit_blur' | 'split_screen';
  selectedPresetId: string;
  videoSource?: string;
  previewClip?: { start: number; end: number } | null;
  clipTitle?: string;
  isRenderedClip?: boolean;
  subPosition?: number;
  showEmoji?: boolean;
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
  isRenderedClip = false,
  subPosition = 68,
  showEmoji = true,
  watermarkEnabled = true,
  sourceWatermark = '',
  accountWatermark = ''
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [centerAnimation, setCenterAnimation] = useState<'play' | 'pause' | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const animTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check if source is a local playable video file path
  const isLocalFile = Boolean(videoSource && !videoSource.startsWith('http://') && !videoSource.startsWith('https://'));
  const videoStreamUrl = isLocalFile && videoSource ? `/api/video-stream?path=${encodeURIComponent(videoSource.trim())}` : '';

  const triggerAnimation = (type: 'play' | 'pause') => {
    setCenterAnimation(type);
    if (animTimerRef.current) clearTimeout(animTimerRef.current);
    animTimerRef.current = setTimeout(() => {
      setCenterAnimation(null);
    }, 600);
  };

  // Auto-seek and loop within clip range when previewClip is set or when switching to rendered clip
  useEffect(() => {
    if (!videoRef.current || !videoStreamUrl) return;

    if (isRenderedClip) {
      videoRef.current.currentTime = 0;
      videoRef.current.muted = isMuted;
      videoRef.current.volume = 1;
      void videoRef.current.play()
        .then(() => setIsPlaying(true))
        .catch(() => {
          if (videoRef.current) {
            videoRef.current.muted = true;
            setIsMuted(true);
            void videoRef.current.play()
              .then(() => setIsPlaying(true))
              .catch(() => setIsPlaying(false));
          }
        });
    } else if (previewClip) {
      videoRef.current.currentTime = previewClip.start;
      videoRef.current.muted = isMuted;
      videoRef.current.volume = 1;
      void videoRef.current.play()
        .then(() => setIsPlaying(true))
        .catch(() => {
          // If unmuted autoplay blocked by browser policy, fallback to muted
          if (videoRef.current) {
            videoRef.current.muted = true;
            setIsMuted(true);
            void videoRef.current.play()
              .then(() => setIsPlaying(true))
              .catch(() => setIsPlaying(false));
          }
        });
    }
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

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || 0);
      videoRef.current.muted = isMuted;
      videoRef.current.volume = 1;
      if (isRenderedClip) {
        videoRef.current.currentTime = 0;
      } else if (previewClip) {
        videoRef.current.currentTime = previewClip.start;
      }
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime || 0);
    }
  };

  const togglePlay = async () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      try {
        video.muted = isMuted;
        if (!isMuted) video.volume = 1.0;
        await video.play();
        setIsPlaying(true);
        triggerAnimation('play');
      } catch {
        // Fallback to muted if browser blocks sound on play
        try {
          video.muted = true;
          setIsMuted(true);
          await video.play();
          setIsPlaying(true);
          triggerAnimation('play');
        } catch {
          setIsPlaying(false);
        }
      }
      return;
    }

    video.pause();
    setIsPlaying(false);
    triggerAnimation('pause');
  };

  const handlePreviewKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    void togglePlay();
  };

  const handleSeek = (time: number) => {
    const nextTime = previewClip
      ? Math.min(previewClip.end, Math.max(previewClip.start, time))
      : time;
    setCurrentTime(nextTime);
    if (videoRef.current) {
      videoRef.current.currentTime = nextTime;
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const nextMuted = !videoRef.current.muted;
    videoRef.current.muted = nextMuted;
    if (!nextMuted) {
      videoRef.current.volume = 1.0;
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

  // Dynamic Subtitle text sample based on preset (disamakan persis dengan kartu preset)
  const getSubtitleSample = () => {
    switch (selectedPresetId) {
      case 'classic_karaoke':
        return (
          <div className="flex items-center justify-center text-center font-['Montserrat',_sans-serif] font-bold text-base tracking-tight select-none">
            <span className="text-cyan-300 font-extrabold drop-shadow-[0_2px_4px_rgba(0,0,0,1)] text-lg">
              Contoh&nbsp;
            </span>
            <span className="text-white drop-shadow-[0_2px_4px_rgba(0,0,0,1)] text-lg">
              Subtitle
            </span>
          </div>
        );
      case 'minimalist':
        return (
          <div className="font-sans font-medium text-sm text-white tracking-wide text-center drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)] select-none">
            <span>Contoh teks subtitle</span>
          </div>
        );
      case 'word_pop':
        return (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[120%] font-['Impact',_sans-serif] font-black uppercase text-[40px] text-yellow-300 tracking-widest text-center drop-shadow-[0_5px_10px_rgba(0,0,0,1)] scale-110 select-none animate-pulse">
            <span>SUBTITLE!</span>
          </div>
        );
      case 'no_subtitle':
      case 'none':
        return null;
      case 'tiktok_viral':
      default:
        return (
          <div className="flex items-center justify-center font-['Montserrat',_sans-serif] font-black uppercase text-base tracking-tight leading-none text-center select-none">
            <span className="text-white drop-shadow-[0_2px_4px_rgba(0,0,0,1)] text-base">CONTOH&nbsp;</span>
            <span className="text-yellow-400 bg-black/90 px-2 py-0.5 rounded font-black scale-105 inline-block drop-shadow-[0_3px_6px_rgba(0,0,0,0.9)] border border-yellow-400/40 text-base">
              SUBTITLE
            </span>
            {showEmoji && <span className="text-white drop-shadow-[0_2px_4px_rgba(0,0,0,1)] text-base">&nbsp;✨</span>}
          </div>
        );
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const playbackProgress = duration > 0
    ? Math.min(100, Math.max(0, (currentTime / duration) * 100))
    : 0;
  const remainingTime = Math.max(0, duration - currentTime);

  return (
    <div className="flex flex-col h-full w-full rounded-2xl bg-[#10161f] border border-[#202b3a] p-4 shadow-xl overflow-hidden">

      {/* ── TOP HEADER OF PREVIEW ── */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <ViewfinderCircleIcon className={`h-4 w-4 ${isRenderedClip ? 'text-amber-400' : 'text-emerald-400'}`} />
          <div className="flex flex-col">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 font-['Outfit']">
              {isRenderedClip ? 'OUTPUT CLIP PREVIEW' : 'VIDEO PREVIEW'}
            </h2>
            {clipTitle && (
              <span className="text-[10px] text-slate-400 truncate max-w-[160px] sm:max-w-[200px]" title={clipTitle}>
                {clipTitle}
              </span>
            )}
          </div>
        </div>

        {isRenderedClip && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/15 border border-amber-500/30 text-[10px] font-mono font-bold text-amber-400">
            <SparklesIcon className="h-3 w-3" />
            <span>Final Render (9:16)</span>
          </span>
        )}
      </div>

      {/* ── CENTER WORKSPACE: REALISTIC iPHONE MOCKUP ── */}
      <div className="relative flex-1 flex items-center justify-center min-h-[380px] py-2 select-none">

        {/* Outer Phone Frame */}
        <div className="relative flex items-center justify-center">

          {/* Phone Bezel Frame */}
          <div className="relative w-[256px] h-[458px] xl:w-[282px] xl:h-[508px] rounded-[48px] bg-gradient-to-tr from-[#1b222d] via-[#2d3848] to-[#161c26] p-[4px] shadow-[0_25px_60px_rgba(0,0,0,0.8),0_0_0_1px_rgba(255,255,255,0.08),inset_0_1px_2px_rgba(255,255,255,0.2)]">

            {/* Inner Black OLED Screen Container */}
            <div className="relative w-full h-full rounded-[44px] bg-black overflow-hidden border-[2px] border-black flex flex-col justify-between">

              {/* Dynamic Island Only */}
              <div className="absolute top-2.5 inset-x-0 z-40 flex justify-center pointer-events-none">
                <div className="h-[22px] w-[88px] rounded-full bg-black border border-neutral-900/80 flex items-center justify-between px-2.5 shadow-md">
                  <div className="flex items-center gap-1.5">
                    <div className="h-3 w-3 rounded-full bg-[#080d14] border border-[#1a2332] flex items-center justify-center">
                      <div className="h-1 w-1 rounded-full bg-blue-900/80" />
                    </div>
                    <div className="h-1.5 w-1.5 rounded-full bg-[#0d131f]" />
                  </div>
                  {isPlaying ? (
                    <div className="flex items-center gap-0.5 h-2.5">
                      <span className="w-0.5 h-2 bg-emerald-400 animate-pulse rounded-full" />
                      <span className="w-0.5 h-3 bg-emerald-300 animate-pulse rounded-full delay-75" />
                      <span className="w-0.5 h-1.5 bg-emerald-400 animate-pulse rounded-full delay-150" />
                    </div>
                  ) : (
                    <div className="h-1.5 w-1.5 rounded-full bg-emerald-500/70 animate-pulse" />
                  )}
                </div>
              </div>

              {/* OLED Screen Content */}
              <div
                className={`relative w-full h-full bg-slate-950 overflow-hidden flex items-center justify-center ${
                  videoStreamUrl ? 'cursor-pointer' : ''
                }`}
                onClick={videoStreamUrl ? () => void togglePlay() : undefined}
                onKeyDown={videoStreamUrl ? handlePreviewKeyDown : undefined}
                role={videoStreamUrl ? 'button' : undefined}
                tabIndex={videoStreamUrl ? 0 : undefined}
                aria-label={videoStreamUrl ? (isPlaying ? 'Pause video preview' : 'Putar video preview') : undefined}
                title={videoStreamUrl ? (isPlaying ? 'Klik untuk pause' : 'Klik untuk putar') : undefined}
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

                    {/* Main Video Screen */}
                    <video
                      ref={videoRef}
                      src={videoStreamUrl}
                      onLoadedMetadata={handleLoadedMetadata}
                      onTimeUpdate={handleTimeUpdateWithClip}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      onEnded={() => setIsPlaying(false)}
                      muted={isMuted}
                      className={`relative z-10 transition-all duration-300 ${
                        !isRenderedClip && framingMode === 'fit_blur'
                          ? 'w-full h-auto max-h-[220px] object-contain shadow-2xl border-y border-white/10'
                          : 'w-full h-full object-cover'
                      }`}
                      playsInline
                    />

                    {/* Smooth Animated Center Play / Pause Pop Indicator */}
                    {centerAnimation && (
                      <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-black/70 backdrop-blur-md border border-white/30 text-white shadow-[0_0_30px_rgba(0,0,0,0.8)] animate-in zoom-in-75 fade-in duration-150 animate-out zoom-out-110 fade-out fill-mode-forwards duration-200">
                          {centerAnimation === 'play' ? (
                            <PlayIcon className="h-8 w-8 ml-1 text-emerald-400 drop-shadow-md" />
                          ) : (
                            <PauseIcon className="h-8 w-8 text-amber-400 drop-shadow-md" />
                          )}
                        </div>
                      </div>
                    )}

                    {/* Center Play Overlay Button when Paused */}
                    {!isPlaying && !centerAnimation && (
                      <div className="absolute inset-0 z-25 flex items-center justify-center pointer-events-none">
                        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-black/55 backdrop-blur-md border border-white/25 text-white shadow-2xl transition-all duration-300 transform scale-100 hover:scale-110">
                          <PlayIcon className="h-7 w-7 ml-0.5 text-white/90 drop-shadow-md" />
                        </div>
                      </div>
                    )}

                    {/* Subtitle floating in safe area (only shown on raw video preview, not final rendered clip) */}
                    {!isRenderedClip && (
                      <div
                        className="absolute z-20 w-full px-3 flex justify-center pointer-events-none transition-all duration-200"
                        style={{ top: `${subPosition}%` }}
                      >
                        {getSubtitleSample()}
                      </div>
                    )}
                  </div>
                ) : (
                  // ── EMPTY STATE GRAPHICS (NO SOURCE VIDEO SELECTED) ──
                  framingMode === 'split_screen' ? (
                    // Dual Stack 50:50 (Podcast Host Atas / Guest Bawah)
                    <div className="relative w-full h-full flex flex-col items-center justify-between bg-slate-950 overflow-hidden select-none">
                      {/* Top Window: Host (50%) */}
                      <div className="relative w-full h-1/2 bg-gradient-to-b from-[#0c1524] to-[#070b12] flex flex-col items-center justify-center border-b-2 border-neutral-800/80 overflow-hidden">
                        <div className="absolute top-2 left-2 flex items-center gap-1 bg-black/60 backdrop-blur-xs px-1.5 py-0.5 rounded border border-cyan-500/30 z-10">
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
                          <span className="text-[7.5px] font-bold text-cyan-300 font-mono">HOST (Top 50%)</span>
                        </div>
                        <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-cyan-950 to-cyan-800 border border-cyan-400/40 flex items-center justify-center shadow-lg">
                          <UserIcon className="h-9 w-9 text-cyan-300" />
                        </div>
                        <span className="text-[8px] font-mono text-cyan-300 font-bold mt-1">Host Anchor (Left)</span>
                      </div>

                      {/* Center Divider Line */}
                      <div className="w-full h-1 bg-gradient-to-r from-cyan-500/40 via-amber-400/60 to-cyan-500/40 shadow-sm z-10" />

                      {/* Bottom Window: Guest (50%) */}
                      <div className="relative w-full h-1/2 bg-gradient-to-b from-[#070b12] to-[#120d1c] flex flex-col items-center justify-center overflow-hidden">
                        <div className="absolute top-2 left-2 flex items-center gap-1 bg-black/60 backdrop-blur-xs px-1.5 py-0.5 rounded border border-amber-500/30 z-10">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
                          <span className="text-[7.5px] font-bold text-amber-300 font-mono">GUEST (Bottom 50%)</span>
                        </div>
                        <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-amber-950 to-amber-800 border border-amber-400/40 flex items-center justify-center shadow-lg">
                          <UserIcon className="h-9 w-9 text-amber-300" />
                        </div>
                        <span className="text-[8px] font-mono text-amber-300 font-bold mt-1">Guest Anchor (Right)</span>
                      </div>

                      {/* Subtitle floating in safe area */}
                      <div
                        className="absolute z-20 w-full px-3 flex justify-center pointer-events-none transition-all duration-200"
                        style={{ top: `${subPosition}%` }}
                      >
                        {getSubtitleSample()}
                      </div>
                    </div>
                  ) : framingMode === 'fit_blur' ? (
                    // 16:9 Fit with Blur Backdrop inside 9:16 iPhone screen
                    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
                      {/* Dynamic Studio Gradient Blur Backdrop */}
                      <div
                        className="absolute inset-0 bg-cover bg-center filter blur-2xl scale-150 opacity-50"
                        style={{
                          backgroundImage: `radial-gradient(ellipse at 50% 35%, #0284c7 0%, #0f172a 60%, #030712 100%)`
                        }}
                      />

                      {/* 16:9 Center Video Frame (Podcast Studio Graphic) */}
                      <div className="relative z-10 w-full h-[152px] -mt-[10%] bg-[#0c131f] border-y border-cyan-500/30 flex flex-col items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.15)] overflow-hidden">
                        <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:10px_10px]" />

                        {/* Dual Speaker / Podcast Graphic Representation */}
                        <div className="relative flex items-center gap-6 z-10">
                          <div className="flex flex-col items-center">
                            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-950 to-cyan-800 border border-cyan-400/50 flex items-center justify-center shadow-lg">
                              <UserIcon className="h-6 w-6 text-cyan-300" />
                            </div>
                            <span className="text-[7.5px] font-mono text-cyan-400 mt-1">Host</span>
                          </div>

                          {/* Center Mic icon / Waveform */}
                          <div className="flex flex-col items-center gap-1">
                            <div className="flex items-center gap-0.5 h-6 px-1.5 py-1 rounded bg-black/40 border border-cyan-500/20">
                              <span className="w-0.5 h-3 bg-cyan-400 animate-pulse rounded-full" />
                              <span className="w-0.5 h-5 bg-cyan-300 animate-pulse rounded-full delay-75" />
                              <span className="w-0.5 h-2 bg-cyan-400 animate-pulse rounded-full delay-150" />
                              <span className="w-0.5 h-4 bg-cyan-300 animate-pulse rounded-full" />
                            </div>
                            <span className="text-[7px] font-mono text-slate-500">16:9 STREAM</span>
                          </div>

                          <div className="flex flex-col items-center">
                            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-amber-950 to-amber-800 border border-amber-400/50 flex items-center justify-center shadow-lg">
                              <UserIcon className="h-6 w-6 text-amber-300" />
                            </div>
                            <span className="text-[7.5px] font-mono text-amber-400 mt-1">Guest</span>
                          </div>
                        </div>

                        {/* 16:9 Fit Badge */}
                        <div className="absolute top-1.5 left-2 flex items-center gap-1 bg-black/70 backdrop-blur-xs px-1.5 py-0.5 rounded border border-cyan-500/30">
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                          <span className="text-[8px] font-bold text-cyan-300 font-mono">16:9 Fit (Blur Mode)</span>
                        </div>
                      </div>

                      {/* Subtitle floating below 16:9 frame */}
                      <div
                        className="absolute z-20 w-full px-3 flex justify-center pointer-events-none transition-all duration-200"
                        style={{ top: `${subPosition}%` }}
                      >
                        {getSubtitleSample()}
                      </div>
                    </div>
                  ) : (
                    // 9:16 Smart Crop Simulated Layout (Solo Creator Stage)
                    <div className="relative w-full h-full flex items-center justify-center bg-gradient-to-b from-[#0a101a] via-[#101b2b] to-[#060a10] overflow-hidden">

                      {/* Background Bokeh & Glow Light */}
                      <div className="absolute top-12 -left-8 h-32 w-32 rounded-full bg-emerald-500/10 filter blur-2xl" />
                      <div className="absolute top-20 -right-8 h-32 w-32 rounded-full bg-cyan-500/10 filter blur-2xl" />

                      {/* AI Target Tracking Box */}
                      <div className="absolute top-[22%] flex flex-col items-center">
                        {/* Bounding Box Corner Brackets */}
                        <div className="relative p-2 rounded-2xl border-2 border-emerald-400/60 bg-emerald-950/20 backdrop-blur-2xs shadow-[0_0_30px_rgba(16,185,129,0.2)]">
                          {/* Corner Reticles */}
                          <div className="absolute -top-1 -left-1 h-2.5 w-2.5 border-t-2 border-l-2 border-emerald-400" />
                          <div className="absolute -top-1 -right-1 h-2.5 w-2.5 border-t-2 border-r-2 border-emerald-400" />
                          <div className="absolute -bottom-1 -left-1 h-2.5 w-2.5 border-b-2 border-l-2 border-emerald-400" />
                          <div className="absolute -bottom-1 -right-1 h-2.5 w-2.5 border-b-2 border-r-2 border-emerald-400" />

                          <div className="relative h-28 w-24 rounded-xl bg-gradient-to-b from-slate-800 to-slate-900 flex flex-col items-center justify-center border border-slate-700/60 shadow-inner">
                            <UserIcon className="h-14 w-14 text-emerald-300 drop-shadow-[0_2px_8px_rgba(16,185,129,0.4)]" />
                            <div className="flex items-center gap-1 mt-1 bg-black/60 px-1.5 py-0.5 rounded-full">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              <span className="text-[7.5px] font-mono text-emerald-300 font-bold">98.4% Lock</span>
                            </div>
                          </div>

                          {/* AI Smart Follow Tag */}
                          <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-slate-950 px-2 py-0.5 rounded-full text-[8.5px] font-black uppercase tracking-wider font-['Outfit'] shadow-md flex items-center gap-1">
                            <SparklesIcon className="h-2.5 w-2.5" />
                            <span>Smart Follow</span>
                          </div>
                        </div>
                      </div>

                      {/* Subtitle Floating Center-Bottom */}
                      <div
                        className="absolute z-20 w-full px-3 flex justify-center pointer-events-none transition-all duration-200"
                        style={{ top: `${subPosition}%` }}
                      >
                        {getSubtitleSample()}
                      </div>
                    </div>
                  )
                )}

                {/* ── LIVE GLASS WATERMARK BADGES (Top Safe Zone) ── */}
                {watermarkEnabled && !isRenderedClip && (sourceWatermark || accountWatermark) && (
                  <div className="absolute top-5 inset-x-3.5 flex items-center justify-between pointer-events-none z-30">
                    {sourceWatermark ? (
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#121418]/70 backdrop-blur-md border border-white/15 shadow-[0_4px_12px_rgba(0,0,0,0.5)] max-w-[55%]">
                        <span className="text-[8px] text-white/90 font-medium truncate tracking-wide">
                          <span className="text-cyan-400 mr-1 text-[7px]">▶</span>Source: {sourceWatermark}
                        </span>
                      </div>
                    ) : <div />}

                    {accountWatermark ? (
                      <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#121418]/70 backdrop-blur-md border border-white/15 shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
                        <span className="text-[8.5px] font-bold text-amber-300 font-mono tracking-tight">
                          {accountWatermark.startsWith('@') ? accountWatermark : `@${accountWatermark}`}
                        </span>
                      </div>
                    ) : null}
                  </div>
                )}

              </div>

            </div>

          </div>

        </div>

      </div>

      {/* ── iOS-INSPIRED PREVIEW TRANSPORT ── */}
      <div className="ios-playback-controls relative mt-5 overflow-hidden rounded-[24px] border border-white/[0.11] bg-[linear-gradient(145deg,rgba(49,56,67,0.9)_0%,rgba(23,28,36,0.94)_48%,rgba(12,15,20,0.97)_100%)] p-px shadow-[0_18px_40px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.12)]">
        <div className="pointer-events-none absolute inset-x-7 top-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent" />
        <div className="relative flex items-center gap-2.5 rounded-[23px] bg-black/15 px-3 py-2.5 backdrop-blur-2xl">

          {/* Primary Transport */}
          <button
            type="button"
            onClick={togglePlay}
            disabled={!videoStreamUrl}
            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-[linear-gradient(180deg,#34d399_0%,#10b981_58%,#059669_100%)] text-[#07130f] shadow-[0_8px_20px_rgba(16,185,129,0.34),inset_0_1px_0_rgba(255,255,255,0.38)] transition duration-200 hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-35 disabled:shadow-none"
            aria-label={isPlaying ? 'Jeda preview' : 'Putar preview'}
            title={isPlaying ? 'Jeda preview' : 'Putar preview'}
          >
            {isPlaying ? (
              <PauseIcon className="h-[18px] w-[18px]" />
            ) : (
              <PlayIcon className="ml-0.5 h-[18px] w-[18px]" />
            )}
          </button>

          {/* Timeline and Time Readout */}
          <div className="min-w-0 flex-1">
            <div className="mb-0.5 flex items-center justify-between text-[10px] font-medium tracking-[-0.01em] text-white/85 [font-variant-numeric:tabular-nums]">
              <span>{duration > 0 ? formatTime(currentTime) : '--:--'}</span>
              <span className="text-white/40">{duration > 0 ? `-${formatTime(remainingTime)}` : '--:--'}</span>
            </div>
            <input
              type="range"
              min="0"
              max={duration > 0 ? duration : 100}
              disabled={duration === 0}
              value={duration > 0 ? currentTime : 0}
              onChange={(e) => handleSeek(Number(e.target.value))}
              className="ios-media-scrubber block w-full disabled:cursor-not-allowed disabled:opacity-35"
              style={{ '--ios-scrubber-progress': `${playbackProgress}%` } as React.CSSProperties}
              aria-label="Posisi video"
            />
          </div>

          {/* Secondary Controls */}
          <div className="flex flex-shrink-0 items-center gap-1.5">
            <button
              type="button"
              onClick={toggleMute}
              disabled={!videoStreamUrl}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.07] text-white/75 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] transition duration-200 hover:bg-white/[0.13] hover:text-white active:scale-95 disabled:cursor-not-allowed disabled:opacity-35"
              aria-label={isMuted ? 'Nyalakan suara preview' : 'Matikan suara preview'}
              title={isMuted ? 'Nyalakan suara' : 'Matikan suara'}
            >
              {isMuted ? <SpeakerXMarkIcon className="h-4 w-4" /> : <SpeakerWaveIcon className="h-4 w-4" />}
            </button>

            <button
              type="button"
              onClick={handleRateChange}
              disabled={!videoStreamUrl}
              className="h-8 min-w-9 rounded-full border border-white/[0.08] bg-white/[0.07] px-2 text-[11px] font-semibold tracking-[-0.02em] text-white/85 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] transition duration-200 hover:bg-white/[0.13] hover:text-white active:scale-95 disabled:cursor-not-allowed disabled:opacity-35"
              aria-label={`Kecepatan pemutaran ${playbackRate}x`}
              title="Ubah kecepatan pemutaran"
            >
              {playbackRate}x
            </button>
          </div>
        </div>
      </div>

    </div>
  );
};
