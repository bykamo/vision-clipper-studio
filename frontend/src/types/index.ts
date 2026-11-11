export type FramingMode = 'smart_crop' | 'fit_blur' | 'split_screen';

export interface SmartCropTrajectory {
  fps: number;
  orig_w: number;
  orig_h: number;
  crop_w: number;
  crop_h: number;
  crop_y: number;
  positions: number[];
  cut_frames: number[];
  /** Padded clip start/end returned by the backend (used to map position index). */
  start?: number;
  end?: number;
}

export type SubtitleAnimation =
  'word_pop' | 'karaoke' | 'bounce' | 'glow_pulse' | 'slide_up' | 'none';

export type SubtitlePresetId =
  'tiktok_viral' | 'classic_karaoke' | 'minimalist' | 'word_pop' | 'no_subtitle';

export interface SubtitleStyleConfig {
  presetId: SubtitlePresetId;
  name: string;
  description?: string;
  icon?: string;
  fontFamily: string;
  fontSize: number;
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
  positionY: number;
}
