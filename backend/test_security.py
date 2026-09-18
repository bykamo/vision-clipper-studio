import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.main as main_module
from backend.main import app


class LocalApiSecurityTest(unittest.TestCase):
    def test_sensitive_routes_require_local_session_cookie(self):
        with TestClient(app) as client:
            client.cookies.clear()
            for method, path in (
                (client.post, "/cancel"),
                (client.get, "/stream"),
                (client.post, "/shutdown"),
                (client.get, "/api/analyze"),
            ):
                self.assertEqual(method(path).status_code, 403, path)

            client.cookies.set("vc_session_token", "invalid")
            self.assertEqual(client.post("/cancel").status_code, 403)
            client.cookies.clear()

            session_response = client.get("/api/session")
            self.assertEqual(session_response.status_code, 204)
            session_cookie = session_response.headers["set-cookie"].lower()
            self.assertIn("httponly", session_cookie)
            self.assertIn("samesite=strict", session_cookie)
            self.assertEqual(session_response.headers["cache-control"], "no-store")

            self.assertEqual(
                client.post(
                    "/cancel", headers={"origin": "http://localhost:3000"}
                ).status_code,
                200,
            )
            self.assertEqual(
                client.post(
                    "/cancel", headers={"origin": "https://attacker.example"}
                ).status_code,
                403,
            )
            self.assertEqual(client.get("/api/analyze").status_code, 400)

    def test_fallback_root_also_sets_session_cookie(self):
        with tempfile.TemporaryDirectory() as empty_serve_dir:
            with patch.object(main_module, "SERVE_DIR", empty_serve_dir):
                with TestClient(app) as client:
                    response = client.get("/")

        self.assertEqual(response.status_code, 200)
        session_cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", session_cookie)
        self.assertIn("samesite=strict", session_cookie)

    def test_youtube_callback_does_not_require_local_session_cookie(self):
        with TestClient(app) as client:
            client.cookies.clear()
            response = client.get(
                "/api/social/youtube/callback", follow_redirects=False
            )

        self.assertEqual(response.status_code, 307)
        self.assertIn("missing_code", response.headers.get("location", ""))

    def test_youtube_callback_can_exchange_code_without_session_cookie(self):
        exchanged = {}

        def fake_exchange(code, state):
            exchanged.update(code=code, state=state)
            return True

        with patch.object(
            main_module.youtube_uploader,
            "save_credentials_from_code",
            side_effect=fake_exchange,
        ):
            with TestClient(app) as client:
                client.cookies.clear()
                response = client.get(
                    "/api/social/youtube/callback?code=test-code&state=test-state",
                    follow_redirects=False,
                )

        self.assertEqual(response.status_code, 307)
        self.assertIn("youtube_auth=success", response.headers["location"])
        self.assertEqual(exchanged, {"code": "test-code", "state": "test-state"})

    def test_youtube_upload_accepts_only_files_from_clips_directory(self):
        with tempfile.TemporaryDirectory() as clips_dir:
            nested_dir = os.path.join(clips_dir, "video")
            os.makedirs(nested_dir)
            inside_path = os.path.join(nested_dir, "clip.mp4")
            with open(inside_path, "wb") as file_handle:
                file_handle.write(b"clip")

            submitted_inside_path = os.path.join(
                nested_dir, "..", "video", "clip.mp4"
            )

            with tempfile.TemporaryDirectory() as outside_dir:
                outside_path = os.path.join(outside_dir, "outside.mp4")
                with open(outside_path, "wb") as file_handle:
                    file_handle.write(b"outside")

                symlink_path = os.path.join(clips_dir, "escape.mp4")
                os.symlink(outside_path, symlink_path)
                uploaded = {}

                def fake_upload(**kwargs):
                    uploaded["video_path"] = kwargs["video_path"]
                    return {"video_id": "123"}

                with patch.object(
                    main_module, "CLIPS_DIR", os.path.realpath(clips_dir)
                ):
                    with patch.object(
                        main_module.youtube_uploader,
                        "upload_video_to_youtube",
                        side_effect=fake_upload,
                    ):
                        with TestClient(app) as client:
                            self.assertEqual(client.get("/api/session").status_code, 204)
                            outside = client.post(
                                "/api/social/youtube/upload",
                                json={"video_path": outside_path},
                            )
                            symlink = client.post(
                                "/api/social/youtube/upload",
                                json={"video_path": symlink_path},
                            )
                            inside = client.post(
                                "/api/social/youtube/upload",
                                json={"video_path": submitted_inside_path},
                            )

        self.assertEqual(outside.status_code, 403)
        self.assertEqual(symlink.status_code, 403)
        self.assertEqual(inside.status_code, 200)
        self.assertEqual(uploaded["video_path"], os.path.realpath(inside_path))

    def test_vite_dev_proxy_is_loopback_only_and_preserves_host(self):
        vite_config_path = os.path.join(
            main_module.PROJECT_ROOT, "frontend", "vite.config.ts"
        )
        package_path = os.path.join(
            main_module.PROJECT_ROOT, "frontend", "package.json"
        )

        with open(vite_config_path, encoding="utf-8") as file_handle:
            vite_config = file_handle.read()
        with open(package_path, encoding="utf-8") as file_handle:
            package_data = json.load(file_handle)

        self.assertIn("host: '127.0.0.1'", vite_config)
        self.assertNotIn("changeOrigin: true", vite_config)
        self.assertIn("--host=127.0.0.1", package_data["scripts"]["dev"])


if __name__ == "__main__":
    unittest.main()
