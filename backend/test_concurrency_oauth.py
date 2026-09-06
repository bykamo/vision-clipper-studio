import asyncio
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


if __name__ == "__main__":
    unittest.main()
