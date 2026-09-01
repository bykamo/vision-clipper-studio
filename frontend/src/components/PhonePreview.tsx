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
  framingMode: 'smart_crop' | 'fit_blur';
  selectedPresetId: string;
  videoSource?: string;
  previewClip?: { start: number; end: number } | null;
}

export const PhonePreview: React.FC<PhonePreviewProps> = ({
  framingMode,
  selectedPresetId,
  videoSource,
  previewClip
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showSafeArea, setShowSafeArea] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1.0);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Auto-seek and loop within clip range when previewClip is set
  useEffect(() => {
    if (previewClip && videoRef.current && videoStreamUrl) {
      videoRef.current.currentTime = previewClip.start;
      void videoRef.current.play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    }
  }, [previewClip?.start, previewClip?.end]);

  // Enforce clip end boundary
  const handleTimeUpdateWithClip = () => {
    handleTimeUpdate();
    if (previewClip && videoRef.current) {
      if (videoRef.current.currentTime >= previewClip.end) {
        videoRef.current.currentTime = previewClip.start;
      }
    }
  };

  // Check if source is a local playable video file path
  const isLocalFile = videoSource && !videoSource.startsWith('http://') && !videoSource.startsWith('https://');
  const videoStreamUrl = isLocalFile ? `/api/video-stream?path=${encodeURIComponent(videoSource.trim())}` : '';

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || 0);
      videoRef.current.muted = isMuted;
      videoRef.current.volume = 1;
      if (previewClip) {
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
        await video.play();
        setIsPlaying(true);
      } catch {
        setIsPlaying(false);
      }
      return;
    }

    video.pause();
    setIsPlaying(false);
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
    const muted = !videoRef.current?.muted;
    if (videoRef.current) videoRef.current.muted = muted;
    setIsMuted(muted);
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
            <span className="text-white drop-shadow-[0_2px_4px_rgba(0,0,0,1)] text-base">&nbsp;✨</span>
          </div>
        );
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col h-full w-full rounded-2xl bg-[#10161f] border border-[#202b3a] p-4 shadow-xl overflow-hidden">

      {/* ── TOP HEADER OF PREVIEW ── */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <ViewfinderCircleIcon className="h-4 w-4 text-emerald-400" />
          <div className="flex flex-col">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 font-['Outfit']">VIDEO PREVIEW</h2>
          </div>
        </div>

        {/* Safe Area button. Layout follows setting in left panel. */}
        <div className="flex items-center">
          <button
            type="button"
            onClick={() => setShowSafeArea(!showSafeArea)}
            className={`flex items-center gap-1 px-2 py-1 rounded-lg border text-[11px] font-medium transition-all ${
              showSafeArea
                ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400'
                : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200'
            }`}
            title="Tampilkan Safe Area Guide (Batas ikon TikTok/Reels)"
          >
            <SparklesIcon className="h-3 w-3" />
            <span>Safe Area</span>
          </button>
        </div>
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
              <div className="relative w-full h-full bg-slate-950 overflow-hidden flex items-center justify-center">

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
                        framingMode === 'fit_blur'
                          ? 'w-full h-auto max-h-[220px] object-contain shadow-2xl border-y border-white/10'
                          : 'w-full h-full object-cover'
                      }`}
                      playsInline
                    />

                    {/* Subtitle floating in safe area */}
                    <div className="absolute top-[60%] z-20 w-full px-3 flex justify-center pointer-events-none">
                      {getSubtitleSample()}
                    </div>
                  </div>
                ) : (
                  // ── EMPTY STATE GRAPHICS (NO SOURCE VIDEO SELECTED) ──
                  framingMode === 'fit_blur' ? (
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
                      <div className="absolute top-[60%] z-20 w-full px-3 flex justify-center">
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
                      <div className="absolute top-[60%] z-20 w-full px-3 flex justify-center">
                        {getSubtitleSample()}
                      </div>
                    </div>
                  )
                )}

                {/* Safe Area Guides Overlay */}
                {showSafeArea && (
                  <div className="absolute inset-0 pointer-events-none z-30 border-2 border-dashed border-emerald-400/40 m-3 rounded-2xl flex flex-col justify-between p-2">
                    <div className="text-[8px] font-mono text-emerald-400/80 uppercase">Top Safe Zone</div>
                    <div className="flex justify-between items-center text-[7px] font-mono text-emerald-400/60 uppercase px-1">
                      <span>Right UI Icons</span>
                    </div>
                    <div className="text-[8px] font-mono text-emerald-400/80 uppercase text-center pb-1">
                      Bottom Caption Safe Zone
                    </div>
                  </div>
                )}

              </div>

            </div>

          </div>

        </div>

      </div>

      {/* ── PREVIEW TOOLBAR (BOTTOM SCRUBBER & CONTROLS) ── */}
      <div className="mt-5 rounded-xl bg-[#0d131c] border border-[#222c3a] p-3 flex flex-col gap-2.5 shadow-lg">
        <div className="flex items-center gap-3">

          {/* Play/Pause Button */}
          <button
            type="button"
            onClick={togglePlay}
            className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors shadow-sm flex-shrink-0"
          >
            {isPlaying ? <PauseIcon className="h-3.5 w-3.5" /> : <PlayIcon className="h-3.5 w-3.5 ml-0.5" />}
          </button>

          {/* Mute Toggle */}
          <button
            type="button"
            onClick={toggleMute}
            className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors flex-shrink-0"
            aria-label={isMuted ? 'Nyalakan suara preview' : 'Matikan suara preview'}
            title={isMuted ? 'Nyalakan suara' : 'Matikan suara'}
          >
            {isMuted ? <SpeakerXMarkIcon className="h-3.5 w-3.5" /> : <SpeakerWaveIcon className="h-3.5 w-3.5" />}
          </button>

          {/* Time Counter */}
          <span className="text-[11px] font-mono text-slate-400 tracking-tight flex-shrink-0">
            {duration > 0 ? `${formatTime(currentTime)} / ${formatTime(duration)}` : '--:-- / --:--'}
          </span>

          {/* Timeline Track */}
          <div className="relative flex-1 flex items-center group cursor-pointer">
            <input
              type="range"
              min="0"
              max={duration > 0 ? duration : 100}
              disabled={duration === 0}
              value={duration > 0 ? currentTime : 0}
              onChange={(e) => handleSeek(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed"
            />
          </div>

          {/* Speed Toggle */}
          <button
            type="button"
            onClick={handleRateChange}
            className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300 hover:text-white"
          >
            {playbackRate}x
          </button>
        </div>
      </div>

    </div>
  );
};
