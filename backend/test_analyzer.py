import json
import unittest
from unittest.mock import patch, MagicMock

from backend.analyzer import build_viral_prompt, call_llm_api, extract_json_block
from backend.utils import parse_timestamp_to_seconds, get_ffprobe_binary


class AnalyzerTest(unittest.TestCase):
    def test_extract_json_block_from_code_fence(self):
        raw = 'Berikut adalah hasilnya:\n```json\n{"clips": [{"title": "Klip Viral 1"}]}\n```\nSemoga bermanfaat!'
        extracted = extract_json_block(raw)
        self.assertEqual(extracted, {"clips": [{"title": "Klip Viral 1"}]})

    def test_extract_json_block_from_raw_braces(self):
        raw = 'Analisis selesai: {"clips": [{"title": "Raw Braces"}]} Silakan dicek.'
        extracted = extract_json_block(raw)
        self.assertEqual(extracted, {"clips": [{"title": "Raw Braces"}]})

    def test_extract_json_block_returns_empty_on_invalid(self):
        raw = "Ini teks biasa tanpa format JSON sama sekali."
        with self.assertRaises(RuntimeError):
            extract_json_block(raw)

    def test_build_viral_prompt_modes(self):
        transcript = "[00:00:00 --> 00:00:10] Halo dunia"
        prompt_hook = build_viral_prompt(transcript, num_clips=3, mode="hook")
        self.assertIn("VIRAL DETECTION FRAMEWORK", prompt_hook)
        self.assertIn(transcript, prompt_hook)

        prompt_affiliate = build_viral_prompt(transcript, num_clips=2, mode="affiliate")
        self.assertIn("AFFILIATE SALES", prompt_affiliate)

    @patch("requests.post")
    def test_call_llm_api_standard_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"choices": [{"message": {"content": "{\\"clips\\": []}"}}]}'
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"clips": []}'}}]
        }
        mock_post.return_value = mock_resp

        result = call_llm_api("prompt text", "model-primary", "https://api.example.com", "fake-key")
        self.assertEqual(result, '{"clips": []}')
        self.assertEqual(mock_post.call_count, 1)

    @patch("requests.post")
    def test_call_llm_api_sse_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        sse_text = (
            'data: {"choices": [{"delta": {"content": "Halo "}}]}\n'
            'data: {"choices": [{"delta": {"content": "Dunia"}}]}\n'
            'data: [DONE]\n'
        )
        mock_resp.text = sse_text
        mock_post.return_value = mock_resp

        result = call_llm_api("prompt text", "model-primary", "https://api.example.com", "fake-key")
        self.assertEqual(result, "Halo Dunia")

    @patch("requests.post")
    def test_call_llm_api_fallback_on_error(self, mock_post):
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        mock_fail.json.side_effect = Exception("Not JSON")
        mock_fail.text = "Internal Server Error"
        import requests
        http_err = requests.HTTPError("500 Server Error")
        mock_fail.raise_for_status.side_effect = http_err

        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.text = '{"choices": [{"message": {"content": "Fallback success"}}]}'
        mock_ok.json.return_value = {
            "choices": [{"message": {"content": "Fallback success"}}]
        }

        mock_post.side_effect = [mock_fail, mock_ok]

        result = call_llm_api("prompt text", "model-primary", "https://api.example.com", "fake-key")
        self.assertEqual(result, "Fallback success")
        self.assertEqual(mock_post.call_count, 2)


class UtilsEnhancementTest(unittest.TestCase):
    def test_parse_timestamp_to_seconds_handles_comma_decimals(self):
        self.assertAlmostEqual(parse_timestamp_to_seconds("00:01:23,456"), 83.456, places=3)
        self.assertAlmostEqual(parse_timestamp_to_seconds("01:23,456"), 83.456, places=3)
        self.assertAlmostEqual(parse_timestamp_to_seconds("23,456"), 23.456, places=3)

    @patch("backend.utils.get_ffmpeg_binary")
    @patch("shutil.which")
    def test_get_ffprobe_binary_does_not_corrupt_parent_folder(self, mock_which, mock_ffmpeg):
        mock_which.return_value = None  # sys_ffprobe not found directly
        mock_ffmpeg.return_value = "/opt/ffmpeg_custom/bin/ffmpeg"
        with patch("os.path.exists", return_value=True):
            probe = get_ffprobe_binary()
            self.assertEqual(probe, "/opt/ffmpeg_custom/bin/ffprobe")


if __name__ == "__main__":
    unittest.main()
