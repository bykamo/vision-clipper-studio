import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  Sparkles, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  Copy, 
  Check, 
  Download, 
  Filter, 
  Activity, 
  Flame, 
  Layers,
  ArrowDownCircle,
  RefreshCw
} from 'lucide-react';
import { ProcessingLog } from '../types';

interface LiveProcessLogProps {
  logs: ProcessingLog[];
  isProcessing: boolean;
  currentProgress: number;
  currentStage: string;
  onClearLogs?: () => void;
  onRestartClipping?: () => void;
}

export const LiveProcessLog: React.FC<LiveProcessLogProps> = ({
  logs,
  isProcessing,
  currentProgress,
  currentStage,
  onClearLogs,
  onRestartClipping
}) => {
  const [filterLevel, setFilterLevel] = useState<'all' | 'gemini' | 'whisper' | 'render'>('all');
  const [copied, setCopied] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter(log => {
    if (filterLevel === 'all') return true;
    return log.level === filterLevel;
  });

  const handleCopyLogs = () => {
    const text = logs.map(l => `[${l.timestamp}] [${l.stage}] ${l.message} ${l.details ? `(${l.details})` : ''}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStageBadge = (stage: ProcessingLog['stage']) => {
    switch (stage) {
      case 'GEMINI_ANALYSIS':
        return <span className="rounded bg-purple-500/20 px-1.5 py-0.5 text-[9px] font-bold text-purple-400 border border-purple-500/30">GEMINI AI</span>;
      case 'WHISPER_STT':
        return <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-bold text-emerald-400 border border-emerald-500/30">WHISPER v3</span>;
      case 'FACE_TRACKING':
        return <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[9px] font-bold text-blue-400 border border-blue-500/30">FACE MESH</span>;
      case 'SUBTITLE_BURN':
        return <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-bold text-amber-400 border border-amber-500/30">SUBTITLE</span>;
      case 'AUTO_ENCODE':
        return <span className="rounded bg-orange-500/20 px-1.5 py-0.5 text-[9px] font-bold text-orange-400 border border-orange-500/30">ENCODER</span>;
      case 'COMPLETED':
        return <span className="rounded bg-emerald-500/30 px-1.5 py-0.5 text-[9px] font-bold text-emerald-300 border border-emerald-500/50">SELESAI</span>;
      default:
        return <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[9px] font-bold text-neutral-400">CORE</span>;
    }
  };

  const stagesList = [
    { label: 'Audio Extract', threshold: 15 },
    { label: 'Whisper STT', threshold: 38 },
    { label: 'Gemini Hook', threshold: 64 },
    { label: 'Face Track 9:16', threshold: 75 },
    { label: 'Subtitle Burn', threshold: 86 },
    { label: 'Auto Encode', threshold: 95 },
  ];

  return (
    <div id="live-process-log" className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-5 shadow-xl">
      
      {/* HEADER & METRICS */}
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30">
              <Terminal className="h-4 w-4" />
            </div>
            <h2 className="text-base font-bold text-white">
              Log Proses Eksekusi AI Real-Time
            </h2>
            {isProcessing ? (
              <span className="flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-bold text-amber-400 border border-amber-500/30">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Live Processing
              </span>
            ) : logs.length > 0 ? (
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-bold text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="h-3 w-3" />
                Selesai (100%)
              </span>
            ) : (
              <span className="rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-neutral-400">
                Standby
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-neutral-400">
            Monitoring step-by-step model Whisper STT, analisis retensi Gemini AI, framing visual, dan generator subtitle kinetik
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            id="btn-copy-logs"
            onClick={handleCopyLogs}
            disabled={logs.length === 0}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-xs font-semibold text-neutral-300 transition-colors hover:border-neutral-700 hover:text-white disabled:opacity-40"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-neutral-400" />}
            <span>{copied ? 'Tersalin' : 'Copy Log'}</span>
          </button>

          {onRestartClipping && !isProcessing && logs.length > 0 && (
            <button
              id="btn-re-run-log"
              onClick={onRestartClipping}
              className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-bold text-black shadow-md hover:bg-amber-400"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Re-Run AI</span>
            </button>
          )}
        </div>
      </div>

      {/* OVERALL PROGRESS BAR */}
      <div className="mb-4 rounded-xl border border-neutral-800 bg-neutral-950 p-3.5">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-amber-400 animate-pulse" />
            <span className="text-xs font-bold text-neutral-200">
              Tahap Aktif: <span className="text-amber-400 font-extrabold">{currentStage || 'Menunggu Trigger'}</span>
            </span>
          </div>
          <span className="font-mono text-xs font-black text-amber-400">
            {currentProgress}%
          </span>
        </div>

        {/* Bar */}
        <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-800">
          <div 
            className="h-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 transition-all duration-300"
            style={{ width: `${currentProgress}%` }}
          />
        </div>

        {/* Visual Stage Checkpoints */}
        <div className="mt-3 grid grid-cols-3 gap-1 sm:grid-cols-6">
          {stagesList.map((stg) => {
            const isDone = currentProgress >= stg.threshold;
            const isCurrent = isProcessing && currentProgress < stg.threshold && currentProgress >= (stg.threshold - 15);
            return (
              <div 
                key={stg.label}
                className={`flex flex-col items-center rounded-lg p-1.5 text-center text-[10px] transition-all ${
                  isDone 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                    : isCurrent 
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/40 animate-pulse'
                    : 'bg-neutral-900/50 text-neutral-500'
                }`}
              >
                <div className="flex items-center gap-1 font-semibold">
                  {isDone ? <Check className="h-2.5 w-2.5" /> : null}
                  <span>{stg.label}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* FILTER BUTTONS & SCROLL TOGGLE */}
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="flex items-center gap-1 text-[11px] text-neutral-400">
            <Filter className="h-3 w-3" /> Filter:
          </span>
          {(['all', 'gemini', 'whisper', 'render'] as const).map((lvl) => (
            <button
              key={lvl}
              onClick={() => setFilterLevel(lvl)}
              className={`rounded-md px-2.5 py-0.5 text-[11px] font-bold capitalize transition-all ${
                filterLevel === lvl
                  ? 'bg-amber-500 text-neutral-950'
                  : 'border border-neutral-800 bg-neutral-950 text-neutral-400 hover:text-white'
              }`}
            >
              {lvl === 'all' ? 'Semua Log' : lvl === 'gemini' ? 'Gemini AI' : lvl === 'whisper' ? 'Whisper STT' : 'Render Engine'}
            </button>
          ))}
        </div>

        <label className="flex cursor-pointer items-center gap-1.5 text-[11px] text-neutral-400 hover:text-neutral-300">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="h-3 w-3 rounded border-neutral-700 bg-neutral-900 accent-amber-500"
          />
          <span>Auto-Scroll ke Bawah</span>
        </label>
      </div>

      {/* TERMINAL CONSOLE */}
      <div 
        id="terminal-output-container"
        className="h-72 w-full overflow-y-auto rounded-xl border border-neutral-800 bg-[#09090b] p-4 font-mono text-xs shadow-inner"
      >
        {logs.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-neutral-500">
            <Terminal className="mb-2 h-8 w-8 text-neutral-600" />
            <p className="font-semibold text-neutral-400">Konsol Log Belum Berjalan</p>
            <p className="text-[11px]">
              Klik tombol <strong className="text-amber-400 font-bold">"Mulai AI Clipper"</strong> di atas untuk melihat proses deteksi real-time.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredLogs.map((log) => (
              <div 
                key={log.id} 
                className="group flex flex-col gap-0.5 rounded p-1 transition-colors hover:bg-neutral-900/60"
              >
                <div className="flex items-start gap-2">
                  <span className="text-[10px] text-neutral-500 select-none">
                    [{log.timestamp}]
                  </span>
                  
                  {getStageBadge(log.stage)}

                  <span className={`flex-1 font-medium ${
                    log.level === 'gemini' ? 'text-purple-300' :
                    log.level === 'whisper' ? 'text-emerald-300' :
                    log.level === 'render' ? 'text-sky-300' :
                    log.level === 'success' ? 'text-emerald-400 font-bold' :
                    'text-neutral-200'
                  }`}>
                    {log.message}
                  </span>
                </div>

                {log.details && (
                  <div className="ml-16 text-[10px] text-neutral-400 pl-2 border-l border-neutral-800">
                    ↳ {log.details}
                  </div>
                )}
              </div>
            ))}
            <div ref={terminalEndRef} />
          </div>
        )}
      </div>

      {/* FOOTER STATS */}
      <div className="mt-3 flex flex-wrap items-center justify-between text-[11px] text-neutral-400 border-t border-neutral-800/80 pt-2.5">
        <div className="flex items-center gap-4">
          <span>Engine: <strong className="text-neutral-200">v2.4-flash + Whisper-v3</strong></span>
          <span>Latency: <strong className="text-neutral-200">~18ms/frame</strong></span>
          <span>Audio Resample: <strong className="text-neutral-200">16kHz Mono</strong></span>
        </div>
        <div className="text-neutral-400">
          Total Baris Log: <strong className="text-amber-400">{filteredLogs.length}</strong>
        </div>
      </div>

    </div>
  );
};
