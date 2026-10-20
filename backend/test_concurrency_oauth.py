import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from backend.main import (
    _worker_is_active,
    _reserve_worker_slot,
    _release_worker_slot,
    analyze,
    stream,
    youtube_callback
)
from backend import youtube_uploader


# Kredensial dummy: CI tidak punya file .env, jadi get_auth_url() akan raise
# ValueError tanpa ini. Nilainya tidak dipakai untuk request jaringan apa pun.
_OAUTH_ENV = {
    "YOUTUBE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
    "YOUTUBE_CLIENT_SECRET": "test-client-secret",
}


class ConcurrencyAndOAuthTest(unittest.TestCase):
    def setUp(self):
        # Reset state aktif
        import backend.main as main_mod
        with main_mod._WORKER_LOCK:
            main_mod._ACTIVE_JOB = None

    def tearDown(self):
        import backend.main as main_mod
        with main_mod._WORKER_LOCK:
            main_mod._ACTIVE_JOB = None

    def test_worker_slot_reservation_blocks_concurrent_request(self):
        job_id = _reserve_worker_slot()
        self.assertTrue(_worker_is_active())

        # Reservasi kedua harus raise RuntimeError
        with self.assertRaises(RuntimeError):
            _reserve_worker_slot()

        # Slot dilepas
        _release_worker_slot(job_id)
        self.assertFalse(_worker_is_active())

    def test_analyze_returns_409_when_worker_is_already_active(self):
        job_id = _reserve_worker_slot()
        mock_req = MagicMock()
        response = asyncio.run(analyze(request=mock_req, source="https://youtube.com/watch?v=12345"))
        self.assertEqual(response.status_code, 409)
        _release_worker_slot(job_id)

    def test_legacy_stream_returns_409_when_worker_is_already_active(self):
        job_id = _reserve_worker_slot()
        mock_req = MagicMock()
        response = asyncio.run(stream(request=mock_req, source="https://youtube.com/watch?v=12345"))
        self.assertEqual(response.status_code, 409)
        _release_worker_slot(job_id)

    def test_youtube_oauth_state_generation_and_validation(self):
        state = youtube_uploader.generate_oauth_state()
        self.assertTrue(len(state) > 16)
        
        # Validasi pertama harus berhasil (consume state)
        self.assertTrue(youtube_uploader.verify_and_consume_oauth_state(state))
        
        # Penggunaan kedua harus gagal (single-use CSRF prevention)
        self.assertFalse(youtube_uploader.verify_and_consume_oauth_state(state))

    def test_youtube_callback_rejects_missing_or_invalid_state(self):
        # State kosong
        res = asyncio.run(youtube_callback(code="auth_code_123", state=""))
        self.assertEqual(res.status_code, 307)
        self.assertIn("Missing+OAuth+state", res.headers.get("location", ""))

        # State palsu / tidak terdaftar
        res_invalid = asyncio.run(youtube_callback(code="auth_code_123", state="unregistered_fake_state"))
        self.assertEqual(res_invalid.status_code, 307)
        self.assertIn("youtube_auth=failed", res_invalid.headers.get("location", ""))

    @patch.dict(os.environ, _OAUTH_ENV)
    def test_youtube_oauth_exchange_reuses_pkce_verifier(self):
        _, state = youtube_uploader.get_auth_url()
        verifier = youtube_uploader._PENDING_OAUTH_STATES[state].get("code_verifier")
        self.assertTrue(verifier)

        class PkceCheckingFlow:
            def __init__(self):
                self.code_verifier = None
                self.credentials = MagicMock(
                    token="access-token",
                    refresh_token="refresh-token",
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id="client-id",
                    client_secret="client-secret",
                    scopes=youtube_uploader.SCOPES,
                )

            def fetch_token(self, code):
                if self.code_verifier != verifier:
                    raise AssertionError("PKCE verifier was not reused for token exchange")

        flow = PkceCheckingFlow()
        with tempfile.TemporaryDirectory() as tempdir:
            token_file = os.path.join(tempdir, "youtube-token.json")
            with patch.object(youtube_uploader, "HOME_TOKEN_FILE", token_file), \
                 patch.object(youtube_uploader.Flow, "from_client_config", return_value=flow), \
                 patch.object(youtube_uploader.requests, "post", side_effect=AssertionError("OAuth flow must not fall back")):
                self.assertTrue(youtube_uploader.save_credentials_from_code("auth-code", state=state))

    @patch.dict(os.environ, _OAUTH_ENV)
    def test_youtube_oauth_fallback_reuses_pkce_verifier(self):
        _, state = youtube_uploader.get_auth_url()
        verifier = youtube_uploader._PENDING_OAUTH_STATES[state].get("code_verifier")
        self.assertTrue(verifier)

        class FailingFlow:
            code_verifier = None

            def fetch_token(self, code):
                raise RuntimeError("simulated Flow failure")

        response = MagicMock()
        response.json.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
        }

        def post_token(url, data):
            if data.get("code_verifier") != verifier:
                raise AssertionError("PKCE verifier was not sent to the token endpoint")
            return response

        with tempfile.TemporaryDirectory() as tempdir:
            token_file = os.path.join(tempdir, "youtube-token.json")
            with patch.object(youtube_uploader, "HOME_TOKEN_FILE", token_file), \
                 patch.object(youtube_uploader.Flow, "from_client_config", return_value=FailingFlow()), \
                 patch.object(youtube_uploader.requests, "post", side_effect=post_token):
                self.assertTrue(youtube_uploader.save_credentials_from_code("auth-code", state=state))

    def test_channel_info_prefers_highest_available_thumbnail(self):
        channel = MagicMock()
        channel.channels().list().execute.return_value = {
            "items": [{
                "id": "UC123",
                "snippet": {
                    "title": "Vision Channel",
                    "thumbnails": {
                        "default": {"url": "https://img.youtube.com/default.jpg"},
                        "medium": {"url": "https://img.youtube.com/medium.jpg"},
                        "high": {"url": "https://img.youtube.com/high.jpg"},
                    },
                },
                "statistics": {},
            }],
        }

        with patch.object(youtube_uploader, "get_saved_credentials", return_value=MagicMock()), \
             patch.object(youtube_uploader, "build", return_value=channel):
            info = youtube_uploader.get_channel_info()

        self.assertEqual(info["thumbnail"], "https://img.youtube.com/high.jpg")


if __name__ == "__main__":
    unittest.main()
