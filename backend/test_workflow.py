import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from backend.downloader import _final_download_path, _selected_video_height
import backend.main as main_module
from backend.main import (
    RenderedClipsFolderError,
    _load_rendered_clips,
    _parse_rendered_clip_metadata,
    analyze,
    app,
)
from backend.worker import _parse_render_indices
from backend.config_wizard import (
    get_ai_config,
    save_ai_config,
    test_ai_connection,
    test_groq_connection,
)


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
        self.assertIn(("/api/rendered-clips/load", ("POST",)), routes)
        self.assertIn(("/api/pick-folder", ("POST",)), routes)
        self.assertIn(("/api/ai-config", ("GET",)), routes)
        self.assertIn(("/api/ai-config", ("POST",)), routes)
        self.assertIn(("/api/ai-config/test", ("POST",)), routes)
        self.assertIn(("/api/ai-config/test-groq", ("POST",)), routes)

    def test_rendered_clip_metadata_parses_multiline_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = os.path.join(temp_dir, "01_clip.txt")
            with open(metadata_path, "w", encoding="utf-8") as metadata_file:
                metadata_file.write(
                    "Title Options:\n"
                    "- Judul Utama\n"
                    "- Judul Cadangan\n\n"
                    "Caption:\n"
                    "Baris pertama\n"
                    "Baris kedua\n\n"
                    "Hashtags:\n"
                    "#fyp #viral #Shorts"
                )

            metadata = _parse_rendered_clip_metadata(metadata_path)

        self.assertEqual(metadata["title"], "Judul Utama")
        self.assertEqual(metadata["caption"], "Baris pertama\nBaris kedua")
        self.assertEqual(metadata["hashtags"], ["#fyp", "#viral", "#Shorts"])

    def test_load_rendered_clips_sorts_and_falls_back_without_sidecar(self):
        with tempfile.TemporaryDirectory() as clips_dir:
            project_dir = os.path.join(clips_dir, "project")
            nested_dir = os.path.join(project_dir, "nested")
            os.makedirs(nested_dir)
            for name in ("10_Tenth.mp4", "02_Second.mp4", "Alpha_Clip.mov"):
                with open(os.path.join(project_dir, name), "wb") as video_file:
                    video_file.write(b"video")
            with open(os.path.join(nested_dir, "01_Nested.mp4"), "wb") as video_file:
                video_file.write(b"nested")
            with open(os.path.join(project_dir, "notes.json"), "w", encoding="utf-8") as notes:
                notes.write("{}")
            with open(os.path.join(project_dir, "02_Second.txt"), "w", encoding="utf-8") as metadata_file:
                metadata_file.write(
                    "Title Options:\n- Metadata Title\n\n"
                    "Caption:\nMetadata caption\n\n"
                    "Hashtags:\n#one #two"
                )

            with patch.object(main_module, "CLIPS_DIR", os.path.realpath(clips_dir)):
                result = _load_rendered_clips(project_dir)

        self.assertEqual(
            [clip["filename"] for clip in result["clips"]],
            ["02_Second.mp4", "10_Tenth.mp4", "Alpha_Clip.mov"],
        )
        self.assertEqual(result["clips"][0]["title"], "Metadata Title")
        self.assertEqual(result["clips"][0]["caption"], "Metadata caption")
        self.assertEqual(result["clips"][0]["hashtags"], ["#one", "#two"])
        self.assertEqual(result["clips"][1]["title"], "Tenth")
        self.assertEqual(result["clips"][2]["title"], "Alpha Clip")
        self.assertEqual([clip["id"] for clip in result["clips"]], ["1", "2", "3"])

    def test_load_rendered_clips_resolves_when_video_file_inside_folder_is_selected(self):
        with tempfile.TemporaryDirectory() as clips_dir:
            project_dir = os.path.join(clips_dir, "project")
            os.makedirs(project_dir)
            video_one = os.path.join(project_dir, "01_Clip.mp4")
            video_two = os.path.join(project_dir, "02_Clip.mp4")
            for path in (video_one, video_two):
                with open(path, "wb") as file_handle:
                    file_handle.write(b"video")

            with patch.object(main_module, "CLIPS_DIR", os.path.realpath(clips_dir)):
                # Passing a video file directly resolves to its parent project folder
                result = _load_rendered_clips(video_one)

        self.assertEqual(result["output_dir"], os.path.realpath(project_dir))
        self.assertEqual(len(result["clips"]), 2)
        self.assertEqual(result["clips"][0]["filename"], "01_Clip.mp4")

    def test_load_rendered_clips_rejects_empty_project(self):
        with tempfile.TemporaryDirectory() as clips_dir:
            project_dir = os.path.join(clips_dir, "empty")
            os.makedirs(project_dir)
            with patch.object(main_module, "CLIPS_DIR", os.path.realpath(clips_dir)):
                with self.assertRaises(RenderedClipsFolderError) as context:
                    _load_rendered_clips(project_dir)

        self.assertEqual(context.exception.status_code, 404)

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

    def test_get_and_save_ai_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test getting default config when .env doesn't exist
            cfg = get_ai_config(project_root=temp_dir)
            self.assertIn("presets", cfg)
            self.assertIn("openrouter", cfg["presets"])

            # Test saving config with preset
            updated = save_ai_config(
                provider="openai",
                api_key="sk-test-secret-key-123456",
                groq_key="gsk_test_groq_secret_key_12345",
                project_root=temp_dir,
            )
            self.assertEqual(updated["provider"], "openai")
            self.assertEqual(updated["endpoint"], "https://api.openai.com/v1/chat/completions")
            self.assertEqual(updated["model"], "gpt-4o-mini")
            self.assertTrue(updated["api_key_set"])
            self.assertTrue(updated["groq_key_set"])
            self.assertTrue(updated["ready"])
            self.assertTrue(updated["groq_ready"])
            self.assertIn("...", updated["api_key_masked"])
            self.assertNotIn("123456", updated["api_key_masked"])

            # Test reading back with get_ai_config
            reread = get_ai_config(project_root=temp_dir)
            self.assertEqual(reread["provider"], "openai")
            self.assertEqual(reread["model"], "gpt-4o-mini")
            self.assertTrue(reread["ready"])

    def test_test_ai_connection_mocked(self):
        with patch("requests.post") as mock_post:
            # 1. Success response
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "PONG"}}]
            }
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            res = test_ai_connection(
                endpoint="https://openrouter.ai/api/v1",
                api_key="sk-test",
                model="test-model"
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["reply"], "PONG")

            # Check normalization to /chat/completions
            called_url = mock_post.call_args[0][0]
            self.assertTrue(called_url.endswith("/chat/completions"))

            # 2. Missing parameter validation
            res_no_ep = test_ai_connection(endpoint="", api_key="sk-test", model="test")
            self.assertFalse(res_no_ep["ok"])

    def test_test_groq_connection_mocked(self):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "data": [{"id": "whisper-large-v3-turbo"}, {"id": "llama-3.3-70b-versatile"}]
            }
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            res = test_groq_connection(groq_key="gsk_real_key_example")
            self.assertTrue(res["ok"])
            self.assertIn("whisper-large-v3-turbo", res["whisper_models"])

            # Missing key
            res_empty = test_groq_connection(groq_key="")
            self.assertFalse(res_empty["ok"])

    def test_ai_config_api_endpoints(self):
        mock_req = MagicMock()
        get_res = asyncio.run(main_module.api_get_ai_config(mock_req))
        self.assertEqual(get_res.status_code, 200)
        data = json.loads(get_res.body)
        self.assertIn("provider", data)
        self.assertIn("presets", data)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("backend.config_wizard._get_env_path", return_value=os.path.join(temp_dir, ".env")):
                mock_post_req = MagicMock()
                async def mock_json():
                    return {
                        "provider": "openrouter",
                        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                        "model": "google/gemini-2.0-flash-exp:free",
                        "api_key": "sk-or-v1-testkey12345",
                    }
                mock_post_req.json = mock_json

                post_res = asyncio.run(main_module.api_save_ai_config(mock_post_req))
                self.assertEqual(post_res.status_code, 200)
                saved_data = json.loads(post_res.body)
                self.assertEqual(saved_data["provider"], "openrouter")
                self.assertTrue(saved_data["api_key_set"])

    def test_worker_retry_backoff_sleep_called(self):
        import backend.worker as worker_module
        with patch.object(sys, "argv", ["worker.py", "--file", "dummy.mp4", "--analyze-only"]), \
             patch("backend.worker.get_video_file", return_value="dummy.mp4"), \
             patch("backend.worker.transcribe_video", return_value=[{"start": 0, "end": 10, "text": "test"}]), \
             patch("backend.worker.build_transcript_text", return_value="test transcript"), \
             patch("backend.worker.build_viral_prompt", return_value="prompt"), \
             patch("backend.worker.call_llm_api", side_effect=[Exception("429 Too Many Requests"), '{"clips": [{"start": 0, "end": 10, "title": "Test"}]}']), \
             patch("backend.worker.time.sleep") as mock_sleep, \
             patch("os._exit", side_effect=SystemExit(0)) as mock_exit:
            with self.assertRaises(SystemExit):
                worker_module.main()
            mock_sleep.assert_called_once_with(1)
            mock_exit.assert_called_once_with(0)

    def test_render_selected_validates_framing_mode(self):
        mock_req = MagicMock()
        async def mock_json():
            return {
                "analysis_id": "analysis_123456",
                "clip_indices": [1],
                "framing_mode": "invalid_mode"
            }
        mock_req.json = mock_json

        res = asyncio.run(main_module.render_selected(mock_req))
        self.assertEqual(res.status_code, 400)

        # framing_mode "split_screen" should be valid
        async def mock_json_split():
            return {
                "analysis_id": "analysis_123456",
                "clip_indices": [1],
                "framing_mode": "split_screen",
                "sub_position": 75,
                "show_emoji": True
            }
        mock_req.json = mock_json_split
        # Fails with 404 because analysis file doesn't exist, NOT 400 invalid framing mode
        res_split = asyncio.run(main_module.render_selected(mock_req))
        self.assertEqual(res_split.status_code, 404)

    def test_analyze_validates_language_params(self):
        mock_req = MagicMock()
        # Invalid source_lang should return 400
        res_invalid_src = asyncio.run(main_module.analyze(mock_req, source="dummy.mp4", source_lang="klingon"))
        self.assertEqual(res_invalid_src.status_code, 400)

        # Invalid target_lang should return 400
        res_invalid_tgt = asyncio.run(main_module.analyze(mock_req, source="dummy.mp4", target_lang="valyrian"))
        self.assertEqual(res_invalid_tgt.status_code, 400)

    def test_worker_cli_language_arguments(self):
        import argparse
        import backend.worker as worker_module

        # Test worker parses --source-lang and --target-lang correctly
        with patch.object(sys, "argv", ["worker.py", "--file", "dummy.mp4", "--source-lang", "en", "--target-lang", "id", "--analyze-only"]), \
             patch("backend.worker.get_video_file", return_value="dummy.mp4"), \
             patch("backend.worker.transcribe_video", return_value=[{"start": 0, "end": 10, "text": "test"}]) as mock_transcribe, \
             patch("backend.worker.build_transcript_text", return_value="test transcript"), \
             patch("backend.worker.build_viral_prompt", return_value="prompt"), \
             patch("backend.worker.call_llm_api", return_value='{"clips": [{"start": 0, "end": 10, "title": "Test"}]}'), \
             patch("os._exit", side_effect=SystemExit(0)):
            with self.assertRaises(SystemExit):
                worker_module.main()
            mock_transcribe.assert_called_once()
            call_kwargs = mock_transcribe.call_args[1]
            self.assertEqual(call_kwargs.get("source_lang"), "en")
            self.assertEqual(call_kwargs.get("target_lang"), "id")


if __name__ == "__main__":
    unittest.main()
