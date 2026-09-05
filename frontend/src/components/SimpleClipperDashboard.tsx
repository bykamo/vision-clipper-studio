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
  FilmIcon
} from '@heroicons/react/24/outline';
import {
  StopIcon as StopIconSolid,
  FilmIcon as FilmIconSolid
} from '@heroicons/react/24/solid';
import { SubtitleStyleConfig } from '../types';
import { SUBTITLE_PRESETS } from '../data/subtitlePresets';
import { PhonePreview } from './PhonePreview';

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
  title_hook: string;
  reason: string;
  viral_score: number;
  sales_score?: number;
  caption: string;
  hashtags: string[];
  decision: 'pending' | 'approved' | 'skipped';
  previewed: boolean;
}

export const SimpleClipperDashboard: React.FC = () => {
  // Navigation Tabs (Modes)
  const [activeTab, setActiveTab] = useState<'hook' | 'affiliate'>('hook');

  // Video Source State
  const [videoPathInput, setVideoPathInput] = useState<string>('');
  const [isPickingFile, setIsPickingFile] = useState<boolean>(false);
  const browserFileInputRef = useRef<HTMLInputElement>(null);

  const handlePickNativeFile = async () => {
    setIsPickingFile(true);
    try {
      const res = await fetch('/api/pick-file');
      if (res.ok) {
        const data = await res.json();
        if (data.path) {
          setVideoPathInput(data.path);
          return;
        }
      }
    } catch {
      // Fallback to browser file input
      browserFileInputRef.current?.click();
    } finally {
      setIsPickingFile(false);
    }
  };

  const handleBrowserFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // If browser provides full path (in Electron/local) or file name
      setVideoPathInput((file as any).path || file.name);
    }
  };

  // Workflow Phase State
  const [phase, setPhase] = useState<WorkflowPhase>('config');
  const [clipCandidates, setClipCandidates] = useState<ClipCandidate[]>([]);
  const [analysisId, setAnalysisId] = useState<string>('');
  const [resolvedVideoPath, setResolvedVideoPath] = useState<string>('');
  const [previewClipRange, setPreviewClipRange] = useState<{ start: number; end: number } | null>(null);
  const [previewOutputClip, setPreviewOutputClip] = useState<{ path: string; title: string; id: string } | null>(null);

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

  // YouTube Social Connection & Upload State
  const [ytConnected, setYtConnected] = useState(false);
  const [ytChannel, setYtChannel] = useState<{ title: string; customUrl?: string; thumbnail?: string; subscriberCount?: string; videoCount?: string; id?: string } | null>(null);
  const [isUploadingYt, setIsUploadingYt] = useState<string | null>(null); // clip id being uploaded
  const [uploadedYtLinks, setUploadedYtLinks] = useState<Record<string, string>>({}); // clip id -> url

  // YouTube Posting Confirmation Modal State
  const [ytModalOpen, setYtModalOpen] = useState(false);
  const [ytChannelModalOpen, setYtChannelModalOpen] = useState(false);
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

  // Toast Popup Message State (Bottom-Right)
  const [toast, setToast] = useState<{
    id: number;
    title: string;
    message: string;
    type: 'success' | 'info' | 'error';
  } | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (title: string, message: string, type: 'success' | 'info' | 'error' = 'success') => {
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
    checkYouTubeStatus();

    // Check if redirected from Google OAuth callback
    const urlParams = new URLSearchParams(window.location.search);
    const authStatus = urlParams.get('youtube_auth');
    if (authStatus === 'success') {
      const ts = new Date().toTimeString().split(' ')[0];
      setLogs(prev => [...prev, `[${ts}] [YOUTUBE] 🎉 Akun YouTube berhasil terhubung!`]);
      checkYouTubeStatus(true);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (authStatus === 'error' || authStatus === 'failed') {
      const ts = new Date().toTimeString().split(' ')[0];
      const msg = urlParams.get('msg') || 'Otorisasi ditolak';
      setLogs(prev => [...prev, `[${ts}] [YOUTUBE] ❌ Gagal menghubungkan akun YouTube: ${msg}`]);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
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

  // Action: Salin caption, buka folder video, dan buka TikTok Creator Center di tab baru
  const handleLaunchTikTokUpload = async () => {
    if (!selectedClipForTt) return;

    // 1. Copy caption & hashtags to clipboard
    try {
      await navigator.clipboard.writeText(ttFormTitle);
      setTtCopied(true);
    } catch (e) {
      console.warn("Clipboard copy failed:", e);
    }

    // 2. Open output folder in Finder/Explorer
    if (outputDir) {
      try {
        await fetch('/api/open-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: outputDir })
        });
      } catch (e) {}
    }

    // 3. Open TikTok Creator Center Upload in new browser tab
    window.open('https://www.tiktok.com/creator-center/upload', '_blank', 'noopener,noreferrer');

    const ts = new Date().toTimeString().split(' ')[0];
    setLogs(prev => [...prev, `[${ts}] [TIKTOK] 🚀 Membuka TikTok Creator Center! Caption & hashtag telah disalin ke clipboard.`]);
    showToast(
      'TikTok Upload Siap! 🚀',
      'Caption disalin ke clipboard & folder video dibuka. Silakan drag-and-drop video ke TikTok.',
      'success'
    );
  };

  // Open Confirmation Modal for Direct YouTube Posting
  const handleOpenUploadModal = (clip: GeneratedClipItem) => {
    if (!ytConnected) {
      if (confirm("Akun YouTube belum terhubung. Apakah Anda ingin menghubungkan channel YouTube sekarang?")) {
        handleConnectYouTube();
      }
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

  // Handle Preset Change
  const handleSelectPreset = (preset: SubtitleStyleConfig) => {
    setSelectedPresetId(preset.presetId);
  };

  const previewCandidate = (clip: ClipCandidate) => {
    setPreviewOutputClip(null);
    setPreviewClipRange({ start: clip.start, end: clip.end });
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
    }
  };

  // Start Real Processing via SSE — Phase 1: Analyze Only
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
    setLogs([
      `[${startTimestamp}] [SYSTEM] Inisialisasi ${activeTab.toUpperCase()} CLIPPER ENGINE...`,
      `[${startTimestamp}] [SYSTEM] Model AI: ${transcriptionModel} | Subtitle Style: ${selectedPresetId}`,
      `[${startTimestamp}] [SYSTEM] Sumber video: ${source}`,
      `[${startTimestamp}] [SYSTEM] Memulai proses transkripsi & analisis AI (tanpa render)...`
    ]);

    const streamUrl = `/api/analyze?mode=${encodeURIComponent(activeTab)}&source=${encodeURIComponent(source)}&num_clips=${encodeURIComponent(clipCount)}&whisper_model=${encodeURIComponent(transcriptionModel)}`;
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
            title_hook: c.title_hook || '',
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
      framing_mode: framingMode
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

        {/* Right: Active Processing Badge & YouTube Connection Button */}
        <div className="flex items-center gap-3">
          {/* YouTube Social Status Pill */}
          {ytConnected && ytChannel ? (
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setYtChannelModalOpen(true)}
                className="flex items-center gap-2 rounded-full border border-red-500/30 bg-red-950/40 hover:bg-red-900/40 px-2.5 py-1 text-xs transition-all cursor-pointer group shadow-sm active:scale-95"
                title="Klik untuk melihat status koneksi YouTube & channel info"
              >
                <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                {ytChannel.thumbnail ? (
                  <img src={ytChannel.thumbnail} alt="" className="h-4 w-4 rounded-full" />
                ) : (
                  <svg className="h-3.5 w-3.5 text-red-500 fill-current" viewBox="0 0 24 24">
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                  </svg>
                )}
                <span className="font-semibold text-slate-200 text-[11px] max-w-[110px] truncate group-hover:text-white">
                  {ytChannel.title}
                </span>
              </button>
              <button
                type="button"
                onClick={handleDisconnectYouTube}
                className="text-[10px] text-slate-400 hover:text-red-400 font-bold px-1.5 py-1 hover:bg-slate-800 rounded-full transition-colors"
                title="Disconnect YouTube"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={handleConnectYouTube}
              className="flex items-center gap-1.5 rounded-full border border-red-500/40 bg-red-600/20 hover:bg-red-600/30 px-3 py-1 text-xs font-semibold text-red-300 transition-colors shadow-sm active:scale-95"
              title="Hubungkan Channel YouTube untuk Direct Upload"
            >
              <svg className="h-3.5 w-3.5 text-red-500 fill-current" viewBox="0 0 24 24">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              <span>Connect YouTube</span>
            </button>
          )}

          {/* Quick TikTok Creator Center Link */}
          <a
            href="https://www.tiktok.com/creator-center/upload"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-full border border-cyan-500/40 bg-cyan-950/40 hover:bg-cyan-900/40 px-3 py-1 text-xs font-semibold text-cyan-300 transition-colors shadow-sm active:scale-95 group"
            title="Buka TikTok Creator Center Upload Web"
          >
            <svg className="h-3.5 w-3.5 fill-current text-cyan-400 group-hover:text-white transition-colors" viewBox="0 0 24 24">
              <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.89 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.35 0 .69.06 1 .17V9.45a6.34 6.34 0 0 0-1-.08 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V8.75a8.28 8.28 0 0 0 4.76 1.49V6.79a4.85 4.85 0 0 1-1-.1z"/>
            </svg>
            <span>TikTok Studio</span>
            <ArrowUpRightIcon className="h-3 w-3 stroke-2 opacity-70 transition-all group-hover:-translate-y-px group-hover:translate-x-px group-hover:opacity-100" />
          </a>

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
              <input
                ref={browserFileInputRef}
                type="file"
                accept="video/*,.mp4,.mkv,.mov,.webm,.avi"
                onChange={handleBrowserFileChange}
                className="hidden"
              />
              <button
                type="button"
                onClick={handlePickNativeFile}
                disabled={isPickingFile}
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/90 text-slate-400 hover:text-white hover:border-slate-700 transition-colors shadow-sm flex-shrink-0 disabled:opacity-50"
                title="Pilih File Video dari Komputer (Native File Explorer)"
              >
                <FolderOpenIcon className={`h-4 w-4 stroke-[2] ${isPickingFile ? 'animate-pulse text-emerald-400' : ''}`} />
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
            <div className="flex items-center mb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
                <VideoCameraIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                <span>LAYOUT VIDEO</span>
              </div>
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
                  </div>

                  {/* Visual Preview Box */}
                  <div className="w-full h-9 rounded-lg bg-neutral-950 border border-neutral-800 flex items-center justify-center overflow-hidden px-1 shadow-inner relative select-none">
                    <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:8px_8px]" />

                    {preset.presetId === 'tiktok_viral' && (
                      <div className="relative font-['Montserrat'] font-black uppercase text-[9px] tracking-tight leading-none text-center">
                        <span className="text-white drop-shadow-[0_1px_2px_rgba(0,0,0,1)]">CONTOH </span>
                        <span className="text-yellow-400 bg-black/80 px-1 py-0.5 rounded font-black scale-105 inline-block drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] border border-yellow-400/30">
                          VIRAL
                        </span>
                        <span className="text-white drop-shadow-[0_1px_2px_rgba(0,0,0,1)]"> ✨</span>
                      </div>
                    )}

                    {preset.presetId === 'classic_karaoke' && (
                      <div className="relative font-['Montserrat'] font-bold text-[9px] tracking-tight leading-none text-center">
                        <span className="text-cyan-300 font-extrabold drop-shadow-[0_1px_2px_rgba(0,0,0,1)]">Contoh </span>
                        <span className="text-white drop-shadow-[0_1px_2px_rgba(0,0,0,1)]">Subtitle</span>
                      </div>
                    )}

                    {preset.presetId === 'minimalist' && (
                      <div className="relative font-sans font-medium text-[9px] text-white tracking-wide leading-none text-center drop-shadow-sm">
                        <span>Contoh teks subtitle</span>
                      </div>
                    )}

                    {preset.presetId === 'word_pop' && (
                      <div className="relative font-['Impact'] font-black uppercase text-[10px] text-yellow-300 tracking-wider leading-none text-center drop-shadow-[0_2px_4px_rgba(0,0,0,1)] scale-110">
                        <span>SUBTITLE!</span>
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
          <div className="mt-auto pt-3 flex items-center gap-2 sticky bottom-0 bg-[#0e1218] border-t border-slate-800/80 pb-2">
              <button
                onClick={handleStartProcessing}
                disabled={isProcessing}
                className={`flex flex-1 h-11 items-center justify-center gap-2 rounded-xl text-xs font-bold transition-all ${themeClasses.actionBtn} ${
                  isProcessing ? 'opacity-70 cursor-wait' : 'active:scale-[0.98]'
                }`}
              >
                {isProcessing ? (
                  <>
                    <span>Processing...</span>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  </>
                ) : (
                  <span>✦ Analyze {clipCount} Clips</span>
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

        </aside>

        {/* ── COLUMN 2: CENTER WORKSPACE (iPHONE PREVIEW MOCKUP) ── */}
        <section className="flex flex-col p-4 bg-[#090d13] overflow-hidden border-r border-slate-800/80">
          <PhonePreview
            framingMode={framingMode}
            selectedPresetId={selectedPresetId}
            videoSource={previewOutputClip ? previewOutputClip.path : (resolvedVideoPath || videoPathInput)}
            previewClip={previewOutputClip ? null : previewClipRange}
            clipTitle={previewOutputClip ? previewOutputClip.title : undefined}
            isRenderedClip={Boolean(previewOutputClip)}
          />
        </section>

        {/* ── COLUMN 3: RIGHT WORKSPACE (60% WORKSPACE / 40% PERMANENT LOG) ── */}
        <main className="flex flex-col h-full overflow-hidden p-3.5 gap-3 bg-[#0b0f15]">

          {/* ── TOP SECTION: 60% WORKSPACE (CLIP PREVIEW / OUTPUT / STATUS) ── */}
          <div className="flex-[6] min-h-0 flex flex-col overflow-hidden">

            {/* 1. CONFIG PHASE: Standby Clip Preview */}
            {phase === 'config' && (
              <div className={`rounded-2xl border ${themeClasses.card} p-4 shadow-xl flex flex-col h-full overflow-hidden`}>
                <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2.5 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <FolderArrowDownIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                    <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                      CLIP PREVIEW
                    </h2>
                  </div>
                  <span className="text-[11px] text-slate-400 font-medium">Standby</span>
                </div>
                <div className="flex flex-1 flex-col items-center justify-center py-6 text-center text-slate-500">
                  <FolderArrowDownIcon className="h-10 w-10 stroke-[1.5] mb-2.5 opacity-30 text-emerald-400" />
                  <p className="text-xs font-semibold text-slate-300">Belum ada klip yang di-generate</p>
                  <p className="text-[11px] text-slate-500 max-w-xs mt-1">
                    Masukkan link video di panel kiri lalu klik <strong>"Analyze"</strong>. AI akan mendeteksi momen terbaik otomatis.
                  </p>
                </div>
              </div>
            )}

            {/* 2. ANALYZING PHASE: Progress Visualizer */}
            {phase === 'analyzing' && (
              <div className={`rounded-2xl border ${themeClasses.card} p-4 shadow-xl flex flex-col h-full overflow-hidden justify-between`}>
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <SparklesIcon className="h-4 w-4 text-emerald-400 animate-spin" />
                    <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                      AI ANALYZING VIDEO
                    </h2>
                  </div>
                  <span className="text-[11px] font-mono text-emerald-400 font-bold">{progress}%</span>
                </div>
                <div className="flex flex-col items-center justify-center text-center py-4 flex-1">
                  <div className="h-10 w-10 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin mb-3" />
                  <p className="text-xs font-semibold text-slate-200">Mendeteksi Momen Viral & Transkripsi Audio...</p>
                  <p className="text-[11px] text-slate-400 max-w-xs mt-1 leading-relaxed">
                    Groq Whisper & frame scanner sedang membedah video Anda. Hasil klip kandidat akan tampil di panel ini sesaat lagi.
                  </p>
                  <div className="w-full max-w-xs bg-slate-800/80 h-2 rounded-full mt-4 overflow-hidden border border-slate-700/50">
                    <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono flex-shrink-0">
                  <span>Model: {transcriptionModel === 'groq' ? 'Groq Whisper Cloud' : 'YouTube Transcript'}</span>
                  <span>Target: {clipCount} Klip</span>
                </div>
              </div>
            )}

            {/* 3. PREVIEW PHASE: Clip Approval Cards (60% Space) */}
            {phase === 'preview' && (
              <div className={`rounded-2xl border ${themeClasses.card} p-3.5 shadow-xl flex flex-col h-full overflow-hidden`}>
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

                        {/* Title Hook */}
                        {clip.title_hook && (
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-[9px] font-bold text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 px-1.5 py-0.5 rounded">
                              HOOK: {clip.title_hook}
                            </span>
                          </div>
                        )}

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

            {/* 4. RENDERING PHASE: Progress Visualizer */}
            {phase === 'rendering' && (
              <div className={`rounded-2xl border ${themeClasses.card} p-4 shadow-xl flex flex-col h-full overflow-hidden justify-between`}>
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <FilmIcon className="h-4 w-4 text-emerald-400 animate-pulse" />
                    <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                      RENDERING VERTICAL CLIPS (9:16)
                    </h2>
                  </div>
                  <span className="text-[11px] font-mono text-emerald-400 font-bold">{progress}%</span>
                </div>
                <div className="flex flex-col items-center justify-center text-center py-4 flex-1">
                  <div className="h-10 w-10 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin mb-3" />
                  <p className="text-xs font-semibold text-slate-200">Sedang Merender {confirmedClipCount} Klip Pilihan...</p>
                  <p className="text-[11px] text-slate-400 max-w-xs mt-1 leading-relaxed">
                    Auto-framing 9:16, subtitle styling, dan audio AAC sedang diproses oleh FFmpeg. Lihat log real-time di bawah.
                  </p>
                  <div className="w-full max-w-xs bg-slate-800/80 h-2 rounded-full mt-4 overflow-hidden border border-slate-700/50">
                    <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono flex-shrink-0">
                  <span>Preset: {selectedPresetId}</span>
                  <span>Format: 1080x1920 MP4</span>
                </div>
              </div>
            )}

            {/* 5. COMPLETE PHASE: Output Clips */}
            {phase === 'complete' && (
              <div className={`rounded-2xl border ${themeClasses.card} p-3.5 shadow-xl flex flex-col h-full overflow-hidden`}>
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
                      onClick={() => { setPhase('config'); setClipCandidates([]); setPreviewClipRange(null); setPreviewOutputClip(null); setGeneratedClips([]); setOutputDir(''); }}
                      className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white transition-colors"
                    >
                      <ArrowPathIcon className="h-3 w-3 stroke-[2]" />
                      <span>Baru</span>
                    </button>
                  </div>
                </div>

                {/* Output Dir Banner */}
                {outputDir && (
                  <div className={`flex items-center justify-between rounded-xl border ${themeClasses.outputBanner} p-2.5 shadow-lg bg-[#161d26] mb-2 flex-shrink-0`}>
                    <div className="flex items-center gap-2.5 truncate">
                      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 text-slate-300 border border-slate-800 flex-shrink-0">
                        <FolderOpenIcon className={`h-4 w-4 stroke-[2] ${themeClasses.accentText}`} />
                      </div>
                      <div className="truncate">
                        <h3 className="text-xs font-bold text-slate-100">Folder Output Siap</h3>
                        <p className="text-[10px] font-mono text-slate-400 truncate max-w-[180px] sm:max-w-xs">
                          {outputDir}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={handleOpenFolder}
                        className={`flex items-center gap-1.5 rounded-xl ${themeClasses.accentBg} px-2.5 py-1 text-[11px] font-bold transition-colors flex-shrink-0 shadow-md active:scale-95`}
                      >
                        <FolderOpenIcon className="h-3.5 w-3.5 stroke-[2]" />
                        <span>Buka Folder</span>
                      </button>
                      {generatedClips.length > 0 && (
                        <button
                          onClick={() => setShowFolderModal(true)}
                          className="rounded-xl border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
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

          {/* ── BOTTOM SECTION: PERMANENT PROCESS LOG (40% SPACE) ── */}
          <div className="flex-[4] min-h-0 flex flex-col overflow-hidden">
            <div className="rounded-2xl border border-slate-800/90 bg-[#0d1117] overflow-hidden shadow-xl flex flex-col h-full">

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
                    {phase === 'analyzing'
                      ? 'PROSES LOG (ANALYZING)'
                      : phase === 'rendering'
                      ? 'PROSES LOG (RENDERING)'
                      : phase === 'complete'
                      ? 'PROSES LOG (100% SELESAI)'
                      : phase === 'preview'
                      ? 'PROSES LOG (ANALISIS SELESAI)'
                      : status === 'error'
                      ? 'PROSES LOG (ERROR)'
                      : 'PROSES LOG'}
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
                    Posting video langsung ke publik tanpa ribet API atau batasan akun privat
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
                <span>Klik tombol di bawah untuk membuka TikTok Studio & Folder Video</span>
              </div>
              <div className="font-bold text-slate-200 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 text-black font-extrabold text-[10px]">2</span>
                <span>Drag file video ke browser TikTok</span>
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
            <div className="flex items-center justify-between pt-2 border-t border-slate-800 gap-2">
              <button
                type="button"
                onClick={handleOpenFolder}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 font-medium"
              >
                <FolderOpenIcon className="h-4 w-4 stroke-[2]" />
                <span>Buka Folder Klip</span>
              </button>

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
                  {ytChannel.thumbnail ? (
                    <img src={ytChannel.thumbnail} alt="" className="h-9 w-9 rounded-full border border-red-500/40 object-cover" />
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
          YOUTUBE CONNECTIVITY & CHANNEL STATUS MODAL
         ───────────────────────────────────────────────────────────── */}
      {ytChannelModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 p-5 shadow-2xl border border-slate-800 text-slate-100">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <svg className="h-5 w-5 text-red-500 fill-current" viewBox="0 0 24 24">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>
                <h3 className="text-sm font-bold text-white">Status Konektivitas YouTube API</h3>
              </div>
              <button
                onClick={() => setYtChannelModalOpen(false)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>

            {ytConnected && ytChannel ? (
              <div className="space-y-3.5">
                <div className="flex items-center gap-3.5 rounded-xl bg-slate-950 p-3 border border-slate-800">
                  {ytChannel.thumbnail ? (
                    <img src={ytChannel.thumbnail} alt="" className="h-12 w-12 rounded-full border border-red-500/50 object-cover" />
                  ) : (
                    <div className="h-12 w-12 rounded-full bg-red-600/20 text-red-400 font-bold flex items-center justify-center text-base">
                      YT
                    </div>
                  )}
                  <div className="flex-1">
                    <h4 className="text-sm font-bold text-white">{ytChannel.title}</h4>
                    <p className="text-xs text-slate-400 font-mono">{ytChannel.customUrl || '@asal.sharing'}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 text-[9px] font-bold text-emerald-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        API Aktif & Terhubung
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800/80">
                    <span className="text-[10px] text-slate-400 block">Subscribers</span>
                    <span className="text-sm font-bold text-slate-200">{(ytChannel as any).subscriberCount || '2'}</span>
                  </div>
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800/80">
                    <span className="text-[10px] text-slate-400 block">Total Video</span>
                    <span className="text-sm font-bold text-slate-200">{(ytChannel as any).videoCount || '5'}</span>
                  </div>
                </div>

                <div className="rounded-lg bg-slate-950/40 p-2.5 border border-slate-800/60 text-[11px] space-y-1">
                  <div className="flex justify-between text-slate-400">
                    <span>Channel ID:</span>
                    <span className="font-mono text-slate-300 text-[10px]">{(ytChannel as any).id || 'UCmUbuH3agtBcNREw5VfzPlw'}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Scopes:</span>
                    <span className="font-mono text-emerald-400 text-[10px]">youtube.upload, readonly</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>OAuth Token:</span>
                    <span className="font-mono text-emerald-400 text-[10px]">Valid (Auto-Refresh)</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                  <button
                    onClick={() => checkYouTubeStatus(true)}
                    disabled={isCheckingYtStatus}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors active:scale-95"
                  >
                    <ArrowPathIcon className={`h-3.5 w-3.5 ${isCheckingYtStatus ? 'animate-spin text-emerald-400' : ''}`} />
                    <span>{isCheckingYtStatus ? 'Memeriksa...' : 'Tes Ulang Koneksi'}</span>
                  </button>

                  <button
                    onClick={() => { setYtChannelModalOpen(false); handleDisconnectYouTube(); }}
                    className="rounded-lg border border-red-500/30 bg-red-950/40 hover:bg-red-900/60 px-3 py-1.5 text-xs font-semibold text-red-400 transition-colors"
                  >
                    Putuskan Akun
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 space-y-3">
                <p className="text-xs text-slate-400">
                  Akun YouTube belum terhubung. Klik tombol di bawah untuk login ke Google dan memberi izin upload.
                </p>
                <button
                  onClick={handleConnectYouTube}
                  className="rounded-xl bg-red-600 hover:bg-red-500 px-4 py-2 text-xs font-bold text-white transition-colors shadow-md"
                >
                  Hubungkan Channel YouTube
                </button>
              </div>
            )}
          </div>
        </div>
      )}

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
            'bg-sky-500/20 text-sky-400 border border-sky-500/30'
          }`}>
            {toast.type === 'success' ? (
              <CheckCircleIcon className="h-5 w-5" />
            ) : toast.type === 'error' ? (
              <XCircleIcon className="h-5 w-5" />
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
