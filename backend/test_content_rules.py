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

    def test_existing_specific_question_is_kept(self):
        caption = "Spesialisasi menang di tahun ke-5. Lu pilih yang mana?"
        self.assertEqual(ensure_closing_question(caption), caption)

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

if __name__ == "__main__":
    unittest.main()
