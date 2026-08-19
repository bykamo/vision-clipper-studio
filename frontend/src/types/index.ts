export type AspectRatio = '9:16' | '1:1' | '4:5' | '16:9';

export type ViralityFocus = 
  | 'hook_first' 
  | 'key_insights' 
  | 'high_energy' 
  | 'storytelling' 
  | 'qa_format';

export type FramingMode = 
  | 'auto_face_track' 
  | 'split_screen' 
  | 'fit_blur' 
  | 'fit_black';

export type SubtitleAnimation = 
  | 'word_pop' 
  | 'karaoke' 
  | 'bounce' 
  | 'glow_pulse' 
  | 'slide_up' 
  | 'none';

export type SubtitlePresetId = 
  | 'tiktok_viral'
  | 'classic_karaoke'
  | 'minimalist'
  | 'word_pop'
  | 'no_subtitle'
  | 'hormozi' 
  | 'mrbeast' 
  | 'neon_glow' 
  | 'minimal_sans' 
  | 'karaoke_box' 
  | 'comic_bold' 
  | 'aesthetic_serif';

export interface SubtitleWord {
  word: string;
  start: number; // in seconds relative to clip start
  end: number;
  highlight?: boolean;
  color?: string;
  emoji?: string;
}

export interface SubtitleLine {
  id: string;
  start: number; // in seconds
  end: number;
  text: string;
  words: SubtitleWord[];
}

export interface SubtitleStyleConfig {
  presetId: SubtitlePresetId;
  name: string;
  description?: string;
  icon?: string;
  fontFamily: string;
  fontSize: number; // rem or px scale
  primaryColor: string;
  highlightColor: string;
  secondaryHighlightColor?: string;
  strokeColor: string;
  strokeWidth: number;
  shadow: boolean;
  backgroundBox: boolean;
  backgroundColor: string;
  animationType: SubtitleAnimation;
  wordsPerLine: number;
  allCaps: boolean;
  positionY: number; // % from bottom (e.g. 22%)
  showEmoji: boolean;
}

export interface SocialPlatformMetadata {
  caption?: string;
  hashtags: string[];
  title?: string;
  description?: string;
  recommendedAspect: AspectRatio;
  maxDurationSec: number;
}

export interface GeneratedClip {
  id: string;
  title: string;
  hookSentence: string;
  viralityScore: number; // 0-100
  viralityRationale: string;
  startTime: number; // in seconds
  endTime: number; // in seconds
  duration: number; // in seconds
  aspectRatio: AspectRatio;
  subtitles: SubtitleLine[];
  videoThumbnail?: string;
  speakerName?: string;
  tags: string[];
  socialMetadata: {
    tiktok: SocialPlatformMetadata;
    instagram: SocialPlatformMetadata;
    youtube_shorts: SocialPlatformMetadata;
    twitter: SocialPlatformMetadata;
    linkedin: SocialPlatformMetadata;
  };
  exportStatus?: 'idle' | 'exporting' | 'completed';
}

export interface SourceVideo {
  id: string;
  title: string;
  duration: number; // in seconds
  category: string;
  speaker: string;
  videoUrl: string;
  videoType: 'sample' | 'custom_file' | 'url';
  originalAspect: '16:9' | '9:16' | '1:1';
  summary: string;
  transcriptSample?: string;
}

export interface ClipGenerationConfig {
  clipCount: number; // 1 to 10
  targetDuration: '15_30' | '30_60' | '60_90' | 'auto';
  viralityFocus: ViralityFocus;
  aspectRatio: AspectRatio;
  framingMode: FramingMode;
  includeCaptions: boolean;
  autoEmojis: boolean;
  detectKeyMomentsOnly: boolean;
  addOutroWatermark: boolean;
}

export interface ProcessingLog {
  id: string;
  timestamp: string;
  stage: 'INIT' | 'AUDIO_EXTRACT' | 'WHISPER_STT' | 'GEMINI_ANALYSIS' | 'FACE_TRACKING' | 'SUBTITLE_BURN' | 'AUTO_ENCODE' | 'COMPLETED';
  stageNameIndo: string;
  level: 'info' | 'gemini' | 'whisper' | 'render' | 'success' | 'warn';
  message: string;
  progress: number; // 0-100
  details?: string;
}

export type SocialPlatformId = 'tiktok' | 'instagram' | 'youtube_shorts' | 'twitter' | 'linkedin';

export interface ExportSettings {
  selectedPlatforms: SocialPlatformId[];
  resolution: '1080p' | '4k' | '720p';
  framerate: 30 | 60;
  codec: 'h264' | 'hevc' | 'webm';
  burnSubtitles: boolean;
  includeSocialMetadataFile: boolean;
  autoSplitCarousel: boolean;
}
