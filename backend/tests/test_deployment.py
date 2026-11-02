import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

FRONTEND_ORIGIN = "https://prismflow.thanabh.at"
API_ORIGIN = "https://prismflow-api.thanabh.at"
WEBSOCKET_URL = "wss://prismflow-api.thanabh.at/ws"
TEST_SECRET = "test-only-signing-key-" + "x" * 32

with patch.dict(os.environ, {
    "JWT_SECRET": TEST_SECRET,
    "COOKIE_SECURE": "true",
    "ALLOWED_ORIGINS": FRONTEND_ORIGIN,
    "EXTERNAL_AUTH_URL": "",
}):
    from fastapi.testclient import TestClient
    from main import app
    from starlette.websockets import WebSocketDisconnect


class SecretConfigurationTests(unittest.TestCase):
    def run_auth(self, overrides: dict[str, str]) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        for key in ("JWT_SECRET", "COOKIE_SECURE", "RENDER"):
            env.pop(key, None)
        env.update(overrides)
        # Compare fingerprints without printing signing keys.
        return subprocess.run(
            [sys.executable, "-c", (
                "import auth, hashlib; "
                "print(hashlib.sha256(auth.JWT_SECRET.encode()).hexdigest())"
            )],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_local_default_generates_a_different_secret_per_process(self):
        first = self.run_auth({})
        second = self.run_auth({})
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotEqual(first.stdout, second.stdout)

    def test_deployment_requires_a_private_secret(self):
        for overrides in ({"RENDER": "true"}, {"COOKIE_SECURE": "true"}):
            with self.subTest(overrides=overrides):
                result = self.run_auth(overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Set JWT_SECRET", result.stderr)

    def test_short_secret_is_rejected(self):
        result = self.run_auth({"JWT_SECRET": "test-only-short-key"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least 32 bytes", result.stderr)

    def test_configured_secret_works_on_render(self):
        result = self.run_auth({"RENDER": "true", "JWT_SECRET": TEST_SECRET})
        self.assertEqual(result.returncode, 0, result.stderr)


class DeploymentRequestTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url=API_ORIGIN)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def login(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "trader", "password": "crypto2026"},
            headers={"Origin": FRONTEND_ORIGIN},
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_health_check_is_public(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_stream_requires_authentication(self):
        self.assertEqual(self.client.get("/api/status").status_code, 401)

    def test_cookie_login_session_and_logout_across_origins(self):
        response = self.login()
        self.assertEqual(response.headers["access-control-allow-origin"], FRONTEND_ORIGIN)
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")
        cookie = response.headers["set-cookie"]
        for attribute in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
            self.assertIn(attribute, cookie)
        self.assertNotIn("Domain=", cookie)
        self.assertEqual(self.client.get("/api/auth/me").json()["username"], "trader")
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_frontend_can_preflight_a_json_post(self):
        response = self.client.options("/api/auth/login", headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], FRONTEND_ORIGIN)

    def test_other_origins_cannot_pass_preflight(self):
        for origin in ("https://untrusted.example", FRONTEND_ORIGIN + ".untrusted.example", "http://localhost:5173"):
            with self.subTest(origin=origin):
                response = self.client.options("/api/auth/login", headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                })
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("access-control-allow-origin", response.headers)

    def test_websocket_requires_authentication(self):
        with self.assertRaises(WebSocketDisconnect) as caught:
            with self.client.websocket_connect(WEBSOCKET_URL, headers={"Origin": FRONTEND_ORIGIN}):
                pass
        self.assertEqual(caught.exception.code, 1008)

    def test_websocket_rejects_untrusted_origin_even_with_valid_cookie(self):
        self.login()
        with self.assertRaises(WebSocketDisconnect) as caught:
            with self.client.websocket_connect(WEBSOCKET_URL, headers={"Origin": "https://untrusted.example"}):
                pass
        self.assertEqual(caught.exception.code, 1008)

    def test_authenticated_frontend_can_connect_to_perspective(self):
        self.login()
        with self.client.websocket_connect(WEBSOCKET_URL, headers={"Origin": FRONTEND_ORIGIN}):
            pass


if __name__ == "__main__":
    unittest.main()
