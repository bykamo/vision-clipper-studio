import React, { useState, useEffect, useRef } from 'react';
import { 
  ScissorsIcon,
  ShoppingBagIcon,
  FolderIcon,
  FolderOpenIcon,
  FolderArrowDownIcon,
  AdjustmentsHorizontalIcon,
  BoltIcon,
  PaintBrushIcon,
  XMarkIcon,
  ChevronDownIcon,
  DocumentTextIcon,
  DocumentDuplicateIcon,
  CheckIcon,
  FireIcon,
  MicrophoneIcon,
  ChatBubbleBottomCenterTextIcon,
  EyeSlashIcon,
  VideoCameraIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import { 
  StopIcon as StopIconSolid,
  FilmIcon as FilmIconSolid
} from '@heroicons/react/24/solid';
import confetti from 'canvas-confetti';
import { SubtitleStyleConfig } from '../types';
import { SUBTITLE_PRESETS } from '../data/subtitlePresets';
import { FileExplorerModal } from './FileExplorerModal';
import { PhonePreview } from './PhonePreview';

interface GeneratedClipItem {
  id: string;
  title: string;
  filename?: string;
  duration?: string;
}

export const SimpleClipperDashboard: React.FC = () => {
  // Navigation Tabs (Modes)
  const [activeTab, setActiveTab] = useState<'hook' | 'affiliate'>('hook');

  // Video Source State
  const [videoPathInput, setVideoPathInput] = useState<string>('');
  const [showExplorerModal, setShowExplorerModal] = useState<boolean>(false);

  // Settings State
  const [clipCount, setClipCount] = useState<number>(4);
  const [transcriptionModel, setTranscriptionModel] = useState<string>('groq');
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('tiktok_viral');
  const [framingMode, setFramingMode] = useState<'smart_crop' | 'fit_blur'>('smart_crop');

  // Generated Clips & Output Folder
  const [outputDir, setOutputDir] = useState<string>('');
  const [generatedClips, setGeneratedClips] = useState<GeneratedClipItem[]>([]);
  const [showFolderModal, setShowFolderModal] = useState(false);

  // Processing State
  const [isProcessing, setIsProcessing] = useState(false);
  const [status, setStatus] = useState<'ready' | 'processing' | 'complete' | 'error'>('ready');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([
    "[SYSTEM] VisionClipper Studio Engine siap.",
    "[SYSTEM] Masukkan path file video atau URL YouTube, lalu klik 'Generate Clips'."
  ]);

  const [copiedLogs, setCopiedLogs] = useState(false);
  const [serverModalOpen, setServerModalOpen] = useState(false);
  const [serverOffline, setServerOffline] = useState(false);

  const terminalRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto Scroll Terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Clean up EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Handle Preset Change
  const handleSelectPreset = (preset: SubtitleStyleConfig) => {
    setSelectedPresetId(preset.presetId);
  };

  // Start Real Processing via SSE
  const handleStartProcessing = () => {
    const source = videoPathInput.trim();
    if (!source) {
      alert('Silakan masukkan file path video atau URL YouTube terlebih dahulu!');
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setIsProcessing(true);
    setStatus('processing');
    setProgress(0);
    setGeneratedClips([]);
    setOutputDir('');

    const startTimestamp = new Date().toTimeString().split(' ')[0];
    setLogs([
      `[${startTimestamp}] [SYSTEM] Inisialisasi ${activeTab.toUpperCase()} CLIPPER ENGINE...`,
      `[${startTimestamp}] [SYSTEM] Model AI: ${transcriptionModel} | Subtitle Style: ${selectedPresetId}`,
      `[${startTimestamp}] [SYSTEM] Sumber video: ${source}`,
      `[${startTimestamp}] [SYSTEM] Memulai proses ekstraksi & analisis hook viral...`
    ]);

    const streamUrl = `/stream?mode=${encodeURIComponent(activeTab)}&source_type=file&source=${encodeURIComponent(source)}&num_clips=${encodeURIComponent(clipCount)}&sub_style=${encodeURIComponent(selectedPresetId)}&whisper_model=${encodeURIComponent(transcriptionModel)}&framing_mode=${encodeURIComponent(framingMode)}`;
    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      const data = event.data;

      if (data === '[PROCESS_COMPLETE]') {
        const doneTimestamp = new Date().toTimeString().split(' ')[0];
        setLogs(prev => [...prev, `[${doneTimestamp}] [SYSTEM] ✅ Semua klip berhasil diproses dan disimpan!`]);
        setProgress(100);
        setStatus('complete');
        setIsProcessing(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      } else if (data === '[PROCESS_FAILED]') {
        const failTimestamp = new Date().toTimeString().split(' ')[0];
        setLogs(prev => [...prev, `[${failTimestamp}] [SYSTEM] ❌ Pemrosesan gagal. Silakan periksa log.`]);
        setStatus('error');
        setIsProcessing(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      } else if (data === '[HEARTBEAT]') {
        // Keep-alive heartbeat
      } else {
        // Parse output directory
        if (data.includes('Outputs will be saved to:')) {
          const match = data.match(/Outputs will be saved to:\s*(.*)/);
          if (match && match[1]) {
            setOutputDir(match[1].trim());
          }
        }

        // Parse rendered clip title
        if (data.includes('Rendering Subtitles, Audio Enhancer, and Color Grading for Clip')) {
          const clipMatch = data.match(/for Clip (\d+):\s*(.*)/);
          if (clipMatch) {
            const index = clipMatch[1];
            const title = clipMatch[2];
            setGeneratedClips(prev => {
              if (prev.some(c => c.id === index)) return prev;
              return [...prev, { id: index, title: title }];
            });
          }
        }

        // Parse Progress percentage
        const progressMatch = data.match(/([\d.]+)%/);
        if (progressMatch) {
          const p = parseFloat(progressMatch[1]);
          if (!isNaN(p)) {
            setProgress(Math.min(100, Math.max(0, Math.round(p))));
          }
        }

        // Check if log is a progress bar update line
        setLogs(prev => {
          if (data.includes('Progress') || data.includes('%|')) {
            const lastLog = prev[prev.length - 1];
            if (lastLog && (lastLog.includes('Progress') || lastLog.includes('%|'))) {
              return [...prev.slice(0, -1), data];
            }
          }
          return [...prev, data];
        });
      }
    };

    es.onerror = (err) => {
      console.error("SSE Error:", err);
      const errTimestamp = new Date().toTimeString().split(' ')[0];
      setLogs(prev => [...prev, `[${errTimestamp}] [SYSTEM] ⚠️ Koneksi ke background worker terputus.`]);
      setStatus('error');
      setIsProcessing(false);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  };

  // Stop / Cancel Processing
  const handleStopProcessing = async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    const stopTime = new Date().toTimeString().split(' ')[0];
    setLogs(prev => [...prev, `[${stopTime}] [SYSTEM] ⛔ Mengirim sinyal pembatalan ke backend...`]);

    try {
      await fetch('/cancel', { method: 'POST' });
      setLogs(prev => [...prev, `[${stopTime}] [SYSTEM] ⛔ Proses berhasil dihentikan oleh pengguna.`]);
    } catch (e: any) {
      setLogs(prev => [...prev, `[${stopTime}] [SYSTEM] Error cancel: ${e.message}`]);
    } finally {
      setIsProcessing(false);
      setStatus('ready');
    }
  };

  // Open output folder
  const handleOpenFolder = async () => {
    if (!outputDir) return;
    try {
      const res = await fetch('/api/open-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: outputDir })
      });
      const data = await res.json();
      if (data.error) {
        alert("Gagal membuka folder: " + data.error);
      }
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  // Shutdown Server
  const handleConfirmShutdown = async () => {
    setServerModalOpen(false);
    try {
      await fetch('/shutdown', { method: 'POST' });
    } catch (e) {}
    setServerOffline(true);
  };

  // Copy Logs
  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopiedLogs(true);
    setTimeout(() => setCopiedLogs(false), 1500);
  };

  // Notion-style icon resolver for Subtitle presets
  const getPresetNotionIcon = (presetId: string) => {
    switch (presetId) {
      case 'tiktok_viral':
        return <FireIcon className="h-3.5 w-3.5 stroke-[2] text-amber-400" />;
      case 'classic_karaoke':
        return <MicrophoneIcon className="h-3.5 w-3.5 stroke-[2] text-cyan-400" />;
      case 'minimalist':
        return <SparklesIcon className="h-3.5 w-3.5 stroke-[2] text-emerald-400" />;
      case 'word_pop':
        return <BoltIcon className="h-3.5 w-3.5 stroke-[2] text-yellow-400" />;
      case 'no_subtitle':
      case 'none':
        return <EyeSlashIcon className="h-3.5 w-3.5 stroke-[2] text-rose-400" />;
      default:
        return <FireIcon className="h-3.5 w-3.5 stroke-[2] text-amber-400" />;
    }
  };

  // Obsidian Slate Dark Theme Styling
  const themeClasses = {
    bg: 'bg-[#0b0f14]',
    header: 'bg-[#0f141b] border-slate-800/80 text-slate-100',
    sidebar: 'bg-[#0e1218] border-slate-800/80 text-slate-200',
    card: 'bg-[#131820] border-slate-800/80 text-slate-100',
    input: 'bg-[#0b0f14] border-slate-800 text-emerald-300 placeholder:text-slate-600 focus:border-emerald-600',
    accentText: 'text-emerald-400',
    accentBg: 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs',
    pillActive: 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40 shadow-xs',
    outputBanner: 'bg-[#131820] border-slate-800',
    actionBtn: 'bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-xs',
    footer: 'bg-[#0e1218] border-slate-800 text-slate-400'
  };

  if (serverOffline) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center bg-[#09090b] text-rose-400 font-['Instrument_Sans',_sans-serif] gap-4 p-4 text-center">
        <div className="text-5xl">⚡</div>
        <h1 className="text-xl font-bold text-white font-['Outfit']">SERVER OFFLINE</h1>
        <p className="text-xs text-slate-400 max-w-sm">
          VisionClipper Studio telah dinonaktifkan. Anda dapat menutup tab ini atau menjalankan kembali lewat terminal.
        </p>
      </div>
    );
  }

  return (
    <div className={`flex h-screen w-screen flex-col overflow-hidden ${themeClasses.bg} font-['Instrument_Sans',_'Plus_Jakarta_Sans',_sans-serif] antialiased`}>
      
      {/* ─────────────────────────────────────────────────────────────
          1. TOP APP HEADER
         ───────────────────────────────────────────────────────────── */}
      <header className={`flex h-14 items-center justify-between border-b ${themeClasses.header} px-5 shadow-md z-20`}>
        
        {/* Left: Brand Logo & Title */}
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${themeClasses.accentBg} text-white shadow-sm`}>
            <FilmIconSolid className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-2">
            <h1 className="font-['Outfit',_sans-serif] text-base font-extrabold tracking-tight text-white">
              VisionClipper <span className={themeClasses.accentText}>Studio</span>
            </h1>
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
              v2.0
            </span>
          </div>
        </div>

        {/* Center: Mode Switcher Pills */}
        <div className="flex items-center rounded-full bg-slate-900/90 p-1 border border-slate-800 font-['Outfit',_sans-serif]">
          <button
            onClick={() => setActiveTab('hook')}
            className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold transition-all ${
              activeTab === 'hook'
                ? themeClasses.pillActive
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ScissorsIcon className="h-3.5 w-3.5 stroke-[2]" />
            <span>Hook Cutter</span>
          </button>
          
          <button
            onClick={() => setActiveTab('affiliate')}
            className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold transition-all ${
              activeTab === 'affiliate'
                ? themeClasses.pillActive
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShoppingBagIcon className="h-3.5 w-3.5 stroke-[2]" />
            <span>Affiliate Clipper</span>
          </button>
        </div>

        {/* Right: Active Processing Badge */}
        <div className="flex items-center gap-3">
          {status === 'processing' ? (
            <div className="flex items-center gap-2 rounded-full bg-amber-950/60 border border-amber-500/40 px-3 py-1 text-xs font-bold text-amber-400 font-['Outfit',_sans-serif]">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500"></span>
              </span>
              <span className="tracking-wider uppercase text-[10px]">PROCESSING</span>
            </div>
          ) : status === 'complete' ? (
            <div className="flex items-center gap-1.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 px-3 py-1 text-xs font-semibold text-emerald-400 font-['Outfit',_sans-serif]">
              <CheckIcon className="h-3 w-3 stroke-[3]" />
              <span className="tracking-wider uppercase text-[10px]">COMPLETE</span>
            </div>
          ) : status === 'error' ? (
            <div className="flex items-center gap-1.5 rounded-full bg-rose-950/60 border border-rose-500/40 px-3 py-1 text-xs font-semibold text-rose-400 font-['Outfit',_sans-serif]">
              <span className="h-2 w-2 rounded-full bg-rose-500"></span>
              <span className="tracking-wider uppercase text-[10px]">ERROR</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 px-3 py-1 text-xs font-semibold text-emerald-400 font-['Outfit',_sans-serif]">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="tracking-wider uppercase text-[10px]">READY</span>
            </div>
          )}
        </div>

      </header>

      {/* ─────────────────────────────────────────────────────────────
          2. MAIN CONTENT: 3-COLUMN WORKSPACE
         ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-[310px_minmax(340px,1fr)_minmax(420px,1.25fr)] xl:grid-cols-[320px_minmax(360px,0.95fr)_minmax(500px,1.3fr)]">
        
        {/* ── COLUMN 1: LEFT SIDEBAR (SETTINGS & CONTROLS) ── */}
        <aside className={`flex flex-col border-r ${themeClasses.sidebar} p-4 overflow-y-auto scrollbar-thin`}>
          
          {/* 1. VIDEO SOURCE SECTION */}
          <div className="mb-4">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              <FolderIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
              <span>VIDEO SOURCE</span>
            </div>

            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              File Path or YouTube URL
            </label>
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={videoPathInput}
                onChange={(e) => setVideoPathInput(e.target.value)}
                placeholder="/path/to/video.mp4 atau URL..."
                className={`flex-1 rounded-xl border px-3 py-2 text-xs font-mono transition-all shadow-inner truncate ${themeClasses.input}`}
              />
              <button
                type="button"
                onClick={() => setShowExplorerModal(true)}
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/90 text-slate-400 hover:text-white hover:border-slate-700 transition-colors shadow-sm flex-shrink-0"
                title="Pilih File Video dari Komputer (File Explorer)"
              >
                <FolderOpenIcon className="h-4 w-4 stroke-[2]" />
              </button>
            </div>
          </div>

          {/* 2. SETTINGS SECTION */}
          <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5">
            <AdjustmentsHorizontalIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
            <span>SETTINGS</span>
          </div>

          {/* Setting 1: Number of Clips SLIDER (1 to 10) */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-medium text-slate-300">
                Number of Clips
              </label>
              <span className={`font-['Outfit'] font-extrabold text-[11px] px-2 py-0.5 rounded-md border transition-all duration-200 ${themeClasses.pillActive}`}>
                {clipCount} Klip
              </span>
            </div>

            {/* Smooth Custom Minimalist Slider */}
            <div className="relative flex items-center h-8 rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 shadow-inner group select-none">
              <div className="relative w-full h-1.5 rounded-full bg-slate-800/90 overflow-hidden">
                <div 
                  className="h-full transition-all duration-150 ease-out rounded-full bg-emerald-500"
                  style={{ width: `${((clipCount - 1) / 9) * 100}%` }}
                />
              </div>

              {/* 10 Step Dots */}
              <div className="absolute inset-x-3 pointer-events-none flex justify-between items-center z-5">
                {Array.from({ length: 10 }).map((_, idx) => {
                  const val = idx + 1;
                  const isPassed = val <= clipCount;
                  return (
                    <span
                      key={val}
                      className={`h-1.5 w-1.5 rounded-full transition-colors ${
                        isPassed ? 'bg-emerald-300' : 'bg-slate-700'
                      }`}
                    />
                  );
                })}
              </div>

              <input
                type="range"
                min={1}
                max={10}
                step={1}
                value={clipCount}
                onChange={(e) => setClipCount(parseInt(e.target.value, 10))}
                className="absolute inset-x-3 w-[calc(100%-24px)] h-6 opacity-0 cursor-pointer z-10"
              />

              <div
                className="absolute pointer-events-none top-1/2 -translate-y-1/2 -translate-x-1/2 h-3.5 w-3.5 rounded-full border-2 border-white bg-slate-900 shadow-sm ring-2 ring-emerald-500/40 transition-all duration-150 ease-out group-hover:scale-110 z-20"
                style={{ left: `calc(12px + (${((clipCount - 1) / 9)} * (100% - 24px)))` }}
              />
            </div>
          </div>

          {/* Setting 2: AI Transcription Model */}
          <div className="mb-4 relative">
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              AI Transcription Model
            </label>
            <button
              type="button"
              onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
              className="flex w-full items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-left text-xs font-medium text-slate-200 hover:border-slate-700 transition-all shadow-inner"
            >
              <div className="flex items-center gap-2 truncate">
                <BoltIcon className="h-3.5 w-3.5 stroke-[2] text-amber-400 flex-shrink-0" />
                <span className="truncate text-[11px]">
                  {transcriptionModel === 'groq' && 'Groq Whisper Cloud (~3 detik)'}
                  {transcriptionModel === 'youtube' && 'YouTube Transcript (Instant 0s)'}
                </span>
              </div>
              <ChevronDownIcon className={`h-3.5 w-3.5 stroke-[2] text-slate-400 transition-transform ${modelDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {modelDropdownOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 z-30 rounded-xl border border-slate-800 bg-slate-900 p-1 shadow-2xl backdrop-blur-md">
                {[
                  { id: 'groq', label: 'Groq Whisper Cloud (~3 detik)', desc: 'Rekomendasi Utama' },
                  { id: 'youtube', label: 'YouTube Transcript (Instant 0 Detik)', desc: 'Khusus video YouTube' }
                ].map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setTranscriptionModel(item.id);
                      setModelDropdownOpen(false);
                    }}
                    className={`flex w-full flex-col rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors ${
                      transcriptionModel === item.id
                        ? `${themeClasses.pillActive} font-semibold`
                        : 'text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <span className="font-semibold text-[11px]">{item.label}</span>
                    <span className="text-[9px] text-slate-400">{item.desc}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 3. VIDEO LAYOUT SECTION */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
                <VideoCameraIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                <span>LAYOUT VIDEO</span>
              </div>
              <span className="text-[9px] font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-500/40 px-1.5 py-0.5 rounded-md">
                NEW
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {/* Option 1: 9:16 Smart Face Tracker */}
              <button
                type="button"
                onClick={() => setFramingMode('smart_crop')}
                className={`flex flex-col items-start rounded-xl p-2 text-left transition-all border ${
                  framingMode === 'smart_crop'
                    ? `border-emerald-500 bg-emerald-950/30 shadow-xs ring-2 ring-emerald-500/20`
                    : `border-slate-800 bg-slate-950/50 hover:bg-slate-900 hover:border-slate-700`
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1 px-0.5">
                  <span className={`text-[10px] font-bold truncate ${framingMode === 'smart_crop' ? themeClasses.accentText : 'text-slate-200'}`}>
                    9:16 Smart Follow
                  </span>
                  {framingMode === 'smart_crop' && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 flex-shrink-0 animate-pulse" />
                  )}
                </div>

                {/* Visual Preview Box */}
                <div className="w-full h-10 rounded-lg bg-neutral-950 border border-neutral-800 flex items-center justify-center overflow-hidden px-1 shadow-inner relative select-none">
                  <div className="w-5 h-7 rounded border border-emerald-500/60 bg-emerald-500/10 flex flex-col items-center justify-center gap-0.5 shadow-sm">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    <span className="h-1.5 w-2 rounded-t-sm bg-emerald-500/60" />
                  </div>
                </div>
                <span className="mt-1 text-[8.5px] text-slate-400 px-0.5 leading-tight">
                  AI Face Tracking
                </span>
              </button>

              {/* Option 2: 16:9 Fit Blur */}
              <button
                type="button"
                onClick={() => setFramingMode('fit_blur')}
                className={`flex flex-col items-start rounded-xl p-2 text-left transition-all border ${
                  framingMode === 'fit_blur'
                    ? `border-emerald-500 bg-emerald-950/30 shadow-xs ring-2 ring-emerald-500/20`
                    : `border-slate-800 bg-slate-950/50 hover:bg-slate-900 hover:border-slate-700`
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1 px-0.5">
                  <span className={`text-[10px] font-bold truncate ${framingMode === 'fit_blur' ? themeClasses.accentText : 'text-slate-200'}`}>
                    16:9 Fit (Blur)
                  </span>
                  {framingMode === 'fit_blur' && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 flex-shrink-0 animate-pulse" />
                  )}
                </div>

                {/* Visual Preview Box */}
                <div className="w-full h-10 rounded-lg bg-neutral-950 border border-neutral-800 flex flex-col items-center justify-center overflow-hidden p-1 shadow-inner relative select-none">
                  <div className="absolute inset-0 bg-slate-700/30 backdrop-blur-sm" />
                  <div className="relative w-full h-4 rounded border border-cyan-400/80 bg-slate-900 flex items-center justify-center gap-1 shadow-md">
                    <span className="h-1 w-1 rounded-full bg-cyan-400" />
                    <span className="h-1 w-1 rounded-full bg-amber-400" />
                  </div>
                </div>
                <span className="mt-1 text-[8.5px] text-slate-400 px-0.5 leading-tight">
                  Podcast 16:9 Fit
                </span>
              </button>
            </div>
          </div>

          {/* 4. SUBTITLE STYLE SECTION */}
          <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
            <PaintBrushIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
            <span>SUBTITLE STYLE</span>
          </div>

          {/* Subtitle Style Cards Grid */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            {SUBTITLE_PRESETS.map((preset) => {
              const isSelected = selectedPresetId === preset.presetId;
              return (
                <button
                  key={preset.presetId}
                  onClick={() => handleSelectPreset(preset)}
                  className={`flex flex-col items-start rounded-xl p-2 text-left transition-all border ${
                    isSelected
                      ? `border-emerald-500 bg-emerald-950/30 shadow-xs ring-2 ring-emerald-500/20`
                      : `border-slate-800 bg-slate-950/50 hover:bg-slate-900 hover:border-slate-700`
                  }`}
                >
                  {/* Card Title */}
                  <div className="flex items-center justify-between w-full mb-1 px-0.5">
                    <div className="flex items-center gap-1.5 truncate">
                      <div className="flex h-4 w-4 items-center justify-center rounded bg-slate-900/90 border border-slate-800 flex-shrink-0">
                        {getPresetNotionIcon(preset.presetId)}
                      </div>
                      <span className={`text-[10px] font-bold truncate ${isSelected ? themeClasses.accentText : 'text-slate-200'}`}>
                        {preset.name}
                      </span>
                    </div>
                    {isSelected && (
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 flex-shrink-0 animate-pulse" />
                    )}
                  </div>

                  {/* Visual Preview Box */}
                  <div className="w-full h-9 rounded-lg bg-neutral-950 border border-neutral-800 flex items-center justify-center overflow-hidden px-1 shadow-inner relative select-none">
                    <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:8px_8px]" />

                    {preset.presetId === 'tiktok_viral' && (
                      <div className="relative font-['Montserrat'] font-black uppercase text-[9px] tracking-tight leading-none text-center">
                        <span className="text-white drop-shadow-[0_1px_2px_rgba(0,0,0,1)]">CARA </span>
                        <span className="text-yellow-400 bg-black/80 px-1 py-0.5 rounded font-black scale-105 inline-block drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] border border-yellow-400/30">
                          VIRAL
                        </span>
                        <span className="text-white drop-shadow-[0_1px_2px_rgba(0,0,0,1)]"> 🔥</span>
                      </div>
                    )}

                    {preset.presetId === 'classic_karaoke' && (
                      <div className="relative font-['Montserrat'] font-bold text-[9px] tracking-tight leading-none text-center">
                        <span className="text-cyan-300 font-extrabold drop-shadow-[0_1px_2px_rgba(0,0,0,1)]">Bikin </span>
                        <span className="text-white drop-shadow-[0_1px_2px_rgba(0,0,0,1)]">Konten</span>
                      </div>
                    )}

                    {preset.presetId === 'minimalist' && (
                      <div className="relative font-sans font-medium text-[9px] text-white tracking-wide leading-none text-center drop-shadow-sm">
                        <span>Ide bisnis kreatif</span>
                      </div>
                    )}

                    {preset.presetId === 'word_pop' && (
                      <div className="relative font-['Impact'] font-black uppercase text-[10px] text-yellow-300 tracking-wider leading-none text-center drop-shadow-[0_2px_4px_rgba(0,0,0,1)] scale-110">
                        <span>FOKUS!</span>
                      </div>
                    )}

                    {preset.presetId === 'no_subtitle' && (
                      <div className="relative flex items-center gap-1 text-[8.5px] font-medium text-slate-500">
                        <span className="rounded bg-rose-950/80 text-rose-400 border border-rose-800/40 px-1 font-mono text-[7px] font-bold">
                          OFF
                        </span>
                        <span>Tanpa Subtitle</span>
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* STICKY BOTTOM GENERATE BUTTON */}
          <div className="mt-auto pt-2 flex flex-col gap-1.5 sticky bottom-0 bg-[#0e1218] border-t border-slate-800/80 pb-1">
            <div className="flex items-center gap-2">
              <button
                onClick={handleStartProcessing}
                disabled={isProcessing}
                className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-xs font-bold transition-all ${themeClasses.actionBtn} ${
                  isProcessing ? 'opacity-70 cursor-wait' : 'active:scale-[0.98]'
                }`}
              >
                {isProcessing ? (
                  <>
                    <span>Processing...</span>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  </>
                ) : (
                  <span>✦ Generate {clipCount} Clips</span>
                )}
              </button>

              {isProcessing && (
                <button
                  onClick={handleStopProcessing}
                  className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-950/80 border border-rose-600/40 text-rose-400 hover:bg-rose-900 transition-all shadow-xs active:scale-95 flex-shrink-0"
                  title="Hentikan Proses (Cancel)"
                >
                  <StopIconSolid className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="text-center">
              <span className="text-[10px] text-slate-500 font-mono">
                Estimated time: ~20-35 detik
              </span>
            </div>
          </div>

        </aside>

        {/* ── COLUMN 2: CENTER WORKSPACE (iPHONE PREVIEW MOCKUP) ── */}
        <section className="flex flex-col p-4 bg-[#090d13] overflow-hidden border-r border-slate-800/80">
          <PhonePreview
            framingMode={framingMode}
            selectedPresetId={selectedPresetId}
            videoSource={videoPathInput}
          />
        </section>

        {/* ── COLUMN 3: RIGHT WORKSPACE (LOGS & OUTPUT CLIPS) ── */}
        <main className="flex flex-col overflow-y-auto p-4 gap-3.5 bg-[#0b0f15]">
          
          {/* 1. PROCESSING LOG TERMINAL (TOP PANEL) */}
          <div className="rounded-2xl border border-slate-800/90 bg-[#0d1117] overflow-hidden shadow-xl flex flex-col h-[280px] xl:h-[310px] flex-shrink-0">
            
            {/* Terminal Window Header */}
            <div className="flex h-8 items-center justify-between px-3.5 border-b border-slate-800/80 bg-[#161b22]">
              
              {/* Left: macOS Window Circles & Title */}
              <div className="flex items-center gap-2.5">
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f56]" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[#27c93f]" />
                </div>
                <span className="font-mono text-[11px] font-bold text-slate-400 tracking-wider">
                  PROCESSING LOG
                </span>
              </div>

              {/* Right: Progress Bar & Percentage */}
              <div className="flex items-center gap-2.5">
                <div className="w-24 sm:w-32 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div 
                    className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="font-mono text-[11px] font-semibold text-emerald-400">
                  {progress}%
                </span>
                <button
                  onClick={handleCopyLogs}
                  className="flex items-center gap-1 text-[10px] font-mono text-slate-400 hover:text-white bg-slate-800/60 px-1.5 py-0.5 rounded border border-slate-700 transition-colors"
                >
                  {copiedLogs ? (
                    <>
                      <CheckIcon className="h-3 w-3 stroke-[2] text-emerald-400" />
                      <span>Tersalin</span>
                    </>
                  ) : (
                    <>
                      <DocumentDuplicateIcon className="h-3 w-3 stroke-[2]" />
                      <span>Salin</span>
                    </>
                  )}
                </button>
              </div>

            </div>

            {/* Terminal Monospace Logs Output */}
            <div 
              ref={terminalRef}
              className="flex-1 p-3 font-mono text-[10.5px] leading-relaxed text-[#f59e0b] overflow-y-auto space-y-1 scrollbar-thin select-text bg-[#0d1117]"
            >
              {logs.map((line, idx) => {
                let colorClass = "text-[#f59e0b]";
                if (line.includes('✅') || line.includes('Selesai') || line.includes('complete')) {
                  colorClass = "text-emerald-400 font-semibold";
                } else if (line.includes('❌') || line.includes('failed') || line.includes('Error')) {
                  colorClass = "text-rose-400 font-semibold";
                } else if (line.includes('Progress')) {
                  colorClass = "text-sky-300";
                } else if (line.includes('SYSTEM')) {
                  colorClass = "text-slate-300";
                }

                return (
                  <div key={idx} className={`break-all ${colorClass}`}>
                    {line.startsWith('[') ? (
                      <span>
                        <span className="text-slate-500">{line.slice(0, 10)}</span>
                        <span>{line.slice(10)}</span>
                      </span>
                    ) : (
                      <span>{line}</span>
                    )}
                  </div>
                );
              })}
            </div>

          </div>

          {/* 2. OUTPUT CLIPS SECTION (BOTTOM PANEL) */}
          <div className={`rounded-2xl border ${themeClasses.card} p-4 shadow-xl flex flex-col flex-1 min-h-[220px]`}>
            
            {/* Header */}
            <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2.5">
              <div className="flex items-center gap-2">
                <FolderArrowDownIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  OUTPUT CLIPS
                </h2>
              </div>
              <span className="text-[11px] text-slate-400 font-medium">
                {generatedClips.length > 0 ? `${generatedClips.length} Klip Dihasilkan` : (outputDir ? 'Folder Siap' : 'Belum Ada Klip')}
              </span>
            </div>

            {/* Body */}
            {isProcessing ? (
              <div className="flex flex-1 flex-col items-center justify-center py-6 text-center">
                <div className="h-7 w-7 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent mb-2" />
                <p className="text-[11px] italic text-slate-400">
                  Memproses video... Klip sedang dipotong & dirender.
                </p>
              </div>
            ) : outputDir ? (
              <div className="space-y-2.5">
                {/* Folder Output Siap Banner */}
                <div className={`flex items-center justify-between rounded-xl border ${themeClasses.outputBanner} p-3 shadow-lg bg-[#161d26]`}>
                  <div className="flex items-center gap-3 truncate">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-slate-300 border border-slate-800 flex-shrink-0">
                      <FolderOpenIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                    </div>
                    <div className="truncate">
                      <h3 className="text-xs font-bold text-slate-100">Folder Output Siap</h3>
                      <p className="text-[10px] font-mono text-slate-400 truncate max-w-[200px] sm:max-w-xs">
                        {outputDir}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleOpenFolder}
                      className={`flex items-center gap-1.5 rounded-xl ${themeClasses.accentBg} px-3 py-1.5 text-xs font-bold transition-colors flex-shrink-0 shadow-md active:scale-95`}
                    >
                      <FolderOpenIcon className="h-3.5 w-3.5 stroke-[2]" />
                      <span>Buka Folder</span>
                    </button>
                    {generatedClips.length > 0 && (
                      <button
                        onClick={() => setShowFolderModal(true)}
                        className="rounded-xl border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
                      >
                        Detail
                      </button>
                    )}
                  </div>
                </div>

                {/* Clips list preview */}
                {generatedClips.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                    {generatedClips.map((clip, i) => (
                      <div key={clip.id} className="flex items-center gap-2.5 rounded-xl border border-slate-800/80 bg-slate-900/60 p-2.5 text-xs">
                        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 flex-shrink-0 font-mono font-bold text-[9px]">
                          0{i + 1}
                        </div>
                        <div className="truncate flex-1">
                          <h4 className="font-semibold text-slate-200 truncate text-[11px]">{clip.title}</h4>
                          <span className="text-[9px] font-mono text-slate-500">MP4 Clip • 9:16 Vertical</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-1 flex-col items-center justify-center py-6 text-center text-slate-500">
                <FolderArrowDownIcon className="h-8 w-8 stroke-[1.5] mb-2 opacity-30" />
                <p className="text-[11px] text-slate-400">
                  Belum ada klip
                </p>
                <p className="text-[10px] text-slate-500 max-w-xs mt-0.5">
                  Hasil klip video dan folder output akan muncul di sini setelah proses selesai.
                </p>
              </div>
            )}

          </div>

        </main>

      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. BOTTOM FOOTER STATUS BAR
         ───────────────────────────────────────────────────────────── */}
      <footer className={`flex h-9 items-center justify-between border-t ${themeClasses.footer} px-5 text-xs z-20`}>
        <div>
          <span>VisionClipper Studio © 2026 — Built by </span>
          <span className="font-semibold text-slate-200">kam2k-dev</span>
        </div>

        <button
          onClick={() => setServerModalOpen(true)}
          className="rounded border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          Shut Down Server
        </button>
      </footer>

      {/* File Explorer Modal */}
      <FileExplorerModal
        isOpen={showExplorerModal}
        onClose={() => setShowExplorerModal(false)}
        onSelect={(path) => setVideoPathInput(path)}
        initialPath={videoPathInput}
      />

      {/* Generated Clips Detail Modal */}
      {showFolderModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 p-5 shadow-2xl border border-slate-800 text-slate-100">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <FolderIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                <h3 className="text-sm font-bold text-white">Daftar Klip Dihasilkan</h3>
              </div>
              <button
                onClick={() => setShowFolderModal(false)}
                className="text-slate-400 hover:text-white text-xs p-1 rounded-md hover:bg-slate-800 transition-colors"
              >
                <XMarkIcon className="h-4 w-4 stroke-[2]" />
              </button>
            </div>
            
            <p className="text-xs text-slate-300 mb-2">
              Klip tersimpan di direktori:
            </p>
            <div className="rounded-lg bg-slate-950 p-2.5 font-mono text-[11px] text-emerald-400 break-all mb-4 border border-slate-800 select-all">
              {outputDir}
            </div>

            <div className="space-y-1.5 mb-4 max-h-48 overflow-y-auto scrollbar-thin">
              {generatedClips.map((c, i) => (
                <div key={c.id} className="flex items-center justify-between text-xs py-2 px-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center gap-2 truncate pr-2">
                    <DocumentTextIcon className="h-4 w-4 stroke-[2] text-slate-400 flex-shrink-0" />
                    <span className="truncate text-slate-200 font-medium">0{i+1}_{c.title}</span>
                  </div>
                  <span className="font-mono text-emerald-400 text-[10px] flex-shrink-0">Ready</span>
                </div>
              ))}
            </div>

            <div className="flex justify-between items-center">
              <button
                onClick={handleOpenFolder}
                className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-semibold"
              >
                <FolderOpenIcon className="h-4 w-4 stroke-[2]" />
                <span>Buka di Finder/Explorer</span>
              </button>
              <button
                onClick={() => setShowFolderModal(false)}
                className={`rounded-xl ${themeClasses.accentBg} px-4 py-1.5 text-xs font-bold`}
              >
                Selesai
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Server Shutdown Confirmation Modal */}
      {serverModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="w-80 rounded-2xl bg-slate-900 p-5 shadow-2xl border border-slate-800 text-slate-100">
            <h3 className="text-sm font-bold text-white mb-2">Shut Down Server?</h3>
            <p className="text-xs text-slate-400 mb-4">
              Apakah Anda yakin ingin mematikan VisionClipper Studio background server?
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setServerModalOpen(false)}
                className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                Batal
              </button>
              <button
                onClick={handleConfirmShutdown}
                className="rounded-lg bg-rose-600 hover:bg-rose-500 text-white px-3 py-1.5 text-xs font-bold shadow-sm"
              >
                Shut Down
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
