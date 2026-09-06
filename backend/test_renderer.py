import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from backend.renderer import _validate_rendered_video, extract_and_format_clip


class RendererIntegrityTest(unittest.TestCase):
    def test_validate_rendered_video_rejects_nonexistent_or_empty_file(self):
        self.assertFalse(_validate_rendered_video("/nonexistent/path/video.mp4"))
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"")
            tf.flush()
            self.assertFalse(_validate_rendered_video(tf.name))

    @patch("backend.renderer.subprocess.run")
    def test_validate_rendered_video_accepts_valid_probe(self, mock_run):
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

    @patch("backend.renderer.apply_smart_crop")
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


if __name__ == "__main__":
    unittest.main()
