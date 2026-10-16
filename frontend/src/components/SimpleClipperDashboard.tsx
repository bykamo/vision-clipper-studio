import React, { useState, useEffect, useRef } from 'react';
import {
  ScissorsIcon,
  ShoppingBagIcon,
  FolderIcon,
  FolderOpenIcon,
  FolderArrowDownIcon,
  AdjustmentsHorizontalIcon,
  XMarkIcon,
  DocumentTextIcon,
  DocumentDuplicateIcon,
  CheckIcon,
  FireIcon,
  ChatBubbleBottomCenterTextIcon,
  VideoCameraIcon,
  SparklesIcon,
  ArrowLeftIcon,
  ArrowUpRightIcon,
  ArrowPathIcon,
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
  GlobeAltIcon,
  LockClosedIcon,
  LinkIcon,
  CommandLineIcon,
  FilmIcon,
  HomeIcon,
  ComputerDesktopIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  KeyIcon,
  ServerIcon,
  CpuChipIcon,
  EyeIcon,
  ShieldCheckIcon,
  Square3Stack3DIcon,
  LanguageIcon,
  PhotoIcon,
  SwatchIcon,
  CloudArrowDownIcon
} from '@heroicons/react/24/outline';
import {
  StopIcon as StopIconSolid,
  FilmIcon as FilmIconSolid
} from '@heroicons/react/24/solid';
import { SubtitleStyleConfig, FramingMode } from '../types';
import { SUBTITLE_PRESETS } from '../data/subtitlePresets';
import { PhonePreview } from './PhonePreview';
import { StudioSettingsModal } from './StudioSettingsModal';
import { AnalyzingSkeleton, RenderingSkeleton } from './SkeletonLoading';

interface AiProviderPreset {
  label: string;
  endpoint: string;
  default_model: string;
  doc_url?: string;
}

interface AiConfigResponse {
  provider: string;
  endpoint: string;
  model: string;
  api_key_set: boolean;
  api_key_masked: string;
  groq_key_set: boolean;
  groq_key_masked: string;
  ready: boolean;
  groq_ready: boolean;
  presets: Record<string, AiProviderPreset>;
}

interface GeneratedClipItem {
  id: string;
  title: string;
  filename?: string;
  duration?: string;
  out_file?: string;
  caption?: string;
  hashtags?: string[];
}

type WorkflowPhase = 'config' | 'analyzing' | 'preview' | 'rendering' | 'complete';

interface ClipCandidate {
  index: number;
  start: number;
  end: number;
  duration: number;
  title_options: string[];
  reason: string;
  viral_score: number;
  sales_score?: number;
  caption: string;
  hashtags: string[];
  decision: 'pending' | 'approved' | 'skipped';
  previewed: boolean;
}

/* ─────────────────────────────────────────────────────────────
   SIDEBAR UI PRIMITIVES — reusable building blocks for the
   left-column menu (section labels, cards, preview tiles)
   ───────────────────────────────────────────────────────────── */

/** Numbered step card with a vertical timeline connector (new sidebar layout) */
const StepCard: React.FC<{
  step: number;
  icon: React.ReactNode;
  title: string;
  hint?: string;
  right?: React.ReactNode;
  isLast?: boolean;
  children: React.ReactNode;
}> = ({ step, icon, title, hint, right, isLast, children }) => (
  <div className="relative pl-9">
    {!isLast && (
      <span
        className="absolute left-[13px] top-8 -bottom-2 w-px bg-gradient-to-b from-emerald-500/40 to-slate-800/40"
        aria-hidden
      />
    )}
    <span className="absolute left-0 top-0.5 flex h-7 w-7 items-center justify-center rounded-full border border-emerald-500/40 bg-[#0b0f14] text-emerald-300 font-['Outfit'] font-extrabold text-[11px] shadow-[0_0_0_3px_rgba(16,185,129,0.08)]">
      {step}
    </span>
    <div className="pb-3.5">
      <div className="flex items-center gap-1.5 mb-2 min-h-[20px]" title={hint}>
        <span className="text-emerald-400 flex-shrink-0">{icon}</span>
        <span className="text-[10.5px] font-bold text-slate-100 uppercase tracking-wider font-['Outfit'] truncate">
          {title}
        </span>
        {right && <div className="ml-auto flex-shrink-0">{right}</div>}
      </div>
      {children}
    </div>
  </div>
);

/** 1..10 number pill picker (replaces the +/- stepper) */
const NumberPills: React.FC<{ value: number; onChange: (n: number) => void }> = ({ value, onChange }) => (
  <div className="flex items-center gap-1">
    {Array.from({ length: 10 }).map((_, i) => {
      const n = i + 1;
      const active = n === value;
      return (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          aria-pressed={active}
          className={`flex-1 h-6 rounded-md text-[10px] font-bold font-['Outfit'] border transition-all ${
            active
              ? 'bg-emerald-500 text-slate-950 border-emerald-400 shadow-sm'
              : 'bg-slate-950/60 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          {n}
        </button>
      );
    })}
  </div>
);

/** Compact labelled switch row used in the control rail */
const CompactToggle: React.FC<{
  icon?: React.ReactNode;
  label: string;
  checked: boolean;
  onChange: () => void;
  accent?: 'emerald' | 'cyan';
  title?: string;
}> = ({ icon, label, checked, onChange, accent = 'emerald', title }) => (
  <div className="flex items-center justify-between rounded-lg border border-slate-800/70 bg-slate-950/40 px-2 py-1.5">
    <span className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-300 min-w-0">
      {icon}
      <span className="truncate">{label}</span>
    </span>
    <button
      type="button"
      onClick={onChange}
      role="switch"
      aria-checked={checked}
      title={title}
      className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
        checked ? (accent === 'cyan' ? 'bg-cyan-500' : 'bg-emerald-500') : 'bg-slate-800'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          checked ? 'translate-x-3' : 'translate-x-0'
        }`}
      />
    </button>
  </div>
);

/** Ultra-compact pill switch (used in section headers) */
const MiniSwitch: React.FC<{
  checked: boolean;
  onChange: () => void;
  accent?: 'emerald' | 'cyan';
  title?: string;
}> = ({ checked, onChange, accent = 'emerald', title }) => (
  <button
    type="button"
    onClick={onChange}
    role="switch"
    aria-checked={checked}
    title={title}
    className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
      checked ? (accent === 'cyan' ? 'bg-cyan-500' : 'bg-emerald-500') : 'bg-slate-800'
    }`}
  >
    <span
      className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
        checked ? 'translate-x-3' : 'translate-x-0'
      }`}
    />
  </button>
);

export const SimpleClipperDashboard: React.FC = () => {
  // Navigation Tabs (Modes)
  const [activeTab, setActiveTab] = useState<'hook' | 'affiliate'>('hook');

  // Video Source State
  const [videoPathInput, setVideoPathInput] = useState<string>('');
  const [sourceKind, setSourceKind] = useState<'video' | 'render-folder'>('video');
  const [isPickingFile, setIsPickingFile] = useState<boolean>(false);
  const [isPickingFolder, setIsPickingFolder] = useState<boolean>(false);

  // Workflow Phase State
  const [phase, setPhase] = useState<WorkflowPhase>('config');
  const [clipCandidates, setClipCandidates] = useState<ClipCandidate[]>([]);
  const [analysisId, setAnalysisId] = useState<string>('');
  const [resolvedVideoPath, setResolvedVideoPath] = useState<string>('');
  const [previewClipRange, setPreviewClipRange] = useState<{ start: number; end: number } | null>(null);
  const [previewOutputClip, setPreviewOutputClip] = useState<{ path: string; title: string; id: string } | null>(null);
  const [activeClipMeta, setActiveClipMeta] = useState<{ title?: string; caption?: string; hashtags?: string[] } | null>(null);

  // Settings State
  const [clipCount, setClipCount] = useState<number>(4);
  // Groq Whisper Cloud adalah satu-satunya model transkripsi (pilihan utama/default).
  const transcriptionModel = 'groq';
  const [languageMode, setLanguageMode] = useState<string>('id');
  // Default = tanpa subtitle. Gaya caption dipilih lewat check/uncheck pada kartu.
  const [selectedPresetId, setSelectedPresetId] = useState<string>('no_subtitle');
  const [framingMode, setFramingMode] = useState<FramingMode>('smart_crop');
  const [subPosition, setSubPosition] = useState<number>(68);
  const [showEmoji, setShowEmoji] = useState<boolean>(true);

  // Watermark Settings State (Glass Effect)
  const [watermarkEnabled, setWatermarkEnabled] = useState<boolean>(true);
  const [sourceWatermark, setSourceWatermark] = useState<string>('');
  const [accountWatermark, setAccountWatermark] = useState<string>('');

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

  // YouTube Social Connection & Upload State
  const [ytConnected, setYtConnected] = useState(false);
  const [ytChannel, setYtChannel] = useState<{ title: string; customUrl?: string; thumbnail?: string; subscriberCount?: string; videoCount?: string; id?: string } | null>(null);
  const [ytAvatarFailed, setYtAvatarFailed] = useState(false);
  const [isUploadingYt, setIsUploadingYt] = useState<string | null>(null); // clip id being uploaded
  const [uploadedYtLinks, setUploadedYtLinks] = useState<Record<string, string>>({}); // clip id -> url

  // YouTube Posting Confirmation Modal State
  const [ytModalOpen, setYtModalOpen] = useState(false);
  const [selectedClipForYt, setSelectedClipForYt] = useState<GeneratedClipItem | null>(null);
  const [ytFormTitle, setYtFormTitle] = useState('');
  const [ytFormDescription, setYtFormDescription] = useState('');
  const [ytFormTags, setYtFormTags] = useState<string[]>([]);
  const [ytFormPrivacy, setYtFormPrivacy] = useState<'public' | 'private' | 'unlisted'>('public'); // Default 'public' for posting langsung
  const [ytFormAutoShortsTag, setYtFormAutoShortsTag] = useState(true);
  const [ytUploadProgress, setYtUploadProgress] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [ytUploadResult, setYtUploadResult] = useState<{ url: string; shorts_url: string; video_id: string } | null>(null);
  const [ytUploadErrorMessage, setYtUploadErrorMessage] = useState<string | null>(null);
  const [isCheckingYtStatus, setIsCheckingYtStatus] = useState(false);
  const [showTerminalInPreview, setShowTerminalInPreview] = useState(false);
  const [renderErrorMessage, setRenderErrorMessage] = useState<string | null>(null);

  // Studio Settings Modal State (AI, YouTube, TikTok)
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [settingsActiveTab, setSettingsActiveTab] = useState<'ai' | 'whisper' | 'youtube' | 'tiktok'>('ai');
  const [aiConfig, setAiConfig] = useState<AiConfigResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSaving, setAiSaving] = useState(false);
  const [aiTesting, setAiTesting] = useState(false);
  const [aiTestingGroq, setAiTestingGroq] = useState(false);
  const [aiShowKey, setAiShowKey] = useState(false);
  const [aiShowGroqKey, setAiShowGroqKey] = useState(false);

  // AI Form State
  const [aiSelectedProvider, setAiSelectedProvider] = useState<string>('openrouter');
  const [aiEndpointInput, setAiEndpointInput] = useState<string>('');
  const [aiModelInput, setAiModelInput] = useState<string>('');
  const [aiApiKeyInput, setAiApiKeyInput] = useState<string>('');
  const [aiGroqKeyInput, setAiGroqKeyInput] = useState<string>('');
  const [aiTestResult, setAiTestResult] = useState<{ ok: boolean; message?: string; error?: string; reply?: string } | null>(null);
  const [aiGroqTestResult, setAiGroqTestResult] = useState<{ ok: boolean; message?: string; error?: string } | null>(null);
  const [aiModels, setAiModels] = useState<string[]>([]);
  const [aiModelsLoading, setAiModelsLoading] = useState(false);
  const [aiModelsError, setAiModelsError] = useState<string | null>(null);
  const [aiModelsOpen, setAiModelsOpen] = useState(false);

  const fetchAiConfig = async () => {
    try {
      setAiLoading(true);
      const res = await fetch('/api/ai-config');
      if (res.ok) {
        const data: AiConfigResponse = await res.json();
        setAiConfig(data);
        setAiSelectedProvider(data.provider || 'openrouter');
        setAiEndpointInput(data.endpoint || '');
        setAiModelInput(data.model || '');
      }
    } catch {
      // Backend may be starting
    } finally {
      setAiLoading(false);
    }
  };

  useEffect(() => {
    fetchAiConfig();
  }, []);

  const handleOpenSettings = (tab: 'ai' | 'whisper' | 'youtube' | 'tiktok' = 'ai') => {
    setSettingsActiveTab(tab);
    if ((tab === 'ai' || tab === 'whisper') && aiConfig) {
      setAiSelectedProvider(aiConfig.provider || 'openrouter');
      setAiEndpointInput(aiConfig.endpoint || '');
      setAiModelInput(aiConfig.model || '');
      setAiApiKeyInput('');
      setAiGroqKeyInput('');
    }
    setAiTestResult(null);
    setAiGroqTestResult(null);
    setSettingsModalOpen(true);
  };

  const handleOpenAiSettings = () => {
    handleOpenSettings('ai');
  };

  // Backwards compatibility aliases
  const setAiSettingsOpen = (open: boolean) => {
    if (open) handleOpenSettings('ai');
    else setSettingsModalOpen(false);
  };

  const setYtChannelModalOpen = (open: boolean) => {
    if (open) handleOpenSettings('youtube');
    else setSettingsModalOpen(false);
  };

  const handleSelectProvider = (providerKey: string) => {
    setAiSelectedProvider(providerKey);
    setAiTestResult(null);
    setAiModels([]);
    setAiModelsError(null);
    setAiModelsOpen(false);
    if (aiConfig?.presets && aiConfig.presets[providerKey]) {
      const preset = aiConfig.presets[providerKey];
      if (providerKey !== 'custom') {
        setAiEndpointInput(preset.endpoint);
        setAiModelInput(preset.default_model);
      }
    }
  };

  /** Auto-detect models from the provider endpoint using the same API key. */
  const handleFetchModels = async () => {
    setAiModelsLoading(true);
    setAiModelsError(null);
    setAiModelsOpen(false);
    try {
      const res = await fetch('/api/ai-config/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          endpoint: aiEndpointInput.trim(),
          api_key: aiApiKeyInput.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (data.ok && Array.isArray(data.models) && data.models.length > 0) {
        setAiModels(data.models);
        setAiModelsOpen(true);
      } else {
        setAiModels([]);
        setAiModelsError(data.error || 'Gagal mengambil daftar model.');
      }
    } catch (e: any) {
      setAiModels([]);
      setAiModelsError(e.message || 'Gagal menghubungi backend.');
    } finally {
      setAiModelsLoading(false);
    }
  };

  const handleTestAiConnection = async () => {
    setAiTesting(true);
    setAiTestResult(null);
    try {
      const res = await fetch('/api/ai-config/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          endpoint: aiEndpointInput.trim(),
          api_key: aiApiKeyInput.trim() || undefined,
          model: aiModelInput.trim(),
        }),
      });
      const data = await res.json();
      setAiTestResult(data);
    } catch (e: any) {
      setAiTestResult({ ok: false, error: e.message || 'Gagal menghubungi backend.' });
    } finally {
      setAiTesting(false);
    }
  };

  const handleTestGroqConnection = async () => {
    setAiTestingGroq(true);
    setAiGroqTestResult(null);
    try {
      const res = await fetch('/api/ai-config/test-groq', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          groq_key: aiGroqKeyInput.trim() || undefined,
        }),
      });
      const data = await res.json();
      setAiGroqTestResult(data);
    } catch (e: any) {
      setAiGroqTestResult({ ok: false, error: e.message || 'Gagal menghubungi backend.' });
    } finally {
      setAiTestingGroq(false);
    }
  };

  const handleSaveAiConfig = async () => {
    setAiSaving(true);
    try {
      const payload: any = {
        provider: aiSelectedProvider,
        endpoint: aiEndpointInput.trim(),
        model: aiModelInput.trim(),
      };
      if (aiApiKeyInput.trim()) {
        payload.api_key = aiApiKeyInput.trim();
      }
      if (aiGroqKeyInput.trim()) {
        payload.groq_key = aiGroqKeyInput.trim();
      }

      const res = await fetch('/api/ai-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Gagal menyimpan konfigurasi.');
      }
      const updated: AiConfigResponse = await res.json();
      setAiConfig(updated);
      setSettingsModalOpen(false);
      showToast('Konfigurasi AI Disimpan', 'Pengaturan model dan API Key telah tersambung langsung ke Engine.', 'success');
      const ts = new Date().toTimeString().split(' ')[0];
      setLogs(prev => [...prev, `[${ts}] [SYSTEM] 🤖 Konfigurasi AI tersambung: ${updated.model} via ${updated.endpoint}`]);
    } catch (e: any) {
      showToast('Gagal Menyimpan', e.message || 'Terjadi kesalahan saat menyimpan.', 'error');
    } finally {
      setAiSaving(false);
    }
  };

  // Toast Popup Message State (Bottom-Right)
  const [toast, setToast] = useState<{
    id: number;
    title: string;
    message: string;
    type: 'success' | 'info' | 'error' | 'warning';
  } | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (title: string, message: string, type: 'success' | 'info' | 'error' | 'warning' = 'success') => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ id: Date.now(), title, message, type });
    toastTimerRef.current = setTimeout(() => {
      setToast(null);
    }, 6000);
  };

  const terminalRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const renderAbortControllerRef = useRef<AbortController | null>(null);
  const analysisReceivedRef = useRef(false);
  const confirmedClipCount = clipCandidates.filter(c => c.decision === 'approved').length;

  const resetWorkflow = (clearSource = false) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    renderAbortControllerRef.current?.abort();
    renderAbortControllerRef.current = null;
    setPhase('config');
    setStatus('ready');
    setProgress(0);
    setIsProcessing(false);
    setClipCandidates([]);
    setAnalysisId('');
    setResolvedVideoPath('');
    setPreviewClipRange(null);
    setPreviewOutputClip(null);
    setGeneratedClips([]);
    setOutputDir('');
    setRenderErrorMessage(null);
    setShowTerminalInPreview(false);
    setUploadedYtLinks({});
    setSelectedClipForYt(null);
    setSelectedClipForTt(null);
    setYtModalOpen(false);
    setTtModalOpen(false);
    setYtUploadProgress('idle');
    setYtUploadResult(null);
    setYtUploadErrorMessage(null);
    setSourceKind('video');
    if (clearSource) setVideoPathInput('');
  };

  const handleLoadRenderedFolder = async (targetPath: string) => {
    try {
      const response = await fetch('/api/rendered-clips/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: targetPath.trim() })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Hasil render tidak dapat dimuat');
      }
      const clips = (data.clips || []) as GeneratedClipItem[];
      if (clips.length === 0) {
        throw new Error('Folder ini tidak berisi video hasil render');
      }

      resetWorkflow(false);
      setVideoPathInput(data.output_dir);
      setSourceKind('render-folder');
      setOutputDir(data.output_dir);
      setGeneratedClips(clips);
      setPreviewOutputClip({
        path: clips[0].out_file || '',
        title: clips[0].title,
        id: clips[0].id
      });
      setProgress(100);
      setPhase('complete');
      setStatus('complete');

      const timestamp = new Date().toTimeString().split(' ')[0];
      setLogs(prev => [
        ...prev,
        `[${timestamp}] [SYSTEM] 📂 Folder hasil render dimuat: ${data.output_dir}`,
        `[${timestamp}] [SYSTEM] ✅ ${clips.length} klip siap dipreview dan diposting langsung ke YouTube / TikTok!`
      ]);
      showToast('Hasil Render Dimuat 🎬', `${clips.length} klip siap diposting ke YouTube / TikTok.`, 'success');
      return true;
    } catch (error: any) {
      showToast('Gagal Memuat Render ❌', error.message || 'Folder tidak valid', 'error');
      return false;
    }
  };

  const handlePickNativeFile = async () => {
    setIsPickingFile(true);
    try {
      const res = await fetch('/api/pick-file', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Gagal membuka file dialog');
      }
      const data = await res.json();
      if (data.path) {
        // If the user selected a clip file inside the clips directory, automatically restore the project!
        const isClipsVideo = data.path.includes('/clips/') || data.path.includes('\\clips\\');
        if (isClipsVideo) {
          const loaded = await handleLoadRenderedFolder(data.path);
          if (loaded) return;
        }

        resetWorkflow(false);
        setVideoPathInput(data.path);
        setSourceKind('video');
        showToast('File Video Terpilih', data.path, 'success');
      }
    } catch (e: any) {
      showToast('Gagal Membuka File Dialog', e.message || 'Pastikan backend server berjalan', 'error');
    } finally {
      setIsPickingFile(false);
    }
  };

  const handlePickNativeFolder = async () => {
    setIsPickingFolder(true);
    try {
      const res = await fetch('/api/pick-folder', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Gagal membuka folder dialog');
      }
      const data = await res.json();
      if (data.path) {
        await handleLoadRenderedFolder(data.path);
      }
    } catch (e: any) {
      showToast('Gagal Membuka Folder Dialog', e.message || 'Pastikan backend server berjalan', 'error');
    } finally {
      setIsPickingFolder(false);
    }
  };

  // Auto Scroll Terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  useEffect(() => {
    setYtAvatarFailed(false);
  }, [ytChannel?.thumbnail]);

  // Clean up EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      renderAbortControllerRef.current?.abort();
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  // Fetch YouTube connection status & handle query params from callback
  const checkYouTubeStatus = async (showNotification = false) => {
    setIsCheckingYtStatus(true);
    try {
      const res = await fetch('/api/social/youtube/status');
      if (res.ok) {
        const data = await res.json();
        setYtConnected(data.connected);
        setYtChannel(data.channel);
        if (data.channel?.customUrl) {
          setAccountWatermark(prev => prev || data.channel.customUrl);
        } else if (data.channel?.title) {
          setAccountWatermark(prev => prev || `@${data.channel.title.replace(/\s+/g, '').toLowerCase()}`);
        }
        if (showNotification) {
          const ts = new Date().toTimeString().split(' ')[0];
          if (data.connected && data.channel) {
            setLogs(prev => [...prev, `[${ts}] [YOUTUBE] 🟢 Konektivitas Aktif! Terhubung ke channel: ${data.channel.title} (${data.channel.customUrl || '@asal.sharing'})`]);
          } else {
            setLogs(prev => [...prev, `[${ts}] [YOUTUBE] ⚠️ Akun YouTube belum terhubung.`]);
          }
        }
      }
    } catch (e: any) {
      if (showNotification) {
        const ts = new Date().toTimeString().split(' ')[0];
        setLogs(prev => [...prev, `[${ts}] [YOUTUBE] ❌ Gagal mengecek status YouTube: ${e.message}`]);
      }
    } finally {
      setIsCheckingYtStatus(false);
    }
  };

  // Fetch TikTok connection status
  // TikTok Quick Upload Assistant State (Solusi 1)
  const [ttModalOpen, setTtModalOpen] = useState(false);
  const [selectedClipForTt, setSelectedClipForTt] = useState<GeneratedClipItem | null>(null);
  const [ttFormTitle, setTtFormTitle] = useState('');
  const [ttCopied, setTtCopied] = useState(false);

  useEffect(() => {
    const initializeYouTube = async () => {
      try {
        await fetch('/api/session');
      } catch {
        // The status request below will surface an unavailable backend.
      }

      await checkYouTubeStatus();

      // Check if redirected from Google OAuth callback
      const urlParams = new URLSearchParams(window.location.search);
      const authStatus = urlParams.get('youtube_auth');
      if (authStatus === 'success') {
        const ts = new Date().toTimeString().split(' ')[0];
        setLogs(prev => [...prev, `[${ts}] [YOUTUBE] 🎉 Akun YouTube berhasil terhubung!`]);
        await checkYouTubeStatus(true);
        window.history.replaceState({}, document.title, window.location.pathname);
      } else if (authStatus === 'error' || authStatus === 'failed') {
        const ts = new Date().toTimeString().split(' ')[0];
        const msg = urlParams.get('msg') || 'Otorisasi ditolak';
        setLogs(prev => [...prev, `[${ts}] [YOUTUBE] ❌ Gagal menghubungkan akun YouTube: ${msg}`]);
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    };

    void initializeYouTube();
  }, []);

  const handleConnectYouTube = async () => {
    try {
      const res = await fetch('/api/social/youtube/auth-url');
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        alert("Gagal membuat OAuth URL: " + (data.error || "Unknown error"));
      }
    } catch (e: any) {
      alert("Error: " + e.message);
    }
  };

  const handleDisconnectYouTube = async () => {
    if (!confirm("Putuskan koneksi akun YouTube? Anda perlu login ulang untuk upload berikutnya.")) return;
    try {
      await fetch('/api/social/youtube/disconnect', { method: 'POST' });
      setYtConnected(false);
      setYtChannel(null);
      const ts = new Date().toTimeString().split(' ')[0];
      setLogs(prev => [...prev, `[${ts}] [YOUTUBE] 🔌 Koneksi YouTube diputuskan.`]);
    } catch (e: any) {}
  };

  // Open Quick Upload Modal for TikTok (Solusi 1)
  const handleOpenTikTokModal = (clip: GeneratedClipItem) => {
    const clipCandidate = clipCandidates.find(c => c.index === parseInt(clip.id));
    const finalTitle = clip.title || (clipCandidate ? clipCandidate.title_options[0] : `Clip #${clip.id}`);
    const caption = clip.caption || clipCandidate?.caption || finalTitle;
    const rawHashtags = clip.hashtags || clipCandidate?.hashtags || ["fyp", "viral", "trending"];
    const hashtags = rawHashtags.map(h => (h.startsWith('#') ? h : `#${h}`)).slice(0, 5).join(' ');

    const fullCaption = `${caption} ${hashtags}`.trim();

    setSelectedClipForTt(clip);
    setTtFormTitle(fullCaption);
    setTtCopied(false);
    setTtModalOpen(true);
  };

  // Copy the caption and open TikTok Studio; file selection stays manual.
  const handleLaunchTikTokUpload = async () => {
    if (!selectedClipForTt) return;

    // Open from the direct click event so the browser does not block the new tab.
    window.open('https://www.tiktok.com/creator-center/upload', '_blank', 'noopener,noreferrer');

    try {
      await navigator.clipboard.writeText(ttFormTitle);
      setTtCopied(true);
    } catch (e) {
      console.warn("Clipboard copy failed:", e);
    }

    const ts = new Date().toTimeString().split(' ')[0];
    setLogs(prev => [...prev, `[${ts}] [TIKTOK] 🚀 Membuka TikTok Creator Center! Caption & hashtag telah disalin ke clipboard.`]);
    showToast(
      'TikTok Upload Siap! 🚀',
      'Caption disalin. Pilih file video secara manual di halaman upload TikTok Studio.',
      'success'
    );
  };

  // Open Confirmation Modal for Direct YouTube Posting
  const handleOpenUploadModal = (clip: GeneratedClipItem) => {
    if (!ytConnected) {
      showToast('YouTube Belum Terhubung', 'Silakan hubungkan channel YouTube di tab Pengaturan.', 'warning');
      handleOpenSettings('youtube');
      return;
    }

    const clipCandidate = clipCandidates.find(c => c.index === parseInt(clip.id));
    const finalTitle = clip.title || (clipCandidate ? clipCandidate.title_options[0] : `Clip #${clip.id}`);
    const caption = clip.caption || clipCandidate?.caption || finalTitle;
    const rawHashtags = clip.hashtags || clipCandidate?.hashtags || ["Shorts", "Viral"];
    const hashtags = rawHashtags.map(h => h.replace(/^#/, '').trim()).filter(Boolean);
    if (!hashtags.includes('Shorts')) hashtags.unshift('Shorts');

    const tagsString = hashtags.map(h => `#${h}`).join(' ');
    const description = `${caption}\n\n${tagsString}\n\nDiproduksi otomatis menggunakan VisionClipper Studio`;

    setSelectedClipForYt(clip);
    setYtFormTitle(finalTitle);
    setYtFormDescription(description);
    setYtFormTags(hashtags);
    setYtFormPrivacy('public'); // Default ke Posting Langsung (Publik)
    setYtFormAutoShortsTag(true);
    setYtUploadProgress('idle');
    setYtUploadResult(null);
    setYtUploadErrorMessage(null);
    setYtModalOpen(true);
  };

  // Confirmed Direct Posting Execution
  const handleConfirmUploadToYouTube = async () => {
    if (!selectedClipForYt) return;
    if (!ytFormTitle.trim()) {
      alert("Judul video Shorts tidak boleh kosong!");
      return;
    }

    const clip = selectedClipForYt;
    let finalTitle = ytFormTitle.trim();
    if (ytFormAutoShortsTag && !finalTitle.toLowerCase().includes('#shorts') && finalTitle.length <= 92) {
      finalTitle = `${finalTitle} #Shorts`;
    }

    // Guess file path if not directly in clip
    let filePath = clip.out_file || '';
    if (!filePath && outputDir) {
      const safeTitle = (clip.title || `Clip_${clip.id}`).replace(/[^a-zA-Z0-9]/g, "_").replace(/^_+|_+$/g, "");
      filePath = `${outputDir}/${String(clip.id).padStart(2, '0')}_${safeTitle}.mp4`;
    }

    setIsUploadingYt(clip.id);
    setYtUploadProgress('uploading');
    setYtUploadErrorMessage(null);

    const ts = new Date().toTimeString().split(' ')[0];
    const privacyLabel = ytFormPrivacy === 'public' ? 'Publik (Posting Langsung)' : ytFormPrivacy === 'unlisted' ? 'Unlisted' : 'Private';
    setLogs(prev => [...prev, `[${ts}] [YOUTUBE] 🚀 Mengunggah Klip #${clip.id} "${finalTitle}" ke YouTube (${privacyLabel})...`]);

    try {
      const res = await fetch('/api/social/youtube/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: filePath,
          title: finalTitle,
          description: ytFormDescription,
          tags: ytFormTags,
          privacy: ytFormPrivacy
        })
      });

      const data = await res.json();
      if (!res.ok || data.status !== 'success') {
        throw new Error(data.error || 'Upload gagal');
      }

      setUploadedYtLinks(prev => ({ ...prev, [clip.id]: data.url || data.shorts_url }));
      setYtUploadResult(data);
      setYtUploadProgress('success');
      const doneTs = new Date().toTimeString().split(' ')[0];
      setLogs(prev => [...prev, `[${doneTs}] [YOUTUBE] ✅ Berhasil diposting! Link: ${data.shorts_url || data.url} (Status: ${privacyLabel})`]);
      showToast(
        'Berhasil Diposting ke YouTube! 🚀',
        `Klip "${finalTitle}" kini telah live di channel YouTube Anda (${privacyLabel}).`,
        'success'
      );
    } catch (err: any) {
      const errTs = new Date().toTimeString().split(' ')[0];
      setYtUploadProgress('error');
      setYtUploadErrorMessage(err.message || 'Gagal mengunggah video ke YouTube');
      setLogs(prev => [...prev, `[${errTs}] [YOUTUBE] ❌ Gagal upload: ${err.message}`]);
      showToast('Gagal Mengunggah ke YouTube ❌', err.message || 'Terjadi kesalahan saat upload', 'error');
    } finally {
      setIsUploadingYt(null);
    }
  };

  // Backward-compatible trigger
  const handleUploadToYouTube = (clip: GeneratedClipItem) => {
    handleOpenUploadModal(clip);
  };

  // Handle Preset Change — klik untuk pilih, klik lagi untuk uncheck (tanpa subtitle)
  const handleSelectPreset = (preset: SubtitleStyleConfig) => {
    setSelectedPresetId(prev => (prev === preset.presetId ? 'no_subtitle' : preset.presetId));
  };

  const previewCandidate = (clip: ClipCandidate) => {
    setPreviewOutputClip(null);
    setPreviewClipRange({ start: clip.start, end: clip.end });
    setActiveClipMeta({
      title: clip.title_options?.[0],
      caption: clip.caption,
      hashtags: clip.hashtags
    });
    setClipCandidates(prev => prev.map(candidate =>
      candidate.index === clip.index ? { ...candidate, previewed: true } : candidate
    ));
  };

  const previewRenderedClip = (clip: GeneratedClipItem) => {
    let filePath = clip.out_file || '';
    if (!filePath && outputDir) {
      const safeTitle = (clip.title || `Clip_${clip.id}`).replace(/[^a-zA-Z0-9]/g, "_").replace(/^_+|_+$/g, "");
      filePath = `${outputDir}/${String(clip.id).padStart(2, '0')}_${safeTitle}.mp4`;
    }
    if (filePath) {
      setPreviewClipRange(null);
      setPreviewOutputClip({
        path: filePath,
        title: clip.title || `Clip #${clip.id}`,
        id: clip.id
      });
      setActiveClipMeta({
        title: clip.title,
        caption: clip.caption,
        hashtags: clip.hashtags
      });
    }
  };

  // Start Real Processing via SSE — Phase 1: Analyze Only
  const handleStartProcessing = async () => {
    if (sourceKind === 'render-folder') {
      showToast('Hasil Render Sudah Siap', 'Pilih file video baru jika ingin menjalankan analisis.', 'info');
      return;
    }
    const source = videoPathInput.trim();
    if (!source) {
      alert('Silakan masukkan file path video atau URL YouTube terlebih dahulu!');
      return;
    }

    if (aiConfig && !aiConfig.ready) {
      showToast('AI Belum Dikonfigurasi', 'Silakan setup AI Provider dan API Key terlebih dahulu.', 'warning');
      handleOpenAiSettings();
      return;
    }

    if (transcriptionModel === 'groq' && aiConfig && !aiConfig.groq_ready) {
      showToast('Groq API Key Kosong', 'Transkripsi Groq membutuhkan API Key. Buka Pengaturan AI untuk memasukkannya.', 'warning');
      handleOpenAiSettings();
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setIsProcessing(true);
    setStatus('processing');
    setPhase('analyzing');
    setProgress(0);
    setGeneratedClips([]);
    setOutputDir('');
    setClipCandidates([]);
    setAnalysisId('');
    setResolvedVideoPath('');
    setPreviewClipRange(null);
    setPreviewOutputClip(null);
    analysisReceivedRef.current = false;

    const startTimestamp = new Date().toTimeString().split(' ')[0];
    const langLabel = languageMode === 'en_to_id'
      ? 'English ➔ Terjemahkan ke Indo'
      : languageMode === 'en'
      ? 'English (Asli)'
      : languageMode === 'auto'
      ? 'Auto-Detect'
      : 'Bahasa Indonesia';

    setLogs([
      `[${startTimestamp}] [SYSTEM] Inisialisasi ${activeTab.toUpperCase()} CLIPPER ENGINE...`,
      `[${startTimestamp}] [SYSTEM] Model AI: Groq Whisper Cloud | Bahasa: ${langLabel} | Subtitle Style: ${selectedPresetId}`,
      `[${startTimestamp}] [SYSTEM] Sumber video: ${source}`,
      `[${startTimestamp}] [SYSTEM] Memulai proses transkripsi & analisis AI (tanpa render)...`
    ]);

    let sourceLang = 'id';
    let targetLang = 'id';
    if (languageMode === 'en_to_id') {
      sourceLang = 'en';
      targetLang = 'id';
    } else if (languageMode === 'en') {
      sourceLang = 'en';
      targetLang = 'en';
    } else if (languageMode === 'auto') {
      sourceLang = 'auto';
      targetLang = 'id';
    }

    try {
      await fetch('/api/session', { credentials: 'include' });
    } catch {
      // Proceed with request
    }

    const streamUrl = `/api/analyze?mode=${encodeURIComponent(activeTab)}&source=${encodeURIComponent(source)}&num_clips=${encodeURIComponent(clipCount)}&whisper_model=${encodeURIComponent(transcriptionModel)}&source_lang=${encodeURIComponent(sourceLang)}&target_lang=${encodeURIComponent(targetLang)}`;
    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;
    let analysisComplete = false;

    es.onmessage = (event) => {
      const data = event.data;

      if (data === '[PROCESS_COMPLETE]') {
        const doneTimestamp = new Date().toTimeString().split(' ')[0];
        const finishedWithCandidates = analysisReceivedRef.current;
        setLogs(prev => [...prev, finishedWithCandidates
          ? `[${doneTimestamp}] [SYSTEM] ✅ Analisis selesai! Silakan review dan pilih klip.`
          : `[${doneTimestamp}] [SYSTEM] ❌ Analisis tidak menghasilkan kandidat klip.`
        ]);
        setProgress(100);
        setStatus(finishedWithCandidates ? 'ready' : 'error');
        if (!finishedWithCandidates) setPhase('config');
        setIsProcessing(false);
        analysisComplete = true;
        // Transition to preview phase happens via [ANALYSIS_RESULT] handler
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      } else if (data === '[PROCESS_FAILED]') {
        const failTimestamp = new Date().toTimeString().split(' ')[0];
        setLogs(prev => [...prev, `[${failTimestamp}] [SYSTEM] ❌ Analisis gagal. Silakan periksa log.`]);
        setPhase('config');
        setStatus('error');
        setIsProcessing(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      } else if (data === '[HEARTBEAT]') {
        // Keep-alive heartbeat
      } else if (data.startsWith('[ANALYSIS_RESULT]')) {
        // Parse analysis JSON from backend
        try {
          const jsonStr = data.substring('[ANALYSIS_RESULT]'.length);
          const result = JSON.parse(jsonStr);
          const candidates: ClipCandidate[] = (result.clips || []).map((c: any, i: number) => ({
            index: c.index || i + 1,
            start: c.start,
            end: c.end,
            duration: c.duration || Math.round((c.end - c.start) * 100) / 100,
            title_options: c.title_options || [c.title || 'Untitled'],
            reason: c.reason || '',
            viral_score: c.viral_score || 0,
            sales_score: c.sales_score,
            caption: c.caption || '',
            hashtags: c.hashtags || [],
            decision: 'pending',
            previewed: false
          }));
          setClipCandidates(candidates);
          setAnalysisId(result.analysis_id || '');
          setResolvedVideoPath(result.video_path || source);
          setOutputDir(result.output_dir || '');
          if (result.source_name) {
            setSourceWatermark(prev => prev || result.source_name);
          }
          analysisReceivedRef.current = true;
          setPhase('preview');
          const ts = new Date().toTimeString().split(' ')[0];
          setLogs(prev => [...prev, `[${ts}] [SYSTEM] 🎯 Ditemukan ${candidates.length} kandidat klip viral. Silakan review di panel kanan.`]);
        } catch (e: any) {
          const ts = new Date().toTimeString().split(' ')[0];
          setLogs(prev => [...prev, `[${ts}] [SYSTEM] ⚠️ Gagal parse hasil analisis: ${e.message}`]);
        }
      } else {
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
      if (analysisComplete || es.readyState === EventSource.CLOSED) return;
      console.error("SSE Error:", err);
      const errTimestamp = new Date().toTimeString().split(' ')[0];
      setLogs(prev => [...prev, `[${errTimestamp}] [SYSTEM] ⚠️ Koneksi ke background worker terputus.`]);
      setPhase('config');
      setStatus('error');
      setIsProcessing(false);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  };

  // Phase 2: Render only approved clips
  const handleRenderSelected = () => {
    const approved = clipCandidates.filter(c => c.decision === 'approved');
    if (!analysisId || approved.length === 0) {
      alert('Preview lalu confirm minimal 1 klip untuk di-render!');
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setIsProcessing(true);
    setStatus('processing');
    setPhase('rendering');
    setProgress(0);
    setGeneratedClips([]);
    setPreviewClipRange(null);
    setPreviewOutputClip(null);

    const startTimestamp = new Date().toTimeString().split(' ')[0];
    setLogs(prev => [
      ...prev,
      `[${startTimestamp}] [SYSTEM] ✨ Memulai rendering ${approved.length} klip yang dipilih...`
    ]);

    const body = {
      analysis_id: analysisId,
      clip_indices: approved.map(c => c.index),
      sub_style: selectedPresetId,
      framing_mode: framingMode,
      sub_position: subPosition,
      show_emoji: showEmoji,
      watermark_enabled: watermarkEnabled,
      source_watermark: sourceWatermark.trim(),
      account_watermark: accountWatermark.trim()
    };

    const controller = new AbortController();
    renderAbortControllerRef.current = controller;

    void (async () => {
      try {
        const response = await fetch('/api/render-selected', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: controller.signal
        });
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.error || `Request gagal (${response.status})`);
        }
        if (!response.body) throw new Error('Response stream tidak tersedia');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finished = false;

        while (!finished) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.substring(6);

            if (data === '[PROCESS_COMPLETE]') {
              const ts = new Date().toTimeString().split(' ')[0];
              setLogs(prev => [...prev, `[${ts}] [SYSTEM] ✅ Semua klip berhasil dirender!`]);
              setProgress(100);
              setPhase('complete');
              setStatus('complete');
              setRenderErrorMessage(null);
              setIsProcessing(false);
              showToast(
                'Semua Klip Selesai Dirender! 🎬',
                'Klip vertikal 9:16 Anda telah siap diposting langsung ke YouTube Shorts.',
                'success'
              );
              finished = true;
              break;
            }
            if (data === '[PROCESS_FAILED]') {
              const ts = new Date().toTimeString().split(' ')[0];
              setLogs(prev => [...prev, `[${ts}] [SYSTEM] ❌ Rendering gagal. Periksa log terminal di bawah untuk rincian error.`]);
              setPhase('preview');
              setStatus('error');
              setRenderErrorMessage('Rendering gagal dieksekusi. Silakan periksa log terminal di bawah untuk melihat rincian error.');
              setShowTerminalInPreview(true);
              setIsProcessing(false);
              showToast('Rendering Gagal ❌', 'Terjadi kendala saat rendering. Periksa log proses di bawah.', 'error');
              finished = true;
              break;
            }
            if (data === '[HEARTBEAT]') continue;

            if (data.includes('Outputs will be saved to:')) {
              const match = data.match(/Outputs will be saved to:\s*(.*)/);
              if (match?.[1]) setOutputDir(match[1].trim());
            }

            if (data.startsWith('[CLIP_RENDERED]')) {
              try {
                const clipObj = JSON.parse(data.substring('[CLIP_RENDERED]'.length));
                const indexStr = String(clipObj.index);
                setGeneratedClips(prev => {
                  const filtered = prev.filter(c => c.id !== indexStr);
                  const updated = [...filtered, {
                    id: indexStr,
                    title: clipObj.title,
                    out_file: clipObj.out_file,
                    caption: clipObj.caption,
                    hashtags: clipObj.hashtags
                  }];
                  return updated;
                });
                // Set as active preview if no output clip is currently being previewed
                setPreviewOutputClip(curr => curr || {
                  path: clipObj.out_file,
                  title: clipObj.title,
                  id: indexStr
                });
              } catch (e) {}
            } else if (data.includes('Rendering Subtitles, Audio Enhancer, and Color Grading for Clip')) {
              const clipMatch = data.match(/for Clip (\d+):\s*(.*)/);
              if (clipMatch) {
                const index = clipMatch[1];
                const title = clipMatch[2];
                setGeneratedClips(prev => prev.some(c => c.id === index) ? prev : [...prev, { id: index, title }]);
              }
            }

            const progressMatch = data.match(/([\d.]+)%/);
            if (progressMatch) {
              const value = parseFloat(progressMatch[1]);
              if (!isNaN(value)) setProgress(Math.min(100, Math.max(0, Math.round(value))));
            }

            setLogs(prev => {
              if (data.includes('Progress') || data.includes('%|')) {
                const lastLog = prev[prev.length - 1];
                if (lastLog && (lastLog.includes('Progress') || lastLog.includes('%|'))) return [...prev.slice(0, -1), data];
              }
              return [...prev, data];
            });
          }
        }

        if (!finished) {
          throw new Error('Render stream berhenti sebelum selesai');
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        const ts = new Date().toTimeString().split(' ')[0];
        setLogs(prev => [...prev, `[${ts}] [SYSTEM] ❌ Error: ${err.message}`]);
        setPhase('preview');
        setStatus('error');
        setRenderErrorMessage(err.message || 'Terjadi kesalahan saat rendering');
        setShowTerminalInPreview(true);
        setIsProcessing(false);
        showToast('Error Rendering ❌', err.message || 'Terjadi kesalahan saat rendering', 'error');
      } finally {
        if (renderAbortControllerRef.current === controller) renderAbortControllerRef.current = null;
      }
    })();
  };

  // Stop / Cancel Processing
  const handleStopProcessing = async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    renderAbortControllerRef.current?.abort();
    renderAbortControllerRef.current = null;
    const returnPhase = phase === 'rendering' ? 'preview' : 'config';
    const stopTime = new Date().toTimeString().split(' ')[0];
    setLogs(prev => [...prev, `[${stopTime}] [SYSTEM] ⛔ Mengirim sinyal pembatalan ke backend...`]);

    try {
      await fetch('/cancel', { method: 'POST' });
      setLogs(prev => [...prev, `[${stopTime}] [SYSTEM] ⛔ Proses berhasil dihentikan oleh pengguna.`]);
    } catch (e: any) {
      setLogs(prev => [...prev, `[${stopTime}] [SYSTEM] Error cancel: ${e.message}`]);
    } finally {
      setIsProcessing(false);
      setPhase(returnPhase);
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
    // Sidebar tile states (shared across LAYOUT / SUBTITLE / option cards)
    tileIdle: 'border-slate-800 bg-slate-950/50 hover:bg-slate-900/80 hover:border-slate-700',
    tileActive: 'border-emerald-500/80 bg-gradient-to-b from-emerald-950/50 to-emerald-950/20 shadow-[0_0_0_1px_rgba(16,185,129,0.25),0_4px_14px_-4px_rgba(16,185,129,0.35)] ring-1 ring-emerald-500/30',
    chipActive: 'bg-emerald-500/15 border-emerald-500/50 text-emerald-300',
    chipIdle: 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
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
      <header className={`flex h-14 flex-shrink-0 items-center justify-between ${themeClasses.header} rounded-2xl border px-5 shadow-lg z-20 mx-3 mt-3`}>

        {/* Left: Brand Logo & Title */}
        <div className="flex items-center gap-3">
          <img
            src="/images/logo-banner-transparent.png"
            alt="VisionClipper Studio"
            className="h-9 w-auto object-contain select-none filter drop-shadow-sm"
          />
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

        {/* Right: Active Processing Badge & Studio Settings Icon */}
        <div className="flex items-center gap-2.5">
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

          {/* Unified Settings Icon Button */}
          <button
            type="button"
            onClick={() => handleOpenSettings()}
            className={`relative flex h-9 w-9 items-center justify-center rounded-xl border transition-all shadow-sm active:scale-95 cursor-pointer ${
              aiConfig && !aiConfig.ready
                ? 'border-amber-500/60 bg-amber-500/20 text-amber-300 ring-2 ring-amber-500/30 animate-pulse'
                : 'border-slate-800 bg-slate-900/90 text-slate-300 hover:text-emerald-400 hover:border-emerald-500/40 hover:bg-slate-800'
            }`}
            title="Pengaturan Studio (Model AI, YouTube, TikTok)"
          >
            <Cog6ToothIcon className={`h-5 w-5 stroke-[1.8] ${aiConfig && !aiConfig.ready ? 'text-amber-400' : 'text-slate-300 hover:text-emerald-400'}`} />
            {aiConfig && !aiConfig.ready ? (
              <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-500 border border-[#0f141b]"></span>
              </span>
            ) : ytConnected ? (
              <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400 border border-[#0f141b]"></span>
              </span>
            ) : null}
          </button>
        </div>

      </header>

      {/* AI Warning Banner when not configured */}
      {aiConfig && !aiConfig.ready && (
        <div className="flex items-center justify-between bg-gradient-to-r from-amber-950/90 via-amber-900/60 to-slate-950/90 border-b border-amber-500/40 px-5 py-2 text-xs text-amber-200 z-10 shadow-sm flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <ExclamationTriangleIcon className="h-4 w-4 text-amber-400 flex-shrink-0" />
            <span>
              <strong className="text-white">AI Engine belum terhubung:</strong> Masukkan API Key & Provider (OpenRouter, OpenAI, Groq, DeepSeek, atau Custom) agar AI dapat menganalisis momen viral.
            </span>
          </div>
          <button
            onClick={() => handleOpenSettings('ai')}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-all shadow-sm active:scale-95 cursor-pointer ml-3 flex-shrink-0"
          >
            <Cog6ToothIcon className="h-3.5 w-3.5 stroke-[2.5]" />
            <span>Buka Pengaturan AI</span>
          </button>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          2. MAIN CONTENT: 3-COLUMN WORKSPACE
         ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-hidden grid grid-cols-1 lg:grid-cols-3 gap-3 px-3 pb-3 pt-3">

        {/* ── COLUMN 1: LEFT SIDEBAR (SETTINGS & CONTROLS) ── */}
        <aside className={`flex min-h-0 flex-col rounded-2xl border ${themeClasses.sidebar} p-3.5 overflow-y-auto scrollbar-thin`}>

          {/* ═══ WORKFLOW STEPPER (numbered vertical timeline) ═══ */}

          {/* STEP 01 — SUMBER VIDEO */}
          <StepCard
            step={1}
            icon={<CloudArrowDownIcon className="h-4 w-4 stroke-[2]" />}
            title="Sumber Video"
            hint="File, YouTube URL, atau Folder Clips"
          >
            <div className="relative">
              <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 flex h-4 w-4 items-center justify-center text-slate-500">
                <LinkIcon className="h-3.5 w-3.5 stroke-[2]" />
              </span>
              <input
                type="text"
                value={videoPathInput}
                onChange={(e) => {
                  if (sourceKind === 'render-folder') resetWorkflow(false);
                  setVideoPathInput(e.target.value);
                  setSourceKind('video');
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && videoPathInput.trim()) {
                    void handleLoadRenderedFolder(videoPathInput.trim());
                  }
                }}
                placeholder="Tempel link YouTube atau path video..."
                className={`w-full rounded-lg border py-1.5 pl-8 pr-2.5 text-[11px] font-mono transition-all shadow-inner truncate ${themeClasses.input} ${sourceKind === 'render-folder' ? 'border-emerald-500/60 ring-1 ring-emerald-500/30' : ''}`}
              />
            </div>

            <div className="grid grid-cols-2 gap-1.5 mt-1.5">
              <button
                type="button"
                onClick={handlePickNativeFile}
                disabled={isPickingFile || isPickingFolder || isProcessing}
                className="group flex items-center justify-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/90 px-2 py-1.5 text-slate-400 hover:text-white hover:border-slate-700 hover:bg-slate-800 transition-colors disabled:opacity-50"
                title="Pilih File Video dari Komputer (Native File Explorer)"
              >
                <VideoCameraIcon className={`h-3.5 w-3.5 stroke-[2] flex-shrink-0 ${isPickingFile ? 'animate-pulse text-cyan-400' : 'group-hover:text-cyan-400'}`} />
                <span className="text-[10px] font-semibold truncate">File Video</span>
              </button>
              <button
                type="button"
                onClick={handlePickNativeFolder}
                disabled={isPickingFile || isPickingFolder || isProcessing}
                className="group flex items-center justify-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-950/40 px-2 py-1.5 text-emerald-400 hover:text-white hover:bg-emerald-900/50 hover:border-emerald-500/60 transition-colors disabled:opacity-50"
                title="Pilih Folder Hasil Render di clips (Native Folder Explorer)"
              >
                <FolderOpenIcon className={`h-3.5 w-3.5 stroke-[2] flex-shrink-0 ${isPickingFolder ? 'animate-pulse text-emerald-300' : ''}`} />
                <span className="text-[10px] font-semibold truncate">Folder Render</span>
              </button>
            </div>

            {sourceKind === 'render-folder' && (
              <div className="mt-1.5 flex items-center justify-between text-[10px] font-semibold text-emerald-300 bg-emerald-950/50 border border-emerald-500/30 rounded-lg px-2.5 py-1 shadow-xs">
                <div className="flex items-center gap-1.5 truncate mr-2">
                  <CheckCircleIcon className="h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                  <span className="truncate">Folder render aktif ({generatedClips.length} klip)</span>
                </div>
                <button
                  type="button"
                  onClick={() => resetWorkflow(true)}
                  className="text-slate-400 hover:text-white underline font-normal flex-shrink-0"
                  title="Kembali ke mode input video baru"
                >
                  Reset
                </button>
              </div>
            )}
          </StepCard>

          {/* STEP 02 — JUMLAH & BAHASA */}
          <StepCard
            step={2}
            icon={<Square3Stack3DIcon className="h-4 w-4 stroke-[2]" />}
            title="Output Klip"
            hint="Jumlah klip & bahasa audio"
          >
            <div className="mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-[10.5px] font-semibold text-slate-400">
                <ScissorsIcon className="h-3.5 w-3.5 text-emerald-400 stroke-[2]" />
                <span>Jumlah Klip</span>
              </span>
              <span className="font-['Outfit'] font-extrabold text-[11px] px-1.5 py-0.5 rounded-md border bg-emerald-950/60 text-emerald-300 border-emerald-500/40">
                {clipCount}
              </span>
            </div>
            <NumberPills value={clipCount} onChange={setClipCount} />

            <div className="mt-2 mb-1.5 flex items-center gap-1.5 text-[10.5px] font-semibold text-slate-400">
              <LanguageIcon className="h-3.5 w-3.5 text-sky-400 stroke-[2]" />
              <span>Bahasa Audio &amp; Subtitle</span>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { id: 'id', label: '🇮🇩 Indonesia' },
                { id: 'en_to_id', label: '🇬🇧→🇮🇩 Terjemah' },
                { id: 'en', label: '🇬🇧 English' },
                { id: 'auto', label: '🌐 Auto → 🇮🇩' },
              ].map((o) => (
                <button
                  key={o.id}
                  type="button"
                  onClick={() => setLanguageMode(o.id)}
                  className={`h-7 rounded-lg border text-[10px] font-semibold transition-colors truncate px-1 ${
                    languageMode === o.id ? themeClasses.chipActive : themeClasses.chipIdle
                  }`}
                  title={o.label}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </StepCard>

          {/* STEP 03 — FRAMING / LAYOUT */}
          <StepCard
            step={3}
            icon={<PhotoIcon className="h-4 w-4 stroke-[2]" />}
            title="Framing 9:16"
            hint="Gaya framing video"
          >
            <div className="grid grid-cols-3 gap-1.5">
              {[
                {
                  id: 'smart_crop' as FramingMode,
                  label: 'Smart',
                  sub: '9:16',
                  glyph: <div className="h-6 w-[13px] rounded-[3px] border border-emerald-400/70 bg-emerald-500/15" />,
                },
                {
                  id: 'fit_blur' as FramingMode,
                  label: 'Fit Blur',
                  sub: '16:9',
                  glyph: <div className="h-[15px] w-7 rounded-[3px] border border-cyan-400/70 bg-cyan-500/10" />,
                },
                {
                  id: 'split_screen' as FramingMode,
                  label: 'Dual',
                  sub: '50:50',
                  glyph: (
                    <div className="flex flex-col gap-[2px]">
                      <div className="h-[9px] w-6 rounded-[2px] bg-cyan-500/30 border border-cyan-500/60" />
                      <div className="h-[9px] w-6 rounded-[2px] bg-amber-500/30 border border-amber-500/60" />
                    </div>
                  ),
                },
              ].map((o) => {
                const isActive = framingMode === o.id;
                return (
                  <button
                    key={o.id}
                    type="button"
                    onClick={() => setFramingMode(o.id)}
                    title={o.label}
                    className={`${isActive ? themeClasses.tileActive : themeClasses.tileIdle} relative flex flex-col items-center justify-center gap-1 rounded-lg px-1 py-2 transition-all`}
                  >
                    <span className="flex h-6 items-center justify-center">{o.glyph}</span>
                    <span className={`text-[9px] font-bold leading-none ${isActive ? 'text-emerald-300' : 'text-slate-200'}`}>
                      {o.label}
                    </span>
                    <span className="text-[7.5px] text-slate-500 font-mono leading-none">{o.sub}</span>
                  </button>
                );
              })}
            </div>
          </StepCard>

          {/* STEP 04 — CAPTION / SUBTITLE */}
          <StepCard
            step={4}
            icon={<SwatchIcon className="h-4 w-4 stroke-[2]" />}
            title="Gaya Caption"
            hint="Klik untuk pakai, klik lagi untuk lepas"
          >
            <div className="grid grid-cols-2 gap-1.5">
              {SUBTITLE_PRESETS.map((preset) => {
                const isSelected = selectedPresetId === preset.presetId;
                return (
                  <button
                    key={preset.presetId}
                    onClick={() => handleSelectPreset(preset)}
                    role="checkbox"
                    aria-checked={isSelected}
                    className={`${isSelected ? themeClasses.tileActive : themeClasses.tileIdle} flex items-center gap-2 rounded-lg px-2 py-1.5 transition-all`}
                  >
                    <span
                      className="h-3 w-3 rounded-full flex-shrink-0 border border-white/20"
                      style={{ backgroundColor: preset.highlightColor }}
                    />
                    <span className={`text-[10px] font-bold truncate ${isSelected ? 'text-emerald-300' : 'text-slate-200'}`}>
                      {preset.name}
                    </span>
                  </button>
                );
              })}
            </div>

            {selectedPresetId !== 'no_subtitle' && (
              <div className="mt-1.5 flex flex-col gap-1.5">
                <div className="flex items-center gap-2 rounded-lg border border-slate-800/70 bg-slate-950/40 px-2 py-1.5">
                  <AdjustmentsHorizontalIcon className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                  <input
                    type="range"
                    min="35"
                    max="80"
                    step="1"
                    value={subPosition}
                    onChange={(e) => setSubPosition(Number(e.target.value))}
                    className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                    title="Area aman 35–80% agar tidak tertutup UI TikTok"
                  />
                  <span className="w-9 text-right font-mono text-[10px] text-emerald-400 font-bold">
                    {subPosition}%
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {[
                    { v: 50, l: 'Tengah' },
                    { v: 68, l: 'TikTok' },
                    { v: 80, l: 'Bawah' },
                  ].map((b) => (
                    <button
                      key={b.v}
                      type="button"
                      onClick={() => setSubPosition(b.v)}
                      className={`flex-1 py-1 rounded-md text-[9px] font-semibold border transition-colors ${
                        subPosition === b.v ? themeClasses.chipActive : themeClasses.chipIdle
                      }`}
                    >
                      {b.l}
                    </button>
                  ))}
                </div>

                <CompactToggle
                  icon={<SparklesIcon className="h-3.5 w-3.5 text-yellow-400" />}
                  label="Auto-Emoji Hook"
                  checked={showEmoji}
                  onChange={() => setShowEmoji(!showEmoji)}
                  title="Suntikkan emoji viral di kata kunci"
                />
              </div>
            )}
          </StepCard>

          {/* STEP 05 — BRANDING / WATERMARK */}
          <StepCard
            step={5}
            icon={<ShieldCheckIcon className="h-4 w-4 stroke-[2]" />}
            title="Branding"
            hint="Label kaca sumber & akun"
            isLast
            right={
              <MiniSwitch
                checked={watermarkEnabled}
                onChange={() => setWatermarkEnabled(!watermarkEnabled)}
                accent="cyan"
                title="Aktifkan / Nonaktifkan Watermark Glass Effect"
              />
            }
          >
            {watermarkEnabled ? (
              <div className="grid grid-cols-1 gap-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 text-[10px] flex-shrink-0" title="Sumber (Kiri Atas)">▶</span>
                  <input
                    type="text"
                    value={sourceWatermark}
                    onChange={(e) => setSourceWatermark(e.target.value)}
                    placeholder="Sumber / Channel (kiri atas)"
                    className="flex-1 h-7 px-2 rounded-lg bg-slate-900/80 border border-slate-800 text-[10.5px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40 transition-all"
                  />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-400 text-[11px] font-bold flex-shrink-0" title="Akun Clipper (Kanan Atas)">@</span>
                  <input
                    type="text"
                    value={accountWatermark}
                    onChange={(e) => setAccountWatermark(e.target.value)}
                    placeholder="@visionclipper (kanan atas)"
                    className="flex-1 h-7 px-2 rounded-lg bg-slate-900/80 border border-slate-800 text-[10.5px] text-amber-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/40 transition-all font-mono"
                  />
                </div>
              </div>
            ) : (
              <p className="text-[10px] text-slate-500">Watermark nonaktif — video bersih tanpa label.</p>
            )}
          </StepCard>

          {/* STICKY BOTTOM GENERATE BUTTON */}
          <div className="mt-auto pt-2.5 flex items-center gap-2 sticky bottom-0 bg-[#0e1218] border-t border-slate-800/80 pb-1.5">
              <button
                onClick={sourceKind === 'render-folder' ? undefined : handleStartProcessing}
                disabled={isProcessing || sourceKind === 'render-folder'}
                className={`flex flex-1 h-10 items-center justify-center gap-2 rounded-xl text-xs font-bold transition-all ${
                  sourceKind === 'render-folder'
                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 cursor-default'
                    : themeClasses.actionBtn
                } ${isProcessing ? 'opacity-70 cursor-wait' : 'active:scale-[0.98]'}`}
              >
                {isProcessing ? (
                  <>
                    <span>Processing...</span>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  </>
                ) : sourceKind === 'render-folder' ? (
                  <span className="flex items-center gap-1.5">
                    <CheckCircleIcon className="h-4 w-4 text-emerald-400" />
                    <span>Hasil Render Siap Diposting ({generatedClips.length} Klip)</span>
                  </span>
                ) : (
                  <span>✦ Analyze {clipCount} Clips</span>
                )}
              </button>

              {isProcessing && (
                <button
                  onClick={handleStopProcessing}
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-950/80 border border-rose-600/40 text-rose-400 hover:bg-rose-900 transition-all shadow-xs active:scale-95 flex-shrink-0"
                  title="Hentikan Proses (Cancel)"
                >
                  <StopIconSolid className="h-4 w-4" />
                </button>
              )}
          </div>

        </aside>

        {/* ── COLUMN 2: CENTER WORKSPACE (iPHONE PREVIEW MOCKUP) ── */}
        {/* PhonePreview renders its own card (bg/border/padding) — no extra wrapper here */}
        <section className="flex min-h-0 flex-col overflow-hidden">
          <PhonePreview
            framingMode={framingMode}
            selectedPresetId={selectedPresetId}
            videoSource={previewOutputClip ? previewOutputClip.path : (resolvedVideoPath || videoPathInput)}
            previewClip={previewOutputClip ? null : previewClipRange}
            clipTitle={previewOutputClip ? previewOutputClip.title : activeClipMeta?.title}
            clipCaption={activeClipMeta?.caption}
            clipHashtags={activeClipMeta?.hashtags}
            isRenderedClip={Boolean(previewOutputClip)}
            isProcessing={isProcessing}
            subPosition={subPosition}
            showEmoji={showEmoji}
            watermarkEnabled={watermarkEnabled}
            sourceWatermark={sourceWatermark}
            accountWatermark={accountWatermark}
          />
        </section>

        {/* ── COLUMN 3: RIGHT WORKSPACE (60% WORKSPACE / 40% PERMANENT LOG) ── */}
        <main className="flex min-h-0 flex-col h-full overflow-hidden">

          {/* ── TOP SECTION: 60% WORKSPACE (CLIP PREVIEW / OUTPUT / STATUS) ── */}
          <div className="flex-[6] min-h-0 flex flex-col overflow-hidden">
            <div className={`rounded-2xl border border-slate-800/80 ${themeClasses.card} flex flex-col h-full overflow-hidden`}>

            {/* 1. CONFIG PHASE: Standby Clip Preview */}
            {phase === 'config' && (
              <div className="flex flex-col h-full overflow-hidden">
                <div className="flex h-8 items-center gap-2.5 px-3.5 border-b border-slate-800/80 bg-[#161b22] flex-shrink-0">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f56]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#27c93f]" />
                  </div>
                  <span className="font-mono text-[11px] font-bold text-slate-400 tracking-wider">
                    CLIP PREVIEW
                  </span>
                </div>
                <div className="flex flex-1 flex-col items-center justify-center p-4 py-6 text-center text-slate-500">
                  <FolderArrowDownIcon className="h-10 w-10 stroke-[1.5] mb-2.5 opacity-30 text-emerald-400" />
                  <p className="text-xs font-semibold text-slate-300">Belum ada klip yang di-generate</p>
                  <p className="text-[11px] text-slate-500 max-w-xs mt-1">
                    Masukkan link video di panel kiri lalu klik <strong>"Analyze"</strong>. AI akan mendeteksi momen terbaik otomatis.
                  </p>
                </div>
              </div>
            )}

            {/* 2. ANALYZING PHASE: Skeleton Loading (mimics upcoming clip cards) */}
            {phase === 'analyzing' && (
              <div className={`${themeClasses.card} p-4 flex flex-col h-full overflow-hidden`}>
                <div className="flex-1 min-h-0">
                  <AnalyzingSkeleton />
                </div>
              </div>
            )}

            {/* 3. PREVIEW PHASE: Clip Approval Cards (60% Space) */}
            {phase === 'preview' && (
              <div className={`${themeClasses.card} p-3.5 flex flex-col h-full overflow-hidden`}>
                {/* Error Notification Banner if render failed */}
                {renderErrorMessage && (
                  <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs shadow-lg mb-2 flex-shrink-0">
                    <span className="text-base leading-none">⚠️</span>
                    <div className="flex-1">
                      <div className="font-bold text-rose-200">Gagal Merender Klip:</div>
                      <div className="mt-0.5 text-rose-300/90 text-[11px]">{renderErrorMessage}</div>
                    </div>
                  </div>
                )}

                {/* Header with back + re-analyze + confirmed count */}
                <div className="flex items-center justify-between mb-2.5 border-b border-slate-800/80 pb-2 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => { setPhase('config'); setPreviewClipRange(null); }}
                      disabled={isProcessing}
                      className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition-colors"
                    >
                      <ArrowLeftIcon className="h-3.5 w-3.5 stroke-[2]" />
                      <span>Kembali</span>
                    </button>
                    <span className="text-slate-700">|</span>
                    <button
                      onClick={handleStartProcessing}
                      className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition-colors"
                    >
                      <ArrowPathIcon className="h-3.5 w-3.5 stroke-[2]" />
                      <span>Re-analyze</span>
                    </button>
                  </div>
                  <span className="text-[11px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                    {confirmedClipCount}/{clipCandidates.length} Dikonfirmasi
                  </span>
                </div>

                {/* Clip Cards List (Scrollable) */}
                <div className="space-y-2.5 overflow-y-auto flex-1 scrollbar-thin pr-1">
                  {clipCandidates.map((clip) => {
                    const title = clip.title_options?.[0] || 'Untitled';
                    const mins = Math.floor(clip.duration / 60);
                    const secs = Math.floor(clip.duration % 60);
                    const durStr = `${mins}:${secs.toString().padStart(2, '0')}`;
                    const startMin = Math.floor(clip.start / 60);
                    const startSec = Math.floor(clip.start % 60);
                    const endMin = Math.floor(clip.end / 60);
                    const endSec = Math.floor(clip.end % 60);
                    const rangeStr = `${startMin}:${startSec.toString().padStart(2, '0')} → ${endMin}:${endSec.toString().padStart(2, '0')}`;

                    return (
                      <div
                        key={clip.index}
                        className={`rounded-xl border p-3 transition-all cursor-pointer ${
                          clip.decision === 'approved'
                            ? 'border-emerald-500/50 bg-emerald-950/20'
                            : clip.decision === 'skipped'
                              ? 'border-slate-800/60 bg-slate-900/40 opacity-60'
                              : 'border-amber-500/30 bg-amber-950/10'
                        }`}
                        onClick={() => previewCandidate(clip)}
                      >
                        {/* Top: Index + Title + Score */}
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <div className={`flex h-6 w-6 items-center justify-center rounded-lg text-[9px] font-mono font-bold flex-shrink-0 ${
                              clip.decision === 'approved'
                                ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
                                : clip.decision === 'skipped'
                                  ? 'bg-slate-800 text-slate-500 border border-slate-700'
                                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                            }`}>
                              {String(clip.index).padStart(2, '0')}
                            </div>
                            <div className="truncate flex-1 min-w-0">
                              <h4 className="text-[11px] font-bold text-slate-200 truncate">{title}</h4>
                              <div className="flex items-center gap-2 text-[9px] text-slate-500 font-mono mt-0.5">
                                <span>{durStr}</span>
                                <span className="text-slate-700">•</span>
                                <span>{rangeStr}</span>
                              </div>
                            </div>
                          </div>

                          {/* Viral Score Badge */}
                          <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold flex-shrink-0 ml-2 ${
                            clip.viral_score >= 85
                              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                              : clip.viral_score >= 70
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}>
                            <FireIcon className="h-3 w-3 stroke-[2]" />
                            <span>{clip.viral_score}</span>
                          </div>
                        </div>

                        {/* Reason */}
                        <p className="text-[10px] text-slate-400 line-clamp-2 mb-2 leading-relaxed">{clip.reason}</p>

                        {/* Caption Preview */}
                        <p className="text-[9px] text-slate-500 italic line-clamp-1 mb-2.5">{clip.caption}</p>

                        {/* Hashtags */}
                        <div className="flex flex-wrap gap-1 mb-2.5">
                          {clip.hashtags.slice(0, 5).map((tag, i) => (
                            <span key={i} className="text-[8px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 px-1.5 py-0.5 rounded-full">
                              {tag}
                            </span>
                          ))}
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center justify-between">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              previewCandidate(clip);
                            }}
                            className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-emerald-400 transition-colors"
                          >
                            <PlayIcon className="h-3 w-3 stroke-[2]" />
                            <span>Preview</span>
                          </button>

                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setClipCandidates(prev => prev.map(c =>
                                  c.index === clip.index
                                    ? { ...c, decision: c.decision === 'approved' ? 'pending' : 'approved' }
                                    : c
                                ));
                              }}
                              disabled={!clip.previewed}
                              title={clip.previewed ? 'Confirm klip untuk dirender' : 'Preview klip dahulu'}
                              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all ${
                                clip.decision === 'approved'
                                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/40 hover:bg-slate-800 hover:text-slate-300 hover:border-slate-700'
                                  : clip.previewed
                                    ? 'bg-slate-800 text-slate-300 border border-slate-700 hover:bg-emerald-600/20 hover:text-emerald-400 hover:border-emerald-500/40'
                                    : 'bg-slate-900 text-slate-600 border border-slate-800 cursor-not-allowed'
                              }`}
                            >
                              <CheckCircleIcon className="h-3.5 w-3.5 stroke-[2]" />
                              <span>{clip.decision === 'approved' ? 'Confirmed' : 'Confirm'}</span>
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setClipCandidates(prev => prev.map(c =>
                                  c.index === clip.index
                                    ? { ...c, decision: c.decision === 'skipped' ? 'pending' : 'skipped' }
                                    : c
                                ));
                              }}
                              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold transition-all ${
                                clip.decision === 'skipped'
                                  ? 'bg-rose-600/20 text-rose-400 border border-rose-500/40'
                                  : 'bg-slate-800 text-slate-400 border border-slate-700 hover:bg-rose-600/20 hover:text-rose-400 hover:border-rose-500/40'
                              }`}
                            >
                              <XCircleIcon className="h-3.5 w-3.5 stroke-[2]" />
                              <span>Cancel</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Bottom: Render Selected Button (Pinned) */}
                <div className="pt-2 border-t border-slate-800/80 flex-shrink-0 mt-2">
                  <button
                    onClick={handleRenderSelected}
                    disabled={isProcessing || confirmedClipCount === 0}
                    className={`flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-bold transition-all ${themeClasses.actionBtn} ${
                      isProcessing || confirmedClipCount === 0
                        ? 'opacity-40 cursor-not-allowed'
                        : 'active:scale-[0.98]'
                    }`}
                  >
                    <span>{isProcessing ? 'Menunggu analisis selesai...' : `🚀 Render ${confirmedClipCount} Confirmed Clips`}</span>
                  </button>
                </div>
              </div>
            )}

            {/* 4. RENDERING PHASE: Skeleton Loading (mimics upcoming output grid) */}
            {phase === 'rendering' && (
              <div className={`${themeClasses.card} p-4 flex flex-col h-full overflow-hidden`}>
                <div className="flex-1 min-h-0">
                  <RenderingSkeleton count={confirmedClipCount || clipCount} />
                </div>
              </div>
            )}

            {/* 5. COMPLETE PHASE: Output Clips */}
            {phase === 'complete' && (
              <div className={`${themeClasses.card} p-3.5 flex flex-col h-full overflow-hidden`}>
                {/* Header */}
                <div className="flex items-center justify-between mb-2.5 border-b border-slate-800/80 pb-2 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <FolderArrowDownIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                    <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                      OUTPUT CLIPS
                    </h2>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400 font-medium">
                      {generatedClips.length > 0 ? `${generatedClips.length} Klip Dihasilkan` : 'Folder Siap'}
                    </span>
                    <button
                      onClick={() => resetWorkflow(true)}
                      className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white transition-colors"
                    >
                      <ArrowPathIcon className="h-3 w-3 stroke-[2]" />
                      <span>Baru</span>
                    </button>
                  </div>
                </div>

                {/* Output Dir Banner */}
                {outputDir && (
                  <div className={`flex items-center justify-between gap-2 rounded-xl border ${themeClasses.outputBanner} p-2.5 shadow-lg bg-[#161d26] mb-2 flex-shrink-0 overflow-hidden`}>
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 text-slate-300 border border-slate-800 flex-shrink-0">
                        <FolderOpenIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-xs font-bold text-slate-100 truncate">Folder Output Siap</h3>
                        <p className="text-[10px] font-mono text-slate-400 truncate">
                          {outputDir}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <button
                        onClick={handleOpenFolder}
                        className={`flex items-center gap-1.5 rounded-xl ${themeClasses.accentBg} px-2.5 py-1 text-[11px] font-bold transition-colors flex-shrink-0 shadow-md active:scale-95 whitespace-nowrap`}
                      >
                        <FolderOpenIcon className="h-3.5 w-3.5 stroke-[2]" />
                        <span>Buka Folder</span>
                      </button>
                      {generatedClips.length > 0 && (
                        <button
                          onClick={() => setShowFolderModal(true)}
                          className="rounded-xl border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] font-semibold text-slate-200 hover:bg-slate-700 transition-colors flex-shrink-0 whitespace-nowrap"
                        >
                          Detail
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Clips list with Direct YouTube Upload Action (Scrollable) */}
                {generatedClips.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 overflow-y-auto flex-1 scrollbar-thin pr-1">
                    {generatedClips.map((clip, i) => {
                      const isUploading = isUploadingYt === clip.id;
                      const ytUrl = uploadedYtLinks[clip.id];
                      const isCurrentPreview = previewOutputClip?.id === clip.id;

                      return (
                        <div
                          key={clip.id}
                          onClick={() => previewRenderedClip(clip)}
                          className={`flex flex-col justify-between rounded-xl border p-2.5 text-xs gap-2 transition-all cursor-pointer ${
                            isCurrentPreview
                              ? 'border-emerald-500/70 bg-emerald-950/20 shadow-lg shadow-emerald-500/5 ring-1 ring-emerald-500/40'
                              : 'border-slate-800/80 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900/90'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                previewRenderedClip(clip);
                              }}
                              className={`flex h-7 w-7 items-center justify-center rounded-lg border flex-shrink-0 transition-all ${
                                isCurrentPreview
                                  ? 'bg-emerald-500 text-black border-emerald-400 font-bold scale-105'
                                  : 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 hover:scale-105'
                              }`}
                              title="Putar video clip ini di preview smartphone"
                            >
                              <PlayIcon className="h-3.5 w-3.5 ml-0.5" />
                            </button>
                            <div className="truncate flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="font-mono text-[9px] font-bold text-emerald-400">0{i + 1}</span>
                                <h4 className="font-semibold text-slate-200 truncate text-[11px]">{clip.title}</h4>
                              </div>
                              <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-500 mt-0.5">
                                <span>MP4 • 1080x1920</span>
                                {isCurrentPreview && (
                                  <span className="text-emerald-400 font-bold">• Sedang Diputar</span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Action Bar: Preview & YouTube Upload */}
                          <div className="flex items-center justify-between border-t border-slate-800/60 pt-1.5 gap-2">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                previewRenderedClip(clip);
                              }}
                              className={`flex items-center gap-1 text-[10px] font-semibold transition-colors ${
                                isCurrentPreview
                                  ? 'text-emerald-400'
                                  : 'text-slate-400 hover:text-emerald-400'
                              }`}
                            >
                              <PlayIcon className="h-3 w-3" />
                              <span>{isCurrentPreview ? 'Diputar' : 'Preview'}</span>
                            </button>

                            {/* Social Upload Actions: YouTube & TikTok */}
                            <div className="flex items-center gap-1.5 flex-wrap justify-end">
                              {/* TikTok Quick Upload Assistant */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenTikTokModal(clip);
                                }}
                                className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[10px] font-bold transition-all shadow-xs bg-gradient-to-r from-cyan-600/30 to-pink-600/30 hover:from-cyan-600/50 hover:to-pink-600/50 text-cyan-200 border border-cyan-500/40 active:scale-95 group"
                                title="Buka TikTok Assistant (Salin caption & buka TikTok Studio)"
                              >
                                <svg className="h-3 w-3 fill-current text-cyan-400 group-hover:text-white transition-colors" viewBox="0 0 24 24">
                                  <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.89 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.35 0 .69.06 1 .17V9.45a6.34 6.34 0 0 0-1-.08 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V8.75a8.28 8.28 0 0 0 4.76 1.49V6.79a4.85 4.85 0 0 1-1-.1z"/>
                                </svg>
                                <span>TikTok</span>
                              </button>

                              {/* YouTube Upload Action */}
                              {ytUrl ? (
                                <div className="flex items-center gap-1.5">
                                  <a
                                    href={ytUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="flex items-center gap-1 text-[10px] font-bold text-red-400 hover:text-red-300 underline"
                                  >
                                    <svg className="h-3 w-3 text-red-500 fill-current" viewBox="0 0 24 24">
                                      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                                    </svg>
                                    <span>YT ↗</span>
                                  </a>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleOpenUploadModal(clip);
                                    }}
                                    className="text-[9px] text-slate-400 hover:text-slate-200 transition-colors underline"
                                    title="Posting ulang dengan judul atau setelan berbeda"
                                  >
                                    Edit
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleOpenUploadModal(clip);
                                  }}
                                  disabled={isUploading}
                                  className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-bold transition-all shadow-xs ${
                                    ytConnected
                                      ? 'bg-gradient-to-r from-red-600/30 to-rose-600/30 hover:from-red-600/50 hover:to-rose-600/50 text-red-200 border border-red-500/40 active:scale-95'
                                      : 'bg-slate-800/80 text-slate-400 border border-slate-700 hover:text-white'
                                  } ${isUploading ? 'opacity-50 cursor-wait' : ''}`}
                                  title={ytConnected ? 'Buka konfirmasi dan posting langsung ke YouTube channel' : 'Hubungkan YouTube terlebih dahulu'}
                                >
                                  <svg className={`h-3 w-3 ${isUploading ? 'animate-spin' : 'text-red-500 fill-current'}`} viewBox="0 0 24 24">
                                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                                  </svg>
                                  <span>{isUploading ? 'Mengunggah...' : ytConnected ? 'YouTube' : 'Connect YT'}</span>
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            </div>
          </div>

          {/* ── BOTTOM SECTION: PERMANENT PROCESS LOG (40% SPACE) ── */}
          <div className="flex-[4] min-h-0 flex flex-col overflow-hidden pt-2">
            <div className="rounded-xl border border-slate-800/90 bg-[#0d1117] overflow-hidden flex flex-col h-full">

              {/* Terminal Window Header */}
              <div className="flex h-8 items-center justify-between px-3.5 border-b border-slate-800/80 bg-[#161b22] flex-shrink-0">

                {/* Left: macOS Window Circles & Dynamic Phase Title */}
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f56]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
                    <span className={`h-2.5 w-2.5 rounded-full ${isProcessing ? 'bg-[#27c93f] animate-pulse' : 'bg-[#27c93f]'}`} />
                  </div>
                  <span className="font-mono text-[11px] font-bold text-slate-400 tracking-wider">
                    PROSES LOG
                  </span>
                </div>

                {/* Right: Progress Bar & Actions */}
                <div className="flex items-center gap-2.5">
                  {(phase === 'analyzing' || phase === 'rendering') && (
                    <>
                      <div className="w-20 sm:w-28 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      <span className="font-mono text-[11px] font-semibold text-emerald-400">
                        {progress}%
                      </span>
                    </>
                  )}
                  {phase === 'complete' && (
                    <span className="font-mono text-[11px] font-semibold text-emerald-400">
                      100%
                    </span>
                  )}
                  <button
                    onClick={handleCopyLogs}
                    className="flex items-center gap-1 text-[10px] font-mono text-slate-400 hover:text-white bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700 transition-colors"
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
          </div>

        </main>

      </div>

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
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => {
                        setShowFolderModal(false);
                        previewRenderedClip(c);
                      }}
                      className="text-[10px] bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30 font-semibold transition-all active:scale-95 flex items-center gap-1"
                      title="Putar video di preview smartphone"
                    >
                      <PlayIcon className="h-3 w-3 text-emerald-400" />
                      <span>Preview</span>
                    </button>
                    <button
                      onClick={() => { setShowFolderModal(false); handleOpenTikTokModal(c); }}
                      className="text-[10px] bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/30 font-semibold transition-all active:scale-95 flex items-center gap-1"
                      title="Posting klip ini ke TikTok"
                    >
                      <span>🎵</span>
                      <span>TikTok</span>
                    </button>
                    {uploadedYtLinks[c.id] ? (
                      <a
                        href={uploadedYtLinks[c.id]}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-red-400 hover:text-red-300 font-bold underline flex items-center gap-0.5"
                      >
                        <VideoCameraIcon className="h-3 w-3" />
                        <span>YouTube ↗</span>
                      </a>
                    ) : (
                      <button
                        onClick={() => { setShowFolderModal(false); handleOpenUploadModal(c); }}
                        className="text-[10px] bg-red-600/20 hover:bg-red-600/30 text-red-300 px-2 py-0.5 rounded border border-red-500/30 font-semibold transition-all active:scale-95 flex items-center gap-1"
                        title="Posting klip ini ke YouTube Shorts"
                      >
                        <VideoCameraIcon className="h-3 w-3 text-red-400" />
                        <span>Post ke YT</span>
                      </button>
                    )}
                    <span className="font-mono text-emerald-400 text-[10px]">Ready</span>
                  </div>
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

      {/* ─────────────────────────────────────────────────────────────
          TIKTOK QUICK UPLOAD ASSISTANT MODAL (SOLUSI 1)
         ───────────────────────────────────────────────────────────── */}
      {ttModalOpen && selectedClipForTt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 p-6 shadow-2xl border border-slate-800 text-slate-100 flex flex-col max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/20 to-pink-500/20 text-cyan-300 border border-cyan-500/30">
                  <svg className="h-4.5 w-4.5 fill-current text-cyan-400" viewBox="0 0 24 24">
                    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.89 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.35 0 .69.06 1 .17V9.45a6.34 6.34 0 0 0-1-.08 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V8.75a8.28 8.28 0 0 0 4.76 1.49V6.79a4.85 4.85 0 0 1-1-.1z"/>
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Quick Post ke TikTok
                    <span className="rounded-full bg-cyan-600/30 px-2 py-0.5 text-[9px] font-bold text-cyan-300 border border-cyan-500/30">
                      TikTok Creator Center
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Salin caption, lalu pilih video secara manual di halaman upload TikTok
                  </p>
                </div>
              </div>
              <button
                onClick={() => setTtModalOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>

            {/* Step-by-Step Guide Banner */}
            <div className="rounded-xl bg-slate-950/80 border border-slate-800 p-3.5 mb-4 text-xs space-y-2">
              <div className="font-bold text-slate-200 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 text-black font-extrabold text-[10px]">1</span>
                <span>Klik tombol di bawah untuk menyalin caption dan membuka TikTok Studio</span>
              </div>
              <div className="font-bold text-slate-200 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 text-black font-extrabold text-[10px]">2</span>
                <span>Pilih file video secara manual dari halaman upload TikTok</span>
              </div>
              <div className="font-bold text-slate-200 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 text-black font-extrabold text-[10px]">3</span>
                <span>Tekan <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-cyan-300 font-mono text-[10px]">Ctrl+V</kbd> / <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-cyan-300 font-mono text-[10px]">Cmd+V</kbd> (Caption & Hashtag otomatis ter-paste)</span>
              </div>
            </div>

            {/* Caption & Hashtag Preview Area */}
            <div className="space-y-3 mb-4">
              <div className="flex justify-between items-center">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                  Caption & Hashtag TikTok (Otomatis Disalin)
                </label>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(ttFormTitle);
                    setTtCopied(true);
                    setTimeout(() => setTtCopied(false), 2500);
                  }}
                  className="flex items-center gap-1 text-[11px] font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
                >
                  {ttCopied ? (
                    <>
                      <CheckIcon className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Tersalin ke Clipboard!</span>
                    </>
                  ) : (
                    <>
                      <DocumentDuplicateIcon className="h-3.5 w-3.5" />
                      <span>Salin Ulang</span>
                    </>
                  )}
                </button>
              </div>

              <textarea
                rows={4}
                value={ttFormTitle}
                onChange={(e) => setTtFormTitle(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-medium leading-relaxed"
                placeholder="Tulis caption dan hashtags TikTok..."
              />
            </div>

            {/* Modal Footer Actions */}
            <div className="flex items-center justify-end pt-2 border-t border-slate-800 gap-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setTtModalOpen(false)}
                  className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition-colors"
                >
                  Tutup
                </button>

                <button
                  type="button"
                  onClick={handleLaunchTikTokUpload}
                  className="flex items-center gap-2 rounded-xl px-5 py-2 text-xs font-bold text-black bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 shadow-lg shadow-cyan-950/40 transition-all active:scale-95"
                >
                  <span>🚀 Salin & Buka TikTok Studio ↗</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          YOUTUBE POSTING CONFIRMATION MODAL
         ───────────────────────────────────────────────────────────── */}
      {ytModalOpen && selectedClipForYt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 p-6 shadow-2xl border border-slate-800 text-slate-100 flex flex-col max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-600/20 text-red-500 border border-red-500/30">
                  <svg className="h-5 w-5 text-red-500 fill-current" viewBox="0 0 24 24">
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Konfirmasi Posting ke YouTube
                    <span className="rounded-full bg-red-600/30 px-2 py-0.5 text-[9px] font-bold text-red-300 border border-red-500/30">
                      Shorts 9:16
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Tinjau detail video sebelum dipublikasikan langsung ke channel Anda
                  </p>
                </div>
              </div>
              <button
                disabled={ytUploadProgress === 'uploading'}
                onClick={() => { setYtModalOpen(false); setYtUploadProgress('idle'); }}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors disabled:opacity-30"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>

            {/* Target Channel Pill/Card */}
            {ytChannel && (
              <div className="flex items-center justify-between rounded-xl bg-slate-950/80 border border-slate-800 p-3 mb-4">
                <div className="flex items-center gap-3">
                  {ytChannel.thumbnail && !ytAvatarFailed ? (
                    <img src={ytChannel.thumbnail} alt="" onError={() => setYtAvatarFailed(true)} className="h-9 w-9 rounded-full border border-red-500/40 object-cover" />
                  ) : (
                    <div className="h-9 w-9 rounded-full bg-red-600/20 flex items-center justify-center text-red-400 font-bold text-xs">
                      YT
                    </div>
                  )}
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-white">{ytChannel.title}</span>
                      {ytChannel.customUrl && (
                        <span className="text-[10px] text-slate-400 font-mono">{ytChannel.customUrl}</span>
                      )}
                    </div>
                    <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-medium">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                      Channel Terhubung & Siap Posting
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 block">Klip #{selectedClipForYt.id}</span>
                  <span className="text-[10px] font-mono text-emerald-400 font-semibold">1080x1920 Vertikal</span>
                </div>
              </div>
            )}

            {/* Success State */}
            {ytUploadProgress === 'success' && ytUploadResult && (
              <div className="rounded-xl bg-emerald-950/40 border border-emerald-500/40 p-5 text-center my-2 animate-in zoom-in-95 duration-200">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 mb-3">
                  <CheckCircleIcon className="h-7 w-7" />
                </div>
                <h4 className="text-sm font-bold text-emerald-300 mb-1">
                  🎉 Video Berhasil Diposting ke YouTube!
                </h4>
                <p className="text-[11px] text-slate-300 mb-4">
                  Video Anda kini telah terunggah ke channel <span className="font-semibold text-white">{ytChannel?.title}</span> dengan status <span className="font-bold text-emerald-300 uppercase">{ytFormPrivacy}</span>.
                </p>

                <div className="flex flex-col sm:flex-row gap-2 justify-center mb-3">
                  <a
                    href={ytUploadResult.shorts_url || ytUploadResult.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 rounded-xl bg-red-600 hover:bg-red-500 px-4 py-2 text-xs font-bold text-white shadow-lg transition-transform active:scale-95"
                  >
                    <VideoCameraIcon className="h-4 w-4" />
                    <span>Tonton di YouTube Shorts ↗</span>
                  </a>
                  <a
                    href={ytUploadResult.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 px-3 py-2 text-xs font-semibold text-slate-300 transition-colors"
                  >
                    <span>Link Reguler ↗</span>
                  </a>
                </div>

                <button
                  onClick={() => { setYtModalOpen(false); setYtUploadProgress('idle'); }}
                  className="text-xs text-slate-400 hover:text-white underline pt-1"
                >
                  Tutup Dialog
                </button>
              </div>
            )}

            {/* Form Fields (Active if not success) */}
            {ytUploadProgress !== 'success' && (
              <div className="space-y-4">
                {/* Privacy Selector with "Posting Langsung (Publik)" Highlight */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                    Pilih Status Privasi / Mode Posting
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      disabled={ytUploadProgress === 'uploading'}
                      onClick={() => setYtFormPrivacy('public')}
                      className={`flex flex-col p-2.5 rounded-xl border text-left transition-all ${
                        ytFormPrivacy === 'public'
                          ? 'border-emerald-500/60 bg-emerald-950/40 text-emerald-300 shadow-md ring-1 ring-emerald-500/30'
                          : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold flex items-center gap-1">
                          <GlobeAltIcon className="h-3.5 w-3.5" />
                          Publik
                        </span>
                        {ytFormPrivacy === 'public' && <CheckIcon className="h-3 w-3 stroke-[3]" />}
                      </div>
                      <span className="text-[10px] leading-snug opacity-80">
                        Posting langsung tayang ke publik & Shorts
                      </span>
                    </button>

                    <button
                      type="button"
                      disabled={ytUploadProgress === 'uploading'}
                      onClick={() => setYtFormPrivacy('unlisted')}
                      className={`flex flex-col p-2.5 rounded-xl border text-left transition-all ${
                        ytFormPrivacy === 'unlisted'
                          ? 'border-cyan-500/60 bg-cyan-950/40 text-cyan-300 shadow-md ring-1 ring-cyan-500/30'
                          : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold flex items-center gap-1">
                          <LinkIcon className="h-3.5 w-3.5" />
                          Unlisted
                        </span>
                        {ytFormPrivacy === 'unlisted' && <CheckIcon className="h-3 w-3 stroke-[3]" />}
                      </div>
                      <span className="text-[10px] leading-snug opacity-80">
                        Hanya bisa ditonton via tautan link
                      </span>
                    </button>

                    <button
                      type="button"
                      disabled={ytUploadProgress === 'uploading'}
                      onClick={() => setYtFormPrivacy('private')}
                      className={`flex flex-col p-2.5 rounded-xl border text-left transition-all ${
                        ytFormPrivacy === 'private'
                          ? 'border-amber-500/60 bg-amber-950/40 text-amber-300 shadow-md ring-1 ring-amber-500/30'
                          : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold flex items-center gap-1">
                          <LockClosedIcon className="h-3.5 w-3.5" />
                          Private
                        </span>
                        {ytFormPrivacy === 'private' && <CheckIcon className="h-3 w-3 stroke-[3]" />}
                      </div>
                      <span className="text-[10px] leading-snug opacity-80">
                        Hanya Anda yang dapat melihat video
                      </span>
                    </button>
                  </div>
                </div>

                {/* Title input */}
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                      Judul Video (Shorts Title)
                    </label>
                    <span className={`text-[10px] font-mono ${ytFormTitle.length > 95 ? 'text-amber-400' : 'text-slate-500'}`}>
                      {ytFormTitle.length}/100
                    </span>
                  </div>
                  <input
                    type="text"
                    maxLength={100}
                    value={ytFormTitle}
                    disabled={ytUploadProgress === 'uploading'}
                    onChange={(e) => setYtFormTitle(e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500 font-medium"
                    placeholder="Masukkan judul video Shorts..."
                  />
                  <div className="flex items-center justify-between mt-1 text-[10px] text-slate-500">
                    <span>Format vertikal 9:16 Shorts</span>
                    <label className="flex items-center gap-1 cursor-pointer hover:text-slate-400">
                      <input
                        type="checkbox"
                        checked={ytFormAutoShortsTag}
                        onChange={(e) => setYtFormAutoShortsTag(e.target.checked)}
                        className="rounded border-slate-700 text-red-500 focus:ring-0 h-3 w-3"
                      />
                      <span>Tambahkan #Shorts di judul</span>
                    </label>
                  </div>
                </div>

                {/* Description input */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-1">
                    Deskripsi & Hashtags
                  </label>
                  <textarea
                    rows={3}
                    value={ytFormDescription}
                    disabled={ytUploadProgress === 'uploading'}
                    onChange={(e) => setYtFormDescription(e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500 resize-none font-mono"
                    placeholder="Tulis deskripsi video..."
                  />
                </div>

                {/* Tags chips */}
                {ytFormTags.length > 0 && (
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Tags Terkait
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {ytFormTags.map((tag, idx) => (
                        <span key={idx} className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300 border border-slate-700/60">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {ytUploadProgress === 'error' && (
                  <div className="rounded-xl bg-red-950/50 border border-red-500/50 p-3 text-xs text-red-300 flex items-start gap-2">
                    <XCircleIcon className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold block">Gagal mengunggah video:</span>
                      <span className="text-[11px] opacity-90">{ytUploadErrorMessage}</span>
                    </div>
                  </div>
                )}

                {/* Action Buttons with Direct Confirmation Button */}
                <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    disabled={ytUploadProgress === 'uploading'}
                    onClick={() => { setYtModalOpen(false); setYtUploadProgress('idle'); }}
                    className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition-colors disabled:opacity-40"
                  >
                    Batal
                  </button>

                  <button
                    type="button"
                    disabled={ytUploadProgress === 'uploading'}
                    onClick={handleConfirmUploadToYouTube}
                    className={`flex items-center gap-2 rounded-xl px-5 py-2 text-xs font-bold text-white shadow-lg transition-all active:scale-95 ${
                      ytFormPrivacy === 'public'
                        ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-emerald-950/50'
                        : ytFormPrivacy === 'unlisted'
                        ? 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-cyan-950/50'
                        : 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 shadow-red-950/50'
                    } ${ytUploadProgress === 'uploading' ? 'opacity-75 cursor-wait' : ''}`}
                  >
                    <VideoCameraIcon className={`h-4 w-4 ${ytUploadProgress === 'uploading' ? 'animate-spin' : ''}`} />
                    <span>
                      {ytUploadProgress === 'uploading'
                        ? 'Sedang Mengunggah Video...'
                        : ytFormPrivacy === 'public'
                        ? '🚀 Konfirmasi & Posting Langsung (Publik)'
                        : ytFormPrivacy === 'unlisted'
                        ? '🔗 Konfirmasi & Upload (Unlisted)'
                        : '🔒 Konfirmasi & Simpan (Private)'}
                    </span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SHADCN UI STUDIO SETTINGS MODAL
         ───────────────────────────────────────────────────────────── */}
      <StudioSettingsModal
        open={settingsModalOpen}
        onOpenChange={setSettingsModalOpen}
        activeTab={settingsActiveTab}
        setActiveTab={setSettingsActiveTab}
        aiConfig={aiConfig}
        aiSelectedProvider={aiSelectedProvider}
        handleSelectProvider={handleSelectProvider}
        aiEndpointInput={aiEndpointInput}
        setAiEndpointInput={setAiEndpointInput}
        aiModelInput={aiModelInput}
        setAiModelInput={setAiModelInput}
        handleFetchModels={handleFetchModels}
        aiModelsLoading={aiModelsLoading}
        aiModelsError={aiModelsError}
        aiModelsOpen={aiModelsOpen}
        aiModels={aiModels}
        aiApiKeyInput={aiApiKeyInput}
        setAiApiKeyInput={setAiApiKeyInput}
        aiGroqKeyInput={aiGroqKeyInput}
        setAiGroqKeyInput={setAiGroqKeyInput}
        aiShowKey={aiShowKey}
        setAiShowKey={setAiShowKey}
        aiShowGroqKey={aiShowGroqKey}
        setAiShowGroqKey={setAiShowGroqKey}
        handleTestAiConnection={handleTestAiConnection}
        aiTesting={aiTesting}
        aiTestResult={aiTestResult}
        setAiTestResult={setAiTestResult}
        handleTestGroqConnection={handleTestGroqConnection}
        aiTestingGroq={aiTestingGroq}
        aiGroqTestResult={aiGroqTestResult}
        setAiGroqTestResult={setAiGroqTestResult}
        handleSaveAiConfig={handleSaveAiConfig}
        aiSaving={aiSaving}
        ytConnected={ytConnected}
        ytChannel={ytChannel}
        ytAvatarFailed={ytAvatarFailed}
        setYtAvatarFailed={setYtAvatarFailed}
        isCheckingYtStatus={isCheckingYtStatus}
        checkYouTubeStatus={checkYouTubeStatus}
        handleConnectYouTube={handleConnectYouTube}
        handleDisconnectYouTube={handleDisconnectYouTube}
        onShutdown={() => {
          setSettingsModalOpen(false);
          setServerModalOpen(true);
        }}
      />

      {/* ─────────────────────────────────────────────────────────────
          TOAST POPUP NOTIFICATION (BOTTOM-RIGHT)
         ───────────────────────────────────────────────────────────── */}
      {toast && (
        <aside
          aria-live="polite"
          className="fixed bottom-6 right-6 z-50 flex items-start gap-3 p-4 rounded-2xl bg-[#161d27]/95 border border-slate-700/80 shadow-[0_20px_50px_rgba(0,0,0,0.85)] backdrop-blur-xl max-w-sm w-full animate-in slide-in-from-bottom-5 fade-in duration-300"
        >
          <div className={`flex h-9 w-9 items-center justify-center rounded-xl flex-shrink-0 ${
            toast.type === 'success' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
            toast.type === 'error' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
            toast.type === 'warning' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
            'bg-sky-500/20 text-sky-400 border border-sky-500/30'
          }`}>
            {toast.type === 'success' ? (
              <CheckCircleIcon className="h-5 w-5" />
            ) : toast.type === 'error' ? (
              <XCircleIcon className="h-5 w-5" />
            ) : toast.type === 'warning' ? (
              <ExclamationTriangleIcon className="h-5 w-5" />
            ) : (
              <SparklesIcon className="h-5 w-5" />
            )}
          </div>

          <div className="flex-1 pt-0.5">
            <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
              <span>{toast.title}</span>
            </h4>
            <p className="text-[11px] text-slate-300/90 leading-relaxed mt-0.5">
              {toast.message}
            </p>
          </div>

          <button
            onClick={() => setToast(null)}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors flex-shrink-0 -mr-1 -mt-1 cursor-pointer"
            aria-label="Tutup notifikasi"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </aside>
      )}

    </div>
  );
};
