import json
import re
import requests
from backend.utils import log

def build_viral_prompt(transcript_text, num_clips, min_len, max_len, mode="hook"):
    if mode == "affiliate":
        prompt = f"""
You are a top-tier affiliate marketing strategist for TikTok, YouTube Shorts, and Instagram Reels.
Your only goal is to maximize SALES, RETENTION, and VIRALITY for affiliate products.

Below is a timestamped transcript of a long-form video. Each line follows the format:
[HH:MM:SS.mmm --> HH:MM:SS.mmm] spoken text

Your task for EACH of the {num_clips} distinct clips:
- Identify exactly {num_clips} distinct segments that either have HIGHEST VIRAL POTENTIAL or HIGHEST SALES CONVERSION POTENTIAL.
- Look for: Controversial statements, strong hooks, product recommendations, life-changing tips, or emotional stories.
- Each segment MUST be between {min_len} and {max_len} seconds long.
- Segments must not overlap.
- SEO & VIRAL METADATA: Generate a catchy title, 1 short clickbait text (`title_hook`) for the first second, and relevant hashtags.

Respond with ONLY valid JSON, no explanation, no markdown formatting.
Use exactly this schema:

{{
  "clips": [
    {{
      "start": 12.5,
      "end": 45.0,
      "type": "affiliate_or_viral",
      "title": "Short catchy title",
      "title_hook": "Teks clickbait 1 detik pertama",
      "reason": "Why this segment will drive sales OR go viral",
      "viral_score": 95,
      "caption": "A highly engaging TikTok/Reels caption with emojis",
      "hashtags": ["#viral", "#fyp", "#product"]
    }}
  ]
}}

Transcript:
{transcript_text}
"""
    else:
        prompt = f"""
You are a top-tier viral content strategist for TikTok, YouTube Shorts, and Instagram Reels.
Your only goal is to maximize RETENTION, ENGAGEMENT, and VIRALITY.

Below is a timestamped transcript of a long-form video. Each line follows the format:
[HH:MM:SS.mmm --> HH:MM:SS.mmm] spoken text

Your task for EACH of the {num_clips} distinct clips:
- Identify exactly {num_clips} distinct segments with the HIGHEST VIRAL POTENTIAL.
- Look for: Controversial statements, mind-blowing facts, high emotional peaks, funny moments, or immediate strong hooks.
- Each segment MUST be between {min_len} and {max_len} seconds long.
- Segments must not overlap.
- SEO & VIRAL METADATA: Generate 3 highly engaging title options, 1 short clickbait text (`title_hook`) for the first second of the video, and 10 highly relevant SEO hashtags based on the video's niche.

Respond with ONLY valid JSON, no explanation, no markdown formatting.
Use exactly this schema:

{{
  "clips": [
    {{
      "start": 12.5,
      "end": 45.0,
      "title_options": ["Title Option 1", "Title Option 2", "Title Option 3"],
      "title_hook": "Teks clickbait 1 detik pertama",
      "reason": "Why this will go viral (hook, peak emotion, etc.)",
      "viral_score": 95,
      "caption": "A highly engaging TikTok/Reels caption with emojis",
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"]
    }}
  ]
}}

Transcript:
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
