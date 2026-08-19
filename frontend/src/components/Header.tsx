import React from 'react';
import { 
  Scissors, 
  Sparkles, 
  Layers, 
  Share2, 
  Terminal, 
  FileVideo,
  Flame,
  CheckCircle2
} from 'lucide-react';

interface HeaderProps {
  activeTab: 'create' | 'editor' | 'logs';
  setActiveTab: (tab: 'create' | 'editor' | 'logs') => void;
  generatedClipsCount: number;
  isProcessing: boolean;
  onOpenExport: () => void;
  onQuickDemo: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  generatedClipsCount,
  isProcessing,
  onOpenExport,
  onQuickDemo
}) => {
  return (
    <header id="main-header" className="sticky top-0 z-40 w-full border-b border-neutral-800 bg-neutral-950/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500 via-orange-500 to-rose-500 shadow-lg shadow-orange-500/20">
            <Scissors className="h-5 w-5 text-black stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-['Outfit'] text-lg font-extrabold tracking-tight text-white">
                Clip<span className="text-amber-400">Forge</span>
              </span>
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-400">
                AI STUDIO
              </span>
            </div>
            <p className="hidden text-xs text-neutral-400 sm:block">
              Auto Clipper, Subtitle Kinetik & Multi-Export Sosmed
            </p>
          </div>
        </div>

        {/* Center Nav Tabs */}
        <nav className="flex items-center gap-1 rounded-xl border border-neutral-800 bg-neutral-900/80 p-1">
          <button
            id="tab-btn-create"
            onClick={() => setActiveTab('create')}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              activeTab === 'create'
                ? 'bg-amber-500 text-neutral-950 shadow-md shadow-amber-500/20'
                : 'text-neutral-300 hover:bg-neutral-800 hover:text-white'
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Generate & Konfigurasi</span>
          </button>

          <button
            id="tab-btn-editor"
            onClick={() => setActiveTab('editor')}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              activeTab === 'editor'
                ? 'bg-amber-500 text-neutral-950 shadow-md shadow-amber-500/20'
                : 'text-neutral-300 hover:bg-neutral-800 hover:text-white'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Editor & Pratinjau</span>
            {generatedClipsCount > 0 && (
              <span className={`flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold ${
                activeTab === 'editor' ? 'bg-black text-amber-400' : 'bg-amber-500/20 text-amber-400'
              }`}>
                {generatedClipsCount}
              </span>
            )}
          </button>

          <button
            id="tab-btn-logs"
            onClick={() => setActiveTab('logs')}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              activeTab === 'logs'
                ? 'bg-amber-500 text-neutral-950 shadow-md shadow-amber-500/20'
                : 'text-neutral-300 hover:bg-neutral-800 hover:text-white'
            }`}
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>Live Log AI</span>
            {isProcessing && (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500"></span>
              </span>
            )}
          </button>
        </nav>

        {/* Right CTA Actions */}
        <div className="flex items-center gap-2.5">
          <button
            id="btn-quick-demo"
            onClick={onQuickDemo}
            className="hidden items-center gap-1.5 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-xs font-medium text-neutral-200 transition-colors hover:border-neutral-600 hover:bg-neutral-800 sm:flex"
            title="Muat contoh podcast siap proses"
          >
            <FileVideo className="h-3.5 w-3.5 text-amber-400" />
            <span>Load Sample</span>
          </button>

          <button
            id="btn-export-all"
            onClick={onOpenExport}
            disabled={generatedClipsCount === 0}
            className={`flex items-center gap-2 rounded-lg px-4 py-1.5 text-xs font-bold transition-all ${
              generatedClipsCount > 0
                ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-neutral-950 shadow-lg shadow-orange-500/20 hover:from-amber-400 hover:to-orange-400'
                : 'cursor-not-allowed bg-neutral-800 text-neutral-500'
            }`}
          >
            <Share2 className="h-3.5 w-3.5" />
            <span>Auto Export ({generatedClipsCount})</span>
          </button>
        </div>

      </div>
    </header>
  );
};
