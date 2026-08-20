import { SubtitleStyleConfig } from '../types';

export const SUBTITLE_PRESETS: SubtitleStyleConfig[] = [
  {
    presetId: 'tiktok_viral',
    name: 'TikTok Viral',
    description: 'Bold, highlight kuning, pop-up text',
    icon: '🎬',
    fontFamily: 'Montserrat, sans-serif',
    fontSize: 26,
    primaryColor: '#FFFFFF',
    highlightColor: '#FACC15', // Kuning terang
    secondaryHighlightColor: '#22C55E',
    strokeColor: '#000000',
    strokeWidth: 4,
    shadow: true,
    backgroundBox: false,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    animationType: 'word_pop',
    wordsPerLine: 3,
    allCaps: true,
    positionY: 26,
    showEmoji: true
  },
  {
    presetId: 'no_subtitle',
    name: 'No Subtitle',
    description: 'Tanpa subtitle sama sekali',
    icon: '❌',
    fontFamily: 'Plus Jakarta Sans, sans-serif',
    fontSize: 0,
    primaryColor: 'transparent',
    highlightColor: 'transparent',
    strokeColor: 'transparent',
    strokeWidth: 0,
    shadow: false,
    backgroundBox: false,
    backgroundColor: 'transparent',
    animationType: 'none',
    wordsPerLine: 0,
    allCaps: false,
    positionY: 0,
    showEmoji: false
  }
];
