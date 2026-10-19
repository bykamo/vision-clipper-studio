import React from 'react';
import {
  Settings2,
  Check,
  CheckCircle2,
  XCircle,
  X,
  ExternalLink,
  RefreshCw,
  Eye,
  EyeOff,
  ArrowUpRight,
  Server,
  Power,
  Plug,
  Cpu,
  Zap,
  Crosshair,
  Gift,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Card } from './ui/card';
import { Label } from './ui/label';
import { Separator } from './ui/separator';
import {
  OpenAILogo,
  GroqLogo,
  OpenRouterLogo,
  DeepSeekLogo,
  TikTokLogo,
  YouTubeLogo,
} from './BrandIcons';

export interface AiProviderPreset {
  label: string;
  endpoint: string;
  default_model: string;
  doc_url?: string;
}

export interface AiConfigResponse {
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

export interface AiTestResult {
  ok: boolean;
  message?: string;
  error?: string;
  reply?: string;
}

export interface AiGroqTestResult {
  ok: boolean;
  message?: string;
  error?: string;
}

export interface YouTubeChannelInfo {
  id?: string;
  title?: string;
  customUrl?: string;
  thumbnail?: string;
  subscriberCount?: string;
  videoCount?: string;
}

/** Shared section header for each settings tab canvas. */
const TabHeader: React.FC<{
  chipClass: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
}> = ({ chipClass, icon, title, desc }) => (
  <div className="flex items-start gap-3.5">
    <span
      className={`flex h-11 w-11 items-center justify-center rounded-xl border flex-shrink-0 ${chipClass}`}
    >
      {icon}
    </span>
    <div className="min-w-0 pt-0.5">
      <h3 className="text-lg font-bold tracking-tight text-white font-['Outfit']">{title}</h3>
      <p className="text-sm text-slate-400 mt-0.5 leading-relaxed">{desc}</p>
    </div>
  </div>
);

interface StudioSettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  activeTab: 'ai' | 'whisper' | 'youtube' | 'tiktok';
  setActiveTab: (tab: 'ai' | 'whisper' | 'youtube' | 'tiktok') => void;
  aiConfig: AiConfigResponse | null;
  aiSelectedProvider: string;
  handleSelectProvider: (pKey: string) => void;
  aiEndpointInput: string;
  setAiEndpointInput: (val: string) => void;
  aiModelInput: string;
  setAiModelInput: (val: string) => void;
  handleFetchModels: () => void;
  aiModelsLoading: boolean;
  aiModelsError: string | null;
  aiModelsOpen: boolean;
  setAiModelsOpen: (val: boolean) => void;
  aiModels: string[];
  aiApiKeyInput: string;
  setAiApiKeyInput: (val: string) => void;
  aiGroqKeyInput: string;
  setAiGroqKeyInput: (val: string) => void;
  aiShowKey: boolean;
  setAiShowKey: (val: boolean) => void;
  aiShowGroqKey: boolean;
  setAiShowGroqKey: (val: boolean) => void;
  handleTestAiConnection: () => void;
  aiTesting: boolean;
  aiTestResult: AiTestResult | null;
  setAiTestResult: (val: AiTestResult | null) => void;
  handleTestGroqConnection: () => void;
  aiTestingGroq: boolean;
  aiGroqTestResult: AiGroqTestResult | null;
  setAiGroqTestResult: (val: AiGroqTestResult | null) => void;
  handleSaveAiConfig: () => void;
  aiSaving: boolean;
  ytConnected: boolean;
  ytChannel: YouTubeChannelInfo | null;
  ytAvatarFailed: boolean;
  setYtAvatarFailed: (val: boolean) => void;
  isCheckingYtStatus: boolean;
  checkYouTubeStatus: (refresh?: boolean) => void;
  handleConnectYouTube: () => void;
  handleDisconnectYouTube: () => void;
  onShutdown: () => void;
}

export const StudioSettingsModal: React.FC<StudioSettingsModalProps> = ({
  open,
  onOpenChange,
  activeTab,
  setActiveTab,
  aiConfig,
  aiSelectedProvider,
  handleSelectProvider,
  aiEndpointInput,
  setAiEndpointInput,
  aiModelInput,
  setAiModelInput,
  handleFetchModels,
  aiModelsLoading,
  aiModelsError,
  aiModelsOpen,
  setAiModelsOpen,
  aiModels,
  aiApiKeyInput,
  setAiApiKeyInput,
  aiGroqKeyInput,
  setAiGroqKeyInput,
  aiShowKey,
  setAiShowKey,
  aiShowGroqKey,
  setAiShowGroqKey,
  handleTestAiConnection,
  aiTesting,
  aiTestResult,
  setAiTestResult,
  handleTestGroqConnection,
  aiTestingGroq,
  aiGroqTestResult,
  setAiGroqTestResult,
  handleSaveAiConfig,
  aiSaving,
  ytConnected,
  ytChannel,
  ytAvatarFailed,
  setYtAvatarFailed,
  isCheckingYtStatus,
  checkYouTubeStatus,
  handleConnectYouTube,
  handleDisconnectYouTube,
  onShutdown,
}) => {
  if (!open) return null;

  /** Resolve the official brand mark for a provider key. */
  const renderProviderLogo = (pKey: string, isSelected: boolean) => {
    const tone = isSelected ? 'text-white' : 'text-slate-300';
    switch (pKey) {
      case 'openrouter':
        return <OpenRouterLogo className={`h-5 w-5 ${tone}`} />;
      case 'openai':
        return <OpenAILogo className={`h-5 w-5 ${tone}`} />;
      case 'groq_llm':
        return <GroqLogo className={`h-5 w-5 ${tone}`} />;
      case 'deepseek':
        return (
          <DeepSeekLogo className={`h-5 w-5 ${isSelected ? 'text-sky-400' : 'text-sky-300/80'}`} />
        );
      default:
        return <Plug className={`h-5 w-5 ${isSelected ? 'text-emerald-400' : 'text-slate-400'}`} />;
    }
  };

  /** Sidebar navigation model — single source of truth for the rail. */
  const navItems: Array<{
    key: 'ai' | 'whisper' | 'youtube' | 'tiktok';
    label: string;
    desc: string;
    icon: React.ReactNode;
    activeChip: string;
    idleChip: string;
    activeText: string;
    activeDesc: string;
  }> = [
    {
      key: 'ai',
      label: 'Model AI (LLM)',
      desc: 'Analisis & Scoring',
      icon: <Cpu className="h-4 w-4" />,
      activeChip: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300',
      idleChip: 'bg-slate-900/90 border-slate-800 text-slate-400',
      activeText: 'text-emerald-200',
      activeDesc: 'text-emerald-400/80',
    },
    {
      key: 'whisper',
      label: 'Groq Whisper',
      desc: 'Transkripsi LPU ~3s',
      icon: <GroqLogo className="h-4 w-4" />,
      activeChip: 'bg-orange-500/15 border-orange-500/40 text-orange-300',
      idleChip: 'bg-slate-900/90 border-slate-800 text-slate-400',
      activeText: 'text-orange-200',
      activeDesc: 'text-orange-400/80',
    },
    {
      key: 'youtube',
      label: 'YouTube Shorts',
      desc: 'Channel & Upload',
      icon: <YouTubeLogo className="h-4 w-4" />,
      activeChip: 'bg-red-500/15 border-red-500/40 text-red-400',
      idleChip: 'bg-slate-900/90 border-slate-800 text-slate-400',
      activeText: 'text-red-200',
      activeDesc: 'text-red-400/80',
    },
    {
      key: 'tiktok',
      label: 'TikTok Studio',
      desc: 'Golden Codec 9:16',
      icon: <TikTokLogo className="h-4 w-4" />,
      activeChip: 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300',
      idleChip: 'bg-slate-900/90 border-slate-800 text-slate-400',
      activeText: 'text-cyan-200',
      activeDesc: 'text-cyan-400/80',
    },
  ];

  const setupDone = [aiConfig?.ready, aiConfig?.groq_key_set, ytConnected && !!ytChannel].filter(
    Boolean,
  ).length;
  const setupPct = Math.round((setupDone / 3) * 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-3 sm:p-5 md:p-8 animate-in fade-in-0 duration-200">
      <div className="relative w-full max-w-5xl h-[680px] max-h-[92vh] rounded-2xl border border-slate-800/80 bg-[#0f141b] p-0 shadow-[0_25px_60px_rgba(0,0,0,0.85)] text-slate-100 flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 font-['Instrument_Sans',_'Plus_Jakarta_Sans',_sans-serif]">
        {/* Ambient top glow */}
        <div
          className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 h-48 w-[420px] rounded-full bg-emerald-500/10 blur-[80px]"
          aria-hidden="true"
        />

        {/* Top Header Bar */}
        <div className="relative px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-[#0f141b] flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-slate-800 border border-emerald-500/40 text-emerald-400 shadow-sm flex-shrink-0">
              <Settings2 className="h-5 w-5 stroke-[1.8]" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight text-white font-['Outfit']">
                Pengaturan Studio
              </h2>
              <p className="text-xs text-slate-400">
                Kelola AI LLM engine, transkripsi audio Whisper, dan integrasi channel publikasi.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`hidden md:inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${
                aiConfig?.groq_key_set
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                  : 'border-slate-700 bg-slate-900 text-slate-400'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${aiConfig?.groq_key_set ? 'bg-emerald-400' : 'bg-slate-500'}`}
              />
              Whisper
            </span>
            <span
              className={`hidden md:inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${
                ytConnected && ytChannel
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                  : 'border-slate-700 bg-slate-900 text-slate-400'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${ytConnected && ytChannel ? 'bg-emerald-400' : 'bg-slate-500'}`}
              />
              YouTube
            </span>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
              className="text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg h-8 w-8 ml-1"
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Tutup</span>
            </Button>
          </div>
        </div>

        {/* Master-Detail Split Layout */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
          {/* ─── LEFT SIDEBAR NAVIGATION ─── */}
          <aside className="w-full md:w-64 bg-[#0e1218] border-b md:border-b-0 md:border-r border-slate-800/80 p-3 sm:p-4 flex flex-col justify-between flex-shrink-0">
            <div className="space-y-1">
              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider px-3 mb-2 font-['Outfit']">
                Kategori Pengaturan
              </p>

              <nav className="flex md:flex-col gap-1.5 overflow-x-auto md:overflow-visible pb-1 md:pb-0 scrollbar-none">
                {navItems.map((item) => {
                  const isActive = activeTab === item.key;
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => setActiveTab(item.key)}
                      className={`group relative flex items-center justify-between w-full px-2.5 py-2.5 rounded-xl text-left transition-all cursor-pointer ${
                        isActive
                          ? 'bg-slate-800/60 border border-slate-600/60 shadow-sm'
                          : 'border border-transparent hover:bg-slate-900/80'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span
                          className={`flex h-8 w-8 items-center justify-center rounded-lg border flex-shrink-0 transition-colors ${
                            isActive
                              ? item.activeChip
                              : `${item.idleChip} group-hover:text-slate-200`
                          }`}
                        >
                          {item.icon}
                        </span>
                        <div className="min-w-0">
                          <span
                            className={`block truncate text-xs sm:text-sm font-semibold leading-tight ${isActive ? item.activeText : 'text-slate-200'}`}
                          >
                            {item.label}
                          </span>
                          <span
                            className={`hidden md:block text-[11px] truncate mt-0.5 font-normal ${
                              isActive ? item.activeDesc : 'text-slate-500'
                            }`}
                          >
                            {item.desc}
                          </span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Bottom Status Card in Sidebar */}
            <div className="p-3 rounded-xl border border-slate-800/80 bg-[#131820] space-y-2.5 mt-4">
              {/* Setup progress */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-slate-200 font-['Outfit']">Progres Setup</span>
                  <span className="font-mono font-semibold text-emerald-400">{setupPct}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-500"
                    style={{ width: `${setupPct}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-500">
                  {setupDone} dari 3 modul siap — LLM, Whisper, YouTube.
                </p>
              </div>

              <div className="h-px bg-slate-800/80" />

              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-slate-300 font-medium">
                  <Server className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Engine Lokal</span>
                </span>
                <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-semibold font-mono">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  Ready
                </span>
              </div>
              <button
                type="button"
                onClick={onShutdown}
                className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 text-[11px] font-medium text-slate-300 hover:bg-rose-950/50 hover:text-rose-300 hover:border-rose-500/40 transition-colors cursor-pointer"
              >
                <Power className="h-3.5 w-3.5" />
                <span>Shut Down Server</span>
              </button>
              <p className="text-[10px] text-slate-500 text-center pt-1">
                VisionClipper Studio © 2026 — Built by kam2k-dev
              </p>
            </div>
          </aside>

          {/* ─── RIGHT MAIN SETTINGS CANVAS ─── */}
          <main className="flex-1 flex flex-col min-w-0 bg-[#0b0f14] overflow-hidden">
            {/* Scrollable Canvas Body */}
            <div className="p-6 sm:p-8 space-y-6 overflow-y-auto flex-1 scrollbar-thin">
              {/* ──────── TAB 1: MODEL AI (LLM) ──────── */}
              {activeTab === 'ai' && (
                <div className="space-y-6">
                  {/* Section Title Header */}
                  <TabHeader
                    chipClass="bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                    icon={<Cpu className="h-5 w-5" />}
                    title="Model AI & Engine Analisis"
                    desc="Pilih provider LLM dan model AI yang digunakan untuk mendeteksi momen klip viral serta hook scoring."
                  />

                  {/* Wizard step chips */}
                  <div className="flex flex-wrap items-center gap-2">
                    {[
                      { n: 1, label: 'Provider', done: true },
                      {
                        n: 2,
                        label: 'Endpoint & Model',
                        done: !!aiEndpointInput.trim() && !!aiModelInput.trim(),
                      },
                      { n: 3, label: 'API Key & Uji', done: !!aiConfig?.api_key_set },
                    ].map((s) => (
                      <span
                        key={s.n}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${
                          s.done
                            ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                            : 'border-slate-700 bg-slate-900 text-slate-400'
                        }`}
                      >
                        <span
                          className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-mono ${
                            s.done
                              ? 'bg-emerald-500/30 text-emerald-200'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {s.n}
                        </span>
                        {s.label}
                        {s.done && <Check className="h-3 w-3" />}
                      </span>
                    ))}
                  </div>

                  <Separator />

                  {/* 1. Provider Selection Cards */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-md bg-emerald-500/15 border border-emerald-500/40 text-[10px] font-mono font-bold text-emerald-300">
                        1
                      </span>
                      <Label className="text-xs uppercase tracking-wider text-slate-400 font-bold">
                        Pilihan Provider AI
                      </Label>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                      {Object.entries(
                        aiConfig?.presets || {
                          openrouter: { label: 'OpenRouter', endpoint: '', default_model: '' },
                          openai: { label: 'OpenAI Resmi', endpoint: '', default_model: '' },
                          groq_llm: { label: 'Groq LLM', endpoint: '', default_model: '' },
                          deepseek: { label: 'DeepSeek', endpoint: '', default_model: '' },
                          custom: { label: 'Custom Endpoint', endpoint: '', default_model: '' },
                        },
                      ).map(([pKey, pVal]) => {
                        const isSelected = aiSelectedProvider === pKey;
                        const shortLabel =
                          pKey === 'custom'
                            ? 'Custom'
                            : pKey === 'openai'
                              ? 'OpenAI'
                              : pKey === 'groq_llm'
                                ? 'Groq LLM'
                                : pVal.label;
                        const badgeText =
                          pKey === 'openrouter'
                            ? 'Free / Murah'
                            : pKey === 'openai'
                              ? 'Official'
                              : pKey === 'groq_llm'
                                ? 'LPU Fast'
                                : pKey === 'deepseek'
                                  ? 'V3 / R1'
                                  : '9Router / Local';

                        return (
                          <button
                            key={pKey}
                            type="button"
                            onClick={() => handleSelectProvider(pKey)}
                            className={`group flex flex-col items-start gap-2 p-3 rounded-xl border text-left transition-all cursor-pointer relative ${
                              isSelected
                                ? 'border-emerald-500/80 bg-gradient-to-b from-emerald-950/50 to-emerald-950/20 shadow-sm ring-1 ring-emerald-500/50'
                                : 'border-slate-800 bg-[#131820]/70 hover:border-slate-700 hover:bg-[#131820]'
                            }`}
                          >
                            <div className="flex items-center justify-between w-full">
                              <span
                                className={`flex h-9 w-9 items-center justify-center rounded-lg border flex-shrink-0 transition-colors ${
                                  isSelected
                                    ? 'bg-emerald-500/10 border-emerald-500/30'
                                    : 'bg-slate-900/80 border-slate-800 group-hover:border-slate-700'
                                }`}
                              >
                                {renderProviderLogo(pKey, isSelected)}
                              </span>
                              {isSelected && (
                                <Check className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                              )}
                            </div>
                            <div className="min-w-0 w-full">
                              <span
                                className={`block text-xs font-bold leading-tight truncate ${isSelected ? 'text-white' : 'text-slate-200'}`}
                              >
                                {shortLabel}
                              </span>
                              <span
                                className={`text-[10px] font-mono block truncate w-full mt-0.5 ${isSelected ? 'text-emerald-300' : 'text-slate-500'}`}
                              >
                                {badgeText}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* 2. Endpoint & Model Grid (2 Columns) */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="ai-endpoint">API Endpoint URL</Label>
                        <span className="text-[11px] text-slate-500 font-mono">
                          OpenAI Compatible
                        </span>
                      </div>
                      <Input
                        id="ai-endpoint"
                        type="text"
                        value={aiEndpointInput}
                        onChange={(e) => {
                          setAiEndpointInput(e.target.value);
                          setAiTestResult(null);
                        }}
                        placeholder="https://openrouter.ai/api/v1/chat/completions"
                        className="font-mono text-xs"
                      />
                      <p className="text-[11px] text-slate-500">
                        Harus mendukung skema chat completions OpenAI.
                      </p>
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="ai-model">Nama Model LLM</Label>
                        <span className="text-[11px] text-slate-500">Transkrip & Scoring</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Input
                          id="ai-model"
                          type="text"
                          value={aiModelInput}
                          onChange={(e) => {
                            setAiModelInput(e.target.value);
                            setAiTestResult(null);
                          }}
                          placeholder="google/gemini-2.0-flash-exp:free"
                          className="font-mono text-xs flex-1 min-w-0"
                        />
                        <button
                          type="button"
                          onClick={handleFetchModels}
                          disabled={aiModelsLoading || !aiEndpointInput.trim()}
                          className="flex items-center gap-1 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-2 text-[11px] font-bold text-emerald-300 hover:bg-emerald-500/20 transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                          title="Deteksi otomatis model yang tersedia dari endpoint (pakai API key yang sama)"
                        >
                          <RefreshCw
                            className={`h-3.5 w-3.5 ${aiModelsLoading ? 'animate-spin' : ''}`}
                          />
                          <span>{aiModelsLoading ? 'Cek...' : 'Auto'}</span>
                        </button>
                      </div>

                      {/* Auto-detected model list */}
                      {aiModelsError && (
                        <p className="text-[11px] text-red-400 flex items-center gap-1">
                          <XCircle className="h-3 w-3 flex-shrink-0" />
                          {aiModelsError}
                        </p>
                      )}
                      {aiModelsOpen && aiModels.length > 0 && (
                        <div className="rounded-lg border border-slate-700/80 bg-[#0b0f14] max-h-44 overflow-y-auto scrollbar-thin shadow-lg">
                          <div className="px-2.5 py-1.5 border-b border-slate-800/80 flex items-center justify-between sticky top-0 bg-[#0b0f14]">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                              {aiModels.length} model tersedia
                            </span>
                            <button
                              type="button"
                              onClick={() => setAiModelsOpen(false)}
                              className="text-[10px] text-slate-500 hover:text-slate-300"
                            >
                              Tutup
                            </button>
                          </div>
                          {aiModels.map((m) => (
                            <button
                              key={m}
                              type="button"
                              onClick={() => {
                                setAiModelInput(m);
                                setAiTestResult(null);
                                setAiModelsOpen(false);
                              }}
                              className={`w-full text-left px-2.5 py-1.5 font-mono text-[11px] transition-colors flex items-center justify-between gap-2 ${
                                aiModelInput === m
                                  ? 'bg-emerald-500/10 text-emerald-300'
                                  : 'text-slate-300 hover:bg-slate-800/70'
                              }`}
                            >
                              <span className="truncate">{m}</span>
                              {aiModelInput === m && <Check className="h-3 w-3 flex-shrink-0" />}
                            </button>
                          ))}
                        </div>
                      )}
                      <p className="text-[11px] text-slate-500">
                        Model yang digunakan untuk menganalisis transkrip audio & scoring hook.
                      </p>
                    </div>
                  </div>

                  <Separator />

                  {/* 3. Authentication & Testing Section */}
                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Label htmlFor="ai-key">LLM API Key</Label>
                          {aiConfig?.api_key_set && (
                            <Badge
                              variant="success"
                              className="text-[10px] py-0 px-1.5 font-mono font-normal"
                            >
                              <Check className="h-3 w-3" />
                              Tersimpan: {aiConfig.api_key_masked}
                            </Badge>
                          )}
                        </div>
                        {aiConfig?.presets?.[aiSelectedProvider]?.doc_url && (
                          <a
                            href={aiConfig.presets[aiSelectedProvider].doc_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-emerald-400 hover:text-emerald-300 underline inline-flex items-center gap-1 font-medium"
                          >
                            <span>Dapatkan Key</span>
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <div className="relative flex-1">
                          <Input
                            id="ai-key"
                            type={aiShowKey ? 'text' : 'password'}
                            value={aiApiKeyInput}
                            onChange={(e) => {
                              setAiApiKeyInput(e.target.value);
                              setAiTestResult(null);
                            }}
                            placeholder={
                              aiConfig?.api_key_set
                                ? 'Biarkan kosong untuk memakai key tersimpan'
                                : 'Masukkan API Key (sk-...)'
                            }
                            className="font-mono text-xs pr-10"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => setAiShowKey(!aiShowKey)}
                            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 text-slate-400 hover:text-white"
                            tabIndex={-1}
                          >
                            {aiShowKey ? (
                              <EyeOff className="h-3.5 w-3.5" />
                            ) : (
                              <Eye className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        </div>

                        <Button
                          type="button"
                          variant="secondary"
                          onClick={handleTestAiConnection}
                          disabled={aiTesting}
                          className="flex-shrink-0"
                        >
                          <RefreshCw
                            className={`h-3.5 w-3.5 ${aiTesting ? 'animate-spin text-emerald-400' : ''}`}
                          />
                          <span>{aiTesting ? 'Menguji...' : 'Uji Koneksi'}</span>
                        </Button>
                      </div>
                    </div>

                    {/* AI Test Result Alert */}
                    {aiTestResult && (
                      <div
                        className={`p-3.5 rounded-xl border text-xs flex items-start justify-between gap-3 animate-in fade-in-50 duration-150 ${
                          aiTestResult.ok
                            ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-200'
                            : 'border-red-500/40 bg-red-950/40 text-red-200'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0">
                          {aiTestResult.ok ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                          )}
                          <div className="min-w-0">
                            <p className="font-semibold text-xs">
                              {aiTestResult.ok
                                ? 'Koneksi AI Berhasil Terhubung!'
                                : 'Koneksi AI Gagal'}
                            </p>
                            <p className="font-mono text-[11px] opacity-90 mt-0.5 break-all">
                              {aiTestResult.ok
                                ? aiTestResult.message || `Respon: "${aiTestResult.reply}"`
                                : aiTestResult.error}
                            </p>
                          </div>
                        </div>

                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setAiTestResult(null)}
                          className="h-6 w-6 text-slate-400 hover:text-white -mr-1 -mt-1"
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ──────── TAB 2: GROQ WHISPER ──────── */}
              {activeTab === 'whisper' && (
                <div className="space-y-6">
                  {/* Section Title Header */}
                  <TabHeader
                    chipClass="bg-orange-500/10 border-orange-500/40 text-orange-300"
                    icon={<GroqLogo className="h-5 w-5" />}
                    title="Transkripsi Audio (Groq Whisper Large V3)"
                    desc="Transkripsi suara ultra-cepat berbantuan akselerasi hardware LPU untuk pembuatan subtitle kata per kata otomatis."
                  />

                  <Separator />

                  {/* 3 Metric Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <Card className="border-slate-800/80 bg-[#131820] p-4">
                      <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 mb-0.5 font-['Outfit']">
                        <Zap className="h-3.5 w-3.5" />
                        Kecepatan ~3 Detik
                      </span>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Memproses audio video 10 menit hanya dalam hitungan detik.
                      </p>
                    </Card>

                    <Card className="border-slate-800/80 bg-[#131820] p-4">
                      <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 mb-0.5 font-['Outfit']">
                        <Crosshair className="h-3.5 w-3.5" />
                        Word Timestamps
                      </span>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Sinkronisasi teks subtitle kinetik akurat per kata.
                      </p>
                    </Card>

                    <Card className="border-slate-800/80 bg-[#131820] p-4">
                      <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 mb-0.5 font-['Outfit']">
                        <Gift className="h-3.5 w-3.5" />
                        100% Gratis
                      </span>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        API key resmi tanpa kartu kredit di console.groq.com.
                      </p>
                    </Card>
                  </div>

                  {/* Groq Key Input Row */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Label htmlFor="groq-key">Groq Cloud API Key</Label>
                        {aiConfig?.groq_key_set && (
                          <Badge
                            variant="success"
                            className="text-[10px] py-0 px-1.5 font-mono font-normal"
                          >
                            <Check className="h-3 w-3" />
                            Tersimpan: {aiConfig.groq_key_masked}
                          </Badge>
                        )}
                      </div>

                      <a
                        href="https://console.groq.com/keys"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-emerald-400 hover:text-emerald-300 underline inline-flex items-center gap-1 font-medium"
                      >
                        <span>Buka Groq Console</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <Input
                          id="groq-key"
                          type={aiShowGroqKey ? 'text' : 'password'}
                          value={aiGroqKeyInput}
                          onChange={(e) => {
                            setAiGroqKeyInput(e.target.value);
                            setAiGroqTestResult(null);
                          }}
                          placeholder={
                            aiConfig?.groq_key_set
                              ? 'Biarkan kosong untuk memakai key tersimpan'
                              : 'Masukkan Groq API Key (gsk_...)'
                          }
                          className="font-mono text-xs pr-10"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => setAiShowGroqKey(!aiShowGroqKey)}
                          className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 text-slate-400 hover:text-white"
                          tabIndex={-1}
                        >
                          {aiShowGroqKey ? (
                            <EyeOff className="h-3.5 w-3.5" />
                          ) : (
                            <Eye className="h-3.5 w-3.5" />
                          )}
                        </Button>
                      </div>

                      <Button
                        type="button"
                        variant="secondary"
                        onClick={handleTestGroqConnection}
                        disabled={aiTestingGroq}
                        className="flex-shrink-0"
                      >
                        <RefreshCw
                          className={`h-3.5 w-3.5 ${aiTestingGroq ? 'animate-spin text-emerald-400' : ''}`}
                        />
                        <span>{aiTestingGroq ? 'Memeriksa...' : 'Uji Groq Key'}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Groq Test Result */}
                  {aiGroqTestResult && (
                    <div
                      className={`p-3.5 rounded-xl border text-xs flex items-start justify-between gap-3 animate-in fade-in-50 duration-150 ${
                        aiGroqTestResult.ok
                          ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-200'
                          : 'border-red-500/40 bg-red-950/40 text-red-200'
                      }`}
                    >
                      <div className="flex items-start gap-2.5 min-w-0">
                        {aiGroqTestResult.ok ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0">
                          <p className="font-semibold text-xs">
                            {aiGroqTestResult.ok
                              ? 'Groq API Key Valid & Siap Digunakan!'
                              : 'Uji Groq Gagal'}
                          </p>
                          <p className="font-mono text-[11px] opacity-90 mt-0.5">
                            {aiGroqTestResult.ok
                              ? aiGroqTestResult.message
                              : aiGroqTestResult.error}
                          </p>
                        </div>
                      </div>

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setAiGroqTestResult(null)}
                        className="h-6 w-6 text-slate-400 hover:text-white -mr-1 -mt-1"
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}

                  {/* Step Guide Callout */}
                  <div className="p-4 rounded-xl border border-slate-800/80 bg-[#131820] text-xs text-slate-300 space-y-1.5">
                    <span className="font-bold text-white block">
                      Panduan Singkat Dapatkan Key:
                    </span>
                    <p>
                      1. Kunjungi <strong>console.groq.com/keys</strong> dan masuk dengan akun
                      Google / GitHub.
                    </p>
                    <p>
                      2. Klik tombol <strong>"Create API Key"</strong> dan salin string berawalan{' '}
                      <code className="font-mono text-emerald-300">gsk_...</code>.
                    </p>
                    <p>
                      3. Tempel pada kolom di atas, lalu klik <strong>"Simpan & Sambungkan"</strong>{' '}
                      pada footer di bawah.
                    </p>
                  </div>
                </div>
              )}

              {/* ──────── TAB 3: YOUTUBE SHORTS ──────── */}
              {activeTab === 'youtube' && (
                <div className="space-y-6">
                  {/* Section Title Header */}
                  <TabHeader
                    chipClass="bg-red-500/10 border-red-500/40 text-red-400"
                    icon={<YouTubeLogo className="h-5 w-5" />}
                    title="Integrasi Channel YouTube"
                    desc="Otorisasi Google OAuth untuk publikasi klip Shorts otomatis langsung dari dashboard."
                  />

                  <Separator />

                  {ytConnected && ytChannel ? (
                    <div className="space-y-5">
                      {/* Connected Profile Box */}
                      <Card className="border-red-500/30 bg-gradient-to-r from-red-950/30 to-[#131820] p-5">
                        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 text-center sm:text-left">
                          {ytChannel.thumbnail && !ytAvatarFailed ? (
                            <img
                              src={ytChannel.thumbnail}
                              alt=""
                              onError={() => setYtAvatarFailed(true)}
                              className="h-14 w-14 rounded-full border-2 border-red-500/60 object-cover shadow-sm flex-shrink-0"
                            />
                          ) : (
                            <div className="h-14 w-14 rounded-full bg-red-600/30 text-red-300 font-bold flex items-center justify-center text-lg border border-red-500/40 flex-shrink-0">
                              YT
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-center sm:justify-start gap-2 flex-wrap">
                              <span className="text-base font-bold text-white truncate font-['Outfit']">
                                {ytChannel.title}
                              </span>
                              <Badge variant="success" className="text-[10px]">
                                Google OAuth Aktif
                              </Badge>
                            </div>
                            <p className="text-xs text-slate-400 font-mono mt-0.5">
                              {ytChannel.customUrl || '@asal.sharing'}
                            </p>
                            <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
                              Channel YouTube resmi Anda tersambung. Klip video yang selesai
                              dirender dapat langsung di-upload sebagai Shorts.
                            </p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-800/80">
                          <div className="p-3 rounded-lg bg-[#0b0f14] border border-slate-800 text-center sm:text-left">
                            <span className="text-[11px] text-slate-400 block font-medium uppercase">
                              Subscribers
                            </span>
                            <span className="text-lg font-bold text-slate-100 mt-0.5 block font-['Outfit']">
                              {ytChannel.subscriberCount || '2'}
                            </span>
                          </div>
                          <div className="p-3 rounded-lg bg-[#0b0f14] border border-slate-800 text-center sm:text-left">
                            <span className="text-[11px] text-slate-400 block font-medium uppercase">
                              Total Video
                            </span>
                            <span className="text-lg font-bold text-slate-100 mt-0.5 block font-['Outfit']">
                              {ytChannel.videoCount || '5'}
                            </span>
                          </div>
                        </div>
                      </Card>

                      {/* Technical Specs List */}
                      <div className="p-4 rounded-xl border border-slate-800/80 bg-[#131820] space-y-2 text-xs">
                        <div className="flex justify-between items-center text-slate-400 pb-2 border-b border-slate-800/60">
                          <span>Channel ID:</span>
                          <span className="font-mono text-slate-200 text-xs">
                            {ytChannel.id || 'UCmUbuH3agtBcNREw5VfzPlw'}
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-slate-400 pb-2 border-b border-slate-800/60">
                          <span>Permissions:</span>
                          <span className="font-mono text-emerald-400 text-xs">
                            youtube.upload, youtube.readonly
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-slate-400">
                          <span>Status Token:</span>
                          <span className="font-mono text-emerald-400 text-xs">
                            Valid & Auto-Refresh
                          </span>
                        </div>
                      </div>

                      {/* Channel Action Buttons */}
                      <div className="flex items-center justify-between pt-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => checkYouTubeStatus(true)}
                          disabled={isCheckingYtStatus}
                        >
                          <RefreshCw
                            className={`h-3.5 w-3.5 ${isCheckingYtStatus ? 'animate-spin text-emerald-400' : ''}`}
                          />
                          <span>
                            {isCheckingYtStatus ? 'Memeriksa...' : 'Tes Ulang Koneksi YouTube'}
                          </span>
                        </Button>

                        <Button variant="destructive" size="sm" onClick={handleDisconnectYouTube}>
                          Putuskan Akun YouTube
                        </Button>
                      </div>
                    </div>
                  ) : (
                    /* Disconnected State */
                    <Card className="border-slate-800/80 bg-[#131820] text-center p-6 sm:p-8 space-y-5">
                      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-red-600/20 text-red-500 border border-red-500/40 shadow-inner">
                        <YouTubeLogo className="h-7 w-7" />
                      </div>

                      <div className="space-y-1.5 max-w-md mx-auto">
                        <h4 className="text-base font-bold text-white font-['Outfit']">
                          Hubungkan Channel YouTube
                        </h4>
                        <p className="text-xs text-slate-400 leading-relaxed">
                          Otorisasikan channel YouTube Anda melalui Google OAuth agar VisionClipper
                          dapat memposting klip Shorts langsung dalam satu klik.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-lg mx-auto text-left text-xs">
                        <div className="p-3 rounded-xl bg-[#0b0f14] border border-slate-800">
                          <span className="font-bold text-slate-200 block mb-0.5">
                            🚀 1-Klik Upload
                          </span>
                          <span className="text-slate-400 text-[11px]">
                            Upload langsung ke Shorts
                          </span>
                        </div>
                        <div className="p-3 rounded-xl bg-[#0b0f14] border border-slate-800">
                          <span className="font-bold text-slate-200 block mb-0.5">
                            🏷️ Auto Tagging
                          </span>
                          <span className="text-slate-400 text-[11px]">
                            Judul, deskripsi & #Shorts
                          </span>
                        </div>
                        <div className="p-3 rounded-xl bg-[#0b0f14] border border-slate-800">
                          <span className="font-bold text-slate-200 block mb-0.5">
                            🔒 Token Lokal
                          </span>
                          <span className="text-slate-400 text-[11px]">Aman di komputer Anda</span>
                        </div>
                      </div>

                      <div className="pt-2">
                        <Button
                          variant="default"
                          size="lg"
                          onClick={handleConnectYouTube}
                          className="bg-red-600 hover:bg-red-500 text-white font-bold"
                        >
                          <YouTubeLogo className="h-4 w-4" />
                          <span>Hubungkan Channel YouTube (Google OAuth)</span>
                        </Button>
                      </div>
                    </Card>
                  )}
                </div>
              )}

              {/* ──────── TAB 4: TIKTOK STUDIO ──────── */}
              {activeTab === 'tiktok' && (
                <div className="space-y-6">
                  {/* Section Title Header */}
                  <TabHeader
                    chipClass="bg-cyan-500/10 border-cyan-500/40 text-cyan-300"
                    icon={<TikTokLogo className="h-5 w-5" />}
                    title="TikTok Creator Studio Assistant"
                    desc="Panduan ekspor dan alur kerja cepat posting video klip vertikal standar TikTok Creator Rewards Program."
                  />

                  <Separator />

                  {/* 4 Steps — vertical timeline */}
                  <div className="space-y-3">
                    <Label className="text-xs uppercase tracking-wider text-slate-400 font-bold">
                      Alur Kerja Cepat (TikTok Quick Assistant)
                    </Label>

                    <ol className="relative space-y-3">
                      <span
                        className="absolute left-[15px] top-3 bottom-3 w-px bg-gradient-to-b from-cyan-500/50 via-slate-700/60 to-transparent"
                        aria-hidden="true"
                      />
                      {[
                        {
                          title: 'Render Klip Video',
                          desc: 'Pilih kandidat klip terbaik di dashboard dan render dengan preset subtitle TikTok Viral.',
                        },
                        {
                          title: 'Klik Tombol TikTok',
                          desc: 'Klik tombol logo TikTok pada kartu klip yang selesai dirender untuk menyalin caption.',
                        },
                        {
                          title: 'Auto Copy Caption',
                          desc: 'Caption hook menarik dan 5 hashtag viral langsung tersalin otomatis ke clipboard.',
                        },
                        {
                          title: 'Drag & Drop ke Web Studio',
                          desc: 'Buka TikTok Studio Web, drag video dari folder clips, dan paste caption (Ctrl+V / ⌘V).',
                        },
                      ].map((step, i) => (
                        <li key={step.title} className="relative flex items-start gap-3.5">
                          <span className="relative z-10 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-cyan-500/40 bg-[#0b0f14] text-[11px] font-mono font-bold text-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.15)]">
                            {i + 1}
                          </span>
                          <div className="min-w-0 flex-1 rounded-xl border border-slate-800/80 bg-[#131820] px-4 py-3">
                            <span className="block text-xs font-bold text-cyan-300 font-['Outfit']">
                              {step.title}
                            </span>
                            <span className="mt-0.5 block text-xs text-slate-400 leading-relaxed">
                              {step.desc}
                            </span>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>

                  {/* Direct Link Card */}
                  <Card className="border-slate-800/80 bg-[#131820] p-5 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <h4 className="text-sm font-bold text-white font-['Outfit']">
                          Buka TikTok Creator Center
                        </h4>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Akses portal upload resmi TikTok di browser untuk mulai memposting video.
                        </p>
                      </div>

                      <a
                        href="https://www.tiktok.com/creator-center/upload"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 px-4 py-2.5 text-xs font-bold text-white transition-all flex-shrink-0 shadow-sm shadow-cyan-600/20 active:scale-95"
                      >
                        <span>Buka TikTok Studio Web</span>
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      </a>
                    </div>

                    <Separator />

                    <div className="text-xs text-slate-400 space-y-1">
                      <p className="font-semibold text-slate-300">
                        Standar Ekspor VisionClipper untuk TikTok:
                      </p>
                      <p>
                        • Resolusi: <strong>1080 x 1920 (9:16 Vertikal)</strong> dengan Smart Face
                        Tracking otomatis.
                      </p>
                      <p>
                        • Video Codec:{' '}
                        <strong>H.264 High Profile @ 60 FPS, CRF 18, FastStart</strong>.
                      </p>
                      <p>
                        • Audio: <strong>AAC 192 kbps Stereo</strong> (Audio Enhancer loudness
                        normalization -14 LUFS).
                      </p>
                      <p>
                        • Durasi Rekomendasi: <strong>60 - 90 detik</strong> untuk kualifikasi
                        TikTok Creator Rewards Program.
                      </p>
                    </div>
                  </Card>
                </div>
              )}
            </div>

            {/* Bottom Footer Bar */}
            <div className="px-6 py-4 border-t border-slate-800/80 bg-[#0f141b] flex items-center justify-between flex-shrink-0">
              <p className="hidden sm:block text-[11px] text-slate-500 truncate pr-4">
                {activeTab === 'ai' && 'Simpan konfigurasi untuk mengaktifkan engine analisis AI.'}
                {activeTab === 'whisper' &&
                  'Simpan untuk mengaktifkan transkripsi & subtitle otomatis.'}
                {activeTab === 'youtube' &&
                  'Sambungkan channel untuk mengaktifkan upload Shorts otomatis.'}
                {activeTab === 'tiktok' && 'Ikuti alur 4 langkah untuk posting klip ke TikTok.'}
              </p>

              <div className="flex items-center gap-2 ml-auto">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Tutup
                </Button>

                {activeTab === 'ai' || activeTab === 'whisper' ? (
                  <Button variant="default" onClick={handleSaveAiConfig} disabled={aiSaving}>
                    {aiSaving ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Menyimpan...</span>
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4 stroke-[2.5]" />
                        <span>Simpan & Sambungkan ke Engine</span>
                      </>
                    )}
                  </Button>
                ) : activeTab === 'youtube' ? (
                  ytConnected ? (
                    <Button
                      variant="outline"
                      onClick={() => checkYouTubeStatus(true)}
                      disabled={isCheckingYtStatus}
                    >
                      <RefreshCw
                        className={`h-3.5 w-3.5 ${isCheckingYtStatus ? 'animate-spin text-emerald-400' : ''}`}
                      />
                      <span>Tes Status YouTube</span>
                    </Button>
                  ) : (
                    <Button
                      variant="default"
                      onClick={handleConnectYouTube}
                      className="bg-red-600 hover:bg-red-500 text-white font-bold"
                    >
                      <YouTubeLogo className="h-4 w-4" />
                      <span>Hubungkan YouTube</span>
                    </Button>
                  )
                ) : (
                  <a
                    href="https://www.tiktok.com/creator-center/upload"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 px-4 py-2 text-xs font-bold text-white transition-all shadow-sm active:scale-95"
                  >
                    <span>Buka TikTok Studio</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </a>
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};
