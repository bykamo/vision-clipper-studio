import React, { useState, useRef, useEffect } from 'react';
import {
  PlayIcon as PlayIconOutline,
  PauseIcon as PauseIconOutline,
  HeartIcon,
  BookmarkIcon,
  ShareIcon,
  ChatBubbleOvalLeftEllipsisIcon,
  PlusIcon,
  MusicalNoteIcon,
  MagnifyingGlassIcon,
  HomeIcon,
  UserGroupIcon,
  UserIcon as UserIconOutline,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';
import {
  PlayIcon,
  PauseIcon,
  HeartIcon as HeartIconSolid,
  BookmarkIcon as BookmarkIconSolid,
  CheckBadgeIcon,
  HomeIcon as HomeIconSolid,
  UserGroupIcon as UserGroupIconSolid,
  UserIcon as UserIconSolid,
  ChatBubbleOvalLeftEllipsisIcon as ChatBubbleOvalLeftEllipsisIconSolid,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ViewfinderCircleIcon,
  SparklesIcon,
  UserIcon
} from '@heroicons/react/24/solid';

export type SocialOverlayType = 'tiktok' | 'reels' | 'shorts' | 'none';

interface PhonePreviewProps {
  framingMode: 'smart_crop' | 'fit_blur' | 'split_screen';
  selectedPresetId: string;
  videoSource?: string;
  previewClip?: { start: number; end: number } | null;
  clipTitle?: string;
  clipCaption?: string;
  clipHashtags?: string[];
  isRenderedClip?: boolean;
  isProcessing?: boolean;
  subPosition?: number;
  showEmoji?: boolean;
  watermarkEnabled?: boolean;
  sourceWatermark?: string;
  accountWatermark?: string;
  initialOverlay?: SocialOverlayType;
}

export const PhonePreview: React.FC<PhonePreviewProps> = ({
  framingMode,
  selectedPresetId,
  videoSource,
  previewClip,
  clipTitle,
  clipCaption,
  clipHashtags,
  isRenderedClip = false,
  isProcessing = false,
  subPosition = 68,
  showEmoji = true,
  watermarkEnabled = true,
  sourceWatermark = '',
  accountWatermark = '',
  initialOverlay = 'tiktok'
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [centerAnimation, setCenterAnimation] = useState<'play' | 'pause' | null>(null);
  const [showPlayPulse, setShowPlayPulse] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [showSafeZone, setShowSafeZone] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState<'home' | 'friends' | 'inbox' | 'profile'>('home');

  // Social Overlay Mode State: TikTok (default), Reels, Shorts, or Off
  const [overlayMode, setOverlayMode] = useState<SocialOverlayType>(() => {
    try {
      return (localStorage.getItem('vc_preview_overlay') as SocialOverlayType) || initialOverlay;
    } catch {
      return initialOverlay;
    }
  });

  const changeOverlayMode = (mode: SocialOverlayType) => {
    setOverlayMode(mode);
    try {
      localStorage.setItem('vc_preview_overlay', mode);
    } catch {
      // ignore
    }
  };

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

    setShowPlayPulse(true);
    setTimeout(() => setShowPlayPulse(false), 500);

    if (video.paused) {
      try {
        video.muted = isMuted;
        if (!isMuted) video.volume = 1.0;
        await video.play();
        setIsPlaying(true);
        triggerAnimation('play');
      } catch {
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

  // Dynamic Subtitle text sample styled matching viral TikTok kinetic format
  const getSubtitleSample = () => {
    switch (selectedPresetId) {
      case 'classic_karaoke':
        return (
          <div className="flex flex-col items-center justify-center font-['Montserrat',_sans-serif] font-black uppercase text-center select-none leading-tight drop-shadow-[0_2px_8px_rgba(0,0,0,1)]">
            <span className="text-[#38BDF8] text-[15px] sm:text-[16px] tracking-wide font-black">
              KONSISTEN ITU LEBIH PENTING
            </span>
            <span className="text-white text-[15px] sm:text-[16px] tracking-wide font-black">
              DARI MOTIVASI {showEmoji && <span>⚡</span>}
            </span>
          </div>
        );
      case 'minimalist':
        return (
          <div className="font-['Inter',_sans-serif] font-medium text-[12px] text-white tracking-wide text-center drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)] select-none bg-black/60 px-3.5 py-1.5 rounded-lg border border-white/10 backdrop-blur-xs">
            <span>Konsisten itu lebih penting dari motivasi</span>
          </div>
        );
      case 'word_pop':
        return (
          <div className="flex flex-col items-center justify-center font-['Impact',_sans-serif] font-black uppercase text-[28px] text-[#FBBF24] tracking-wider text-center drop-shadow-[0_4px_10px_rgba(0,0,0,1)] select-none animate-pulse leading-none">
            <span>KONSISTEN! 🔥</span>
          </div>
        );
      case 'no_subtitle':
      case 'none':
        return null;
      case 'tiktok_viral':
      default:
        return (
          <div className="flex flex-col items-center justify-center font-['Montserrat',_sans-serif] font-black uppercase text-center select-none leading-tight drop-shadow-[0_2px_10px_rgba(0,0,0,1)]">
            <span className="text-[#FBBF24] text-[16px] sm:text-[17px] tracking-wide font-black drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)]">
              KONSISTEN ITU LEBIH PENTING
            </span>
            <span className="text-white text-[16px] sm:text-[17px] tracking-wide font-black drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)] mt-0.5">
              DARI MOTIVASI {showEmoji && <span>🔥</span>}
            </span>
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

  // Dynamic values for Social Media overlay
  const displayAccount = (accountWatermark || 'visionclipper.ai').replace(/^@/, '');
  const displayCaption = clipCaption || clipTitle || 'Kenapa berat badan lu gak turun meski makan dikit? Ini fakta biologisnya...';
  const displayHashtags = clipHashtags && clipHashtags.length > 0
    ? clipHashtags.map(t => t.startsWith('#') ? t : `#${t}`).slice(0, 4).join(' ')
    : '#fyp #podcast #viralkonten #tips';

  return (
    <div className="flex flex-col h-full w-full rounded-2xl bg-[#10161f] border border-[#202b3a] p-4 shadow-xl overflow-hidden">

      {/* ── TOP HEADER OF PREVIEW + SOCIAL PLATFORM SWITCHER ── */}
      <div className="flex items-center justify-between mb-3 px-1 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <ViewfinderCircleIcon className={`h-4 w-4 flex-shrink-0 ${isRenderedClip ? 'text-amber-400' : 'text-emerald-400'}`} />
          <div className="flex flex-col truncate">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 font-['Outfit'] truncate">
              {isRenderedClip ? 'OUTPUT CLIP PREVIEW' : 'VIDEO PREVIEW'}
            </h2>
            {clipTitle && (
              <span className="text-[10px] text-slate-400 truncate max-w-[120px] sm:max-w-[150px]" title={clipTitle}>
                {clipTitle}
              </span>
            )}
          </div>
        </div>

        {/* Platform Overlay Selector Pills (TikTok, Reels, Shorts, Clean) + Safe Zone */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-slate-900/90 border border-slate-800 shadow-inner">
            {[
              { id: 'tiktok', label: 'TikTok', icon: '🎵' },
              { id: 'reels', label: 'Reels', icon: '📸' },
              { id: 'shorts', label: 'Shorts', icon: '🔴' },
              { id: 'none', label: 'Off', icon: '🚫' }
            ].map(p => (
              <button
                key={p.id}
                type="button"
                onClick={() => changeOverlayMode(p.id as SocialOverlayType)}
                className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium transition-all ${
                  overlayMode === p.id
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold shadow-xs'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
                title={`Preview tampilan ${p.label}`}
              >
                <span>{p.icon}</span>
                <span className="hidden sm:inline text-[9.5px]">{p.label}</span>
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setShowSafeZone(!showSafeZone)}
            className={`flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium transition-all border ${
              showSafeZone
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold shadow-xs'
                : 'bg-slate-900/90 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle TikTok 9:16 Safe Zone Overlay"
          >
            <ShieldCheckIcon className="w-3 h-3 text-amber-400" />
            <span className="hidden md:inline text-[9.5px]">Safe Zone</span>
          </button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          CENTER STAGE: PHOTOREALISTIC WEBMOBILEFIRST iPHONE 17 PRO (2-LAYER COMPOSITE)
          - True 1:1 Apple Viewport Underneath (.iphone-screen: 354px × 771px)
          - Transparent Official iPhone 17 Pro Overlay (.iphone-frame-overlay: 389px × 800px)
          - Scaled cleanly via CSS transform to fit desktop displays
         ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 w-full items-center justify-center p-2 overflow-hidden relative select-none">

        {/* Subtle Ambient Radial Lighting Floor */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-white/[0.02] via-transparent to-transparent pointer-events-none -z-10" />

        {/* ─────────────────────────────────────────────────────────
            1:1 PHOTOREALISTIC iPHONE 17 PRO SCALED CONTAINER (389px × 800px)
           ───────────────────────────────────────────────────────── */}
        <div 
          className="relative shrink-0 flex items-center justify-center transition-transform duration-200 select-none"
          style={{
            width: '389px',
            height: '800px',
            transform: 'scale(0.74)',
            transformOrigin: 'center center'
          }}
        >
          {/* ─────────────────────────────────────────────────────────
              1. UNDERNEATH LAYER (.iphone-screen): Exact Apple Viewport
              - 354px width × 771px height
              - top: 14px, left: 18px
              - border-radius: 46px
              - overflow: hidden
             ───────────────────────────────────────────────────────── */}
          <div className="iphone-screen bg-[#07090e] absolute top-[14px] left-[18px] w-[354px] h-[771px] rounded-[46px] overflow-hidden shadow-2xl flex flex-col z-10">

            {/* Front Screen Diagonal Glass Reflection Highlight */}
            <div className="pointer-events-none absolute inset-0 z-20 bg-gradient-to-tr from-transparent via-white/[0.015] to-white/[0.04] rounded-[46px]" />

            {/* ── AUTHENTIC iOS STATUS BAR (Shows through transparent ears of PNG overlay) ── */}
            <div className="absolute top-[8px] inset-x-0 h-[27px] px-6 z-25 flex items-center justify-between text-white pointer-events-none select-none">
              
              {/* Left Flank: Authentic iOS Time (9:41 SF Pro Style) */}
              <div className="pl-1 flex items-center">
                <span className="text-[12.5px] font-semibold tracking-tight text-white drop-shadow-[0_1px_2px_rgba(0,0,0,0.7)] font-sans antialiased">
                  9:41
                </span>
              </div>

              {/* Right Flank: Authentic iOS Cellular (4 Stadium Pills) + Battery */}
              <div className="flex items-center gap-1.5 pr-1">
                {/* 1. iOS Cellular 4-Pill Signal Indicator */}
                <svg className="w-[17px] h-[11.5px] text-white shrink-0 drop-shadow-[0_1px_2px_rgba(0,0,0,0.7)]" viewBox="0 0 17.5 12" fill="none">
                  <rect x="0.5" y="8" width="3" height="4" rx="1.5" fill="currentColor" />
                  <rect x="5" y="5.5" width="3" height="6.5" rx="1.5" fill="currentColor" />
                  <rect x="9.5" y="3" width="3" height="9" rx="1.5" fill="currentColor" />
                  <rect x="14" y="0.5" width="3" height="11.5" rx="1.5" fill="currentColor" />
                </svg>

                {/* 2. iOS Battery Capsule */}
                <svg className="w-[24.5px] h-[11.5px] text-white shrink-0 drop-shadow-[0_1px_2px_rgba(0,0,0,0.7)]" viewBox="0 0 24.5 11.5" fill="none">
                  <rect x="0.6" y="0.6" width="20.4" height="10.3" rx="3.5" stroke="currentColor" strokeWidth="1.1" strokeOpacity="0.4" />
                  <rect x="2.1" y="2.1" width="13.8" height="7.3" rx="1.8" fill="currentColor" />
                  <path d="M22.5 4.1C23.3 4.1 23.7 4.5 23.7 5.2V6.3C23.7 7.0 23.3 7.4 22.5 7.4" stroke="currentColor" strokeWidth="1.1" strokeOpacity="0.4" strokeLinecap="round" fill="none" />
                </svg>
              </div>
            </div>

            {/* OLED Screen Content Container */}
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

                    {/* Subtitle floating in safe area */}
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
                    <div className="relative w-full h-full flex flex-col items-center justify-between bg-slate-950 overflow-hidden select-none">
                      {/* Top Window: Host (50%) */}
                      <div className="relative w-full h-1/2 bg-gradient-to-b from-[#0c1524] to-[#070b12] flex flex-col items-center justify-center border-b border-neutral-800 overflow-hidden">
                        <div className="absolute top-8 left-2 flex items-center gap-1 bg-black/60 backdrop-blur-xs px-1.5 py-0.5 rounded border border-cyan-500/30 z-10">
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
                          <span className="text-[7px] font-bold text-cyan-300 font-mono">HOST (Top 50%)</span>
                        </div>
                        <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-cyan-950 to-cyan-800 border border-cyan-400/40 flex items-center justify-center shadow-lg">
                          <UserIcon className="h-8 w-8 text-cyan-300" />
                        </div>
                        <span className="text-[7.5px] font-mono text-cyan-300 font-bold mt-1">Host Anchor</span>
                      </div>

                      {/* Bottom Window: Guest (50%) */}
                      <div className="relative w-full h-1/2 bg-gradient-to-b from-[#070b12] to-[#120d1c] flex flex-col items-center justify-center overflow-hidden">
                        <div className="absolute top-2 left-2 flex items-center gap-1 bg-black/60 backdrop-blur-xs px-1.5 py-0.5 rounded border border-amber-500/30 z-10">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
                          <span className="text-[7px] font-bold text-amber-300 font-mono">GUEST (Bottom 50%)</span>
                        </div>
                        <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-amber-950 to-amber-800 border border-amber-400/40 flex items-center justify-center shadow-lg">
                          <UserIcon className="h-8 w-8 text-amber-300" />
                        </div>
                        <span className="text-[7.5px] font-mono text-amber-300 font-bold mt-1">Guest Anchor</span>
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
                    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
                      <div
                        className="absolute inset-0 bg-cover bg-center filter blur-2xl scale-150 opacity-50"
                        style={{
                          backgroundImage: `radial-gradient(ellipse at 50% 35%, #0284c7 0%, #0f172a 60%, #030712 100%)`
                        }}
                      />
                      <div className="relative z-10 w-full h-[152px] -mt-[10%] bg-[#0c131f] border-y border-cyan-500/30 flex flex-col items-center justify-center shadow-lg overflow-hidden">
                        <div className="relative flex items-center gap-6 z-10">
                          <div className="flex flex-col items-center">
                            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-cyan-950 to-cyan-800 border border-cyan-400/50 flex items-center justify-center shadow-lg">
                              <UserIcon className="h-5 w-5 text-cyan-300" />
                            </div>
                            <span className="text-[7px] font-mono text-cyan-400 mt-1">Host</span>
                          </div>
                          <div className="flex flex-col items-center">
                            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-amber-950 to-amber-800 border border-amber-400/50 flex items-center justify-center shadow-lg">
                              <UserIcon className="h-5 w-5 text-amber-300" />
                            </div>
                            <span className="text-[7px] font-mono text-amber-400 mt-1">Guest</span>
                          </div>
                        </div>
                      </div>
                      <div
                        className="absolute z-20 w-full px-3 flex justify-center pointer-events-none transition-all duration-200"
                        style={{ top: `${subPosition}%` }}
                      >
                        {getSubtitleSample()}
                      </div>
                    </div>
                  ) : (
                    // 9:16 Smart Crop Simulated Layout
                    <div className="relative w-full h-full flex items-center justify-center bg-gradient-to-b from-[#0a101a] via-[#101b2b] to-[#060a10] overflow-hidden">
                      <div className="absolute top-[24%] flex flex-col items-center">
                        <div className="relative p-2 rounded-2xl border-2 border-emerald-400/60 bg-emerald-950/20 backdrop-blur-2xs shadow-[0_0_30px_rgba(16,185,129,0.2)]">
                          <div className="relative h-24 w-20 rounded-xl bg-gradient-to-b from-slate-800 to-slate-900 flex flex-col items-center justify-center border border-slate-700/60 shadow-inner">
                            <UserIcon className="h-12 w-12 text-emerald-300 drop-shadow-[0_2px_8px_rgba(16,185,129,0.4)]" />
                          </div>
                          <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-slate-950 px-2 py-0.5 rounded-full text-[7.5px] font-black uppercase tracking-wider font-['Outfit'] shadow-md flex items-center gap-1">
                            <SparklesIcon className="h-2.5 w-2.5" />
                            <span>Smart Follow</span>
                          </div>
                        </div>
                      </div>
                      <div
                        className="absolute z-20 w-full px-3 flex justify-center pointer-events-none transition-all duration-200"
                        style={{ top: `${subPosition}%` }}
                      >
                        {getSubtitleSample()}
                      </div>
                    </div>
                  )
                )}

                {/* ── 1. TIKTOK SOCIAL MEDIA UI OVERLAY ── */}
                {overlayMode === 'tiktok' && (
                  <div className="absolute inset-0 z-20 flex flex-col justify-between pointer-events-none p-3 pb-7 select-none">
                    
                    {/* Top Feed Tabs: Mengikuti | Untuk Anda | Search */}
                    <div className="pt-9 flex items-center justify-between text-xs font-bold text-white/90">
                      {/* Left balancing spacer to keep center tabs perfectly centered */}
                      <div className="w-6 h-6" />

                      {/* Center Feed Tabs: Mengikuti | Untuk Anda */}
                      <div className="flex items-center gap-3.5 text-[12.5px] drop-shadow-md">
                        <span className="text-white/60 font-semibold cursor-pointer pointer-events-auto hover:text-white transition-colors">
                          Mengikuti
                        </span>
                        <div className="relative cursor-pointer pointer-events-auto font-extrabold text-white">
                          <span>Untuk Anda</span>
                          <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-4 h-[2px] bg-white rounded-full shadow-xs" />
                        </div>
                      </div>

                      {/* Right: Search Icon Button */}
                      <button className="w-6 h-6 flex items-center justify-center p-0.5 text-white/90 pointer-events-auto hover:text-white cursor-pointer transition-transform active:scale-90">
                        <MagnifyingGlassIcon className="h-[18px] w-[18px] stroke-[2.3]" />
                      </button>
                    </div>

                    {/* Bottom Half: Creator Info + Right Social Actions */}
                    <div className="flex items-end justify-between w-full mt-auto">
                      
                      {/* Bottom-Left: Creator Username, Caption, Music Audio */}
                      <div className="flex-1 pr-2 pb-1 space-y-1 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)] text-left">
                        {/* Creator Handle */}
                        <div className="flex items-center gap-1">
                          <span className="font-['Outfit',_sans-serif] text-[12px] font-bold text-white tracking-wide">
                            @{displayAccount}
                          </span>
                          <CheckBadgeIcon className="h-3.5 w-3.5 text-sky-400" />
                        </div>

                        {/* Video Caption */}
                        <p className="text-[10.5px] leading-tight text-white/95 line-clamp-2 font-normal">
                          {displayCaption}
                        </p>

                        {/* Hashtags */}
                        <div className="flex items-center gap-1 text-[9.5px] text-white/80 font-bold">
                          {displayHashtags.split(' ').map((tag, idx) => (
                            <span key={idx}>{tag}</span>
                          ))}
                        </div>

                        {/* Music Audio Ticker */}
                        <div className="flex items-center gap-1.5 text-[9.5px] text-white/90 pt-0.5">
                          <MusicalNoteIcon className={`h-3 w-3 ${isPlaying ? 'animate-spin' : ''} stroke-[2]`} style={{ animationDuration: '4s' }} />
                          <div className="w-32 overflow-hidden whitespace-nowrap">
                            <p className="text-[9.5px] truncate">
                              Suara Asli - {displayAccount} (Podcast Viral)
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Right Side: TikTok Signature Floating Action Stack */}
                      <div className="flex flex-col items-center gap-2.5 pointer-events-auto shrink-0 pb-1">
                        
                        {/* 1. Creator Avatar with Follow Red Plus */}
                        <div className="relative mb-0.5">
                          <div className="h-8 w-8 rounded-full border-2 border-white bg-slate-800 overflow-hidden shadow-lg flex items-center justify-center">
                            <div className="w-full h-full rounded-full bg-gradient-to-tr from-sky-400 via-indigo-500 to-pink-500 flex items-center justify-center text-white text-[10px] font-bold">
                              {displayAccount.charAt(0).toUpperCase()}
                            </div>
                          </div>
                          <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-rose-500 text-white shadow-md hover:scale-110 cursor-pointer transition-transform">
                            <PlusIcon className="h-2 w-2 stroke-[3]" />
                          </div>
                        </div>

                        {/* 2. Heart / Like Button */}
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            setIsLiked(!isLiked);
                          }}
                          className="flex flex-col items-center group transition-transform active:scale-75 cursor-pointer"
                        >
                          <div className={`p-0.5 rounded-full ${isLiked ? 'text-rose-500' : 'text-white drop-shadow-md'}`}>
                            {isLiked ? (
                              <HeartIconSolid className="h-6 w-6 text-rose-500 animate-pulse" />
                            ) : (
                              <HeartIcon className="h-6 w-6 stroke-[2]" />
                            )}
                          </div>
                          <span className="text-[9.5px] font-bold text-white drop-shadow-md">
                            {isLiked ? '248.6K' : '248.5K'}
                          </span>
                        </button>

                        {/* 3. Comment Button */}
                        <div className="flex flex-col items-center cursor-pointer hover:scale-105 transition-transform">
                          <div className="p-0.5 text-white drop-shadow-md">
                            <ChatBubbleOvalLeftEllipsisIcon className="h-6 w-6 stroke-[2]" />
                          </div>
                          <span className="text-[9.5px] font-bold text-white drop-shadow-md">
                            1,842
                          </span>
                        </div>

                        {/* 4. Bookmark / Favorite Button */}
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            setIsBookmarked(!isBookmarked);
                          }}
                          className="flex flex-col items-center group transition-transform active:scale-75 cursor-pointer"
                        >
                          <div className={`p-0.5 rounded-full ${isBookmarked ? 'text-amber-400' : 'text-white drop-shadow-md'}`}>
                            {isBookmarked ? (
                              <BookmarkIconSolid className="h-6 w-6 text-amber-400" />
                            ) : (
                              <BookmarkIcon className="h-6 w-6 stroke-[2]" />
                            )}
                          </div>
                          <span className="text-[9.5px] font-bold text-white drop-shadow-md">
                            {isBookmarked ? '34.3K' : '34.2K'}
                          </span>
                        </button>

                        {/* 5. Share Button */}
                        <div className="flex flex-col items-center cursor-pointer hover:scale-105 transition-transform">
                          <div className="p-0.5 text-white drop-shadow-md">
                            <ShareIcon className="h-5 w-5 stroke-[2]" />
                          </div>
                          <span className="text-[9.5px] font-bold text-white drop-shadow-md">
                            12.8K
                          </span>
                        </div>

                        {/* 6. Rotating Vinyl Record Sound Disc (Tap to mute/unmute audio) */}
                        <div 
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleMute();
                          }}
                          className="relative mt-0.5 cursor-pointer hover:scale-110 active:scale-95 transition-transform"
                          title={isMuted ? 'Nyalakan Audio' : 'Matikan Audio'}
                        >
                          <div 
                            className={`h-7 w-7 rounded-full border border-slate-700 bg-neutral-900 shadow-xl overflow-hidden flex items-center justify-center ${
                              isPlaying && !isMuted ? 'animate-spin' : ''
                            }`}
                            style={{ animationDuration: '3.5s' }}
                          >
                            <div className="h-3.5 w-3.5 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center">
                              <span className={`h-1.5 w-1.5 rounded-full ${isMuted ? 'bg-rose-500' : 'bg-emerald-400'}`} />
                            </div>
                          </div>
                        </div>

                      </div>

                    </div>

                    {/* Bottom TikTok Tab Navigation Bar with Authentic Icons */}
                    <div className="pt-2 border-t border-white/10 flex items-center justify-between px-0.5 pointer-events-auto bg-gradient-to-t from-black/80 via-black/40 to-transparent">
                      
                      {/* 1. Beranda */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveBottomTab('home');
                        }}
                        className="flex flex-col items-center justify-center flex-1 cursor-pointer transition-colors group"
                      >
                        {activeBottomTab === 'home' ? (
                          <HomeIconSolid className="h-[18px] w-[18px] text-white drop-shadow-sm" />
                        ) : (
                          <HomeIcon className="h-[18px] w-[18px] text-white/70 group-hover:text-white stroke-[2]" />
                        )}
                        <span className={`text-[8px] mt-0.5 leading-none ${activeBottomTab === 'home' ? 'text-white font-extrabold' : 'text-white/70 font-semibold group-hover:text-white'}`}>
                          Beranda
                        </span>
                      </button>

                      {/* 2. Teman */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveBottomTab('friends');
                        }}
                        className="flex flex-col items-center justify-center flex-1 cursor-pointer transition-colors group"
                      >
                        {activeBottomTab === 'friends' ? (
                          <UserGroupIconSolid className="h-[18px] w-[18px] text-white drop-shadow-sm" />
                        ) : (
                          <UserGroupIcon className="h-[18px] w-[18px] text-white/70 group-hover:text-white stroke-[2]" />
                        )}
                        <span className={`text-[8px] mt-0.5 leading-none ${activeBottomTab === 'friends' ? 'text-white font-extrabold' : 'text-white/70 font-semibold group-hover:text-white'}`}>
                          Teman
                        </span>
                      </button>

                      {/* 3. Center Create [+] Button */}
                      <div 
                        onClick={(e) => e.stopPropagation()}
                        className="flex flex-col items-center justify-center flex-1 cursor-pointer hover:scale-105 active:scale-95 transition-transform"
                        title="Buat Video"
                      >
                        <div className="relative flex h-[22px] w-[34px] items-center justify-center">
                          <div className="absolute inset-y-0 left-0 w-[27px] rounded-[7px] bg-[#00f2fe]" />
                          <div className="absolute inset-y-0 right-0 w-[27px] rounded-[7px] bg-[#fe0979]" />
                          <div className="relative flex h-full w-[29px] items-center justify-center rounded-[6px] bg-white text-black shadow-xs">
                            <PlusIcon className="h-3.5 w-3.5 stroke-[3] text-black" />
                          </div>
                        </div>
                      </div>

                      {/* 4. Kotak Masuk */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveBottomTab('inbox');
                        }}
                        className="flex flex-col items-center justify-center flex-1 cursor-pointer transition-colors group"
                      >
                        <div className="relative">
                          {activeBottomTab === 'inbox' ? (
                            <ChatBubbleOvalLeftEllipsisIconSolid className="h-[18px] w-[18px] text-white drop-shadow-sm" />
                          ) : (
                            <ChatBubbleOvalLeftEllipsisIcon className="h-[18px] w-[18px] text-white/70 group-hover:text-white stroke-[2]" />
                          )}
                          <span className="absolute -top-0.5 -right-1 h-1.5 w-1.5 rounded-full bg-rose-500 ring-1 ring-black" />
                        </div>
                        <span className={`text-[8px] mt-0.5 leading-none whitespace-nowrap ${activeBottomTab === 'inbox' ? 'text-white font-extrabold' : 'text-white/70 font-semibold group-hover:text-white'}`}>
                          Kotak Masuk
                        </span>
                      </button>

                      {/* 5. Profil */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveBottomTab('profile');
                        }}
                        className="flex flex-col items-center justify-center flex-1 cursor-pointer transition-colors group"
                      >
                        {activeBottomTab === 'profile' ? (
                          <UserIconSolid className="h-[18px] w-[18px] text-white drop-shadow-sm" />
                        ) : (
                          <UserIconOutline className="h-[18px] w-[18px] text-white/70 group-hover:text-white stroke-[2]" />
                        )}
                        <span className={`text-[8px] mt-0.5 leading-none ${activeBottomTab === 'profile' ? 'text-white font-extrabold' : 'text-white/70 font-semibold group-hover:text-white'}`}>
                          Profil
                        </span>
                      </button>

                    </div>

                  </div>
                )}

                {/* ── 2. INSTAGRAM REELS UI OVERLAY ── */}
                {overlayMode === 'reels' && (
                  <div className="absolute inset-0 pointer-events-none z-25 flex flex-col justify-between overflow-hidden">
                    {/* Top Reels Header (Below iOS 18/26 Status Bar) */}
                    <div className="pt-[44px] px-3.5 flex items-center justify-between text-white drop-shadow-[0_1px_3px_rgba(0,0,0,0.8)]">
                      <div className="flex items-center gap-1">
                        <span className="text-[12px] font-bold tracking-tight">Reels</span>
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                        </svg>
                      </div>
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" />
                      </svg>
                    </div>

                    {/* Right Action Icons Column (Reels Style) */}
                    <div className="absolute right-2.5 bottom-12 flex flex-col items-center gap-3 z-25 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
                        </svg>
                        <span className="text-[7.5px] font-semibold text-white mt-0.5">184K</span>
                      </div>

                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 0 1-.923 1.785A5.969 5.969 0 0 0 6 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337Z" />
                        </svg>
                        <span className="text-[7.5px] font-semibold text-white mt-0.5">1,290</span>
                      </div>

                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                        </svg>
                        <span className="text-[7.5px] font-semibold text-white mt-0.5">42K</span>
                      </div>

                      {/* 3 dots */}
                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" />
                        </svg>
                      </div>

                      {/* Audio square thumbnail */}
                      <div className="w-6 h-6 rounded-md border border-white/60 bg-slate-900 p-0.5 flex items-center justify-center">
                        <div className="w-full h-full bg-gradient-to-tr from-fuchsia-600 to-amber-500 rounded-sm flex items-center justify-center text-[7px] text-white">
                          ♫
                        </div>
                      </div>
                    </div>

                    {/* Bottom Left Creator & Caption Info */}
                    <div className="px-3 pb-10 flex flex-col text-left z-25 max-w-[80%] drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)]">
                      <div className="flex items-center gap-1.5">
                        <div className="w-6 h-6 rounded-full border border-white p-0.5 bg-gradient-to-tr from-yellow-400 via-rose-500 to-purple-600 flex items-center justify-center">
                          <div className="w-full h-full rounded-full bg-slate-950 flex items-center justify-center text-white text-[8px] font-bold">
                            {displayAccount.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <span className="text-[9.5px] font-bold text-white tracking-tight">@{displayAccount}</span>
                        <button className="px-2 py-0.5 rounded-md border border-white/70 text-[8px] font-bold text-white ml-1">
                          Ikuti
                        </button>
                      </div>
                      <p className="text-[8.5px] text-white/95 leading-tight mt-1 line-clamp-1">
                        {displayCaption}
                      </p>
                      <div className="flex items-center gap-1 mt-0.5 text-[7.5px] text-white/80">
                        <span>♫ Audio asli • {displayAccount}</span>
                      </div>
                    </div>

                    {/* Bottom Home Indicator */}
                    <div className="absolute inset-x-0 bottom-0.5 flex justify-center pointer-events-none">
                      <div className="w-20 h-0.5 bg-white/70 rounded-full" />
                    </div>
                  </div>
                )}

                {/* ── 3. YOUTUBE SHORTS UI OVERLAY ── */}
                {overlayMode === 'shorts' && (
                  <div className="absolute inset-0 pointer-events-none z-25 flex flex-col justify-between overflow-hidden">
                    {/* Top Shorts Header (Below iOS 18/26 Status Bar) */}
                    <div className="pt-[44px] px-3.5 flex items-center justify-between text-white drop-shadow-[0_1px_3px_rgba(0,0,0,0.8)]">
                      <div className="flex items-center gap-1">
                        <span className="text-[12px] font-black tracking-tight text-white font-['Outfit']">Shorts</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                        </svg>
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 12.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 18.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z" />
                        </svg>
                      </div>
                    </div>

                    {/* Right Action Icons Column (Shorts Style) */}
                    <div className="absolute right-2.5 bottom-12 flex flex-col items-center gap-2.5 z-25 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white fill-white" viewBox="0 0 24 24">
                          <path d="M7.493 18.5c-.425 0-.82-.236-.975-.632A7.48 7.48 0 0 1 6 15.125c0-1.75.599-3.358 1.603-4.633.441-.56.637-1.282.527-1.986l-.27-1.73a2.25 2.25 0 0 1 1.763-2.553l.422-.065c1.196-.184 2.378.508 2.766 1.62.339.972.84 1.879 1.48 2.686.438.552 1.05.94 1.734 1.085 1.517.323 2.628 1.636 2.628 3.197 0 1.835-1.464 3.325-3.298 3.344l-3.076.033c-.76.008-1.487.35-1.988.946l-.578.69a1.05 1.05 0 0 1-.808.415Z" />
                        </svg>
                        <span className="text-[7.5px] font-semibold text-white mt-0.5">312K</span>
                      </div>

                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white fill-white rotate-180" viewBox="0 0 24 24">
                          <path d="M7.493 18.5c-.425 0-.82-.236-.975-.632A7.48 7.48 0 0 1 6 15.125c0-1.75.599-3.358 1.603-4.633.441-.56.637-1.282.527-1.986l-.27-1.73a2.25 2.25 0 0 1 1.763-2.553l.422-.065c1.196-.184 2.378.508 2.766 1.62.339.972.84 1.879 1.48 2.686.438.552 1.05.94 1.734 1.085 1.517.323 2.628 1.636 2.628 3.197 0 1.835-1.464 3.325-3.298 3.344l-3.076.033c-.76.008-1.487.35-1.988.946l-.578.69a1.05 1.05 0 0 1-.808.415Z" />
                        </svg>
                        <span className="text-[7.5px] font-semibold text-white mt-0.5">Dislike</span>
                      </div>

                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white fill-white" viewBox="0 0 24 24">
                          <path fillRule="evenodd" d="M4.848 2.771A49.144 49.144 0 0 1 12 2.25c2.43 0 4.817.177 7.152.521 1.942.286 3.348 1.984 3.348 3.946v6.262c0 1.962-1.406 3.66-3.348 3.946-1.579.233-3.208.384-4.871.448l-4.103 3.518a.75.75 0 0 1-1.238-.57v-3.084A50.04 50.04 0 0 1 4.848 16.98C2.906 16.694 1.5 14.996 1.5 13.034V6.77c0-1.962 1.406-3.66 3.348-3.946Z" clipRule="evenodd" />
                        </svg>
                        <span className="text-[7.5px] font-semibold text-white mt-0.5">2.4K</span>
                      </div>

                      <div className="flex flex-col items-center">
                        <svg className="w-5 h-5 text-white fill-white" viewBox="0 0 24 24">
                          <path fillRule="evenodd" d="M15.75 4.5a3 3 0 1 1 .825 2.066l-8.421 4.679a3.002 3.002 0 0 1 0 1.51l8.421 4.679a3 3 0 1 1-.729 1.31l-8.421-4.678a3 3 0 1 1 0-4.132l8.421-4.679a3 3 0 0 1-.096-.755Z" clipRule="evenodd" />
                        </svg>
                        <span className="text-[7.5px] font-semibold text-white mt-0.5">Bagikan</span>
                      </div>

                      {/* Sound square */}
                      <div className="w-6 h-6 rounded-md border border-white/60 bg-red-600 p-0.5 flex items-center justify-center">
                        <span className="text-[8px] text-white">▶</span>
                      </div>
                    </div>

                    {/* Bottom Left Shorts Creator & Caption Info */}
                    <div className="px-3 pb-10 flex flex-col text-left z-25 max-w-[80%] drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)]">
                      <div className="flex items-center gap-1.5">
                        <div className="w-5 h-5 rounded-full bg-red-600 flex items-center justify-center text-white text-[8px] font-bold">
                          {displayAccount.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-[9.5px] font-bold text-white tracking-tight">@{displayAccount}</span>
                        <button className="px-2 py-0.5 rounded-full bg-white text-black text-[7.5px] font-black uppercase tracking-wider ml-1">
                          Subscribe
                        </button>
                      </div>
                      <p className="text-[8.5px] text-white/95 leading-tight mt-1 line-clamp-1">
                        {displayCaption}
                      </p>
                    </div>

                    {/* Bottom Home Indicator */}
                    <div className="absolute inset-x-0 bottom-0.5 flex justify-center pointer-events-none">
                      <div className="w-20 h-0.5 bg-white/70 rounded-full" />
                    </div>
                  </div>
                )}

                {/* ── LIVE GLASS WATERMARK BADGES (Top Safe Zone) ── */}
                {watermarkEnabled && !isRenderedClip && (sourceWatermark || accountWatermark) && (
                  <div className="absolute top-11 inset-x-3.5 flex items-center justify-between pointer-events-none z-30">
                    {sourceWatermark ? (
                      <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#121418]/75 backdrop-blur-md border border-white/15 shadow-[0_4px_12px_rgba(0,0,0,0.5)] max-w-[55%]">
                        <span className="text-[7.5px] text-white/90 font-medium truncate tracking-wide">
                          <span className="text-cyan-400 mr-1 text-[6.5px]">▶</span>Source: {sourceWatermark}
                        </span>
                      </div>
                    ) : <div />}

                    {accountWatermark ? (
                      <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#121418]/75 backdrop-blur-md border border-white/15 shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
                        <span className="text-[8px] font-bold text-amber-300 font-mono tracking-tight">
                          {accountWatermark.startsWith('@') ? accountWatermark : `@${accountWatermark}`}
                        </span>
                      </div>
                    ) : null}
                  </div>
                )}

                {/* SAFE ZONE OVERLAY GUIDE */}
                {showSafeZone && (
                  <div className="absolute inset-x-2 top-11 bottom-14 border-2 border-dashed border-amber-400/80 rounded-2xl pointer-events-none z-30 flex flex-col justify-between p-2">
                    <div className="bg-amber-500 text-black font-mono font-bold text-[8px] px-1.5 py-0.5 rounded self-start shadow-xs">
                      TIKTOK SAFE ZONE (9:16)
                    </div>
                    <div className="bg-amber-500 text-black font-mono font-bold text-[8px] px-1.5 py-0.5 rounded self-end shadow-xs">
                      CONTENT CLEAR AREA
                    </div>
                  </div>
                )}

                {/* Video Scrubber Bar on Phone Screen */}
                <div className="absolute bottom-0 inset-x-0 h-1 bg-white/20 z-30 pointer-events-none">
                  <div 
                    className="h-full bg-emerald-500 transition-all duration-100"
                    style={{ width: `${playbackProgress}%` }}
                  />
                </div>

              </div>

              {/* ─────────────────────────────────────────────────────
                  AUTHENTIC iOS HOME INDICATOR BAR
                  - White rounded bar at bottom center
                 ───────────────────────────────────────────────────── */}
              <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 h-[3.5px] w-28 rounded-full bg-white/70 shadow-sm pointer-events-none z-40" />

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
                e.currentTarget.src = 'https://www.webmobilefirst.com/img/mockups/mockup-apple-iphone-17-pro-2025-transparent.png';
              }}
              alt="Apple iPhone 17 Pro Frame"
              className="iphone-frame-overlay absolute inset-0 w-[389px] h-[800px] pointer-events-none z-30 object-contain select-none"
              draggable={false}
            />

          </div>

        </div>

      {/* ── STUDIO TRANSPORT BAR ── */}
      <div className="w-full max-w-[480px] bg-[#14161C] border border-white/[0.08] rounded-xl px-3.5 py-2.5 flex items-center gap-3 shadow-lg select-none mb-1">
        {/* Primary Transport Play/Pause */}
        <button
          type="button"
          onClick={togglePlay}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-[#FF5500] hover:bg-[#E04B00] text-white shadow-sm transition active:scale-95"
          aria-label={isPlaying ? 'Jeda preview' : 'Putar preview'}
          title={isPlaying ? 'Jeda preview' : 'Putar preview'}
        >
          {isPlaying ? (
            <PauseIcon className="h-4 w-4 text-white" />
          ) : (
            <PlayIcon className="h-4 w-4 ml-0.5 text-white" />
          )}
        </button>

        {/* Timeline and Time Readout */}
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between text-[11px] font-mono text-white/90">
            <span className="text-white font-semibold">{formatTime(currentTime)}</span>
            <span className="text-white/40">/{formatTime(duration || 45)}</span>
          </div>
          <input
            type="range"
            min={0}
            max={duration || 45}
            value={currentTime}
            onChange={(e) => handleSeek(Number(e.target.value))}
            className="ios-media-scrubber block w-full cursor-pointer"
            style={{ '--ios-scrubber-progress': `${playbackProgress}%` } as React.CSSProperties}
            aria-label="Posisi video"
          />
        </div>

        {/* Secondary Controls: Mute + Playback Rate */}
        <div className="flex flex-shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={toggleMute}
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/[0.08] bg-[#1A1D24] text-white/70 hover:text-white transition"
            title={isMuted ? 'Nyalakan suara' : 'Matikan suara'}
          >
            {isMuted ? <SpeakerXMarkIcon className="h-3.5 w-3.5 text-rose-400" /> : <SpeakerWaveIcon className="h-3.5 w-3.5" />}
          </button>

          <button
            type="button"
            onClick={handleRateChange}
            className="h-7 min-w-8 rounded-lg border border-white/[0.08] bg-[#1A1D24] px-1.5 text-[10.5px] font-mono font-semibold text-white/80 hover:text-white transition"
            title="Kecepatan pemutaran"
          >
            {playbackRate}x
          </button>
        </div>
      </div>

    </div>
  );
};

export const IPhoneSocialPreview = PhonePreview;

