import json
import os
import re
import requests
from backend.utils import log


def env_int(key, default):
    """Read an integer env var with a safe fallback."""
    try:
        return int(str(os.environ.get(key, "")).strip() or default)
    except (ValueError, TypeError):
        return default


def env_float(key, default):
    """Read a float env var with a safe fallback."""
    try:
        return float(str(os.environ.get(key, "")).strip() or default)
    except (ValueError, TypeError):
        return default


class PermanentLLMError(RuntimeError):
    """Raised when every candidate model failed with a non-recoverable error
    (e.g. location restriction, missing credentials). Retrying won't help."""


def build_viral_prompt(transcript_text, num_clips, mode="hook"):
    if mode == "affiliate":
        prompt = f"""You are an elite affiliate marketing content strategist specializing in short-form video platforms (TikTok, YouTube Shorts, Instagram Reels). You have deep expertise in SALES PSYCHOLOGY, CONVERSION OPTIMIZATION, and VIRAL CONTENT MECHANICS.

## YOUR MISSION
Analyze the transcript below and extract exactly {num_clips} high-converting segments optimized for AFFILIATE SALES + VIRAL REACH.

## TRANSCRIPT FORMAT
Each line: [HH:MM:SS.mmm --> HH:MM:SS.mmm] spoken text

## SEGMENT SELECTION CRITERIA (Ranked by Priority)

### Sales Psychology Triggers (MUST contain at least 2):
1. **Pain Point Identification** — Speaker describes a relatable problem or frustration
2. **Product/Solution Reveal** — The "aha moment" when the product is introduced as the fix
3. **Social Proof** — Testimonials, user count, reviews, authority endorsements
4. **Before/After Transformation** — Clear contrast showing results
5. **Urgency/Scarcity** — Limited time, limited stock, "before it's too late"
6. **Price Anchoring** — Comparing to expensive alternatives, "only $X"
7. **Call-to-Action (CTA)** — "Link in bio", "Use my code", "Check the description"
8. **Emotional Storytelling** — Personal anecdotes that build trust and desire

### Virality Boosters (Bonus points):
- Controversial opinion about a product category
- Unexpected comparison ("This $10 product beats the $200 one")
- Relatable "I was today years old" moments
- Satisfying demo/unboxing energy

## CRITICAL RULES (MUST FOLLOW STRICTLY)

### 1. COMPLETE POINT & FULL CLOSURE (ABSOLUTE HIGHEST PRIORITY - NEVER CUT OFF MID-POINT):
- **FULL NARRATIVE ARC**: Every clip MUST be 100% self-contained and deliver a full thought from start to finish: `[Hook / Problem Opening] -> [Product Solution / Core Argument] -> [Full Conclusion / Takeaway / CTA]`.
- **NO PREMATURE CUTOFF**: NEVER end a clip while the speaker is still explaining the solution, in the middle of a sentence, or before the final conclusion is delivered. The audience must get the full payoff.
- **NO HANGING CONJUNCTIONS**: NEVER end on connector words or incomplete clauses (e.g. "karena...", "tapi...", "dan akhirnya...", "artinya...", "jadi...", "makanya...").
- **DURATION IS FLEXIBLE FOR COMPLETENESS**: Target duration is typically 60 - 150 seconds (up to 180 seconds for deep explanations). **NEVER sacrifice the completeness of a point just to keep the duration under 90 seconds**. A clip that cuts off mid-point has ZERO conversion value. Extend `end` until the point finishes completely.
- **EXACT TRANSCRIPT TIMESTAMPS**:
  * Set `start` (in seconds, e.g. 15.0) matching the start timestamp `[HH:MM:SS.mmm --> ...]` of the opening sentence.
  * Set `end` (in seconds, e.g. 112.5) matching the end timestamp `[... --> HH:MM:SS.mmm]` of the concluding sentence.

### 2. HOOK & FLOW:
- The first 2-3 seconds MUST contain a strong hook (question, bold claim, or pattern interrupt). Never start on filler words ("um", "jadi gini") or mid-sentence.
- Segments MUST NOT overlap.
- If possible, include the CTA/product mention within the segment. If the CTA is nearby, extend the segment to include it.
- `viral_score` ranges from 0-100. Score based on: hook strength (30%), sales potential (40%), emotional impact (15%), shareability (15%).
- SCORING CALIBRATION:
  * Skor adalah RELATIVE RANKING antar kandidat di transkrip ini, bukan skor absolut.
  * Tidak boleh ada dua klip dengan selisih < 3 poin.
  * 90+ HANYA untuk segmen yang secara objektif luar biasa (hook kuat + emosi tinggi + quotable). Klip rata-rata harus di 60-75.

### 2b. RETENTION ENGINEERING:
- Prefer durasi 45-80 detik. Hanya gunakan 90-150s jika arc-nya benar-benar padat tanpa bagian lambat.
- Buang filler, jeda diam, dan pengulangan dari segmen — mulai tepat sebelum hook, akhiri tepat setelah payoff.
- Utamakan segmen dengan "open loop" di tengah (cerita yang payoff-nya ditunda) agar penonton menonton sampai habis.
- Ending ideal: punchline/takeaway yang terasa menyambung kembali ke pembukaan (rewatch/loop-friendly).

### 2c. TITLE OPTIONS (HOOK OVERLAY):
- title_options[0] (angle paling curiosity) akan dipakai sebagai teks overlay di 3 detik pertama video:
  * Maksimal 8 kata, ada angka atau spesifik (contoh: "3 kesalahan...", "Rp50 ribu...", "90% orang...").
  * Tidak boleh clickbait palsu — janjinya harus terbayar dalam klip.

### 3. CAPTION GUIDELINES (100% HUMAN CREATOR TONE, NO AI VIBES):
- Write like an authentic Indonesian TikTok / Reels affiliate creator. Use natural, conversational colloquial Indonesian (lu-gue/gw/lo/aja/nih/banget/kan/worth it).
- Length: 1-2 punchy, concise sentences (max 100-120 chars). Maximum 1 emoji (e.g. 😭, 🤯, 🔥).
- TIKTOK SEO: Sisipkan 1-2 keyword pencarian yang orang Indonesia ketik di search (contoh: "cara", "tips", "review", "alasan kenapa", nama produk) secara NATURAL dalam 40-50 karakter pertama caption. Kalimat pembuka caption = kalimat yang terlihat sebelum "...selengkapnya" di feed.
- SHOP CTA: Jika produk tersedia di TikTok Shop, akhiri caption dengan CTA belanja natural seperti "ada di keranjang kuning 🛒" atau "cek keranjang kuning sebelum kehabisan". Maksimal 1 CTA per caption, jangan menagih.
- ANGKA = HOOK KUAT: Jika ada promo/diskon/harga yang disebut di segmen, masukkan angkanya di caption (contoh: "cuma Rp50 ribu").
- ABSOLUTE PROHIBITION - NEVER END WITH A QUESTION: Do NOT end with questions or engagement bait like "Gimana menurut kalian?", "Setuju gak?", "Pernah ngalamin?", "Coba komen di bawah!", "Ada yang relate?". The caption MUST end with a strong, definitive statement, benefit takeaway, or relatable insight.
- FORBIDDEN BANNED AI WORDS: "Apakah kamu", "Ini dia", "Pernahkah Anda", "Yuk simak", "Tonton sampai habis", "Tahukah kamu", "Fakta menarik", "Jangan lewatkan", "Simak penjelasannya".
- GOOD EXAMPLES:
  * "Review jujur headset Rp50 ribu ini, buat meeting online aman banget, ada di keranjang kuning 🛒"
  * "Nyesel baru tau barang ini sekarang, beneran ngebantu banget pas kerjaan numpuk 😭"
  * "Solusi paling masuk akal buat yang pengen rapi tanpa harus keluar modal jutaan."
- HASHTAG STRATEGY (untuk distribusi akun kecil/baru):
  * Maksimal 1 tag broad (contoh: #fyp). JANGAN pakai #viral, #trending, #beranda, #foryou.
  * 2-3 tag NICHE spesifik yang mendeskripsikan TOPIK PERSIS klip ini (contoh: #reviewgadget, #headsetmurah, #tipsshop).
  * 1-2 tag komunitas medium (pemirsa aktif, kompetisi rendah).
  * 1 tag nama produk/brand jika disebut di transkrip (contoh: #namaproduk).
  * Total 4-5 tag. Tag harus membantu algoritma MENGKATEGORIKAN video, bukan sekadar ngejar traffic.

## RESPONSE FORMAT (ONLY valid JSON, no explanation, no markdown)

{{
  "clips": [
    {{
      "start": 15.0,
      "end": 82.5,
      "type": "affiliate|viral|hybrid",
      "title": "Short catchy title (max 60 chars)",
      "title_options": ["Title 1", "Title 2", "Title 3"],
      "reason": "Why this converts — which sales psychology triggers are present",
      "viral_score": 95,
      "sales_score": 88,
      "caption": "Review jujur headset Rp50 ribu ini, buat meeting online aman banget, ada di keranjang kuning 🛒",
      "hashtags": ["#fyp", "#reviewgadget", "#headsetmurah", "#tipsonline", "#namaproduk"]
    }}
  ]
}}

## TRANSCRIPT
{transcript_text}
"""
    else:
        prompt = f"""You are an elite viral content strategist with deep expertise in SHORT-FORM VIDEO VIRALITY MECHANICS for TikTok, YouTube Shorts, and Instagram Reels. You understand algorithmic reach, audience psychology, and content hooks at a professional level.

## YOUR MISSION
Analyze the transcript below and extract exactly {num_clips} segments with the ABSOLUTE HIGHEST VIRAL POTENTIAL. These clips must be engineered to maximize watch time, engagement, and shares.

## TRANSCRIPT FORMAT
Each line: [HH:MM:SS.mmm --> HH:MM:SS.mmm] spoken text

## VIRAL DETECTION FRAMEWORK (Score each segment against these):

### Tier 1 — Immediate Hook Power (Most Important):
1. **Curiosity Gap** — Opens a loop the viewer MUST see closed ("You won't believe what happened next")
2. **Pattern Interrupt** — Breaks expectations with a shocking statement or reversal
3. **Bold Controversial Claim** — Hot take that forces people to agree, disagree, or share
4. **Direct Challenge** — "Nobody talks about this", "They don't want you to know"

### Tier 2 — Emotional Peak:
5. **High Arousal Emotion** — Anger, surprise, awe, hilarity (NOT boredom, sadness)
6. **Storytelling Climax** — The peak moment of a story arc (not the buildup)
7. **Relatable Truth Bomb** — "This is SO true" moments that demand a tag/share
8. **Inspirational Breakthrough** — Goosebump-inducing motivational peaks

### Tier 3 — Engagement Drivers:
9. **Debate Fuel** — Statements that split opinion 50/50 (goldmine for comments)
10. **Information Density** — Rapid-fire valuable facts/tips (high save rate)
11. **Humor/Wit** — Genuinely funny moments (high share rate)
12. **Quotable Moment** — One-liners people will screenshot or stitch

## CRITICAL RULES (MUST FOLLOW STRICTLY)

### 1. COMPLETE POINT & FULL CLOSURE (ABSOLUTE HIGHEST PRIORITY - NEVER CUT OFF MID-POINT):
- **FULL NARRATIVE ARC & THOUGHT COMPLETION**: Every clip MUST be 100% self-contained and deliver a full thought from start to finish: `[Hook / Intriguing Setup] -> [Core Argument / Story / Insight] -> [Full Conclusion / Punchline / Takeaway]`.
- **NO PREMATURE CUTOFF**: NEVER cut off while the speaker is still in the middle of making a point, explaining a concept, building up an argument, or before delivering the conclusion/takeaway. The audience must get the full payoff and context.
- **NO HANGING CONJUNCTIONS**: NEVER end on connector words or incomplete thoughts (e.g. "karena...", "tapi...", "dan setelah itu...", "artinya...", "jadi kesimpulannya...", "sehingga...").
- **DURATION IS FLEXIBLE FOR COMPLETENESS**: Target duration is typically 60 - 150 seconds (up to 180 seconds for deep analysis, case studies, or storytelling). **NEVER sacrifice the completeness of a point just to keep duration under 90 seconds**. It is 100x better to have a 110s or 140s clip where the point is 100% complete and understandable, than an 80s clip that cuts off abruptly.
- **EXACT TRANSCRIPT TIMESTAMPS**:
  * Set `start` (in seconds as float, e.g. 15.0) matching the start timestamp `[HH:MM:SS.mmm --> ...]` of the opening line.
  * Set `end` (in seconds as float, e.g. 125.4) matching the end timestamp `[... --> HH:MM:SS.mmm]` of the concluding sentence.

### 2. HOOK & FLOW:
- The first 2-3 seconds of each segment MUST contain a strong hook. NEVER start on dead air, filler words ("um", "so anyway", "jadi begini"), or mid-sentence. If the hook starts slightly before your ideal segment, extend backward to capture it cleanly.
- Segments MUST NOT overlap.
- `title_options` should provide 3 distinct angles: (1) curiosity-driven, (2) benefit-driven, (3) controversial/provocative.
- `viral_score` ranges from 0-100. Weight: hook strength (35%), emotional intensity (25%), shareability (20%), comment potential (20%).
- SCORING CALIBRATION:
  * Skor adalah RELATIVE RANKING antar kandidat di transkrip ini, bukan skor absolut.
  * Tidak boleh ada dua klip dengan selisih < 3 poin.
  * 90+ HANYA untuk segmen yang secara objektif luar biasa (hook kuat + emosi tinggi + quotable). Klip rata-rata harus di 60-75.

### 2b. RETENTION ENGINEERING:
- Prefer durasi 45-80 detik. Hanya gunakan 90-150s jika arc-nya benar-benar padat tanpa bagian lambat.
- Buang filler, jeda diam, dan pengulangan dari segmen — mulai tepat sebelum hook, akhiri tepat setelah payoff.
- Utamakan segmen dengan "open loop" di tengah (cerita yang payoff-nya ditunda) agar penonton menonton sampai habis.
- Ending ideal: punchline/takeaway yang terasa menyambung kembali ke pembukaan (rewatch/loop-friendly).

### 2c. TITLE OPTIONS (HOOK OVERLAY):
- title_options[0] (angle paling curiosity) akan dipakai sebagai teks overlay di 3 detik pertama video:
  * Maksimal 8 kata, ada angka atau spesifik (contoh: "3 kesalahan...", "90% orang...", "Alasan kenapa...").
  * Tidak boleh clickbait palsu — janjinya harus terbayar dalam klip.

### 3. CAPTION GUIDELINES (100% HUMAN CREATOR TONE, NO AI VIBES):
- Write like an authentic Indonesian podcast/video clipper posting on TikTok, Shorts, or Instagram Reels. Use natural, everyday colloquial Indonesian (lu-gue/gw/lo/aja/nih/banget/kan/parah/asli).
- Length: 1-2 punchy, concise sentences (max 100-120 chars). Maximum 1 subtle emoji (e.g. 🗿, 💀, 🤯, 🔥) or no emoji.
- TIKTOK SEO: Sisipkan 1-2 keyword pencarian yang orang Indonesia ketik di search (contoh: "alasan kenapa", "cara", "mindset", "psikologi", topik spesifik klip) secara NATURAL dalam 40-50 karakter pertama caption. Kalimat pembuka caption = kalimat yang terlihat sebelum "...selengkapnya" di feed.
- ABSOLUTE PROHIBITION - NEVER END WITH A QUESTION: Do NOT end with questions or engagement bait like "Gimana menurut kalian?", "Setuju gak?", "Pernah ngalamin hal serupa?", "Kalian tim mana nih?", "Coba komen di bawah!", "Ada yang ngerasa gini juga?". The caption MUST end with a strong, definitive statement, hard-hitting observation, or brutal truth takeaway.
- FORBIDDEN BANNED AI WORDS: "Apakah kamu", "Ini dia", "Pernahkah Anda", "Yuk simak", "Tonton sampai habis", "Tahukah kamu", "Fakta menariknya", "Simak baik-baik", "Mari kita bahas", "Jangan lewatkan".
- GOOD EXAMPLES:
  * "Realita pahit kenapa kerja keras doang gak bakal bikin lu kaya kalau polanya salah 🗿"
  * "Mindset kayak gini yang bikin banyak orang stuck bertahun-tahun tanpa sadar."
  * "Alasan kenapa orang yang beneran kompeten justru jarang banyak omong di publik."
  * "Ternyata ini penyebab utama kenapa generasi sekarang gampang banget burnout."
- HASHTAG STRATEGY (untuk distribusi akun kecil/baru):
  * Maksimal 1 tag broad (contoh: #fyp). JANGAN pakai #viral, #trending, #beranda, #foryou.
  * 2-3 tag NICHE spesifik yang mendeskripsikan TOPIK PERSIS klip ini (contoh: #mindsetbisnis, #psikologija, #keuanganpribadi, #caradagang).
  * 1-2 tag komunitas medium (pemirsa aktif, kompetisi rendah).
  * Total 4-5 tag. Tag harus membantu algoritma MENGKATEGORIKAN video, bukan sekadar ngejar traffic.

## RESPONSE FORMAT (ONLY valid JSON, no explanation, no markdown)

{{
  "clips": [
    {{
      "start": 15.0,
      "end": 82.5,
      "title_options": ["Curiosity Title", "Benefit Title", "Controversial Title"],
      "reason": "Which viral triggers from the framework are present and why this will go viral",
      "viral_score": 95,
      "caption": "Realita pahit kenapa kerja keras doang gak bakal bikin lu kaya kalau polanya salah 🗿",
      "hashtags": ["#fyp", "#mindsetbisnis", "#psikologija", "#keuanganpribadi"]
    }}
  ]
}}

## TRANSCRIPT
{transcript_text}
"""
    return prompt

# ── LLM fallback pool ──
# Models tried in order after the configured primary model fails. These are
# verified available on the tiprouter.my.id gateway (see GET /v1/models for
# the authoritative list for the current API key). Override with the
# ROUTER_FALLBACK_MODELS env var (comma-separated).
DEFAULT_FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "deepseek-v4.1-flash",
    "mimo-v2.6.flash",
]

# Auth errors mean the gateway rejects the credential itself: every model on
# that gateway will fail identically, so the whole fallback chain is aborted.
_AUTH_MARKERS = (
    "invalid api key",
    "incorrect api key",
    "invalid_api_key",
    "unauthorized",
    "authentication_error",
)

# Errors that mean "this model/request will never succeed" -> skip immediately.
# 400 location-restricted, 401/403 auth, 404 no credentials/model, 413 payload
# too large for this model's token budget.
_PERMANENT_STATUS = {400, 401, 403, 404, 413, 422}
_PERMANENT_MARKERS = (
    "user location is not supported",
    "no active credentials",
    "missing api key",
    "invalid api key",
    "request too large",
    "tokens per minute",
    "context length",
    "maximum context",
    "does not exist",
)

# Errors where shrinking the transcript may let the same model succeed.
_OVERSIZE_MARKERS = (
    "request too large",
    "tokens per minute",
    "payload too large",
    "context length",
    "maximum context",
    "reduce your message size",
)


def _is_permanent_llm_error(status_code, err_text=""):
    """True when retrying this model with the same payload cannot succeed."""
    text = (err_text or "").lower()
    if any(marker in text for marker in _PERMANENT_MARKERS):
        return True
    return status_code in _PERMANENT_STATUS


def _is_oversize_error(status_code, err_text=""):
    """True when the request was rejected purely for being too large."""
    text = (err_text or "").lower()
    if status_code == 413:
        return True
    return any(marker in text for marker in _OVERSIZE_MARKERS)


def _is_auth_error(status_code, err_text=""):
    """True when the gateway rejected the API key itself (not the model).

    Sending the same credential to the next model in the chain is pointless and
    may trigger rate-limit/IP bans, so the caller aborts the whole chain.
    Note: a bare 403 is NOT treated as auth-only here because gateways also use
    it for "no credentials for THIS provider", which the next model may avoid.
    """
    text = (err_text or "").lower()
    if any(marker in text for marker in _AUTH_MARKERS):
        return True
    return status_code == 401

def get_fallback_models(primary=None):
    """Resolve the ordered fallback model list (env override or defaults)."""
    raw = (os.environ.get("ROUTER_FALLBACK_MODELS") or "").strip()
    pool = [m.strip() for m in raw.split(",") if m.strip()] if raw else list(DEFAULT_FALLBACK_MODELS)
    return [m for m in pool if m and m != primary]


def call_llm_api(prompt, model_name, endpoint, api_key, job_id=None, compact_prompt=None):
    if not (endpoint or "").strip():
        raise PermanentLLMError("ROUTER_API_ENDPOINT kosong. Isi endpoint AI di Pengaturan Studio.")
    if not (api_key or "").strip():
        raise PermanentLLMError("ROUTER_API_KEY kosong. Isi API key AI di Pengaturan Studio.")

    if not endpoint.rstrip('/').endswith('/chat/completions'):
        endpoint = endpoint.rstrip('/') + '/chat/completions'
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Never send an empty model name: the gateway would answer with an opaque
    # auth/validation error that hides the real configuration problem.
    candidate_models = []
    for m in [model_name] + list(get_fallback_models(primary=model_name)):
        name = (m or "").strip()
        if name and name not in candidate_models:
            candidate_models.append(name)
    if not candidate_models:
        raise PermanentLLMError("ROUTER_LLM_MODEL kosong. Pilih model AI di Pengaturan Studio.")

    last_error = None
    permanent_only = True
    for m in candidate_models:
        active_prompt = prompt
        tried_compact = False
        while True:
            payload = {
                "model": m,
                "messages": [{"role": "user", "content": active_prompt}],
                "stream": False,
                "temperature": env_float("ROUTER_LLM_TEMPERATURE", 0.4),
            }

            log(f"Sending transcript to '{m}' via {endpoint} for analysis...", job_id=job_id)
            status_code = None
            try:
                # Per-request timeout (seconds). A hung/slow model must fail over
                # to the fallback chain quickly instead of blocking for minutes.
                req_timeout = env_int("ROUTER_LLM_TIMEOUT", 180)
                response = requests.post(endpoint, json=payload, headers=headers, timeout=req_timeout)
                status_code = response.status_code
                if response.status_code != 200:
                    err_msg = ""
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error", {}).get("message", "") or json.dumps(err_json)
                    except Exception:
                        err_msg = response.text[:500]
                    log(f"LLM API Error with '{m}' [{response.status_code}]: {err_msg}", job_id=job_id)
                    # The API key is rejected: every model on this gateway will
                    # fail the same way, so stop the chain immediately.
                    if _is_auth_error(response.status_code, err_msg):
                        raise PermanentLLMError(
                            f"API key ditolak oleh gateway ({response.status_code}): {err_msg or 'Invalid API key'}. "
                            f"Periksa ROUTER_API_KEY / ROUTER_API_ENDPOINT di Pengaturan Studio."
                        )
                    if not _is_permanent_llm_error(response.status_code, err_msg):
                        permanent_only = False
                    # Payload too big: retry the SAME model once with a compact transcript.
                    if (
                        compact_prompt
                        and not tried_compact
                        and _is_oversize_error(response.status_code, err_msg)
                    ):
                        tried_compact = True
                        active_prompt = compact_prompt
                        log(f"Model '{m}': payload terlalu besar, mencoba ulang dengan transkrip terkompresi...", job_id=job_id)
                        continue
                    response.raise_for_status()

                # Handle standard JSON or SSE chunked formats
                resp_text = response.text.strip()
                if resp_text.startswith("data:"):
                    collected = []
                    for line in resp_text.splitlines():
                        line = line.strip()
                        if line.startswith("data:") and not line.endswith("[DONE]"):
                            raw = line[5:].strip()
                            try:
                                chunk = json.loads(raw)
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    collected.append(delta)
                            except Exception:
                                pass
                    if collected:
                        return "".join(collected)

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content
                log(f"Unexpected response shape from LLM endpoint with '{m}': {json.dumps(data)[:500]}", job_id=job_id)
                permanent_only = False
                break
            except PermanentLLMError:
                # Credential rejected - no other model on this gateway can help.
                raise
            except Exception as e:
                last_error = e
                err_text = ""
                try:
                    err_text = e.response.text[:500] if getattr(e, "response", None) is not None else str(e)
                except Exception:
                    err_text = str(e)
                code = status_code if status_code is not None else getattr(getattr(e, "response", None), "status_code", None)
                if _is_auth_error(code, err_text):
                    raise PermanentLLMError(
                        f"API key ditolak oleh gateway ({code}): {err_text[:200] or 'Invalid API key'}. "
                        f"Periksa ROUTER_API_KEY / ROUTER_API_ENDPOINT di Pengaturan Studio."
                    ) from e
                if not _is_permanent_llm_error(code, err_text):
                    permanent_only = False
                # Retry same model with compact transcript if we haven't yet.
                if compact_prompt and not tried_compact and _is_oversize_error(code, err_text):
                    tried_compact = True
                    active_prompt = compact_prompt
                    log(f"Model '{m}': payload terlalu besar, mencoba ulang dengan transkrip terkompresi...", job_id=job_id)
                    continue
                if m != candidate_models[-1]:
                    log(f"Model '{m}' gagal ({e}), otomatis beralih ke model fallback berikutnya...", job_id=job_id)
                break

    if last_error:
        if permanent_only:
            raise PermanentLLMError(str(last_error)) from last_error
        raise last_error
    return ""

def extract_json_block(raw_text, job_id=None):
    text = raw_text.strip()
    
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx+1]
            
    text = re.sub(r',\s*([\]}])', r'\1', text)
        
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        log("Failed to parse LLM output as JSON:\n" + text, job_id=job_id)
        raise RuntimeError("LLM did not return valid JSON.") from e

# ═══════════════════════════════════════════════════════════════════════════
# TWO-PASS VIRAL SELECTION
# Pass 1 (LLM): discover a POOL of candidate moments with relative scores.
# Pass 1.5 (code): greedily pick top-N with time + topic diversity guards.
# Pass 2 (LLM): enrich only the SELECTED clips with caption/hashtags/titles.
# This fixes the single-pass flaw where the model is forced to output exactly
# N clips in one shot — producing filler clips and same-idea duplicates.
# ═══════════════════════════════════════════════════════════════════════════

# Filler openers that must never be the first spoken line of a clip.
_FILLER_OPENERS = (
    "jadi gini", "jadi begini", "nah", "um", "uh", "eh", "anu",
    "so anyway", "well", "okay jadi",
)

# Hanging conjunctions a clip must never end on.
_HANGING_ENDINGS = (
    "karena", "tapi", "dan", "lalu", "kemudian", "sehingga", "artinya",
    "jadi", "makanya", "yang", "di", "ke", "dengan", "untuk", "agar",
    "supaya", "kalau", "jika", "when", "because", "so", "and", "then",
)


def _token_set(text):
    """Lowercased alphanumeric tokens, for rough topic-similarity checks."""
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _jaccard(a, b):
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def build_transcript_slice(segments, start, end, pad_sec=3.0):
    """Transcript lines overlapping [start-pad, end+pad], for enrichment context."""
    lines = []
    lo, hi = float(start) - pad_sec, float(end) + pad_sec
    for seg in segments or []:
        try:
            s, e = float(seg["start"]), float(seg["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if e >= lo and s <= hi:
            mm_s, ss_s = divmod(int(s), 60)
            hh_s, mm_s = divmod(mm_s, 60)
            mm_e, ss_e = divmod(int(e), 60)
            hh_e, mm_e = divmod(mm_e, 60)
            lines.append(
                f"[{hh_s:02d}:{mm_s:02d}:{ss_s:02d} --> {hh_e:02d}:{mm_e:02d}:{ss_e:02d}] "
                f"{(seg.get('text') or '').strip()}"
            )
    return "\n".join(lines)


def select_diverse_clips(candidates, num_clips=5, min_gap_sec=60.0, diversity_threshold=0.55):
    """Greedy diversity-aware pick from scored candidates.

    Walks candidates from highest viral_score down and keeps a candidate only
    when it (a) does not overlap / sit too close to an already-picked clip and
    (b) is not about the same topic as an already-picked clip (Jaccard over
    title + topic_label tokens).

    Returns the picked dicts in pick order with an added 1-based "index".
    May return FEWER than num_clips — that is intentional: no filler clips.
    """
    scored = []
    for c in candidates or []:
        if not isinstance(c, dict):
            continue
        try:
            s, e = float(c.get("start", 0)), float(c.get("end", 0))
        except (TypeError, ValueError):
            continue
        if e <= s:
            continue
        try:
            score = float(c.get("viral_score", 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        scored.append((score, s, e, c))
    scored.sort(key=lambda t: t[0], reverse=True)

    try:
        min_gap = float(min_gap_sec)
    except (TypeError, ValueError):
        min_gap = 60.0
    try:
        div_thr = float(diversity_threshold)
    except (TypeError, ValueError):
        div_thr = 0.55

    selected = []
    for score, s, e, c in scored:
        if len(selected) >= num_clips:
            break
        # ── time guard: reject overlap AND near-duplicate placement ──
        if any(not (e + min_gap <= ps or s >= pe + min_gap) for _, ps, pe, _ in selected):
            continue
        # ── topic guard: reject same-idea duplicates ──
        text = f"{c.get('title', '')} {c.get('topic_label', '')}"
        if any(
            _jaccard(text, f"{o.get('title', '')} {o.get('topic_label', '')}") >= div_thr
            for _, _, _, o in selected
        ):
            continue
        selected.append((score, s, e, c))

    out = []
    for i, (score, s, e, c) in enumerate(selected, 1):
        d = dict(c)
        d["index"] = i
        out.append(d)
    return out

def build_candidate_discovery_prompt(transcript_text, max_candidates=15, mode="hook"):
    """Pass 1 of two-pass selection: discover a POOL of candidate moments.

    The model acts as a SCOUT: find up to `max_candidates` moments with the
    highest viral potential and score them RELATIVELY. A later deterministic
    step picks the final clips with diversity guards. Quality over quota —
    if the transcript only has 6 great moments, return 6.
    """
    if mode == "affiliate":
        trigger_section = """### Sales Psychology Triggers (tag 1-3 per candidate):
- pain_point — relatable problem/frustration
- solution_reveal — "aha moment", product introduced as the fix
- social_proof — testimonials, user count, reviews, endorsements
- before_after — clear transformation contrast
- urgency — limited time/stock pressure
- price_anchor — vs expensive alternatives
- cta — "link in bio", "use my code"
- storytelling — personal anecdote building trust/desire
### Virality Boosters (bonus):
controversial product opinion, unexpected comparison, "I was today years old" moments"""
        mission = "discover candidate segments with the highest AFFILIATE SALES + VIRAL potential"
    else:
        trigger_section = """### Tier 1 — Hook Power (most important):
- curiosity_gap — opens a loop the viewer MUST see closed
- pattern_interrupt — shocking statement / expectation reversal
- controversial_claim — hot take forcing agree/disagree/share
- direct_challenge — "nobody talks about this"
### Tier 2 — Emotional Peak:
- high_arousal — anger, surprise, awe (NOT boredom/sadness)
- story_climax — peak of a story arc, not the buildup
- truth_bomb — "this is SO true" tag-a-friend moments
- breakthrough — goosebump motivational peaks
### Tier 3 — Engagement Drivers:
- debate_fuel — splits opinion 50/50 (comment goldmine)
- info_dense — rapid-fire valuable facts (high saves)
- humor — genuinely funny (high shares)
- quotable — one-liners people screenshot/stitch"""
        mission = "discover candidate segments with the highest VIRAL potential"

    return f"""You are an elite viral content strategist for short-form video (TikTok, YouTube Shorts, Instagram Reels).

## YOUR MISSION
Analyze the transcript below and {mission}. You are a SCOUT, not the final editor: return UP TO {max_candidates} candidates ranked by viral_score. A later step picks the final clips and enforces topic diversity — so find MORE strong moments than needed, each centered on a DIFFERENT idea. Quality over quota: if only 6 moments are truly great, return 6.

## TRANSCRIPT FORMAT
Each line: [HH:MM:SS.mmm --> HH:MM:SS.mmm] spoken text

## VIRAL DETECTION FRAMEWORK
{trigger_section}

## CANDIDATE RULES (MUST FOLLOW STRICTLY)
1. SELF-CONTAINED ARC: every candidate MUST deliver a full thought: [Hook] -> [Core argument] -> [Conclusion/punchline]. NEVER cut mid-point. NEVER end on hanging conjunctions (karena..., tapi..., jadi..., artinya...).
2. HOOK FIRST: the first 2-3 seconds MUST contain the hook. NEVER start on filler ("um", "jadi gini", "nah", "so anyway") or mid-sentence. If the hook starts slightly before the ideal segment, extend backward to capture it cleanly.
3. DURATION: prefer 25-60 seconds. Go longer ONLY if every ~10 seconds has a payoff (no slow stretches). A tight 35s clip beats a rambling 90s one — completion rate is king.
4. DISTINCT IDEAS: candidates may sit near each other in time, but each MUST center on a DIFFERENT idea. Do NOT return 3 candidates making the same point with different words.
5. topic_label: 2-5 words naming the SPECIFIC idea (e.g. "tanggung jawab hidup", "gengsi vs kaya"). Used later for diversity filtering — make it precise, not generic.
6. trigger_tags: 1-3 tags from the framework above that are actually present.
7. SCORING (relative ranking within THIS transcript):
   - viral_score 0-100. No two candidates may differ by < 3 points.
   - 90+ ONLY for objectively exceptional (strong hook + high emotion + quotable).
   - Average candidates: 60-75.
8. EXACT TIMESTAMPS: start/end as seconds (float) matching the transcript line timestamps of the opening and concluding sentences.

## RESPONSE FORMAT (ONLY valid JSON, no explanation, no markdown)
{{
  "video_summary": "2-3 sentences: what the video is about, who is speaking, main themes",
  "candidates": [
    {{
      "start": 15.0,
      "end": 52.5,
      "title": "Short catchy title (max 60 chars)",
      "topic_label": "tanggung jawab hidup",
      "trigger_tags": ["controversial_claim", "debate_fuel"],
      "reason": "Which triggers are present and why this can go viral",
      "viral_score": 92
    }}
  ]
}}

## TRANSCRIPT
{transcript_text}
"""

def build_clip_enrichment_prompt(clips_with_slices, video_summary="", mode="hook"):
    """Pass 2 of two-pass selection: write titles/captions/hashtags.

    `clips_with_slices`: list of dicts with keys:
        index, start, end, title, transcript (slice text of the clip).
    Returns a prompt asking for exactly one enrichment entry per clip,
    in the same order. Only the SELECTED clips are enriched — never waste
    tokens writing captions for rejected candidates.
    """
    if mode == "affiliate":
        cta_rule = (
            '- SHOP CTA: jika produk tersedia di TikTok Shop, akhiri caption dengan CTA belanja natural '
            'seperti "ada di keranjang kuning" (maks 1 emoji 🛒). Maksimal 1 CTA per caption.\n'
        )
        hashtag_rule = (
            "* Maksimal 1 tag broad (contoh: #fyp). JANGAN pakai #viral, #trending, #beranda, #foryou.\n"
            "  * 2-3 tag NICHE spesifik yang mendeskripsikan TOPIK PERSIS klip ini (contoh: #reviewgadget, #headsetmurah).\n"
            "  * 1-2 tag komunitas medium (pemirsa aktif, kompetisi rendah).\n"
            "  * 1 tag nama produk/brand jika disebut.\n"
            "  * Total 4-5 tag. Tag harus membantu algoritma MENGKATEGORIKAN video."
        )
        tone = "an authentic Indonesian TikTok affiliate creator"
        good_examples = (
            '  * "Review jujur headset Rp50 ribu ini, buat meeting online aman banget, ada di keranjang kuning"\n'
            '  * "Nyesel baru tau barang ini sekarang, beneran ngebantu banget pas kerjaan numpuk"\n'
            '  * "Solusi paling masuk akal buat yang pengen rapi tanpa harus keluar modal jutaan."'
        )
    else:
        cta_rule = ""
        hashtag_rule = (
            "* Maksimal 1 tag broad (contoh: #fyp). JANGAN pakai #viral, #trending, #beranda, #foryou.\n"
            "  * 2-3 tag NICHE spesifik yang mendeskripsikan TOPIK PERSIS klip ini (contoh: #mindsetbisnis, #psikologija, #keuanganpribadi).\n"
            "  * 1-2 tag komunitas medium (pemirsa aktif, kompetisi rendah).\n"
            "  * Total 4-5 tag. Tag harus membantu algoritma MENGKATEGORIKAN video."
        )
        tone = "an authentic Indonesian podcast/video clipper posting on TikTok"
        good_examples = (
            '  * "Realita pahit kenapa kerja keras doang gak bakal bikin lu kaya kalau polanya salah"\n'
            '  * "Mindset kayak gini yang bikin banyak orang stuck bertahun-tahun tanpa sadar."\n'
            '  * "Alasan kenapa orang yang beneran kompeten justru jarang banyak omong di publik."'
        )

    blocks = []
    for c in clips_with_slices or []:
        blocks.append(
            f"### Clip {c.get('index')} [{c.get('start')}s --> {c.get('end')}s] "
            f"(working title: {c.get('title', '')})\n{(c.get('transcript') or '').strip()}"
        )
    clips_block = "\n\n".join(blocks) if blocks else "(no clips)"

    return f"""You are an elite short-form copywriter. Write like {tone}. Use natural, everyday colloquial Indonesian (lu-gue/gw/lo/aja/nih/banget/kan/parah/asli).

## YOUR MISSION
For EACH clip below, write 3 title_options (hook overlay text), 1 caption, and hashtags. These clips were already selected as the strongest moments — your job is packaging, not selection.

## VIDEO SUMMARY (context)
{video_summary or "(not provided)"}

## CLIPS
{clips_block}

## TITLE OPTIONS (hook overlay, shown in the first 3 seconds of the video)
- title_options[0]: curiosity angle — max 8 kata, ada angka atau spesifik (contoh: "3 kesalahan...", "90% orang...", "Rp50 ribu..."). Tidak boleh clickbait palsu: janjinya HARUS terbayar dalam klip.
- title_options[1]: benefit angle.
- title_options[2]: controversial/provocative angle.

## CAPTION RULES (100% HUMAN CREATOR TONE, NO AI VIBES)
- 1-2 kalimat punchy (max 100-120 chars). Maksimal 1 emoji.
- TIKTOK SEO: sisipkan 1-2 keyword pencarian secara NATURAL dalam 40-50 karakter pertama (kalimat pembuka = yang terlihat sebelum "...selengkapnya").
- NEVER END WITH A QUESTION: do NOT end with engagement bait ("Gimana menurut kalian?", "Setuju gak?", "Coba komen di bawah!"). End with a strong definitive statement, benefit takeaway, or hard-hitting observation.
- FORBIDDEN AI WORDS: "Apakah kamu", "Ini dia", "Pernahkah Anda", "Yuk simak", "Tonton sampai habis", "Tahukah kamu", "Fakta menarik", "Jangan lewatkan", "Simak penjelasannya".
{cta_rule}- GOOD EXAMPLES:
{good_examples}

## HASHTAG STRATEGY (for small/new accounts)
{hashtag_rule}

## RESPONSE FORMAT (ONLY valid JSON, no explanation, no markdown)
{{
  "clips": [
    {{
      "index": 1,
      "title_options": ["Curiosity Title", "Benefit Title", "Controversial Title"],
      "caption": "Realita pahit kenapa kerja keras doang gak bakal bikin lu kaya kalau polanya salah",
      "hashtags": ["#fyp", "#mindsetbisnis", "#psikologija", "#keuanganpribadi"]
    }}
  ]
}}
Return EXACTLY one entry per input clip, in the same order, with matching "index" values.
"""
