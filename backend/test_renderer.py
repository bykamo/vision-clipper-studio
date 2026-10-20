import math
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from backend.renderer import _validate_rendered_video, extract_and_format_clip
import numpy as np

from backend.renderer import (
    SceneCutDetector,
    _build_shot_trajectory,
    _parse_loudnorm_json,
    _write_crop_commands,
    build_audio_filter,
    build_audio_pre_chain,
    build_split_screen_graph,
    _calc_margin_v,
    generate_ass_subtitles,
)


class RendererIntegrityTest(unittest.TestCase):
    def test_validate_rendered_video_rejects_nonexistent_or_empty_file(self):
        self.assertFalse(_validate_rendered_video("/nonexistent/path/video.mp4"))
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"")
            tf.flush()
            self.assertFalse(_validate_rendered_video(tf.name))

    @patch("backend.renderer.get_ffprobe_binary", return_value="ffprobe")
    @patch("backend.renderer.subprocess.run")
    def test_validate_rendered_video_accepts_valid_probe(self, mock_run, _mock_ffprobe):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"x" * 2048)
            tf.flush()

            # Mock stream probe & duration probe
            res_stream = MagicMock()
            res_stream.returncode = 0
            res_stream.stdout = '{"streams": [{"codec_name": "h264", "width": 1080, "height": 1920}]}'

            res_dur = MagicMock()
            res_dur.returncode = 0
            res_dur.stdout = "15.5\n"

            mock_run.side_effect = [res_stream, res_dur]

            self.assertTrue(_validate_rendered_video(tf.name, min_duration=5.0))

    @patch("backend.renderer.compute_smart_crop_trajectory")
    @patch("backend.renderer.generate_ass_subtitles")
    @patch("backend.renderer.run_command")
    def test_extract_and_format_clip_raises_if_all_codecs_fail(self, mock_run_command, mock_ass, mock_smart_crop):
        mock_run_command.side_effect = Exception("Encoder hardware error")
        with tempfile.TemporaryDirectory() as out_dir:
            clip_info = {
                "title": "Test Viral Clip",
                "start": 0.0,
                "end": 10.0,
                "caption": "Test Caption"
            }
            with self.assertRaises(RuntimeError) as ctx:
                extract_and_format_clip(
                    video_path="dummy.mp4",
                    clip_info=clip_info,
                    index=1,
                    segments=[],
                    out_dir=out_dir
                )
            self.assertIn("All codecs failed to render clip", str(ctx.exception))
            # Pastikan file mp4 final tidak dibuat
            files = os.listdir(out_dir)
            mp4_files = [f for f in files if f.endswith(".mp4")]
            self.assertEqual(len(mp4_files), 0)


class ShotTrajectoryTest(unittest.TestCase):
    def _samples(self, total, stride, fn):
        idx = list(range(0, total, stride))
        return idx, [fn(i) for i in idx]

    def test_hard_cut_snaps_without_glide(self):
        total, cut = 200, 100
        idx, vals = self._samples(total, 5, lambda i: 500.0 if i < cut else 1500.0)
        out = _build_shot_trajectory(total, idx, vals, [cut], deadzone_px=50, sigma=25, default_x=960)
        self.assertEqual(len(out), total)
        np.testing.assert_allclose(out[:cut], 500.0)
        np.testing.assert_allclose(out[cut:], 1500.0)

    def test_without_cut_glides_like_before(self):
        total = 200
        idx, vals = self._samples(total, 5, lambda i: 500.0 if i < 100 else 1500.0)
        out = _build_shot_trajectory(total, idx, vals, [], deadzone_px=50, sigma=25, default_x=960)
        # Tanpa cut ada transisi halus (nilai di antara 500 dan 1500 di sekitar frame 100)
        self.assertTrue(np.any((out > 600) & (out < 1400)))

    def test_smooth_within_shot(self):
        total = 300
        idx, vals = self._samples(total, 5, lambda i: 500.0 + i * 3.0)
        out = _build_shot_trajectory(total, idx, vals, [150], deadzone_px=10, sigma=25, default_x=960)
        # Di dalam shot tidak boleh ada lompatan besar per frame (gimbal halus)
        self.assertLess(np.max(np.abs(np.diff(out[:150]))), 20)
        self.assertLess(np.max(np.abs(np.diff(out[150:]))), 20)

    def test_shot_without_detection_uses_previous_shot(self):
        total = 120
        idx = [0, 5, 10, 60, 65, 70]
        vals = [400.0, 400.0, 400.0, None, None, None]
        out = _build_shot_trajectory(total, idx, vals, [60], deadzone_px=50, sigma=10, default_x=960)
        np.testing.assert_allclose(out[60:], 400.0)

    def test_first_shot_without_detection_uses_default(self):
        out = _build_shot_trajectory(30, [0, 5], [None, None], [], deadzone_px=50, sigma=10, default_x=960)
        np.testing.assert_allclose(out, 960.0)

    def test_failed_detection_is_held_within_shot_only(self):
        total = 100
        idx = [0, 5, 10, 50, 55]
        vals = [300.0, None, None, 1200.0, None]
        out = _build_shot_trajectory(total, idx, vals, [50], deadzone_px=50, sigma=5, default_x=960)
        np.testing.assert_allclose(out[:50], 300.0)
        np.testing.assert_allclose(out[50:], 1200.0)

    def test_ignores_out_of_range_cuts(self):
        out = _build_shot_trajectory(10, [0], [700.0], [0, 10, 99, -3], deadzone_px=50, sigma=5, default_x=960)
        np.testing.assert_allclose(out, 700.0)


class SceneCutDetectorTest(unittest.TestCase):
    @staticmethod
    def _solid(bgr, noise_seed=None):
        frame = np.zeros((90, 160, 3), dtype=np.uint8)
        frame[:] = bgr
        if noise_seed is not None:
            rng = np.random.default_rng(noise_seed)
            frame = np.clip(frame.astype(np.int16) + rng.integers(-4, 5, frame.shape), 0, 255).astype(np.uint8)
        return frame

    def test_detects_hard_cut(self):
        det = SceneCutDetector(fps=30)
        cuts = [i for i in range(60) if det.update(i, self._solid((30, 30, 200) if i < 30 else (200, 120, 20), noise_seed=i))]
        self.assertEqual(cuts, [30])

    def test_small_noise_is_not_a_cut(self):
        det = SceneCutDetector(fps=30)
        cuts = [i for i in range(90) if det.update(i, self._solid((90, 140, 180), noise_seed=i))]
        self.assertEqual(cuts, [])

    def test_flash_within_min_gap_is_ignored(self):
        det = SceneCutDetector(fps=30)
        frames = [(30, 30, 200)] * 20 + [(255, 255, 255)] + [(30, 30, 200)] * 20
        cuts = [i for i, c in enumerate(frames) if det.update(i, self._solid(c))]
        self.assertEqual(cuts, [20])  # kembalinya dari flash (frame 21) diabaikan

    def test_similar_color_angle_change_detected_by_adaptive_rule(self):
        # Dua "angle" dengan warna rata-rata mirip tapi layout berbeda (setengah kiri/kanan ditukar)
        a = np.zeros((90, 160, 3), dtype=np.uint8); a[:, :80] = (40, 60, 160); a[:, 80:] = (60, 50, 90)
        b = a[:, ::-1].copy()
        det = SceneCutDetector(fps=30)
        cuts = [i for i in range(40) if det.update(i, a if i < 20 else b)]
        self.assertEqual(cuts, [20])


class CropCommandTimingTest(unittest.TestCase):
    def test_commands_are_half_frame_early_and_deduplicated(self):
        traj = {"fps": 30.0, "positions": np.array([100.0, 100.0, 101.0, 600.0, 600.0])}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cmd.txt")
            x0 = _write_crop_commands(traj, path)
            with open(path, encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(x0, 100)
        # 101 dibulatkan ke genap -> 100 (duplikat dibuang); cut di frame 3 -> (3-0.5)/30
        self.assertEqual(lines, ["0.0000 crop x 100;", f"{2.5 / 30:.4f} crop x 600;"])


class AudioFilterTest(unittest.TestCase):
    MEASURED = {"input_i": -27.3, "input_tp": -8.1, "input_lra": 6.2, "input_thresh": -37.9, "target_offset": 0.4}

    def test_parse_loudnorm_json_from_stderr(self):
        stderr = (
            "[Parsed_loudnorm_3 @ 0x1] \n{\n\t\"input_i\" : \"-27.30\",\n\t\"input_tp\" : \"-8.10\",\n"
            "\t\"input_lra\" : \"6.20\",\n\t\"input_thresh\" : \"-37.90\",\n\t\"output_i\" : \"-14.0\",\n"
            "\t\"normalization_type\" : \"dynamic\",\n\t\"target_offset\" : \"0.40\"\n}\n"
        )
        self.assertEqual(_parse_loudnorm_json(stderr), self.MEASURED)

    def test_parse_loudnorm_handles_inf_and_garbage(self):
        stderr = '{"input_i" : "-inf", "input_tp" : "-inf", "input_lra" : "0.00", "input_thresh" : "-inf", "target_offset" : "inf"}'
        parsed = _parse_loudnorm_json(stderr)
        self.assertTrue(math.isinf(parsed["input_i"]))
        self.assertIsNone(_parse_loudnorm_json("no json here"))
        self.assertIsNone(_parse_loudnorm_json('{"input_i": "abc"}'))
        self.assertIsNone(_parse_loudnorm_json(""))

    def test_two_pass_filter_uses_measurement(self):
        af, mode = build_audio_filter(9.5, build_audio_pre_chain(), -14.0, self.MEASURED)
        self.assertEqual(mode, "two_pass")
        self.assertIn("loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=-27.30", af)
        self.assertIn("linear=true", af)
        self.assertTrue(af.endswith("afade=t=out:st=9.500:d=0.5"))
        self.assertLess(af.index("acompressor"), af.index("loudnorm"))
        self.assertLess(af.index("loudnorm"), af.index("afade"))

    def test_single_pass_fallback_when_measurement_missing(self):
        af, mode = build_audio_filter(5.0, build_audio_pre_chain(), -14.0, None)
        self.assertEqual(mode, "single_pass")
        self.assertIn("loudnorm=I=-14:TP=-1.5:LRA=11,", af)
        self.assertNotIn("measured_I", af)

    def test_silent_clip_skips_loudnorm(self):
        for measured in (
            dict(self.MEASURED, input_i=float("-inf"), input_thresh=float("-inf")),
            dict(self.MEASURED, input_i=-62.0),
        ):
            af, mode = build_audio_filter(5.0, build_audio_pre_chain(), -14.0, measured)
            self.assertEqual(mode, "skip")
            self.assertNotIn("loudnorm", af)

    def test_pre_chain_denoise_toggle(self):
        self.assertNotIn("afftdn", build_audio_pre_chain(denoise=False))
        self.assertIn("afftdn", build_audio_pre_chain(denoise=True))
        self.assertIn("highpass=f=80", build_audio_pre_chain())


class SplitScreenAndSubtitleEnhancementTest(unittest.TestCase):
    @patch("backend.renderer.detect_speaker_anchors")
    @patch("backend.renderer._probe_video_stream")
    def test_build_split_screen_graph_structure(self, mock_probe, mock_anchors):
        mock_probe.return_value = (1920, 1080, 30.0)
        mock_anchors.return_value = {"left_anchor": 480.0, "right_anchor": 1440.0}

        finish_chain = "eq=contrast=1.1,fade=t=out:st=9.5:d=0.5"
        graph = build_split_screen_graph("dummy.mp4", 0.0, 10.0, finish_chain)

        self.assertIn("split=2[vtop_in][vbot_in]", graph)
        self.assertIn("scale=1080:960", graph)
        self.assertIn("vstack=inputs=2[stacked]", graph)
        self.assertIn("drawbox=x=0:y=958:w=1080:h=4", graph)
        self.assertIn(finish_chain, graph)

    def test_calc_margin_v(self):
        # 68% from top -> 32% from bottom: 1920 * 0.32 = 614
        self.assertEqual(_calc_margin_v(68), 614)
        # 50% from top -> 50% from bottom: 1920 * 0.50 = 960
        self.assertEqual(_calc_margin_v(50), 960)
        # 80% from top -> 20% from bottom: 1920 * 0.20 = 384
        self.assertEqual(_calc_margin_v(80), 384)

    @patch("backend.renderer.build_split_screen_graph")
    @patch("backend.renderer.generate_ass_subtitles")
    @patch("backend.renderer.run_command")
    @patch("backend.renderer._validate_rendered_video")
    def test_extract_and_format_clip_split_screen_mode(
        self, mock_validate, mock_run, mock_ass, mock_split
    ):
        mock_split.return_value = "[0:v]split=2[top][bot]vstack[v]"
        def fake_run(cmd, *args, **kwargs):
            part_path = cmd[-1]
            with open(part_path, "wb") as f:
                f.write(b"x" * 2048)
            return "Done"
        mock_run.side_effect = fake_run
        mock_validate.return_value = True

        with tempfile.TemporaryDirectory() as out_dir:
            clip_info = {
                "title": "Split Screen Test",
                "start": 0.0,
                "end": 8.0,
                "caption": "Test Split"
            }
            out = extract_and_format_clip(
                video_path="dummy.mp4",
                clip_info=clip_info,
                index=1,
                segments=[],
                out_dir=out_dir,
                framing_mode="split_screen",
                sub_position=65,
            )
            self.assertTrue(mock_split.called)
            self.assertTrue(mock_ass.called)
            self.assertEqual(mock_ass.call_args[1]["sub_position"], 65)
            self.assertTrue(os.path.exists(out))

    def test_generate_ass_subtitles_with_watermark_glass_effect(self):
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tf:
            ass_path = tf.name

        try:
            segments = [
                {
                    "start": 1.0,
                    "end": 3.0,
                    "words": [
                        {"word": "Halo", "start": 1.0, "end": 1.5},
                        {"word": "dunia", "start": 1.6, "end": 2.2}
                    ]
                }
            ]
            generate_ass_subtitles(
                segments,
                ass_path,
                clip_start=0.0,
                clip_end=5.0,
                sub_style="tiktok_viral",
                watermark_enabled=True,
                source_watermark="Deddy Corbuzier",
                account_watermark="@visionclipper"
            )

            self.assertTrue(os.path.exists(ass_path))
            with open(ass_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("Style: GlassSource,Plus Jakarta Sans,32", content)
            self.assertIn("Style: GlassAccount,Plus Jakarta Sans,34", content)
            self.assertIn("&H70181412", content)  # Smoked glass color
            self.assertIn("Dialogue: 0,0:00:00.00,0:00:05.00,GlassSource,,0,0,0,,▶  Source: Deddy Corbuzier", content)
            self.assertIn("Dialogue: 0,0:00:00.00,0:00:05.00,GlassAccount,,0,0,0,,@visionclipper", content)
            self.assertIn("ViralStyle", content)
        finally:
            if os.path.exists(ass_path):
                os.remove(ass_path)

    def test_generate_ass_subtitles_no_subtitle_with_watermark(self):
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tf:
            ass_path = tf.name

        try:
            generate_ass_subtitles(
                segments=[],
                out_ass_path=ass_path,
                clip_start=0.0,
                clip_end=4.0,
                sub_style="no_subtitle",
                watermark_enabled=True,
                source_watermark="Close The Door",
                account_watermark="myhandle"
            )

            self.assertTrue(os.path.exists(ass_path))
            with open(ass_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("Style: GlassSource", content)
            self.assertIn("Style: GlassAccount", content)
            self.assertIn("▶  Source: Close The Door", content)
            self.assertIn("@myhandle", content)
            self.assertNotIn("ViralStyle", content)
        finally:
            if os.path.exists(ass_path):
                os.remove(ass_path)

    def test_generate_ass_subtitles_no_subtitle_and_no_watermark(self):
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tf:
            ass_path = tf.name
        # Remove file so we can check if it gets created
        os.remove(ass_path)

        generate_ass_subtitles(
            segments=[],
            out_ass_path=ass_path,
            clip_start=0.0,
            clip_end=4.0,
            sub_style="no_subtitle",
            watermark_enabled=False
        )
        self.assertFalse(os.path.exists(ass_path))

    @patch("backend.renderer.generate_ass_subtitles")
    @patch("backend.renderer.run_command")
    @patch("backend.renderer._validate_rendered_video")
    def test_extract_and_format_clip_passes_watermark_params(
        self, mock_validate, mock_run, mock_ass
    ):
        def fake_run(cmd, *args, **kwargs):
            part_path = cmd[-1]
            with open(part_path, "wb") as f:
                f.write(b"x" * 2048)
            return "Done"
        mock_run.side_effect = fake_run
        mock_validate.return_value = True

        with tempfile.TemporaryDirectory() as out_dir:
            clip_info = {
                "title": "Watermark Param Test",
                "start": 0.0,
                "end": 5.0,
                "caption": "Test"
            }
            extract_and_format_clip(
                video_path="dummy.mp4",
                clip_info=clip_info,
                index=1,
                segments=[],
                out_dir=out_dir,
                watermark_enabled=True,
                source_watermark="YouTube Channel",
                account_watermark="@clipper"
            )
            self.assertTrue(mock_ass.called)
            kwargs = mock_ass.call_args[1]
            self.assertTrue(kwargs["watermark_enabled"])
            self.assertEqual(kwargs["source_watermark"], "YouTube Channel")
            self.assertEqual(kwargs["account_watermark"], "@clipper")

    def test_native_mode_keeps_word_highlight(self):
        """Regresi: konten native (id->id) tidak boleh berubah gayanya."""
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tf:
            ass_path = tf.name

        try:
            segments = [{
                "start": 1.0, "end": 3.0,
                "words": [
                    {"word": "Konsisten", "start": 1.0, "end": 1.5},
                    {"word": "itu", "start": 1.6, "end": 2.0},
                ],
            }]
            generate_ass_subtitles(
                segments, ass_path, clip_start=0.0, clip_end=4.0,
                sub_style="tiktok_viral",
            )
            with open(ass_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("ViralStyle", content)
            self.assertIn("&H0000FFFF&", content)
        finally:
            if os.path.exists(ass_path):
                os.remove(ass_path)

if __name__ == "__main__":
    unittest.main()
