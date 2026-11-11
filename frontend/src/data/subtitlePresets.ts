import { SubtitleStyleConfig } from '../types';

export const SUBTITLE_PRESETS: SubtitleStyleConfig[] = [
  {
    presetId: 'tiktok_viral',
    name: 'Subtitle On/Off',
    description: 'CapCut style: frasa horizontal 3-4 kata, highlight emerald, bold pop',
    icon: '🎬',
    fontFamily: 'Montserrat, sans-serif',
    fontSize: 26,
    primaryColor: '#FFFFFF',
    highlightColor: '#34D399', // Emerald terang (warna utama VisionClipper)
    secondaryHighlightColor: '#10B981', // Emerald dasar
    strokeColor: '#000000',
    strokeWidth: 4,
    shadow: true,
    backgroundBox: false,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    animationType: 'word_pop',
    wordsPerLine: 4,
    allCaps: true,
    positionY: 26,
  },
];
