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

### 3. CAPTION GUIDELINES (100% HUMAN CREATOR TONE, NO AI VIBES):
- Write like an authentic Indonesian TikTok / Reels affiliate creator. Use natural, conversational colloquial Indonesian (lu-gue/gw/lo/aja/nih/banget/kan/worth it).
- Length: 1-2 punchy, concise sentences (max 100-120 chars). Maximum 1 emoji (e.g. 😭, 🤯, 🔥).
- ABSOLUTE PROHIBITION - NEVER END WITH A QUESTION: Do NOT end with questions or engagement bait like "Gimana menurut kalian?", "Setuju gak?", "Pernah ngalamin?", "Coba komen di bawah!", "Ada yang relate?". The caption MUST end with a strong, definitive statement, benefit takeaway, or relatable insight.
- FORBIDDEN BANNED AI WORDS: "Apakah kamu", "Ini dia", "Pernahkah Anda", "Yuk simak", "Tonton sampai habis", "Tahukah kamu", "Fakta menarik", "Jangan lewatkan", "Simak penjelasannya".
- GOOD EXAMPLES:
  * "Nyesel baru tau barang ini sekarang, beneran ngebantu banget pas kerjaan numpuk 😭"
  * "Solusi paling masuk akal buat yang pengen rapi tanpa harus keluar modal jutaan."
  * "Ternyata ini alasan kenapa barang murah gini bisa laku ratusan ribu pcs."
- HASHTAGS: Provide EXACTLY 4 to 5 HIGH-TRAFFIC, targeted Indonesian viral hashtags with '#' prefix directly matching the product and niche (e.g. ["#fyp", "#racuntiktok", "#gadget", "#rekomendasi", "#trending"]). DO NOT output more than 5 hashtags.

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
      "caption": "Nyesel baru tau barang ini sekarang, beneran ngebantu pas kerjaan numpuk 😭",
      "hashtags": ["#fyp", "#racuntiktok", "#gadget", "#rekomendasi", "#trending"]
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

### 3. CAPTION GUIDELINES (100% HUMAN CREATOR TONE, NO AI VIBES):
- Write like an authentic Indonesian podcast/video clipper posting on TikTok, Shorts, or Instagram Reels. Use natural, everyday colloquial Indonesian (lu-gue/gw/lo/aja/nih/banget/kan/parah/asli).
- Length: 1-2 punchy, concise sentences (max 100-120 chars). Maximum 1 subtle emoji (e.g. 🗿, 💀, 🤯, 🔥) or no emoji.
- ABSOLUTE PROHIBITION - NEVER END WITH A QUESTION: Do NOT end with questions or engagement bait like "Gimana menurut kalian?", "Setuju gak?", "Pernah ngalamin hal serupa?", "Kalian tim mana nih?", "Coba komen di bawah!", "Ada yang ngerasa gini juga?". The caption MUST end with a strong, definitive statement, hard-hitting observation, or brutal truth takeaway.
- FORBIDDEN BANNED AI WORDS: "Apakah kamu", "Ini dia", "Pernahkah Anda", "Yuk simak", "Tonton sampai habis", "Tahukah kamu", "Fakta menariknya", "Simak baik-baik", "Mari kita bahas", "Jangan lewatkan".
- GOOD EXAMPLES:
  * "Realita pahit kenapa kerja keras doang gak bakal bikin lu kaya kalau polanya salah 🗿"
  * "Mindset kayak gini yang bikin banyak orang stuck bertahun-tahun tanpa sadar."
  * "Alasan kenapa orang yang beneran kompeten justru jarang banyak omong di publik."
  * "Ternyata ini penyebab utama kenapa generasi sekarang gampang banget burnout."
- HASHTAGS: Provide EXACTLY 4 to 5 HIGH-TRAFFIC, targeted Indonesian viral hashtags with '#' prefix directly matching the video topic (e.g. ["#fyp", "#mindset", "#bisnis", "#edukasi", "#beranda"]). DO NOT output more than 5 hashtags.

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
      "hashtags": ["#fyp", "#mindset", "#bisnis", "#edukasi", "#beranda"]
    }}
  ]
}}

## TRANSCRIPT
{transcript_text}
"""
    return prompt

# ── LLM fallback pool ──
# Models tried in order after the configured primary model fails. These are
# verified to work on the default 9Router/kamodev gateway. Override with the
# ROUTER_FALLBACK_MODELS env var (comma-separated).
DEFAULT_FALLBACK_MODELS = [
    "tip/gemini-3.8-flash",
    "freemax",
    "tip/mimo-v2.6.flash",
]

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


def get_fallback_models(primary=None):
    """Resolve the ordered fallback model list (env override or defaults)."""
    raw = (os.environ.get("ROUTER_FALLBACK_MODELS") or "").strip()
    pool = [m.strip() for m in raw.split(",") if m.strip()] if raw else list(DEFAULT_FALLBACK_MODELS)
    return [m for m in pool if m and m != primary]


def call_llm_api(prompt, model_name, endpoint, api_key, job_id=None, compact_prompt=None):
    if not endpoint.rstrip('/').endswith('/chat/completions'):
        endpoint = endpoint.rstrip('/') + '/chat/completions'
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    candidate_models = [model_name]
    for fb in get_fallback_models(primary=model_name):
        if fb not in candidate_models:
            candidate_models.append(fb)

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
                "temperature": 0.7,
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
            except Exception as e:
                last_error = e
                err_text = ""
                try:
                    err_text = e.response.text[:500] if getattr(e, "response", None) is not None else str(e)
                except Exception:
                    err_text = str(e)
                code = status_code if status_code is not None else getattr(getattr(e, "response", None), "status_code", None)
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
