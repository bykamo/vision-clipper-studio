import json
import re
import requests
from backend.utils import log

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

## STRICT RULES
- DURATION STRATEGY (CRITICAL):
  1. Gold Standard (60 - 90 seconds): This is the primary target for TikTok Creator Rewards. Must be >60 seconds.
  2. Mid-Form Highlights (120 - 180 seconds): Use this ONLY IF the topic is extremely engaging and cannot be cut (e.g., deep analysis, case studies, storytelling, horror/conspiracies that need atmosphere building).
- PRIORITIZE NATURAL FLOW: You MUST ensure the segment starts and ends naturally without cutting off mid-sentence or mid-thought, even if it slightly violates the duration targets.
- Segments MUST NOT overlap.
- Segments MUST start with a strong hook (question, bold claim, or pattern interrupt) — NEVER start mid-sentence or on dead air.
- END segments on a natural pause, complete thought, or conclusion. DO NOT cut off the speaker abruptly.
- If possible, include the CTA/product mention within the segment. If the CTA is nearby but outside the segment, extend it.
- The `title_hook` is a 1-3 word BOLD text shown in the first second of the video (think: "STOP BUYING THIS", "GAME CHANGER", "$9 VS $200"). It must create immediate curiosity or shock.
- `viral_score` ranges from 0-100. Score based on: hook strength (30%), sales potential (40%), emotional impact (15%), shareability (15%).
- `caption` must be written as a real TikTok creator would post, in a highly casual and everyday Indonesian slang/style (using lu-gue/casual colloquial Indonesian, to-the-point). Do NOT use rigid, AI-looking template phrases (avoid things like "Apakah kamu...", "Ini dia...", "Pernahkah Anda..."). Limit emojis to a maximum of 1-2. Include a strong hook sentence, value proposition, and CTA.
- `hashtags`: Provide EXACTLY 4 to 5 HIGH-TRAFFIC, PROVEN Indonesian viral hashtags directly matching the video product and niche (e.g. ["#fyp", "#racuntiktok", "#bisnis", "#edukasi", "#trending"]). DO NOT output more than 5 hashtags.

## RESPONSE FORMAT (ONLY valid JSON, no explanation, no markdown)

{{
  "clips": [
    {{
      "start": 12.5,
      "end": 45.0,
      "type": "affiliate|viral|hybrid",
      "title": "Short catchy title (max 60 chars)",
      "title_options": ["Title 1", "Title 2", "Title 3"],
      "title_hook": "1-3 word bold hook text for first second",
      "reason": "Why this converts — which sales psychology triggers are present",
      "viral_score": 95,
      "sales_score": 88,
      "caption": "Hook sentence + value + CTA + emojis for TikTok caption",
      "hashtags": ["#fyp", "#racuntiktok", "#bisnis", "#edukasi", "#trending"]
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

## STRICT RULES
- DURATION STRATEGY (CRITICAL):
  1. Gold Standard (60 - 90 seconds): This is the primary target for TikTok Creator Rewards. Must be >60 seconds.
  2. Mid-Form Highlights (120 - 180 seconds): Use this ONLY IF the topic is extremely engaging and cannot be cut (e.g., deep analysis, case studies, storytelling, horror/conspiracies that need atmosphere building).
- PRIORITIZE NATURAL FLOW: You MUST ensure the segment starts and ends naturally without cutting off mid-sentence or mid-thought, even if it slightly violates the duration targets.
- Segments MUST NOT overlap.
- The first 2-3 seconds of each segment MUST contain a strong hook. NEVER start on dead air, filler words ("um", "so anyway"), or mid-sentence. If the hook starts slightly before your ideal segment, extend backward to capture it.
- End segments on a punchline, conclusion, or natural pause — NOT mid-thought. It is completely fine to ignore the max_len if it means finishing a sentence properly.
- The `title_hook` is a BOLD 1-3 word text overlay shown in the first second of the video. It must create instant curiosity or emotional reaction. Examples: "WAIT FOR IT", "HE SNAPPED", "THIS IS INSANE", "NOBODY KNOWS THIS".
- `title_options` should provide 3 distinct angles: (1) curiosity-driven, (2) benefit-driven, (3) controversial/provocative.
- `viral_score` ranges from 0-100. Weight: hook strength (35%), emotional intensity (25%), shareability (20%), comment potential (20%).
- `caption` must be written as a real TikTok creator would post, in a highly casual and everyday Indonesian slang/style (using lu-gue/casual colloquial Indonesian, to-the-point). Do NOT use rigid, AI-looking template phrases (avoid things like "Apakah kamu...", "Ini dia...", "Pernahkah Anda..."). Limit emojis to a maximum of 1-2. Include a hook line, context, and CTA. Max 150 chars.
- `hashtags`: Provide EXACTLY 4 to 5 HIGH-TRAFFIC, PROVEN Indonesian viral hashtags directly matching the video topic (e.g. ["#fyp", "#beranda", "#bisnis", "#mindset", "#motivasi"]). DO NOT output more than 5 hashtags.

## RESPONSE FORMAT (ONLY valid JSON, no explanation, no markdown)

{{
  "clips": [
    {{
      "start": 12.5,
      "end": 45.0,
      "title_options": ["Curiosity Title", "Benefit Title", "Controversial Title"],
      "title_hook": "1-3 word bold text for first second",
      "reason": "Which viral triggers from the framework are present and why this will go viral",
      "viral_score": 95,
      "caption": "Hook + context + CTA + emojis (max 150 chars)",
      "hashtags": ["#fyp", "#beranda", "#bisnis", "#mindset", "#motivasi"]
    }}
  ]
}}

## TRANSCRIPT
{transcript_text}
"""
    return prompt

def call_llm_api(prompt, model_name, endpoint, api_key, job_id=None):
    if not endpoint.rstrip('/').endswith('/chat/completions'):
        endpoint = endpoint.rstrip('/') + '/chat/completions'
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.7,
    }

    log(f"Sending transcript to '{model_name}' via {endpoint} for analysis...", job_id=job_id)
    response = requests.post(endpoint, json=payload, headers=headers, timeout=600)
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        log("Unexpected response shape from LLM endpoint: " + json.dumps(data)[:500], job_id=job_id)
        return ""

def extract_json_block(raw_text, job_id=None):
    text = raw_text.strip()
    
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
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
