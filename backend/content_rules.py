"""Deterministic post-processing rules for LLM clip output.

The LLM is good at *finding* moments, but unreliable at the mechanical parts
that actually decide whether a clip performs on TikTok:

* clip length (completion rate is the strongest distribution signal),
* hashtag hygiene (3-5 relevant tags instead of #fyp spam),
* a closing question that provokes comments,
* a pinned first comment.

Doing this in code (instead of trusting the prompt) makes the output stable,
testable, and independent of which model answered.
"""

import re

# ── Duration windows (seconds) ──────────────────────────────────────────────
# Short clips keep completion rate high. `MAX` is a hard clamp applied after the
# LLM answers; `TARGET` is what the prompt asks for and what the UI shows.
MAX_DURATION = {"hook": 45.0, "affiliate": 60.0}
MIN_DURATION = {"hook": 18.0, "affiliate": 20.0}
TARGET_DURATION = {"hook": (25.0, 40.0), "affiliate": (30.0, 55.0)}

# ── Hashtags ────────────────────────────────────────────────────────────────
# Broad tags (#fyp, #viral, #trending, #foryou) are pure noise for a small
# account: they only tell the algorithm "this video is about nothing".
BANNED_HASHTAGS = {
    "fyp", "fypシ", "fy", "foryou", "foryoupage", "foru", "viral", "viralvideo",
    "trending", "trend", "beranda", "explore", "explorepage", "xyzbca", "fypage",
    "tiktok", "tiktokindonesia", "shorts", "shortsfeed", "reels", "reelsviral",
    "masukberanda", "racuntiktok", "kontenkreator",
}
NICHE_FALLBACK = ("#mindset", "#selfimprovement", "#motivasi")
MAX_HASHTAGS = 5
MIN_HASHTAGS = 3

# ── Caption hygiene ─────────────────────────────────────────────────────────
# Begging-style CTAs are the fastest way to look like a bot account.
BANNED_CTA_PHRASES = (
    "jangan lupa like",
    "jangan lupa follow",
    "like dan follow",
    "like & follow",
    "komen di bawah",
    "komentar di bawah",
    "cek bio",
    "cek link di bio",
    "swipe up",
    "tonton sampai habis",
    "subscribe",
    "share ke teman",
    "tag teman",
)
BANNED_AI_PHRASES = (
    "apakah kamu",
    "pernahkah anda",
    "yuk simak",
    "tahukah kamu",
    "fakta menariknya",
    "simak baik-baik",
    "mari kita bahas",
    "jangan lewatkan",
    "ini dia",
)

# Generic engagement bait the prompt used to forbid entirely. A *specific*
# closing question is now required, but these vague ones still get replaced.
GENERIC_BAIT = (
    "gimana menurut kalian",
    "menurut kalian gimana",
    "ada yang relate",
    "setuju gak semuanya",
    "pendapat kalian",
)

QUESTION_FALLBACKS = {
    "hook": "Lu tim yang mana?",
    "affiliate": "Masih ragu atau langsung checkout?",
}

MAX_CAPTION_CHARS = 150


def _normalize_tag(tag) -> str:
    """Turn ``mindset`` / ``#mindset`` / ``##mindset`` into ``#mindset``."""
    cleaned = re.sub(r"^[#\s]+", "", str(tag or "")).strip()
    cleaned = re.sub(r"[^\w\u00C0-\u024F]+", "", cleaned, flags=re.UNICODE)
    return f"#{cleaned}" if cleaned else ""


def normalize_hashtags(tags, mode="hook"):
    """Sanitize, de-duplicate, cap and top-up a hashtag list.

    - strips banned broad tags (#fyp, #viral, ...),
    - normalizes the leading ``#``,
    - caps at ``MAX_HASHTAGS``,
    - pads with niche fallbacks so a clip never ships with 0-2 tags.
    """
    if isinstance(tags, str):
        tags = re.split(r"[\s,]+", tags)

    result = []
    seen = set()
    for raw in tags or []:
        tag = _normalize_tag(raw)
        if not tag:
            continue
        key = tag.lstrip("#").lower()
        if key in BANNED_HASHTAGS or key in seen:
            continue
        seen.add(key)
        result.append(tag)
        if len(result) >= MAX_HASHTAGS:
            break

    for fallback in NICHE_FALLBACK:
        if len(result) >= MIN_HASHTAGS:
            break
        key = fallback.lstrip("#").lower()
        if key not in seen:
            seen.add(key)
            result.append(fallback)

    return result


def clean_caption(caption, mode="hook"):
    """Strip bot-like CTA/AI phrasing and collapse whitespace.

    The closing question is preserved: it is the single most reliable comment
    driver for a small account.
    """
    text = str(caption or "").strip()
    if not text:
        return text

    lowered = text.lower()
    for phrase in BANNED_CTA_PHRASES + BANNED_AI_PHRASES:
        if phrase not in lowered:
            continue
        parts = re.split(r"(?<=[.!?])\s+", text)
        kept = [p for p in parts if phrase not in p.lower()]
        if kept:
            text = " ".join(kept).strip()
        else:
            # The phrase is in the only sentence: drop just the phrase instead
            # of nuking the whole caption.
            text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
            text = re.sub(r"^[\s,;:.-]+", "", text).strip()
            text = text[:1].upper() + text[1:] if text else text
        lowered = text.lower()

    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"[ \t]*([,.!?])", r"\1", text)

    if len(text) > MAX_CAPTION_CHARS:
        cut = text[:MAX_CAPTION_CHARS]
        # Prefer cutting on a sentence boundary, else on a word boundary.
        boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        if boundary > 60:
            cut = cut[: boundary + 1]
        else:
            cut = cut.rsplit(" ", 1)[0]
        text = cut.rstrip(" ,;:-") + ("?" if "?" in text[:MAX_CAPTION_CHARS] else "")

    return text.strip()


def has_question(text) -> bool:
    return "?" in str(text or "")


def ensure_closing_question(caption, mode="hook"):
    """Guarantee the caption ends with a short, specific question.

    A vague bait ("gimana menurut kalian?") is replaced with a concrete
    either/or question, because specific questions are answerable in 2 words
    and therefore actually get replies.
    """
    text = str(caption or "").strip()
    lowered = text.lower()
    fallback = QUESTION_FALLBACKS.get(mode, QUESTION_FALLBACKS["hook"])

    if has_question(text):
        if any(bait in lowered for bait in GENERIC_BAIT):
            head = re.split(r"[?.!]", text)[0].strip()
            return f"{head} {fallback}".strip() if head else fallback
        return text

    if not text:
        return fallback
    # Keep the sentence terminator so the appended question reads naturally.
    if text[-1] in ".!?":
        return f"{text} {fallback}"
    return f"{text} {fallback}"


def is_generic_caption(caption) -> bool:
    """Heuristic: does the caption sound like a generic motivation quote?

    Generic quotes ("konsisten itu penting") have no number, no contrast, and no
    concrete noun. They are exactly the clips that died at a few hundred views.
    """
    text = str(caption or "").lower()
    if not text:
        return True
    has_number = bool(re.search(r"\d", text))
    has_contrast = any(
        word in text
        for word in ("tapi", "justru", "bukan", "kecuali", "karena", "padahal", "malah")
    )
    concrete = any(
        word in text
        for word in ("rp", "juta", "ribu", "tahun", "hari", "jam", "%", "orang", "kerja", "uang")
    )
    return not (has_number or has_contrast or concrete)


def _iter_words(segments):
    for seg in segments or []:
        words = seg.get("words") or []
        if words:
            for word in words:
                text = str(word.get("word", "")).strip()
                if not text:
                    continue
                yield text, float(word.get("start", 0.0)), float(word.get("end", 0.0))
        else:
            text = str(seg.get("text", "")).strip()
            if text:
                yield text, float(seg.get("start", 0.0)), float(seg.get("end", 0.0))


def snap_clip_end(clip, segments, mode="hook"):
    """Clamp a clip to ``MAX_DURATION`` while cutting on a sentence boundary.

    Cutting mid-sentence destroys the payoff, so we look for the last sentence
    terminator inside the allowed window and end there. If none exists we fall
    back to the hard limit (still better than a 90s clip nobody finishes).
    """
    start = float(clip.get("start", 0.0))
    end = float(clip.get("end", 0.0))
    max_dur = MAX_DURATION.get(mode, MAX_DURATION["hook"])
    min_dur = MIN_DURATION.get(mode, MIN_DURATION["hook"])

    if end - start <= max_dur:
        return clip

    hard_limit = start + max_dur
    soft_limit = start + max(max_dur - 6.0, min_dur)
    best = None
    for text, _w_start, w_end in _iter_words(segments):
        if w_end <= soft_limit:
            continue
        if w_end > hard_limit:
            break
        if text and text[-1] in ".?!":
            best = w_end

    clip["end"] = round(min(hard_limit, best) if best else hard_limit, 2)
    return clip


def dedupe_overlapping(clips, threshold=0.6):
    """Drop clips that re-tell the same moment.

    Batching seven near-identical clips is what starved the account's test
    budget in the first place, so overlapping candidates are collapsed.
    """
    kept = []
    for clip in sorted(clips, key=lambda c: float(c.get("viral_score") or 0), reverse=True):
        start, end = float(clip.get("start", 0.0)), float(clip.get("end", 0.0))
        span = max(end - start, 0.01)
        duplicate = False
        for other in kept:
            o_start, o_end = float(other.get("start", 0.0)), float(other.get("end", 0.0))
            overlap = min(end, o_end) - max(start, o_start)
            if overlap <= 0:
                continue
            if overlap / span > threshold or overlap / max(o_end - o_start, 0.01) > threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(clip)
    kept.sort(key=lambda c: float(c.get("start", 0.0)))
    return kept


def build_quality(clip, mode="hook"):
    """Collect the flags the UI needs to warn about a weak clip."""
    start = float(clip.get("start", 0.0))
    end = float(clip.get("end", 0.0))
    duration = round(end - start, 2)
    low, high = TARGET_DURATION.get(mode, TARGET_DURATION["hook"])
    hard_max = MAX_DURATION.get(mode, MAX_DURATION["hook"])
    caption = clip.get("caption", "")
    hashtags = clip.get("hashtags") or []

    return {
        "duration": duration,
        # `ok` allows the full legal window; `in_target` is the ideal band the
        # UI highlights so a 45s clip is not shown as broken, just not ideal.
        "duration_ok": low <= duration <= hard_max,
        "in_target": low <= duration <= high,
        "duration_hint": f"{int(low)}-{int(high)}s",
        "has_question": has_question(caption),
        "hashtag_count": len(hashtags),
        "hashtags_ok": MIN_HASHTAGS <= len(hashtags) <= MAX_HASHTAGS,
        "generic_risk": is_generic_caption(caption),
        "has_hook": bool(str(clip.get("hook_line") or "").strip()),
        "has_first_comment": bool(str(clip.get("first_comment") or "").strip()),
    }


def apply_clip_rules(clip, segments, mode="hook"):
    """Apply every deterministic rule to a single clip, in place.

    Returns the same dict so callers can chain.
    """
    snap_clip_end(clip, segments, mode=mode)

    clip["caption"] = ensure_closing_question(
        clean_caption(clip.get("caption", ""), mode=mode), mode=mode
    )
    clip["hashtags"] = normalize_hashtags(clip.get("hashtags"), mode=mode)

    hook = str(clip.get("hook_line") or "").strip()
    if not hook:
        titles = clip.get("title_options") or []
        hook = str(titles[0]).strip() if titles else str(clip.get("title") or "").strip()
    clip["hook_line"] = hook

    clip["first_comment"] = str(clip.get("first_comment") or "").strip()
    clip["series"] = str(clip.get("series") or "").strip()

    clip["quality"] = build_quality(clip, mode=mode)
    return clip


def apply_content_rules(clips, segments, mode="hook"):
    """Sanitize a whole candidate list: durations, captions, tags, duplicates."""
    if not isinstance(clips, list):
        return []
    prepared = [apply_clip_rules(clip, segments, mode=mode) for clip in clips if isinstance(clip, dict)]
    return dedupe_overlapping(prepared)
