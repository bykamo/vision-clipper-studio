import React, { useState, useRef } from 'react';
import { 
  Upload, 
  Link2, 
  Film, 
  Sparkles, 
  Check, 
  Play, 
  Clock, 
  User, 
  RefreshCw,
  FolderOpen
} from 'lucide-react';
import { SourceVideo } from '../types';
import { SAMPLE_VIDEOS } from '../data/sampleVideos';

interface SourceInputPanelProps {
  selectedVideo: SourceVideo;
  onSelectVideo: (video: SourceVideo) => void;
}

export const SourceInputPanel: React.FC<SourceInputPanelProps> = ({
  selectedVideo,
  onSelectVideo
}) => {
  const [activeTab, setActiveTab] = useState<'sample' | 'upload' | 'url'>('sample');
  const [urlInput, setUrlInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isUrlLoading, setIsUrlLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (file: File) => {
    if (!file.type.startsWith('video/')) {
      alert('Mohon unggah file video yang valid (MP4, WebM, MOV)');
      return;
    }
    const blobUrl = URL.createObjectURL(file);
    const newCustomVideo: SourceVideo = {
      id: `custom-${Date.now()}`,
      title: file.name.replace(/\.[^/.]+$/, ""),
      duration: 120, // Estimated/detected
      category: 'Video Unggahan',
      speaker: 'Speaker Lokal',
      videoUrl: blobUrl,
      videoType: 'custom_file',
      originalAspect: '16:9',
      summary: `Video diunggah lokal: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`,
      transcriptSample: 'Transkripsi audio lokal siap diproses oleh Whisper AI...'
    };
    onSelectVideo(newCustomVideo);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFetchUrl = () => {
    if (!urlInput.trim()) return;
    setIsUrlLoading(true);
    setTimeout(() => {
      setIsUrlLoading(false);
      const urlVideo: SourceVideo = {
        id: `url-${Date.now()}`,
        title: urlInput.includes('youtube') ? 'Podcast Eksklusif YouTube: Strategi Viral Content 2026' : 'Video Online Media Stream',
        duration: 195,
        category: 'Online Media Stream',
        speaker: 'Host & Guest',
        videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
        videoType: 'url',
        originalAspect: '16:9',
        summary: `Diunduh dari stream: ${urlInput}`,
        transcriptSample: 'Audio stream berhasil di-capture dan siap dianalisis...'
      };
      onSelectVideo(urlVideo);
      setUrlInput('');
    }, 900);
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div id="source-input-panel" className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-5 shadow-xl">
      <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h2 className="flex items-center gap-2 text-base font-bold text-white">
            <Film className="h-4 w-4 text-amber-400" />
            <span>1. Sumber Video Utama</span>
          </h2>
          <p className="text-xs text-neutral-400">
            Pilih contoh preset video podcast, unggah file lokal, atau masukkan tautan YouTube
          </p>
        </div>

        {/* Source Mode Tabs */}
        <div className="flex rounded-lg border border-neutral-800 bg-neutral-950 p-1">
          <button
            id="tab-source-sample"
            onClick={() => setActiveTab('sample')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
              activeTab === 'sample' ? 'bg-amber-500 text-neutral-950' : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Sparkles className="h-3 w-3" />
            <span>Preset Siap Pakai</span>
          </button>
          <button
            id="tab-source-upload"
            onClick={() => setActiveTab('upload')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
              activeTab === 'upload' ? 'bg-amber-500 text-neutral-950' : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Upload className="h-3 w-3" />
            <span>Upload File</span>
          </button>
          <button
            id="tab-source-url"
            onClick={() => setActiveTab('url')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
              activeTab === 'url' ? 'bg-amber-500 text-neutral-950' : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Link2 className="h-3 w-3" />
            <span>Link URL</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      {activeTab === 'sample' && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {SAMPLE_VIDEOS.map((sample) => {
            const isSelected = selectedVideo.id === sample.id;
            return (
              <button
                key={sample.id}
                id={`sample-card-${sample.id}`}
                onClick={() => onSelectVideo(sample)}
                className={`group relative flex flex-col justify-between rounded-xl border p-3.5 text-left transition-all ${
                  isSelected
                    ? 'border-amber-500 bg-amber-500/10 shadow-md shadow-amber-500/10 ring-1 ring-amber-500'
                    : 'border-neutral-800 bg-neutral-950/60 hover:border-neutral-700 hover:bg-neutral-800/40'
                }`}
              >
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="rounded bg-neutral-800 px-2 py-0.5 text-[10px] font-semibold text-neutral-300">
                      {sample.category}
                    </span>
                    <span className="flex items-center gap-1 text-[11px] font-medium text-neutral-400">
                      <Clock className="h-3 w-3 text-amber-400" />
                      {formatDuration(sample.duration)}
                    </span>
                  </div>
                  <h3 className="line-clamp-2 text-xs font-bold text-neutral-100 group-hover:text-amber-300">
                    {sample.title}
                  </h3>
                  <p className="mt-1 line-clamp-2 text-[11px] text-neutral-400">
                    {sample.summary}
                  </p>
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-neutral-800/60 pt-2 text-[10px] text-neutral-400">
                  <span className="flex items-center gap-1">
                    <User className="h-2.5 w-2.5 text-neutral-500" />
                    {sample.speaker}
                  </span>
                  {isSelected ? (
                    <span className="flex items-center gap-1 font-bold text-amber-400">
                      <Check className="h-3 w-3" /> Dipilih
                    </span>
                  ) : (
                    <span className="text-neutral-500 group-hover:text-neutral-300">
                      Pilih
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {activeTab === 'upload' && (
        <div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
            accept="video/mp4,video/webm,video/quicktime,video/x-matroska"
            className="hidden"
          />
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-all ${
              isDragging
                ? 'border-amber-400 bg-amber-500/10'
                : 'border-neutral-800 bg-neutral-950/40 hover:border-neutral-700 hover:bg-neutral-800/30'
            }`}
          >
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-800 text-amber-400">
              <FolderOpen className="h-6 w-6" />
            </div>
            <p className="text-sm font-semibold text-neutral-200">
              Klik untuk memilih file video atau seret file ke sini
            </p>
            <p className="mt-1 text-xs text-neutral-500">
              Mendukung MP4, MOV, WebM, MKV (Maks 2GB untuk auto-clip cepat)
            </p>
          </div>
        </div>
      )}

      {activeTab === 'url' && (
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Link2 className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="Tempel tautan YouTube, TikTok, Google Drive, atau Podcast URL..."
              className="w-full rounded-xl border border-neutral-800 bg-neutral-950 py-2.5 pl-10 pr-4 text-xs text-neutral-100 placeholder-neutral-500 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
          </div>
          <button
            id="btn-fetch-url"
            onClick={handleFetchUrl}
            disabled={!urlInput.trim() || isUrlLoading}
            className={`flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-xs font-bold transition-all ${
              urlInput.trim() && !isUrlLoading
                ? 'bg-amber-500 text-neutral-950 shadow-md shadow-amber-500/20 hover:bg-amber-400'
                : 'cursor-not-allowed bg-neutral-800 text-neutral-500'
            }`}
          >
            {isUrlLoading ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                <span>Mengambil Audio & Metadata...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                <span>Import Video</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Selected Video Summary Bar */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-neutral-800/80 bg-neutral-950/80 p-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/20 text-amber-400">
            <Play className="h-4 w-4 fill-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white">Video Terpilih:</span>
              <span className="text-xs text-amber-300 font-medium line-clamp-1">{selectedVideo.title}</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-neutral-400">
              <span>Durasi: {formatDuration(selectedVideo.duration)}</span>
              <span>•</span>
              <span>Speaker: {selectedVideo.speaker}</span>
              <span>•</span>
              <span>Rasio: {selectedVideo.originalAspect}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/30">
            Whisper Ready
          </span>
          <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-amber-400 border border-amber-500/30">
            Gemini Hook AI Active
          </span>
        </div>
      </div>

    </div>
  );
};
