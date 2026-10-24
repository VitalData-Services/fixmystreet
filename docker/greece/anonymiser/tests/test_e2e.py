"""End-to-end test: start the HTTP server in a thread, POST /anonymise,
check the JSON response, and GET /health."""

import os
import sys
import base64
import json
import threading
import time
import urllib.request
import urllib.error

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import _init_models, main, _Handler
from http.server import ThreadingHTTPServer

_INIT_DONE = False


def _ensure_models():
    global _INIT_DONE
    if not _INIT_DONE:
        _init_models()
        _INIT_DONE = True


# --- Fixtures -------------------------------------------------------------

_FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures"
)


def _read_fixture(name: str) -> bytes:
    with open(os.path.join(_FIXTURES_DIR, name), "rb") as f:
        return f.read()


def _build_jpeg(arr: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


# --- Helpers --------------------------------------------------------------

def _post_anonymise(data: bytes) -> dict:
    """POST /anonymise and return the parsed JSON response."""
    req = urllib.request.Request(
        "http://127.0.0.1:18080/anonymise",
        data=data,
        headers={"Content-Type": "image/jpeg"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 200
        return json.loads(resp.read())


def _get_health() -> dict:
    """GET /health and return the parsed JSON response."""
    req = urllib.request.Request(
        "http://127.0.0.1:18080/health",
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        return json.loads(resp.read())


# --- Test fixture for images without plates/faces -------------------------

def _blank_jpeg():
    """Return a blank JPEG with no plates or faces."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    return _build_jpeg(arr)


# --- E2E tests ------------------------------------------------------------

class TestEndToEnd:
    """Start the server once and run all e2e tests against it."""

    @classmethod
    def setup_class(cls):
        _ensure_models()
        cls._server = ThreadingHTTPServer(("127.0.0.1", 18080), _Handler)
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(1)  # let the server start

    @classmethod
    def teardown_class(cls):
        cls._server.shutdown()

    def test_health(self):
        """GET /health returns ok=true."""
        resp = _get_health()
        assert resp["ok"] is True
        assert "models" in resp

    def test_anonymise_plate_image(self):
        """POST /anonymise on a plate photo returns public + police + plates."""
        jpeg = _read_fixture("plate_gov.jpg")
        resp = _post_anonymise(jpeg)

        assert "public" in resp
        assert "police" in resp
        assert "plates" in resp
        assert "faces" in resp

        # Decode and verify they are valid JPEGs
        pub = cv2.imdecode(
            np.frombuffer(base64.b64decode(resp["public"]), dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        assert pub is not None

        pol = cv2.imdecode(
            np.frombuffer(base64.b64decode(resp["police"]), dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        assert pol is not None

    def test_anonymise_blank_image(self):
        """A blank JPEG (no plates, no faces) should return public=null, police=null."""
        jpeg = _blank_jpeg()
        resp = _post_anonymise(jpeg)

        assert resp["public"] is None
        assert resp["police"] is None
        assert resp["plates"] == []
        assert resp["faces"] == 0

    def test_response_keys(self):
        """The response must contain exactly the expected top-level keys."""
        jpeg = _read_fixture("plate_gov.jpg")
        resp = _post_anonymise(jpeg)

        expected_keys = {"public", "police", "plates", "faces"}
        assert set(resp.keys()) == expected_keys

    def test_plate_entry_format(self):
        """Each plate entry must have text, text_raw, confidence, and box."""
        jpeg = _read_fixture("plate_gov.jpg")
        resp = _post_anonymise(jpeg)

        for entry in resp["plates"]:
            assert "text" in entry
            assert "text_raw" in entry
            assert "confidence" in entry
            assert "box" in entry
            assert isinstance(entry["box"], list)
            assert len(entry["box"]) == 4
            assert isinstance(entry["confidence"], (int, float))
