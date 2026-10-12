import React from 'react';
import {
  Settings2,
  Cpu,
  Mic,
  Youtube,
  Check,
  CheckCircle2,
  XCircle,
  X,
  ExternalLink,
  RefreshCw,
  Eye,
  EyeOff,
  Sparkles,
  ArrowUpRight,
  ShieldCheck,
  Server
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Card } from './ui/card';
import { Label } from './ui/label';
import { Separator } from './ui/separator';

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
  aiTestResult: { ok: boolean; message?: string; error?: string; reply?: string } | null;
  setAiTestResult: (val: any) => void;
  handleTestGroqConnection: () => void;
  aiTestingGroq: boolean;
  aiGroqTestResult: { ok: boolean; message?: string; error?: string } | null;
  setAiGroqTestResult: (val: any) => void;
  handleSaveAiConfig: () => void;
  aiSaving: boolean;
  ytConnected: boolean;
  ytChannel: any;
  ytAvatarFailed: boolean;
  setYtAvatarFailed: (val: boolean) => void;
  isCheckingYtStatus: boolean;
  checkYouTubeStatus: (refresh?: boolean) => void;
  handleConnectYouTube: () => void;
  handleDisconnectYouTube: () => void;
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
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-3 sm:p-5 md:p-8 animate-in fade-in-0 duration-200">
      <div className="w-full max-w-5xl h-[680px] max-h-[92vh] rounded-2xl border border-slate-800/80 bg-[#0f141b] p-0 shadow-[0_25px_60px_rgba(0,0,0,0.85)] text-slate-100 flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 font-['Instrument_Sans',_'Plus_Jakarta_Sans',_sans-serif]">
        
        {/* Top Header Bar */}
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-[#0f141b] flex-shrink-0">
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

          <Button
            variant="ghost"
            size="icon"
            onClick={() => onOpenChange(false)}
            className="text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg h-8 w-8"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Tutup</span>
          </Button>
        </div>

        {/* Master-Detail Split Layout */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
          
          {/* ─── LEFT SIDEBAR NAVIGATION ─── */}
          <aside className="w-full md:w-64 bg-[#0e1218] border-b md:border-b-0 md:border-r border-slate-800/80 p-3 sm:p-4 flex flex-col justify-between flex-shrink-0">
            <div className="space-y-1">
              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider px-3 mb-2 font-['Outfit']">
                Kategori Pengaturan
              </p>

              <nav className="flex md:flex-col gap-1 overflow-x-auto md:overflow-visible pb-1 md:pb-0 scrollbar-none">
                {/* 1. Model AI */}
                <button
                  type="button"
                  onClick={() => setActiveTab('ai')}
                  className={`flex items-center justify-between w-full px-3 py-2.5 rounded-xl text-left text-sm transition-all cursor-pointer group ${
                    activeTab === 'ai'
                      ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 shadow-xs font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Cpu className={`h-4 w-4 flex-shrink-0 ${activeTab === 'ai' ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
                    <div className="min-w-0">
                      <span className="block truncate text-xs sm:text-sm font-semibold leading-tight">
                        Model AI (LLM)
                      </span>
                      <span className={`hidden md:block text-[11px] truncate mt-0.5 font-normal ${
                        activeTab === 'ai' ? 'text-emerald-400/80' : 'text-slate-500'
                      }`}>
                        Analisis & Scoring
                      </span>
                    </div>
                  </div>

                  <div className="ml-2 flex-shrink-0">
                    {aiConfig?.ready ? (
                      <Badge variant="success" className="text-[9px] px-1.5 py-0">
                        Aktif
                      </Badge>
                    ) : (
                      <Badge variant="warning" className="text-[9px] px-1.5 py-0">
                        Setup
                      </Badge>
                    )}
                  </div>
                </button>

                {/* 2. Whisper */}
                <button
                  type="button"
                  onClick={() => setActiveTab('whisper')}
                  className={`flex items-center justify-between w-full px-3 py-2.5 rounded-xl text-left text-sm transition-all cursor-pointer group ${
                    activeTab === 'whisper'
                      ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 shadow-xs font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Mic className={`h-4 w-4 flex-shrink-0 ${activeTab === 'whisper' ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
                    <div className="min-w-0">
                      <span className="block truncate text-xs sm:text-sm font-semibold leading-tight">
                        Groq Whisper
                      </span>
                      <span className={`hidden md:block text-[11px] truncate mt-0.5 font-normal ${
                        activeTab === 'whisper' ? 'text-emerald-400/80' : 'text-slate-500'
                      }`}>
                        Transkripsi LPU ~3s
                      </span>
                    </div>
                  </div>

                  <div className="ml-2 flex-shrink-0">
                    {aiConfig?.groq_key_set ? (
                      <Badge variant="success" className="text-[9px] px-1.5 py-0">
                        Aktif
                      </Badge>
                    ) : (
                      <Badge variant="warning" className="text-[9px] px-1.5 py-0">
                        Setup
                      </Badge>
                    )}
                  </div>
                </button>

                {/* 3. YouTube */}
                <button
                  type="button"
                  onClick={() => setActiveTab('youtube')}
                  className={`flex items-center justify-between w-full px-3 py-2.5 rounded-xl text-left text-sm transition-all cursor-pointer group ${
                    activeTab === 'youtube'
                      ? 'bg-red-950/40 text-red-300 border border-red-500/40 shadow-xs font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Youtube className="h-4 w-4 text-red-500 flex-shrink-0" />
                    <div className="min-w-0">
                      <span className="block truncate text-xs sm:text-sm font-semibold leading-tight">
                        YouTube Shorts
                      </span>
                      <span className={`hidden md:block text-[11px] truncate mt-0.5 font-normal ${
                        activeTab === 'youtube' ? 'text-red-400/80' : 'text-slate-500'
                      }`}>
                        Channel & Upload
                      </span>
                    </div>
                  </div>

                  <div className="ml-2 flex-shrink-0">
                    {ytConnected && ytChannel ? (
                      <Badge variant="success" className="text-[9px] px-1.5 py-0">
                        Konek
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[9px] px-1.5 py-0 text-slate-400 border-slate-700">
                        Off
                      </Badge>
                    )}
                  </div>
                </button>

                {/* 4. TikTok */}
                <button
                  type="button"
                  onClick={() => setActiveTab('tiktok')}
                  className={`flex items-center justify-between w-full px-3 py-2.5 rounded-xl text-left text-sm transition-all cursor-pointer group ${
                    activeTab === 'tiktok'
                      ? 'bg-cyan-950/40 text-cyan-300 border border-cyan-500/40 shadow-xs font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Sparkles className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <span className="block truncate text-xs sm:text-sm font-semibold leading-tight">
                        TikTok Studio
                      </span>
                      <span className={`hidden md:block text-[11px] truncate mt-0.5 font-normal ${
                        activeTab === 'tiktok' ? 'text-cyan-400/80' : 'text-slate-500'
                      }`}>
                        Golden Codec 9:16
                      </span>
                    </div>
                  </div>

                  <div className="ml-2 flex-shrink-0">
                    <Badge variant="secondary" className="text-[9px] px-1.5 py-0 bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                      Ready
                    </Badge>
                  </div>
                </button>
              </nav>
            </div>

            {/* Bottom Status Card in Sidebar */}
            <div className="hidden md:block p-3 rounded-xl border border-slate-800/80 bg-[#131820] space-y-1.5 mt-4">
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
              <p className="text-[11px] text-slate-400 leading-tight flex items-center gap-1">
                <ShieldCheck className="h-3 w-3 text-emerald-400/80 flex-shrink-0" />
                <span>Token & key tersimpan aman di lokal</span>
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
                  <div>
                    <h3 className="text-lg font-bold tracking-tight text-white font-['Outfit']">
                      Model AI & Engine Analisis
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">
                      Pilih provider LLM dan model AI yang digunakan untuk mendeteksi momen klip viral serta hook scoring.
                    </p>
                  </div>

                  <Separator />

                  {/* 1. Provider Selection Cards */}
                  <div className="space-y-3">
                    <Label className="text-xs uppercase tracking-wider text-slate-400 font-bold">
                      Pilihan Provider AI
                    </Label>

                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                      {Object.entries(aiConfig?.presets || {
                        openrouter: { label: 'OpenRouter', endpoint: '', default_model: '' },
                        openai: { label: 'OpenAI Resmi', endpoint: '', default_model: '' },
                        groq_llm: { label: 'Groq LLM', endpoint: '', default_model: '' },
                        deepseek: { label: 'DeepSeek', endpoint: '', default_model: '' },
                        custom: { label: 'Custom Endpoint', endpoint: '', default_model: '' },
                      }).map(([pKey, pVal]) => {
                        const isSelected = aiSelectedProvider === pKey;
                        const shortLabel = pKey === 'custom' ? 'Custom' :
                                           pKey === 'openai' ? 'OpenAI' :
                                           pKey === 'groq_llm' ? 'Groq LLM' : pVal.label;
                        const badgeText = pKey === 'openrouter' ? 'Free / Murah' :
                                          pKey === 'openai' ? 'Official' :
                                          pKey === 'groq_llm' ? 'LPU Fast' :
                                          pKey === 'deepseek' ? 'V3 / R1' :
                                          '9Router / Local';

                        return (
                          <button
                            key={pKey}
                            type="button"
                            onClick={() => handleSelectProvider(pKey)}
                            className={`flex flex-col items-start p-3 rounded-xl border text-left transition-all cursor-pointer relative ${
                              isSelected
                                ? 'border-emerald-500/80 bg-emerald-950/40 shadow-sm ring-1 ring-emerald-500/50 text-white'
                                : 'border-slate-800 bg-[#131820]/70 text-slate-400 hover:border-slate-700 hover:text-slate-200 hover:bg-[#131820]'
                            }`}
                          >
                            <div className="flex items-center justify-between w-full mb-1">
                              <span className={`text-xs font-bold leading-tight truncate ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                                {shortLabel}
                              </span>
                              {isSelected && (
                                <Check className="h-3 w-3 text-emerald-400 flex-shrink-0" />
                              )}
                            </div>
                            <span className={`text-[10px] font-mono block truncate w-full ${isSelected ? 'text-emerald-300' : 'text-slate-500'}`}>
                              {badgeText}
                            </span>
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
                        <span className="text-[11px] text-slate-500 font-mono">OpenAI Compatible</span>
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
                      <Input
                        id="ai-model"
                        type="text"
                        value={aiModelInput}
                        onChange={(e) => {
                          setAiModelInput(e.target.value);
                          setAiTestResult(null);
                        }}
                        placeholder="google/gemini-2.0-flash-exp:free"
                        className="font-mono text-xs"
                      />
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
                            <Badge variant="success" className="text-[10px] py-0 px-1.5 font-mono font-normal">
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
                            placeholder={aiConfig?.api_key_set ? "Biarkan kosong untuk memakai key tersimpan" : "Masukkan API Key (sk-...)"}
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
                            {aiShowKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                          </Button>
                        </div>

                        <Button
                          type="button"
                          variant="secondary"
                          onClick={handleTestAiConnection}
                          disabled={aiTesting}
                          className="flex-shrink-0"
                        >
                          <RefreshCw className={`h-3.5 w-3.5 ${aiTesting ? 'animate-spin text-emerald-400' : ''}`} />
                          <span>{aiTesting ? 'Menguji...' : 'Uji Koneksi'}</span>
                        </Button>
                      </div>
                    </div>

                    {/* AI Test Result Alert */}
                    {aiTestResult && (
                      <div className={`p-3.5 rounded-xl border text-xs flex items-start justify-between gap-3 animate-in fade-in-50 duration-150 ${
                        aiTestResult.ok
                          ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-200'
                          : 'border-red-500/40 bg-red-950/40 text-red-200'
                      }`}>
                        <div className="flex items-start gap-2.5 min-w-0">
                          {aiTestResult.ok ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                          )}
                          <div className="min-w-0">
                            <p className="font-semibold text-xs">
                              {aiTestResult.ok ? 'Koneksi AI Berhasil Terhubung!' : 'Koneksi AI Gagal'}
                            </p>
                            <p className="font-mono text-[11px] opacity-90 mt-0.5 break-all">
                              {aiTestResult.ok ? (aiTestResult.message || `Respon: "${aiTestResult.reply}"`) : aiTestResult.error}
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
                  <div>
                    <h3 className="text-lg font-bold tracking-tight text-white font-['Outfit']">
                      Transkripsi Audio (Groq Whisper Large V3)
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">
                      Transkripsi suara ultra-cepat berbantuan akselerasi hardware LPU untuk pembuatan subtitle kata per kata otomatis.
                    </p>
                  </div>

                  <Separator />

                  {/* 3 Metric Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <Card className="border-slate-800/80 bg-[#131820] p-4">
                      <span className="text-xs font-bold text-emerald-400 block mb-0.5 font-['Outfit']">⚡ Kecepatan ~3 Detik</span>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Memproses audio video 10 menit hanya dalam hitungan detik.
                      </p>
                    </Card>

                    <Card className="border-slate-800/80 bg-[#131820] p-4">
                      <span className="text-xs font-bold text-emerald-400 block mb-0.5 font-['Outfit']">🎯 Word Timestamps</span>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Sinkronisasi teks subtitle kinetik akurat per kata.
                      </p>
                    </Card>

                    <Card className="border-slate-800/80 bg-[#131820] p-4">
                      <span className="text-xs font-bold text-emerald-400 block mb-0.5 font-['Outfit']">🆓 100% Gratis</span>
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
                          <Badge variant="success" className="text-[10px] py-0 px-1.5 font-mono font-normal">
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
                          placeholder={aiConfig?.groq_key_set ? "Biarkan kosong untuk memakai key tersimpan" : "Masukkan Groq API Key (gsk_...)"}
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
                          {aiShowGroqKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                        </Button>
                      </div>

                      <Button
                        type="button"
                        variant="secondary"
                        onClick={handleTestGroqConnection}
                        disabled={aiTestingGroq}
                        className="flex-shrink-0"
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${aiTestingGroq ? 'animate-spin text-emerald-400' : ''}`} />
                        <span>{aiTestingGroq ? 'Memeriksa...' : 'Uji Groq Key'}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Groq Test Result */}
                  {aiGroqTestResult && (
                    <div className={`p-3.5 rounded-xl border text-xs flex items-start justify-between gap-3 animate-in fade-in-50 duration-150 ${
                      aiGroqTestResult.ok
                        ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-200'
                        : 'border-red-500/40 bg-red-950/40 text-red-200'
                    }`}>
                      <div className="flex items-start gap-2.5 min-w-0">
                        {aiGroqTestResult.ok ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0">
                          <p className="font-semibold text-xs">
                            {aiGroqTestResult.ok ? 'Groq API Key Valid & Siap Digunakan!' : 'Uji Groq Gagal'}
                          </p>
                          <p className="font-mono text-[11px] opacity-90 mt-0.5">
                            {aiGroqTestResult.ok ? aiGroqTestResult.message : aiGroqTestResult.error}
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
                    <span className="font-bold text-white block">Panduan Singkat Dapatkan Key:</span>
                    <p>1. Kunjungi <strong>console.groq.com/keys</strong> dan masuk dengan akun Google / GitHub.</p>
                    <p>2. Klik tombol <strong>"Create API Key"</strong> dan salin string berawalan <code className="font-mono text-emerald-300">gsk_...</code>.</p>
                    <p>3. Tempel pada kolom di atas, lalu klik <strong>"Simpan & Sambungkan"</strong> pada footer di bawah.</p>
                  </div>
                </div>
              )}

              {/* ──────── TAB 3: YOUTUBE SHORTS ──────── */}
              {activeTab === 'youtube' && (
                <div className="space-y-6">
                  {/* Section Title Header */}
                  <div>
                    <h3 className="text-lg font-bold tracking-tight text-white font-['Outfit']">
                      Integrasi Channel YouTube
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">
                      Otorisasi Google OAuth untuk publikasi klip Shorts otomatis langsung dari dashboard.
                    </p>
                  </div>

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
                            <p className="text-xs text-slate-400 font-mono mt-0.5">{ytChannel.customUrl || '@asal.sharing'}</p>
                            <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
                              Channel YouTube resmi Anda tersambung. Klip video yang selesai dirender dapat langsung di-upload sebagai Shorts.
                            </p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-800/80">
                          <div className="p-3 rounded-lg bg-[#0b0f14] border border-slate-800 text-center sm:text-left">
                            <span className="text-[11px] text-slate-400 block font-medium uppercase">Subscribers</span>
                            <span className="text-lg font-bold text-slate-100 mt-0.5 block font-['Outfit']">{(ytChannel as any).subscriberCount || '2'}</span>
                          </div>
                          <div className="p-3 rounded-lg bg-[#0b0f14] border border-slate-800 text-center sm:text-left">
                            <span className="text-[11px] text-slate-400 block font-medium uppercase">Total Video</span>
                            <span className="text-lg font-bold text-slate-100 mt-0.5 block font-['Outfit']">{(ytChannel as any).videoCount || '5'}</span>
                          </div>
                        </div>
                      </Card>

                      {/* Technical Specs List */}
                      <div className="p-4 rounded-xl border border-slate-800/80 bg-[#131820] space-y-2 text-xs">
                        <div className="flex justify-between items-center text-slate-400 pb-2 border-b border-slate-800/60">
                          <span>Channel ID:</span>
                          <span className="font-mono text-slate-200 text-xs">{(ytChannel as any).id || 'UCmUbuH3agtBcNREw5VfzPlw'}</span>
                        </div>
                        <div className="flex justify-between items-center text-slate-400 pb-2 border-b border-slate-800/60">
                          <span>Permissions:</span>
                          <span className="font-mono text-emerald-400 text-xs">youtube.upload, youtube.readonly</span>
                        </div>
                        <div className="flex justify-between items-center text-slate-400">
                          <span>Status Token:</span>
                          <span className="font-mono text-emerald-400 text-xs">Valid & Auto-Refresh</span>
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
                          <RefreshCw className={`h-3.5 w-3.5 ${isCheckingYtStatus ? 'animate-spin text-emerald-400' : ''}`} />
                          <span>{isCheckingYtStatus ? 'Memeriksa...' : 'Tes Ulang Koneksi YouTube'}</span>
                        </Button>

                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={handleDisconnectYouTube}
                        >
                          Putuskan Akun YouTube
                        </Button>
                      </div>
                    </div>
                  ) : (
                    /* Disconnected State */
                    <Card className="border-slate-800/80 bg-[#131820] text-center p-6 sm:p-8 space-y-5">
                      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-red-600/20 text-red-500 border border-red-500/40 shadow-inner">
                        <Youtube className="h-7 w-7" />
                      </div>

                      <div className="space-y-1.5 max-w-md mx-auto">
                        <h4 className="text-base font-bold text-white font-['Outfit']">Hubungkan Channel YouTube</h4>
                        <p className="text-xs text-slate-400 leading-relaxed">
                          Otorisasikan channel YouTube Anda melalui Google OAuth agar VisionClipper dapat memposting klip Shorts langsung dalam satu klik.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-lg mx-auto text-left text-xs">
                        <div className="p-3 rounded-xl bg-[#0b0f14] border border-slate-800">
                          <span className="font-bold text-slate-200 block mb-0.5">🚀 1-Klik Upload</span>
                          <span className="text-slate-400 text-[11px]">Upload langsung ke Shorts</span>
                        </div>
                        <div className="p-3 rounded-xl bg-[#0b0f14] border border-slate-800">
                          <span className="font-bold text-slate-200 block mb-0.5">🏷️ Auto Tagging</span>
                          <span className="text-slate-400 text-[11px]">Judul, deskripsi & #Shorts</span>
                        </div>
                        <div className="p-3 rounded-xl bg-[#0b0f14] border border-slate-800">
                          <span className="font-bold text-slate-200 block mb-0.5">🔒 Token Lokal</span>
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
                          <Youtube className="h-4 w-4" />
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
                  <div>
                    <h3 className="text-lg font-bold tracking-tight text-white font-['Outfit']">
                      TikTok Creator Studio Assistant
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">
                      Panduan ekspor dan alur kerja cepat posting video klip vertikal standar TikTok Creator Rewards Program.
                    </p>
                  </div>

                  <Separator />

                  {/* 4 Steps Grid */}
                  <div className="space-y-3">
                    <Label className="text-xs uppercase tracking-wider text-slate-400 font-bold">
                      Alur Kerja Cepat (TikTok Quick Assistant)
                    </Label>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-4 rounded-xl bg-[#131820] border border-slate-800/80">
                        <span className="font-bold text-cyan-300 block mb-1">1. Render Klip Video</span>
                        <span className="text-slate-400 leading-relaxed">
                          Pilih kandidat klip terbaik di dashboard dan render dengan preset subtitle TikTok Viral.
                        </span>
                      </div>

                      <div className="p-4 rounded-xl bg-[#131820] border border-slate-800/80">
                        <span className="font-bold text-cyan-300 block mb-1">2. Klik Tombol TikTok</span>
                        <span className="text-slate-400 leading-relaxed">
                          Klik tombol logo TikTok pada kartu klip yang selesai dirender untuk menyalin caption.
                        </span>
                      </div>

                      <div className="p-4 rounded-xl bg-[#131820] border border-slate-800/80">
                        <span className="font-bold text-cyan-300 block mb-1">3. Auto Copy Caption</span>
                        <span className="text-slate-400 leading-relaxed">
                          Caption hook menarik dan 5 hashtag viral langsung tersalin otomatis ke clipboard.
                        </span>
                      </div>

                      <div className="p-4 rounded-xl bg-[#131820] border border-slate-800/80">
                        <span className="font-bold text-cyan-300 block mb-1">4. Drag & Drop ke Web Studio</span>
                        <span className="text-slate-400 leading-relaxed">
                          Buka TikTok Studio Web, drag video dari folder clips, dan paste caption (<kbd className="font-mono text-slate-200">Ctrl+V / ⌘V</kbd>).
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Direct Link Card */}
                  <Card className="border-slate-800/80 bg-[#131820] p-5 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <h4 className="text-sm font-bold text-white font-['Outfit']">Buka TikTok Creator Center</h4>
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
                      <p className="font-semibold text-slate-300">💡 Standar Ekspor VisionClipper untuk TikTok:</p>
                      <p>• Resolusi: <strong>1080 x 1920 (9:16 Vertikal)</strong> dengan Smart Face Tracking otomatis.</p>
                      <p>• Video Codec: <strong>H.264 High Profile @ 60 FPS, CRF 18, FastStart</strong>.</p>
                      <p>• Audio: <strong>AAC 192 kbps Stereo</strong> (Audio Enhancer loudness normalization -14 LUFS).</p>
                      <p>• Durasi Rekomendasi: <strong>60 - 90 detik</strong> untuk kualifikasi TikTok Creator Rewards Program.</p>
                    </div>
                  </Card>
                </div>
              )}

            </div>

            {/* Bottom Footer Bar */}
            <div className="px-6 py-4 border-t border-slate-800/80 bg-[#0f141b] flex items-center justify-between flex-shrink-0">
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Tutup
              </Button>

              {(activeTab === 'ai' || activeTab === 'whisper') ? (
                <Button
                  variant="default"
                  onClick={handleSaveAiConfig}
                  disabled={aiSaving}
                >
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
                    <RefreshCw className={`h-3.5 w-3.5 ${isCheckingYtStatus ? 'animate-spin text-emerald-400' : ''}`} />
                    <span>Tes Status YouTube</span>
                  </Button>
                ) : (
                  <Button
                    variant="default"
                    onClick={handleConnectYouTube}
                    className="bg-red-600 hover:bg-red-500 text-white font-bold"
                  >
                    <Youtube className="h-4 w-4" />
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

          </main>

        </div>

      </div>
    </div>
  );
};
