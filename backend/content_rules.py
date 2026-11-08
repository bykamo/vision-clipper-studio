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


# Words that, when a question consists ONLY of them, mean the question is vague
# opinion-bait ("Setuju gak?") instead of a specific, claim-tied question.
_VAGUE_QUESTION_WORDS = {
    "setuju", "gak", "ga", "nggak", "enggak", "betul", "bener", "gimana",
    "bagaimana", "menurut", "lu", "kalian", "kamu", "anda", "pendapat",
    "relate", "iya", "ya", "tidak", "gk",
}

def _is_vague_question(q):
    """True when a question is generic opinion-bait with no specific stake."""
    ql = (q or "").strip().lower()
    if not ql.endswith("?"):
        return False
    if any(bait in ql for bait in GENERIC_BAIT):
        return True
    words = re.findall(r"[a-z\u00C0-\u024F]+", ql)
    if not words:
        return False
    # A question made up only of vague bait words ("Setuju gak?", "Gimana?")
    # has no stake in the actual claim.
    return all(w in _VAGUE_QUESTION_WORDS for w in words)


def _extract_last_question(text):
    """Return the final question sentence in `text`, or '' if none."""
    q_idx = (text or "").rfind("?")
    if q_idx == -1:
        return ""
    candidates = [i for i in (text.rfind(".", 0, q_idx), text.rfind("!", 0, q_idx)) if i != -1]
    start = max(candidates) + 1 if candidates else 0
    return text[start: q_idx + 1].strip()


def ensure_closing_question(caption, mode="hook", specific=None):
    """Guarantee the caption ends with a short, SPECIFIC closing question.

    Order of preference:
      1. `specific` — a clip-specific question written by the LLM (pass 2).
      2. the question already present in the caption, when it is not vague bait.
      3. the mode fallback (last resort, generic).

    A vague bait ("gimana menurut kalian?") is replaced with a concrete
    either/or question, because specific questions are answerable in 2 words
    and therefore actually get replies.
    """
    text = str(caption or "").strip()
    fallback = QUESTION_FALLBACKS.get(mode, QUESTION_FALLBACKS["hook"])

    specific = str(specific or "").strip().rstrip()
    if specific and not specific.endswith(("?", "!", ".")):
        specific += "?"

    last_q = _extract_last_question(text)

    if text.endswith("?"):
        if last_q and not _is_vague_question(last_q):
            # Caption already ends on a specific question → keep as-is.
            return text
        # Vague question (or question made only of bait words) → swap it.
        head = re.split(r"[?.!]", text)[0].strip()
        question = specific or fallback
        return f"{head} {question}".strip() if head else question

    # No question yet: append the clip-specific one if we have it.
    if specific:
        if not text:
            return specific
        if text[-1] in ".!?":
            return f"{text} {specific}"
        return f"{text} {specific}"

    if not text:
        return fallback
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


SENTENCE_ENDINGS = (".", "?", "!", "…")
HANGING_WORDS = {
    "karena", "tapi", "tetapi", "jadi", "dan", "atau", "artinya", "makanya", "terus",
    "nah", "yang", "kalau", "kalo", "soalnya", "sehingga", "supaya", "biar", "trus",
    "namun", "bahkan", "sedangkan", "yaitu", "contohnya", "misalnya", "serta", "lalu",
    "kemudian", "sebab", "maka", "dengan", "untuk", "pada", "di", "ke", "dari", "ini",
    "itu", "bahwa", "adalah", "merupakan",
}
PAUSE_SEC = 0.40           # Jeda hening yang dianggap batas jeda alami ucapan
END_GRACE_SEC = 6.0        # Toleransi tambahan di atas MAX_DURATION demi menyelesaikan kalimat/payoff
START_BACKTRACK_SEC = 3.5  # Maksimal detik mundur untuk menangkap pembukaan kalimat utuh


def _build_speech_units(segments):
    """Mengekstrak unit kata/ujaran berurutan beserta status akhir kalimat & jeda suara.

    Groq Whisper API sering menghasilkan daftar kata (words) tanpa tanda baca,
    sedangkan tanda baca (titik, tanda tanya, tanda seru) berada pada teks segmen.
    Fungsi ini menyinkronkan tanda baca segmen ke kata terakhirnya dan menghitung
    jeda hening (gap) ke kata berikutnya.
    """
    units = []
    for seg in segments or []:
        seg_text = str(seg.get("text", "")).strip()
        words = [w for w in (seg.get("words") or []) if str(w.get("word", "")).strip()]

        if not words:
            if seg_text:
                units.append({
                    "text": seg_text,
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                    "sent_end": seg_text.endswith(SENTENCE_ENDINGS),
                })
            continue

        for i, w in enumerate(words):
            raw_w = str(w.get("word", "")).strip()
            is_last = (i == len(words) - 1)
            has_sent_end = raw_w.endswith(SENTENCE_ENDINGS) or (is_last and seg_text.endswith(SENTENCE_ENDINGS))
            units.append({
                "text": raw_w,
                "start": float(w.get("start", 0.0)),
                "end": float(w.get("end", 0.0)),
                "sent_end": has_sent_end,
            })

    units.sort(key=lambda u: u["start"])
    for i in range(len(units) - 1):
        units[i]["gap_after"] = max(0.0, units[i + 1]["start"] - units[i]["end"])
    if units:
        units[-1]["gap_after"] = 99.0
    return units


def _is_good_sentence_end(u, require_sentence=False):
    cleaned = re.sub(r"[^\w]+", "", u["text"].lower())
    if cleaned in HANGING_WORDS:
        return False
    if require_sentence:
        return u["sent_end"]
    return u["sent_end"] or (u.get("gap_after", 0.0) >= PAUSE_SEC)


def _snap_start_boundary(units, start):
    """Selaraskan start ke awal kata/kalimat terdekat, mundur jika di tengah kalimat."""
    idx = next((i for i, u in enumerate(units) if u["end"] > start), None)
    if idx is None:
        return start

    target_unit = units[idx]
    # Jika unit terlalu panjang (segmen besar tanpa word timestamps) atau
    # start berjarak jauh dari batas unit, jangan paksa snap jauh
    if (target_unit["end"] - target_unit["start"]) > 6.0 and abs(start - target_unit["start"]) > 2.0:
        return start

    if abs(start - target_unit["start"]) > 2.5:
        return start

    j = idx
    # Mundur ke awal kalimat jika start jatuh di tengah kalimat yang sedang berjalan
    while (j > 0
           and not units[j - 1]["sent_end"]
           and units[j - 1].get("gap_after", 0.0) < PAUSE_SEC
           and (start - units[j - 1]["start"]) <= START_BACKTRACK_SEC):
        j -= 1
        w_prev = re.sub(r"[^\w]+", "", units[j]["text"].lower())
        if w_prev in {"dan", "atau", "tapi", "soalnya"} and j + 1 <= idx:
            j += 1
            break

    return units[j]["start"]


def _snap_end_boundary(units, start, end, min_dur, max_dur):
    """Selaraskan end agar tidak memotong isi penting/payoff di tengah jalan."""
    hard_max_with_grace = start + max_dur + END_GRACE_SEC

    # 1. Prioritas utama: jika kalimat sedang berlangsung di dekat 'end',
    # tuntaskan kalimat tersebut (sent_end) dengan grace period
    for u in units:
        if u["end"] < end - 0.4:
            continue
        if u["end"] > hard_max_with_grace:
            break
        # Jika selisih terlalu jauh (> 6.0s), jangan melompat
        if (u["end"] - end) > 6.0:
            break
        if _is_good_sentence_end(u, require_sentence=True):
            return u["end"]

    # 2. Jika kalimat belum selesai tapi melewati batas grace, cari akhir kalimat
    # atau jeda hening terbaik di dalam jendela legal [start + min_dur, start + max_dur]
    lo = start + min_dur
    hi = start + max_dur
    window = [u for u in units if lo <= u["end"] <= hi]

    for require_sent in (True, False):
        good_candidates = [u for u in window if _is_good_sentence_end(u, require_sentence=require_sent)]
        if good_candidates:
            return good_candidates[-1]["end"]

    # 3. Fallback: ambil unit dengan jeda hening terpanjang yang bukan hanging word
    non_hanging = [u for u in window if re.sub(r"[^\w]+", "", u["text"].lower()) not in HANGING_WORDS]
    if non_hanging:
        best_pause = max(non_hanging, key=lambda u: u.get("gap_after", 0.0))
        return best_pause["end"]

    if window:
        return window[-1]["end"]

    return min(end, hi)


def snap_clip_boundaries(clip, segments, mode="hook"):
    """Clamp dan selaraskan start serta end klip ke batas kata & kalimat alami.

    Mencegah klip terpotong di tengah kalimat/kata dan menghindari berhenti
    pada kata sambung (hanging words). Menjamin isi penting & payoff tuntas.
    """
    try:
        start = float(clip.get("start", 0.0))
        end = float(clip.get("end", 0.0))
    except (TypeError, ValueError):
        return clip

    units = _build_speech_units(segments)
    if not units:
        return clip

    max_dur = MAX_DURATION.get(mode, MAX_DURATION["hook"])
    min_dur = MIN_DURATION.get(mode, MIN_DURATION["hook"])

    new_start = _snap_start_boundary(units, start)
    new_end = _snap_end_boundary(units, new_start, end, min_dur, max_dur)

    if new_end > new_start:
        clip["start"] = round(new_start, 2)
        clip["end"] = round(new_end, 2)

    return clip


def snap_clip_end(clip, segments, mode="hook"):
    """Backward-compatible alias untuk snap_clip_boundaries."""
    return snap_clip_boundaries(clip, segments, mode=mode)


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
        clean_caption(clip.get("caption", ""), mode=mode), mode=mode,
        specific=clip.get("closing_question"),
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
