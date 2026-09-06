import asyncio
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from backend.downloader import _final_download_path, _selected_video_height
from backend.main import analyze, app
from backend.worker import _parse_render_indices


class WorkflowSelfCheck(unittest.TestCase):
    def test_selected_video_height_uses_video_stream(self):
        info = {
            "requested_formats": [
                {"format_id": "399", "vcodec": "av01", "height": 1080},
                {"format_id": "251", "vcodec": "none", "height": None},
            ]
        }
        self.assertEqual(_selected_video_height(info), 1080)

    def test_selected_video_height_rejects_360p_fallback(self):
        info = {"format_id": "18", "vcodec": "avc1", "height": 360}
        self.assertEqual(_selected_video_height(info), 360)

    def test_final_download_path_prefers_actual_merged_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            actual_path = os.path.join(temp_dir, "video.mp4")
            with open(actual_path, "wb") as output:
                output.write(b"video")

            ydl = MagicMock()
            ydl.prepare_filename.return_value = os.path.join(temp_dir, "video.webm")
            info = {"requested_downloads": [{"filepath": actual_path}]}
            self.assertEqual(_final_download_path(ydl, info), actual_path)

    def test_render_indices_are_validated(self):
        self.assertEqual(_parse_render_indices("1,3", 4), [1, 3])
        for value in ("", "1,1", "0", "5", "nope"):
            with self.assertRaises(ValueError):
                _parse_render_indices(value, 4)

    def test_workflow_routes_exist(self):
        routes = {
            (route.path, tuple(sorted(route.methods or [])))
            for route in app.routes
            if hasattr(route, "methods")
        }
        self.assertIn(("/api/analyze", ("GET",)), routes)
        self.assertIn(("/api/render-selected", ("POST",)), routes)

    def test_analyze_rejects_empty_source(self):
        mock_req = MagicMock()
        response = asyncio.run(analyze(request=mock_req, source=""))
        self.assertEqual(response.status_code, 400)

    def test_ass_escaping_and_word_filtering(self):
        from backend.renderer import _escape_ass_text, generate_ass_subtitles
        escaped = _escape_ass_text("Halo {teman} \\ dunia\n!")
        self.assertNotIn("{", escaped)
        self.assertNotIn("}", escaped)
        self.assertNotIn("\\", escaped)
        self.assertNotIn("\n", escaped)

        with tempfile.TemporaryDirectory() as tmpdir:
            ass_path = os.path.join(tmpdir, "test.ass")
            segments = [
                {
                    "start": 10.0,
                    "end": 20.0,
                    "text": "sebelum dan sesudah",
                    "words": [
                        {"word": "sebelum", "start": 8.0, "end": 9.5},
                        {"word": "dalam", "start": 11.0, "end": 12.0},
                        {"word": "sesudah", "start": 21.0, "end": 22.0},
                    ]
                }
            ]
            generate_ass_subtitles(segments, ass_path, 10.0, 15.0)
            self.assertTrue(os.path.exists(ass_path))
            with open(ass_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("dalam", content)
            self.assertNotIn("sebelum", content)
            self.assertNotIn("sesudah", content)

    def test_ffmpeg_and_ffprobe_resolvers(self):
        from backend.utils import get_ffmpeg_binary, get_ffprobe_binary
        ffmpeg = get_ffmpeg_binary()
        ffprobe = get_ffprobe_binary()
        self.assertTrue(isinstance(ffmpeg, str) and len(ffmpeg) > 0)
        self.assertTrue(isinstance(ffprobe, str) and len(ffprobe) > 0)


if __name__ == "__main__":
    unittest.main()
