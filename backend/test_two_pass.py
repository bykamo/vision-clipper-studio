"""Tests for the two-pass viral selection (analyzer additions)."""
import unittest

from backend.analyzer import (
    build_candidate_discovery_prompt,
    build_clip_enrichment_prompt,
    build_transcript_slice,
    select_diverse_clips,
    _jaccard,
)


def _cand(start, end, score, title, topic):
    return {
        "start": start, "end": end, "viral_score": score,
        "title": title, "topic_label": topic,
        "trigger_tags": ["controversial_claim"], "reason": "test",
    }


class DiscoveryPromptTest(unittest.TestCase):
    def test_hook_mode_structure(self):
        t = "[00:00:01 --> 00:00:05] halo dunia"
        p = build_candidate_discovery_prompt(t, max_candidates=12, mode="hook")
        self.assertIn(t, p)
        self.assertIn('"candidates"', p)
        self.assertIn("video_summary", p)
        self.assertIn("topic_label", p)
        self.assertIn("controversial_claim", p)
        self.assertIn("12", p)  # max_candidates interpolated

    def test_affiliate_mode_triggers(self):
        p = build_candidate_discovery_prompt("x", max_candidates=5, mode="affiliate")
        self.assertIn("pain_point", p)
        self.assertIn("social_proof", p)


class EnrichmentPromptTest(unittest.TestCase):
    def test_structure_and_index_matching(self):
        items = [
            {"index": 1, "start": 10.0, "end": 40.0, "title": "Judul Satu",
             "transcript": "[00:00:10 --> 00:00:15] teks satu"},
            {"index": 2, "start": 100.0, "end": 130.0, "title": "Judul Dua",
             "transcript": "[00:01:40 --> 00:01:45] teks dua"},
        ]
        p = build_clip_enrichment_prompt(items, video_summary="Ringkasan video.", mode="hook")
        self.assertIn("Ringkasan video.", p)
        self.assertIn("teks satu", p)
        self.assertIn("teks dua", p)
        self.assertIn("title_options", p)
        self.assertIn("caption", p)
        self.assertIn("hashtags", p)
        self.assertIn('"index": 1', p)


class SelectDiverseClipsTest(unittest.TestCase):
    def test_picks_highest_scores_first(self):
        cands = [
            _cand(0, 30, 70, "Klip A soal uang", "uang dan kaya"),
            _cand(200, 230, 95, "Klip B soal mindset", "mindset sukses"),
            _cand(400, 430, 80, "Klip C soal kesehatan", "kesehatan tubuh"),
        ]
        out = select_diverse_clips(cands, num_clips=2)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["title"], "Klip B soal mindset")
        self.assertEqual(out[1]["title"], "Klip C soal kesehatan")
        self.assertEqual([c["index"] for c in out], [1, 2])

    def test_rejects_overlap(self):
        cands = [
            _cand(0, 60, 95, "Klip A soal uang", "uang dan kaya"),
            _cand(30, 90, 90, "Klip B soal uang juga", "investasi saham"),  # overlaps A
            _cand(300, 330, 80, "Klip C soal tidur", "kualitas tidur"),
        ]
        out = select_diverse_clips(cands, num_clips=3, min_gap_sec=60.0)
        titles = [c["title"] for c in out]
        self.assertIn("Klip A soal uang", titles)
        self.assertNotIn("Klip B soal uang juga", titles)
        self.assertIn("Klip C soal tidur", titles)

    def test_rejects_near_duplicates_by_gap(self):
        cands = [
            _cand(0, 30, 95, "Klip A soal uang", "uang dan kaya"),
            _cand(50, 80, 90, "Klip B soal diet", "diet sehat"),  # only 20s gap
            _cand(500, 530, 85, "Klip C soal baca", "baca buku"),
        ]
        out = select_diverse_clips(cands, num_clips=3, min_gap_sec=60.0)
        titles = [c["title"] for c in out]
        self.assertNotIn("Klip B soal diet", titles)
        self.assertEqual(len(out), 2)

    def test_rejects_same_topic(self):
        cands = [
            _cand(0, 30, 95, "Rahasia kaya raya", "kaya dan uang"),
            _cand(500, 530, 90, "Cara jadi kaya raya", "kaya dan uang"),  # same idea
            _cand(1000, 1030, 85, "Tidur cukup itu penting", "kualitas tidur"),
        ]
        out = select_diverse_clips(cands, num_clips=3, min_gap_sec=60.0,
                                   diversity_threshold=0.55)
        titles = [c["title"] for c in out]
        self.assertIn("Rahasia kaya raya", titles)
        self.assertNotIn("Cara jadi kaya raya", titles)
        self.assertIn("Tidur cukup itu penting", titles)

    def test_no_filler_when_not_enough_diverse(self):
        cands = [
            _cand(0, 30, 95, "Rahasia kaya raya", "kaya dan uang"),
            _cand(40, 70, 90, "Tips kaya raya", "kaya dan uang"),  # dup topic + close
        ]
        out = select_diverse_clips(cands, num_clips=5)
        self.assertEqual(len(out), 1)  # fewer is intentional — no filler

    def test_handles_empty_and_malformed(self):
        self.assertEqual(select_diverse_clips([], num_clips=5), [])
        self.assertEqual(select_diverse_clips(None, num_clips=5), [])
        cands = [
            {"start": "bad", "end": 30},           # malformed -> skipped
            _cand(100, 50, 80, "Terbalik", "x"),    # end <= start -> skipped
            _cand(200, 230, 80, "Valid", "topik valid"),
        ]
        out = select_diverse_clips(cands, num_clips=5)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "Valid")


class HelpersTest(unittest.TestCase):
    def test_jaccard(self):
        self.assertAlmostEqual(_jaccard("kaya dan uang", "kaya dan uang"), 1.0)
        self.assertEqual(_jaccard("apel jeruk", "mobil motor"), 0.0)
        self.assertEqual(_jaccard("", "x"), 0.0)

    def test_build_transcript_slice(self):
        segs = [
            {"start": 0.0, "end": 10.0, "text": "pembuka"},
            {"start": 10.0, "end": 20.0, "text": "inti pembahasan"},
            {"start": 50.0, "end": 60.0, "text": "jauh di belakang"},
        ]
        s = build_transcript_slice(segs, 10.0, 20.0, pad_sec=1.0)
        self.assertIn("inti pembahasan", s)
        self.assertNotIn("jauh di belakang", s)


if __name__ == "__main__":
    unittest.main()
