import unittest

from backend.content_rules import (
    MAX_DURATION,
    MIN_HASHTAGS,
    apply_clip_rules,
    apply_content_rules,
    clean_caption,
    dedupe_overlapping,
    ensure_closing_question,
    is_generic_caption,
    normalize_hashtags,
    snap_clip_end,
)


def _segments(*spans):
    """Build transcript segments: (start, end, text)."""
    return [{"start": s, "end": e, "text": t} for s, e, t in spans]


class HashtagRulesTest(unittest.TestCase):
    def test_broad_tags_are_dropped(self):
        tags = normalize_hashtags(["#fyp", "#viral", "#trending", "#foryou", "#mindset"])
        self.assertEqual(tags, ["#mindset", "#selfimprovement", "#motivasi"])

    def test_missing_hash_is_added_and_duplicates_removed(self):
        tags = normalize_hashtags(["mindset", "#Mindset", "psikologikerja"])
        self.assertEqual(tags, ["#mindset", "#psikologikerja", "#selfimprovement"])

    def test_capped_at_five(self):
        tags = normalize_hashtags([f"#tag{i}" for i in range(9)])
        self.assertEqual(len(tags), 5)

    def test_never_returns_fewer_than_minimum(self):
        tags = normalize_hashtags([])
        self.assertEqual(len(tags), MIN_HASHTAGS)

    def test_string_input_is_split(self):
        tags = normalize_hashtags("#fyp #mindset #kerja")
        self.assertEqual(tags, ["#mindset", "#kerja", "#selfimprovement"])


class CaptionRulesTest(unittest.TestCase):
    def test_begging_cta_sentence_is_removed(self):
        cleaned = clean_caption("Kerja keras doang gak bikin kaya. Jangan lupa like dan follow ya!")
        self.assertNotIn("like", cleaned.lower())
        self.assertIn("Kerja keras", cleaned)

    def test_ai_phrases_are_removed(self):
        cleaned = clean_caption("Tahukah kamu bahwa konsisten itu penting.")
        self.assertNotIn("Tahukah kamu", cleaned)

    def test_caption_ends_with_question_when_missing(self):
        result = ensure_closing_question("Spesialisasi menang di tahun kelima.")
        self.assertTrue(result.endswith("?"))
        self.assertIn("Spesialisasi menang di tahun kelima.", result)

    def test_vague_bait_is_replaced_with_specific_question(self):
        result = ensure_closing_question("Kerja keras gak bikin kaya. Gimana menurut kalian?")
        self.assertNotIn("menurut kalian", result.lower())
        self.assertTrue(result.endswith("?"))

    def test_question_mid_caption_is_kept_and_closing_appended(self):
        # A rhetorical question in the middle of the caption is fine; the
        # closing question is appended at the end so the final line provokes
        # two-word replies about the claim.
        result = ensure_closing_question(
            "Ada yang ngerasa gitu gak? Kerja keras gak bikin kaya.",
            mode="hook",
            specific="Lu tim lembur atau tim strategi?",
        )
        self.assertTrue(result.endswith("Lu tim lembur atau tim strategi?"))
        self.assertIn("ngerasa gitu gak?", result.lower())
        self.assertIn("kerja keras gak bikin kaya.", result.lower())

    def test_existing_specific_question_is_kept(self):
        caption = "Spesialisasi menang di tahun ke-5. Lu pilih yang mana?"
        self.assertEqual(ensure_closing_question(caption), caption)

    def test_clip_specific_question_is_preferred_over_fallback(self):
        # When pass 2 returned a clip-specific question, it must replace the
        # generic fallback instead of "Lu tim yang mana?".
        result = ensure_closing_question(
            "Spesialisasi menang di tahun kelima.", mode="hook",
            specific="Lu pilih spesialis atau generalis?",
        )
        self.assertTrue(result.endswith("Lu pilih spesialis atau generalis?"))
        self.assertNotIn("Lu tim yang mana", result)

    def test_specific_question_not_appended_when_caption_still_ends_in_generic_bait(self):
        # Vague bait in the caption is swapped for the clip-specific question.
        result = ensure_closing_question(
            "Kerja keras gak bikin kaya. Gimana menurut kalian?", mode="hook",
            specific="Lu tim lembur atau tim strategi?",
        )
        self.assertNotIn("menurut kalian", result.lower())
        self.assertTrue(result.endswith("Lu tim lembur atau tim strategi?"))

    def test_existing_specific_last_question_not_double_appended(self):
        caption = "Kerja keras gak bikin kaya. Lu tim lembur atau tim strategi?"
        result = ensure_closing_question(caption, mode="hook", specific="Sesuatu yang beda?")
        # Last question is already specific → keep caption as-is, no append.
        self.assertEqual(result, caption)

    def test_generic_quote_detected(self):
        self.assertTrue(is_generic_caption("Konsisten itu penting banget"))
        self.assertFalse(is_generic_caption("Kerja 12 jam tapi gak punya sistem itu cuma capek"))

    def test_long_caption_is_trimmed(self):
        cleaned = clean_caption("kata " * 80)
        self.assertLessEqual(len(cleaned), 160)


class DurationRulesTest(unittest.TestCase):
    def test_long_clip_is_clamped_to_hard_max(self):
        segments = _segments((0, 120, "satu kalimat panjang tanpa titik penutup"))
        clip = {"start": 0.0, "end": 120.0}
        snap_clip_end(clip, segments, mode="hook")
        self.assertLessEqual(clip["end"], MAX_DURATION["hook"])

    def test_clip_snaps_to_sentence_boundary_inside_window(self):
        segments = _segments(
            (0, 10, "Pembuka tanpa titik"),
            (10, 26, "Ini kalimat inti."),
            (26, 44, "Ini kalimat penutup."),
            (44, 70, "Kalimat yang harusnya kebuang."),
        )
        clip = {"start": 0.0, "end": 70.0}
        snap_clip_end(clip, segments, mode="hook")
        self.assertEqual(clip["end"], 44.0)

    def test_short_clip_is_untouched(self):
        clip = {"start": 10.0, "end": 34.0}
        snap_clip_end(clip, _segments((10, 34, "Pendek.")), mode="hook")
        self.assertEqual(clip["end"], 34.0)


class DedupeRulesTest(unittest.TestCase):
    def test_overlapping_clip_is_dropped(self):
        clips = [
            {"start": 0.0, "end": 30.0, "viral_score": 90},
            {"start": 5.0, "end": 32.0, "viral_score": 70},
            {"start": 60.0, "end": 90.0, "viral_score": 80},
        ]
        kept = dedupe_overlapping(clips)
        self.assertEqual(len(kept), 2)
        self.assertEqual([c["start"] for c in kept], [0.0, 60.0])

    def test_higher_score_wins(self):
        clips = [
            {"start": 0.0, "end": 30.0, "viral_score": 60},
            {"start": 2.0, "end": 31.0, "viral_score": 95},
        ]
        kept = dedupe_overlapping(clips)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["viral_score"], 95)


class ApplyRulesTest(unittest.TestCase):
    def test_apply_clip_rules_fills_hook_and_quality(self):
        clip = {
            "start": 0.0,
            "end": 30.0,
            "title_options": ["Kerja keras gak bikin kaya"],
            "caption": "Kerja keras tanpa pola cuma bikin capek",
            "hashtags": ["#fyp"],
        }
        apply_clip_rules(clip, _segments((0, 30, "Kerja keras tanpa pola.")), mode="hook")
        self.assertEqual(clip["hook_line"], "Kerja keras gak bikin kaya")
        self.assertTrue(clip["caption"].endswith("?"))
        self.assertNotIn("#fyp", clip["hashtags"])
        self.assertTrue(clip["quality"]["has_question"])
        self.assertTrue(clip["quality"]["hashtags_ok"])

    def test_apply_content_rules_handles_non_dict_entries(self):
        self.assertEqual(apply_content_rules(["bukan dict"], [], mode="hook"), [])

    def test_apply_content_rules_returns_sorted_by_start(self):
        clips = [
            {"start": 100.0, "end": 120.0, "viral_score": 80},
            {"start": 0.0, "end": 25.0, "viral_score": 90},
        ]
        result = apply_content_rules(clips, _segments((0, 200, "teks.")), mode="hook")
        self.assertEqual([c["start"] for c in result], [0.0, 100.0])

    def test_whisper_groq_words_without_punctuation_snaps_to_sentence_end(self):
        # Simulasi output Whisper Groq: kata-kata tidak punya titik, titik ada di segmen
        segments = [
            {
                "start": 0.0,
                "end": 20.0,
                "text": "Ini kalimat pertama yang penting.",
                "words": [
                    {"word": "Ini", "start": 0.0, "end": 0.4},
                    {"word": "kalimat", "start": 0.5, "end": 1.0},
                    {"word": "pertama", "start": 1.1, "end": 1.7},
                    {"word": "yang", "start": 1.8, "end": 2.1},
                    {"word": "penting", "start": 2.2, "end": 2.8},
                ]
            },
            {
                "start": 20.0,
                "end": 40.0,
                "text": "Ini kesimpulan inti yang wajib selesai.",
                "words": [
                    {"word": "Ini", "start": 20.0, "end": 20.3},
                    {"word": "kesimpulan", "start": 20.4, "end": 21.2},
                    {"word": "inti", "start": 21.3, "end": 21.8},
                    {"word": "yang", "start": 21.9, "end": 22.3},
                    {"word": "wajib", "start": 22.4, "end": 22.8},
                    {"word": "selesai", "start": 22.9, "end": 23.5},
                ]
            }
        ]
        # LLM memotong terlalu cepat di detik 22.5 (sebelum kata 'selesai' di 23.5)
        clip = {"start": 0.0, "end": 22.5}
        snap_clip_end(clip, segments, mode="hook")
        # snap harus maju menuntaskan kalimat sampai detik 23.5
        self.assertEqual(clip["end"], 23.5)

    def test_avoid_ending_on_hanging_conjunction(self):
        # Jika LLM memotong di kata sambung "karena"
        segments = [
            {
                "start": 0.0,
                "end": 25.0,
                "text": "Pekerjaan ini selesai karena kita fokus.",
                "words": [
                    {"word": "Pekerjaan", "start": 0.0, "end": 0.8},
                    {"word": "ini", "start": 0.9, "end": 1.2},
                    {"word": "selesai", "start": 1.3, "end": 2.0},
                    {"word": "karena", "start": 2.1, "end": 2.6},
                    {"word": "kita", "start": 2.7, "end": 3.0},
                    {"word": "fokus", "start": 3.1, "end": 3.8},
                ]
            }
        ]
        clip = {"start": 0.0, "end": 2.6}  # Tepat di kata 'karena'
        snap_clip_end(clip, segments, mode="hook")
        # Tidak boleh berhenti di 2.6 (kata 'karena'), melainkan menuntaskan kalimat sampai 'fokus' (3.8)
        self.assertEqual(clip["end"], 3.8)

if __name__ == "__main__":
    unittest.main()
