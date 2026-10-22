import json
import os
import unittest
from unittest.mock import patch, MagicMock

from backend.analyzer import (
    build_viral_prompt,
    call_llm_api,
    extract_json_block,
    get_fallback_models,
    _is_permanent_llm_error,
    _is_oversize_error,
    PermanentLLMError,
    DEFAULT_FALLBACK_MODELS,
)
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
        self.assertIn("WHAT ACTUALLY TRAVELS", prompt_hook)
        self.assertIn("Tier 0", prompt_hook)
        self.assertIn("HARD DURATION BUDGET", prompt_hook)
        self.assertIn(transcript, prompt_hook)
        self.assertIn("HASHTAG STRATEGY", prompt_hook)
        self.assertIn("TIKTOK SEO", prompt_hook)
        self.assertIn("RETENTION ENGINEERING", prompt_hook)
        self.assertIn("SCORING CALIBRATION", prompt_hook)
        self.assertIn("HOOK LINE (OVERLAY 3 DETIK PERTAMA)", prompt_hook)
        self.assertNotIn("keranjang kuning", prompt_hook)

        prompt_affiliate = build_viral_prompt(transcript, num_clips=2, mode="affiliate")
        self.assertIn("AFFILIATE SALES", prompt_affiliate)
        self.assertIn("SEGMENT SELECTION CRITERIA", prompt_affiliate)
        self.assertIn("HASHTAG STRATEGY", prompt_affiliate)
        self.assertIn("TIKTOK SEO", prompt_affiliate)
        self.assertIn("RETENTION ENGINEERING", prompt_affiliate)
        self.assertIn("SCORING CALIBRATION", prompt_affiliate)
        self.assertIn("TITLE OPTIONS (HOOK OVERLAY)", prompt_affiliate)
        self.assertIn("keranjang kuning", prompt_affiliate)

    def test_viral_prompt_uses_shared_duration_budget(self):
        """Prompt text must be driven by content_rules constants, not hardcoded."""
        from backend.content_rules import MAX_DURATION, MIN_DURATION, TARGET_DURATION

        prompt_hook = build_viral_prompt("[00:00:00 --> 00:00:10] Halo", 3, mode="hook")
        self.assertIn(
            f"between {int(MIN_DURATION['hook'])} and {int(TARGET_DURATION['hook'][1])} seconds",
            prompt_hook,
        )
        self.assertIn(f"hard ceiling: {int(MAX_DURATION['hook'])} seconds", prompt_hook)

        prompt_affiliate = build_viral_prompt("[00:00:00 --> 00:00:10] Halo", 3, mode="affiliate")
        lo, hi = TARGET_DURATION["affiliate"]
        self.assertIn(f"{int(lo)}-{int(hi)} seconds per clip", prompt_affiliate)
        self.assertIn(f"hard ceiling {int(MAX_DURATION['affiliate'])}s", prompt_affiliate)

    def test_env_float_temperature(self):
        from backend.analyzer import env_float
        with patch.dict(os.environ, {"ROUTER_LLM_TEMPERATURE": "0.55"}):
            self.assertEqual(env_float("ROUTER_LLM_TEMPERATURE", 0.4), 0.55)
        self.assertEqual(env_float("ROUTER_LLM_TEMPERATURE_NOT_SET", 0.4), 0.4)
        with patch.dict(os.environ, {"ROUTER_LLM_TEMPERATURE": "bukan-angka"}):
            self.assertEqual(env_float("ROUTER_LLM_TEMPERATURE", 0.4), 0.4)

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

    def test_fallback_pool_excludes_primary_and_honors_env(self):
        # Defaults are used when no env override, and the primary is filtered out.
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("ROUTER_FALLBACK_MODELS", None)
            pool = get_fallback_models("model-primary")
            self.assertEqual(pool, DEFAULT_FALLBACK_MODELS)
            self.assertNotIn("model-primary", get_fallback_models("tip/gemini-3.8-flash"))
        with patch.dict("os.environ", {"ROUTER_FALLBACK_MODELS": "a/b, c/d ,, e/f"}):
            self.assertEqual(get_fallback_models("a/b"), ["c/d", "e/f"])

    def test_permanent_error_classification(self):
        self.assertTrue(_is_permanent_llm_error(400, "User location is not supported"))
        self.assertTrue(_is_permanent_llm_error(404, "No active credentials for provider: github"))
        self.assertTrue(_is_permanent_llm_error(413, "Request too large ... Limit 8000"))
        self.assertFalse(_is_permanent_llm_error(429, "rate limited"))
        self.assertFalse(_is_permanent_llm_error(500, "internal server error"))
        self.assertFalse(_is_permanent_llm_error(200, ""))

    def test_oversize_error_detection(self):
        self.assertTrue(_is_oversize_error(413, ""))
        self.assertTrue(_is_oversize_error(400, "please reduce your message size"))
        self.assertFalse(_is_oversize_error(429, "rate limited"))

    @patch("requests.post")
    def test_permanent_error_raises_without_endless_retry(self, mock_post):
        """All-models-permanent failures raise PermanentLLMError after trying each once."""
        import requests

        def make_fail(status, message):
            m = MagicMock()
            m.status_code = status
            m.json.return_value = {"error": {"message": message}}
            m.text = message
            err = requests.HTTPError(f"{status} error")
            m.raise_for_status.side_effect = err
            return m

        mock_post.side_effect = [
            make_fail(400, "User location is not supported"),
            make_fail(413, "Request too large"),
            make_fail(404, "No active credentials for provider: x"),
            make_fail(403, "invalid api key"),
        ]
        with self.assertRaises(PermanentLLMError):
            call_llm_api("prompt", "model-primary", "https://api.example.com", "fake-key")
        # primary + 3 fallbacks = 4 attempts, each tried once (no compact retry w/o compact_prompt)
        self.assertEqual(mock_post.call_count, 4)

    @patch("requests.post")
    def test_oversize_retries_same_model_with_compact_prompt(self, mock_post):
        """A 413 triggers one retry of the SAME model using the compact prompt."""
        import requests

        oversize = MagicMock()
        oversize.status_code = 413
        oversize.json.return_value = {"error": {"message": "Request too large for model"}}
        oversize.text = "Request too large"
        oversize.raise_for_status.side_effect = requests.HTTPError("413")

        ok = MagicMock()
        ok.status_code = 200
        ok.text = '{"choices": [{"message": {"content": "{\\"clips\\": []}"}}]}'
        ok.json.return_value = {"choices": [{"message": {"content": '{"clips": []}'}}]}

        mock_post.side_effect = [oversize, ok]

        result = call_llm_api(
            "FULL prompt", "model-primary", "https://api.example.com", "fake-key",
            compact_prompt="COMPACT prompt",
        )
        self.assertEqual(result, '{"clips": []}')
        self.assertEqual(mock_post.call_count, 2)
        # Second call must use the compact prompt on the same primary model.
        second_payload = mock_post.call_args_list[1].kwargs["json"]
        self.assertEqual(second_payload["model"], "model-primary")
        self.assertEqual(second_payload["messages"][0]["content"], "COMPACT prompt")

    @patch("requests.post")
    def test_auth_error_aborts_chain_immediately(self, mock_post):
        """401/403 means the key itself is bad: stop after ONE request.

        Trying every model with the same rejected credential only burns time and
        can trigger gateway rate-limit/IP bans.
        """
        import requests

        unauthorized = MagicMock()
        unauthorized.status_code = 401
        unauthorized.json.return_value = {
            "error": {"message": "Invalid API key", "type": "authentication_error"}
        }
        unauthorized.text = "Invalid API key"
        unauthorized.raise_for_status.side_effect = requests.HTTPError("401")

        mock_post.return_value = unauthorized

        with self.assertRaises(PermanentLLMError) as ctx:
            call_llm_api("prompt", "model-primary", "https://api.example.com", "bad-key")
        self.assertEqual(mock_post.call_count, 1)
        self.assertIn("API key", str(ctx.exception))

    @patch("requests.post")
    def test_empty_model_names_are_never_sent(self, mock_post):
        """An empty model entry in the pool must be skipped, not posted."""
        ok = MagicMock()
        ok.status_code = 200
        ok.text = '{"choices": [{"message": {"content": "ok"}}]}'
        ok.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_post.return_value = ok

        with patch.dict("os.environ", {"ROUTER_FALLBACK_MODELS": "a/b, ,c/d"}):
            call_llm_api("prompt", "", "https://api.example.com", "fake-key")

        sent_models = [c.kwargs["json"]["model"] for c in mock_post.call_args_list]
        self.assertNotIn("", sent_models)
        self.assertEqual(sent_models, ["a/b"])

    def test_missing_credentials_raise_permanent_error(self):
        """Empty endpoint/key must fail fast with a config hint, no HTTP call."""
        with self.assertRaises(PermanentLLMError):
            call_llm_api("prompt", "model-primary", "", "fake-key")
        with self.assertRaises(PermanentLLMError):
            call_llm_api("prompt", "model-primary", "https://api.example.com", "")

    def test_default_fallback_pool_has_no_empty_entries(self):
        self.assertTrue(all(m.strip() for m in DEFAULT_FALLBACK_MODELS))


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
