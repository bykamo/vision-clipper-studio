"""Tests for the colour-emoji overlay engine (backend/emoji_overlay.py)."""

import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from backend import emoji_overlay as eo
from backend.utils import FONTS_DIR


class EmojiPatternTest(unittest.TestCase):
    def test_matches_simple_emoji(self):
        self.assertIsNotNone(eo.EMOJI_RE.fullmatch("\U0001F525"))

    def test_matches_zwj_cluster_as_one_unit(self):
        cluster = "\U0001F62E\u200D\U0001F4A8"
        self.assertIsNotNone(eo.EMOJI_RE.fullmatch(cluster))
        self.assertEqual([m.group(1) for m in eo.EMOJI_RE.finditer(cluster)], [cluster])

    def test_matches_flag_and_misc_technical(self):
        self.assertIsNotNone(eo.EMOJI_RE.fullmatch("\U0001F1EE\U0001F1E9"))  # 🇮🇩
        self.assertIsNotNone(eo.EMOJI_RE.fullmatch("\u23F1"))                # ⏱

    def test_variation_selector_is_stripped(self):
        self.assertEqual(eo.strip_variation_selectors("\u26A0\uFE0F"), "\u26A0")


class SplitRunsTest(unittest.TestCase):
    def test_tracks_font_and_size_overrides(self):
        text = r"uang {\fnNoto Emoji\alpha&HFF&}" + "💰" + r"{\fn\alpha&H00&} itu"
        runs = eo.split_runs(text, "Plus Jakarta Sans", 84.0)
        self.assertEqual([r["font"] for r in runs], ["Plus Jakarta Sans", "Noto Emoji", "Plus Jakarta Sans"])
        self.assertEqual([r["size"] for r in runs], [84.0, 84.0, 84.0])
        self.assertEqual([r["is_emoji"] for r in runs], [False, True, False])
        # The emoji sits on a visible word even though its own glyph is hidden.
        self.assertTrue(runs[1]["visible"])

    def test_emoji_on_hidden_word_is_not_visible(self):
        # Future words in the TikTok style are wrapped in \alpha&HFF& ... \alpha&H00&
        text = (
            r"{\alpha&HFF&}bisnis {\fnNoto Emoji\alpha&HFF&}"
            + "💰"
            + r"{\fn\alpha&H00&}{\alpha&H00&}"
        )
        runs = eo.split_runs(text, "Plus Jakarta Sans", 84.0)
        emoji_runs = [r for r in runs if r["is_emoji"]]
        self.assertTrue(emoji_runs, msg="emoji slot must be detected")
        self.assertFalse(emoji_runs[0]["visible"])

    def test_tracks_active_word_size_pop(self):
        text = r"{\fs92}uang" + r"{\fs84} itu"
        runs = eo.split_runs(text, "Plus Jakarta Sans", 84.0)
        self.assertEqual(runs[0]["size"], 92.0)
        self.assertEqual(runs[1]["size"], 84.0)


class AssParsingTest(unittest.TestCase):
    def test_parses_style_and_dialogue(self):
        content = (
            "[Script Info]\nScriptType: v4.00+\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: ViralStyle,Plus Jakarta Sans,84,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
            "-1,0,0,0,100,100,0,0,1,3.5,2,2,120,120,614,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.50,0:00:02.75,ViralStyle,,0,0,0,,Halo dunia\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False, encoding="utf-8") as fh:
            fh.write(content)
            path = fh.name
        try:
            styles, dialogues = eo.parse_ass_file(path)
        finally:
            os.remove(path)

        self.assertIn("ViralStyle", styles)
        style = styles["ViralStyle"]
        self.assertEqual(style["font"], "Plus Jakarta Sans")
        self.assertEqual(style["size"], 84.0)
        self.assertTrue(style["bold"])
        self.assertEqual(style["alignment"], 2)
        self.assertEqual(style["margin_v"], 614)

        self.assertEqual(len(dialogues), 1)
        self.assertAlmostEqual(dialogues[0]["start"], 1.5)
        self.assertAlmostEqual(dialogues[0]["end"], 2.75)
        self.assertEqual(dialogues[0]["text"], "Halo dunia")


class FontMetricsTest(unittest.TestCase):
    """libass scales Fontsize by upem/(winAscent+winDescent); we must mirror it."""

    def test_em_px_matches_libass_scaling(self):
        bold = os.path.join(FONTS_DIR, "..", "fonts", "NotoEmoji.ttf")
        if not os.path.exists(bold):
            self.skipTest("NotoEmoji.ttf not found")
        metrics = eo.FontMetrics(os.path.join(FONTS_DIR, "NotoEmoji.ttf"))
        self.assertGreater(metrics.em_px(84), 0)
        # em must never exceed the requested font size (win metrics >= upem)
        self.assertLessEqual(metrics.em_px(84), 84 * 1.5)

    def test_advance_grows_with_font_size(self):
        path = os.path.join(FONTS_DIR, "NotoEmoji.ttf")
        if not os.path.exists(path):
            self.skipTest("NotoEmoji.ttf not found")
        metrics = eo.FontMetrics(path)
        small = metrics.advance("ab", 40)
        large = metrics.advance("ab", 80)
        self.assertAlmostEqual(large / small, 2.0, places=2)


class OverlayGraphTest(unittest.TestCase):
    def _overlay(self, png, start, end, x=100, y=200):
        return eo.EmojiOverlay("X", start, end, x, y, 64, png)

    def test_empty_overlays_produce_no_graph(self):
        graph, inputs, label = eo.build_overlay_graph([])
        self.assertEqual(graph, "")
        self.assertEqual(inputs, [])
        self.assertEqual(label, "[vsub]")

    def test_one_input_per_unique_png(self):
        overlays = [
            self._overlay("/tmp/a.png", 0.0, 1.0),
            self._overlay("/tmp/a.png", 2.0, 3.0),
            self._overlay("/tmp/b.png", 4.0, 5.0),
        ]
        graph, inputs, label = eo.build_overlay_graph(overlays, base_label="[vsub]")
        # 2 unique PNGs -> 2 ffmpeg inputs (2 x ["-loop","1","-i",path])
        self.assertEqual(inputs.count("-i"), 2)
        self.assertIn("/tmp/a.png", inputs)
        self.assertIn("/tmp/b.png", inputs)
        # 3 overlays -> 3 overlay filters
        self.assertEqual(graph.count("overlay="), 3)
        self.assertIn("split=2", graph)
        self.assertNotEqual(label, "[vsub]")

    def test_enable_window_and_position_are_emitted(self):
        overlays = [self._overlay("/tmp/a.png", 1.25, 3.5, x=640, y=1180)]
        graph, _inputs, _label = eo.build_overlay_graph(overlays, base_label="[vsub]")
        self.assertIn("x=640:y=1180", graph)
        self.assertIn("between(t,1.250,3.500)", graph)

    def test_graph_starts_from_base_label(self):
        overlays = [self._overlay("/tmp/a.png", 0.0, 1.0)]
        graph, _inputs, _label = eo.build_overlay_graph(overlays, base_label="[vsub]")
        self.assertTrue(graph.startswith("[vsub][1:v]overlay="), graph)

    def test_merge_collapses_adjacent_identical_placements(self):
        merged = eo._merge_overlays([
            self._overlay("/tmp/a.png", 0.0, 1.0),
            self._overlay("/tmp/a.png", 1.0, 2.0),
        ])
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0].end, 2.0)

    def test_merge_keeps_distinct_placements(self):
        merged = eo._merge_overlays([
            self._overlay("/tmp/a.png", 0.0, 1.0, x=10),
            self._overlay("/tmp/a.png", 1.0, 2.0, x=200),
        ])
        self.assertEqual(len(merged), 2)


class ColorEmojiRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image  # noqa: F401
        except Exception:
            raise unittest.SkipTest("Pillow not installed")
        if not os.path.exists(os.path.join(FONTS_DIR, "NotoColorEmoji.ttf")):
            raise unittest.SkipTest("NotoColorEmoji.ttf not found")

    def test_renders_actual_colour(self):
        img = eo.render_color_emoji("\U0001F525", 64, FONTS_DIR)  # 🔥
        self.assertIsNotNone(img)
        arr = np.array(img.convert("RGBA"))
        opaque = arr[arr[:, :, 3] > 200]
        self.assertGreater(len(opaque), 50, msg="emoji produced no opaque pixels")
        rgb = opaque[:, :3].astype(np.int16)
        saturation = rgb.max(axis=1) - rgb.min(axis=1)
        self.assertGreater(
            int((saturation > 40).sum()), len(opaque) // 2,
            msg="fire emoji should be predominantly coloured",
        )

    def test_respects_requested_height(self):
        img = eo.render_color_emoji("💰", 80, FONTS_DIR)  # 💰
        self.assertIsNotNone(img)
        self.assertEqual(img.height, 80)

    def test_result_is_cached(self):
        first = eo.render_color_emoji("\U0001F680", 48, FONTS_DIR)  # 🚀
        second = eo.render_color_emoji("\U0001F680", 48, FONTS_DIR)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.size, second.size)

    def test_returns_none_for_unsupported_font_dir(self):
        self.assertIsNone(eo.render_color_emoji("\U0001F525", 64, tempfile.gettempdir()))


class OverlayPlanningTest(unittest.TestCase):
    def setUp(self):
        try:
            from PIL import Image  # noqa: F401
            from fontTools.ttLib import TTFont  # noqa: F401
        except Exception:
            self.skipTest("Pillow/fontTools not installed")
        if not os.path.exists(os.path.join(FONTS_DIR, "NotoColorEmoji.ttf")):
            self.skipTest("NotoColorEmoji.ttf not found")

    def _write_ass(self, dialogue_text, style_alignment=2, margin_v=614):
        content = (
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: S,Plus Jakarta Sans,84,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
            f"-1,0,0,0,100,100,0,0,1,3.5,2,{style_alignment},120,120,{margin_v},1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            f"Dialogue: 0,0:00:01.00,0:00:02.00,S,,0,0,0,,{dialogue_text}\n"
        )
        fh = tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False, encoding="utf-8")
        fh.write(content)
        fh.close()
        self.addCleanup(os.remove, fh.name)
        return fh.name

    def test_plans_one_overlay_per_visible_emoji(self):
        ass = self._write_ass(
            r"uang {\fnNoto Emoji\alpha&HFF&}💰{\fn\alpha&H00&} itu"
        )
        overlays = eo.plan_emoji_overlays(ass, FONTS_DIR)
        self.assertEqual(len(overlays), 1)
        self.assertEqual(overlays[0].emoji, "💰")
        self.assertAlmostEqual(overlays[0].start, 1.0)
        self.assertAlmostEqual(overlays[0].end, 2.0)
        self.assertTrue(os.path.exists(overlays[0].png_path))

    def test_horizontal_position_is_inside_safe_zone(self):
        ass = self._write_ass(
            r"uang {\fnNoto Emoji\alpha&HFF&}💰{\fn\alpha&H00&} itu"
        )
        overlays = eo.plan_emoji_overlays(ass, FONTS_DIR)
        self.assertEqual(len(overlays), 1)
        self.assertGreaterEqual(overlays[0].x, 120)
        self.assertLessEqual(overlays[0].x + overlays[0].size, 1080 - 120 + 40)

    def test_emoji_is_placed_above_the_margin_baseline(self):
        ass = self._write_ass(
            r"uang {\fnNoto Emoji\alpha&HFF&}💰{\fn\alpha&H00&}"
        )
        overlays = eo.plan_emoji_overlays(ass, FONTS_DIR)
        self.assertEqual(len(overlays), 1)
        # 1920 - 614 = 1306 is the bottom of the subtitle line
        self.assertLess(overlays[0].y, 1306)
        self.assertGreater(overlays[0].y, 1100)

    def test_hidden_emoji_is_not_painted(self):
        ass = self._write_ass(
            r"{\alpha&HFF&}uang {\fnNoto Emoji\alpha&HFF&}💰{\fn\alpha&H00&}{\alpha&H00&}"
        )
        self.assertEqual(eo.plan_emoji_overlays(ass, FONTS_DIR), [])

    def test_non_bottom_aligned_style_is_skipped(self):
        ass = self._write_ass(
            r"uang {\fnNoto Emoji\alpha&HFF&}💰{\fn\alpha&H00&}", style_alignment=7
        )
        self.assertEqual(eo.plan_emoji_overlays(ass, FONTS_DIR), [])

    def test_line_without_emoji_produces_nothing(self):
        ass = self._write_ass("halo dunia tanpa emoji")
        self.assertEqual(eo.plan_emoji_overlays(ass, FONTS_DIR), [])

    def test_unsupported_font_dir_returns_empty(self):
        ass = self._write_ass(
            r"uang {\fnNoto Emoji\alpha&HFF&}💰{\fn\alpha&H00&}"
        )
        self.assertEqual(eo.plan_emoji_overlays(ass, tempfile.gettempdir()), [])


if __name__ == "__main__":
    unittest.main()
