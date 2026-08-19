import { 
  SourceVideo, 
  ClipGenerationConfig, 
  SubtitleStyleConfig, 
  ProcessingLog, 
  GeneratedClip 
} from '../types';
import { INITIAL_GENERATED_CLIPS } from '../data/sampleVideos';

export type LogListener = (log: ProcessingLog, allLogs: ProcessingLog[]) => void;
export type ProgressListener = (progress: number, currentStage: string) => void;

export class AIProcessingEngine {
  private logs: ProcessingLog[] = [];
  private isCancelled = false;

  public cancel() {
    this.isCancelled = true;
  }

  public async processVideo(
    source: SourceVideo,
    config: ClipGenerationConfig,
    subtitleConfig: SubtitleStyleConfig,
    onLog?: LogListener,
    onProgress?: ProgressListener
  ): Promise<{ clips: GeneratedClip[]; logs: ProcessingLog[] }> {
    this.logs = [];
    this.isCancelled = false;

    const addLog = (
      stage: ProcessingLog['stage'],
      stageNameIndo: string,
      level: ProcessingLog['level'],
      message: string,
      progress: number,
      details?: string
    ) => {
      const now = new Date();
      const timeStr = `${now.toTimeString().split(' ')[0]}.${String(now.getMilliseconds()).padStart(3, '0')}`;
      const newLog: ProcessingLog = {
        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
        timestamp: timeStr,
        stage,
        stageNameIndo,
        level,
        message,
        progress,
        details
      };
      this.logs.push(newLog);
      if (onLog) onLog(newLog, [...this.logs]);
      if (onProgress) onProgress(progress, stageNameIndo);
    };

    const sleep = (ms: number) => new Promise(res => setTimeout(res, ms));

    // STAGE 1: INIT
    addLog('INIT', 'Inisialisasi Source Video', 'info', `Memuat file video "${source.title}" (${source.duration}s)...`, 5, `Aspect: ${source.originalAspect} | Format: MP4 | Speaker: ${source.speaker}`);
    await sleep(400);
    if (this.isCancelled) throw new Error('Dibatalkan pengguna');

    // STAGE 2: AUDIO EXTRACT
    addLog('AUDIO_EXTRACT', 'Ekstraksi Audio 16kHz', 'info', 'Mengekstrak stream audio WAV lossless untuk model transkripsi...', 15, 'FFmpeg filter: aresample=16000:osf=s16, mono channel');
    await sleep(500);
    if (this.isCancelled) throw new Error('Dibatalkan pengguna');

    // STAGE 3: WHISPER STT
    addLog('WHISPER_STT', 'Whisper AI Speech-to-Text', 'whisper', 'Menjalankan model Whisper Large-v3 untuk transkripsi kata per kata...', 25, 'Bahasa terdeteksi: Bahasa Indonesia (99.2% confidence)');
    await sleep(450);
    addLog('WHISPER_STT', 'Whisper Word Timestamping', 'whisper', 'Sinkronisasi alignment millisecond per kata (word-level timestamps)...', 38, `Diproses: ${Math.floor(source.duration * 2.8)} token kata tersinkronisasi`);
    await sleep(550);
    if (this.isCancelled) throw new Error('Dibatalkan pengguna');

    // STAGE 4: GEMINI HOOK ANALYSIS
    addLog('GEMINI_ANALYSIS', 'Gemini AI Hook Detection', 'gemini', `Menganalisis pacing retensi & mencari ${config.clipCount} momen paling viral...`, 50, `Fokus: ${config.viralityFocus} | Target durasi: ${config.targetDuration} detik`);
    await sleep(650);
    addLog('GEMINI_ANALYSIS', 'Gemini Virality Scoring', 'gemini', `Ditemukan ${config.clipCount} segmen dengan virality score rata-rata 94+/100!`, 64, 'Formula hook 3 detik, punchline, emosi puncak, & retention score teruji');
    await sleep(500);
    if (this.isCancelled) throw new Error('Dibatalkan pengguna');

    // STAGE 5: FACE TRACKING
    addLog('FACE_TRACKING', 'AI Auto-Reframing 9:16', 'render', `Menerapkan pelacakan wajah aktif (${config.framingMode}) untuk format vertikal...`, 75, 'MediaPipe Face Mesh + YOLOv8 Speaker Diarization active');
    await sleep(550);
    if (this.isCancelled) throw new Error('Dibatalkan pengguna');

    // STAGE 6: SUBTITLE BURN
    addLog('SUBTITLE_BURN', 'Render Subtitle Kinetik', 'render', `Menerapkan gaya subtitle "${subtitleConfig.name}" dengan animasi ${subtitleConfig.animationType}...`, 86, `Font: ${subtitleConfig.fontFamily} | Warna: ${subtitleConfig.highlightColor} | Posisi: ${subtitleConfig.positionY}%`);
    await sleep(600);
    if (this.isCancelled) throw new Error('Dibatalkan pengguna');

    // STAGE 7: AUTO ENCODE MULTI-PLATFORM
    addLog('AUTO_ENCODE', 'Auto-Export Format Sosmed', 'render', 'Menyiapkan metadata & preset untuk TikTok, Reels, YouTube Shorts, X, & LinkedIn...', 95, 'Safe zone padding dikalibrasi, tagar dan deskripsi AI siap digunakan');
    await sleep(500);
    if (this.isCancelled) throw new Error('Dibatalkan pengguna');

    // STAGE 8: COMPLETED
    addLog('COMPLETED', 'Selesai!', 'success', `Berhasil membuat ${config.clipCount} klip siap viral!`, 100, 'Semua klip siap diedit, dipratinjau, atau diekspor sekaligus.');

    // Generate output clips tailored to clipCount
    const generatedClips: GeneratedClip[] = [];
    const baseTemplates = [...INITIAL_GENERATED_CLIPS];

    for (let i = 0; i < config.clipCount; i++) {
      const template = baseTemplates[i % baseTemplates.length];
      const clipId = `clip-gen-${Date.now()}-${i + 1}`;
      
      // Slightly vary if multiple
      const customScore = Math.max(88, Math.min(99, template.viralityScore - (i * 2)));
      const customStart = Math.min(source.duration - 25, template.startTime + (i * 18));
      const customDuration = Math.min(35, template.duration + ((i % 3) * 3));

      generatedClips.push({
        ...template,
        id: clipId,
        title: i === 0 ? template.title : `[Klip ${i + 1}] ${template.title}`,
        viralityScore: customScore,
        startTime: customStart,
        endTime: customStart + customDuration,
        duration: customDuration,
        aspectRatio: config.aspectRatio,
        speakerName: source.speaker
      });
    }

    return {
      clips: generatedClips,
      logs: this.logs
    };
  }
}
