export type FramingMode = 'smart_crop' | 'fit_blur' | 'split_screen';

export type SubtitleAnimation =
  'word_pop' | 'karaoke' | 'bounce' | 'glow_pulse' | 'slide_up' | 'none';

export type SubtitlePresetId =
  | 'tiktok_viral'
  | 'classic_karaoke'
  | 'minimalist'
  | 'word_pop'
  | 'no_subtitle';

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
