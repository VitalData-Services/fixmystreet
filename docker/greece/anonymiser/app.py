"""FixMyStreets Greece — anonymiser service.

Detects license plates and faces in JPEG images, returns:
  - a "public" version with both plates and faces blurred,
  - a "police" version with only faces blurred,
  - OCR results for plates with high confidence,
  - "nsfw": nudity found (NudeNet), so that the site holds the report for a moderator.

Endpoints:
  POST /anonymise  — accept JPEG, return anonymised images + OCR
  GET  /health     — readiness check
"""

import base64
import io
import json
import logging
import os
import re
import struct
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import cv2
import numpy as np
from fast_alpr import ALPR
from nudenet import NudeDetector

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Greek-letter mapping (Latin letters that look like Greek on EU plates)
# ---------------------------------------------------------------------------
_LATIN_TO_GREEK = {
    "A": "Α", "B": "Β", "E": "Ε", "Z": "Ζ", "H": "Η",
    "I": "Ι", "K": "Κ", "M": "Μ", "N": "Ν", "O": "Ο",
    "P": "Ρ", "T": "Τ", "Y": "Υ", "X": "Χ",
}

# Pattern for Greek plates: 2-3 Greek-lookalike letters + 3-4 digits
GREEK_PLATE_RE = re.compile(
    r"^[ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ]{2,3}[0-9]{3,4}$"
)


def normalise_greek_plate(raw: str) -> str:
    """Convert Latin-lookalike text to Greek and add dash if it matches
    the Greek plate pattern.

    Examples
    --------
    >>> normalise_greek_plate("IKX1234")
    'ΙΚΧ-1234'
    >>> normalise_greek_plate("ABC123")
    'ABC123'  # not a Greek-plate pattern (C is not Greek-lookalike)
    """
    greek = "".join(_LATIN_TO_GREEK.get(c, c) for c in raw.upper())
    if GREEK_PLATE_RE.match(greek):
        # Insert dash between letters and digits
        m = re.match(r"([ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ]{2,3})([0-9]{3,4})", greek)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
    return raw.upper()


# ---------------------------------------------------------------------------
# Blurring helpers — pixelation + blur (not reversible)
# ---------------------------------------------------------------------------

def _blur_region(img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
                 max_blocks: int = 8) -> np.ndarray:
    """Blur the region [x1:y1:x2:y2] with heavy pixelation followed by
    Gaussian blur.  The long side is divided into at most *max_blocks*
    blocks.  Returns *img* with the region modified in-place."""

    h, w = img.shape[:2]
    # Clamp to image bounds
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return img

    roi = img[y1:y2, x1:x2].copy()
    rh, rw = roi.shape[:2]

    # 1. Add 15 % padding to the box (already done by caller on coordinates)
    # 2. Pixelation: resize down then up
    blocks = min(max_blocks, max(rw, rh))
    if blocks < 1:
        blocks = 1
    # Determine block dimensions — aim for max_blocks on the long side
    if rw >= rh:
        blocks_x = max(1, blocks)
        blocks_y = max(1, blocks * rh // rw)
    else:
        blocks_y = max(1, blocks)
        blocks_x = max(1, blocks * rw // rh)

    small = cv2.resize(roi, (blocks_x, blocks_y), interpolation=cv2.INTER_AREA)
    pixelated = cv2.resize(small, (rw, rh), interpolation=cv2.INTER_NEAREST)

    # 3. Multiple passes of Gaussian blur on top of pixelation
    #    Using a larger kernel and multiple passes to ensure solid areas
    #    are also blurred (single pass on solid pixelation does nothing).
    blurred = pixelated
    for _ in range(3):
        blurred = cv2.GaussianBlur(blurred, (9, 9), 0)

    img[y1:y2, x1:x2] = blurred
    return img


# ---------------------------------------------------------------------------
# ALPR + face detector globals (lazy init, thread-safe)
# ---------------------------------------------------------------------------

_alpr: ALPR | None = None
_face_det = None
_nude = None
_lock = threading.Lock()


def _init_models():
    """Load ALPR and face-detection models.  Called once at startup."""
    global _alpr, _face_det, _nude

    with _lock:
        if _alpr is not None:
            return  # already loaded

        log.info("Loading ALPR (yolo-v9-t-384 + cct-xs-v2)...")
        _alpr = ALPR(
            detector_model="yolo-v9-t-384-license-plate-end2end",
            ocr_model="cct-xs-v2-global-model",
        )

        # YuNet face detector — model baked into the image
        # Allow overriding via env var for testing on the host machine
        model_path = os.environ.get(
            "ANONYMISER_FACE_MODEL",
            "/usr/share/anonymiser/face_detection_yunet_2023mar.onnx",
        )
        log.info("Loading YuNet face detector from %s ...", model_path)
        _face_det = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=(640, 640),
            score_threshold=0.5,
            nms_threshold=0.3,
            top_k=5000,
        )
        # NudeNet 3.4.2 (AGPL-3.0, its 320n model is in the package)
        log.info("Loading NudeNet ...")
        _nude = NudeDetector()
        log.info("All models loaded.")


# ---------------------------------------------------------------------------
# Anonymise logic
# ---------------------------------------------------------------------------

_PLATE_CONFIDENCE_THRESH = 0.8   # include in OCR output only
_BLUR_CONFIDENCE_THRESH = 0.25  # blur every detection above this

_PlateEntry = tuple[str, str, float, tuple[int, int, int, int]]


def anonymise_image(jpeg_bytes: bytes):
    """Process one JPEG image.

    Returns (public_b64 | None, police_b64 | None, plates, face_count).
    """
    # Decode JPEG
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return None, None, [], 0

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = img_bgr.shape[:2]

    # --- ALPR detection ---
    results = _alpr.predict(img_rgb)

    plates: list[_PlateEntry] = []
    plate_boxes: list[tuple[int, int, int, int]] = []  # for blurring
    faces: int = 0

    for r in results:
        det = r.detection
        if not det or det.confidence < _BLUR_CONFIDENCE_THRESH:
            continue

        x1 = int(det.bounding_box.x1)
        y1 = int(det.bounding_box.y1)
        x2 = int(det.bounding_box.x2)
        y2 = int(det.bounding_box.y2)

        plate_boxes.append((x1, y1, x2, y2))

        # OCR confidence: mean of per-character confidences
        if r.ocr:
            if isinstance(r.ocr.confidence, list):
                conf = float(np.mean(r.ocr.confidence))
            elif isinstance(r.ocr.confidence, (int, float)):
                conf = float(r.ocr.confidence)
            else:
                conf = 0.0
        else:
            conf = 0.0

        text_raw = (r.ocr.text or "").strip().upper() if r.ocr else ""

        if conf >= _PLATE_CONFIDENCE_THRESH and text_raw:
            plates.append((
                normalise_greek_plate(text_raw),
                text_raw,
                conf,
                (x1, y1, x2, y2),
            ))

    # --- Face detection ---
    _face_det.setInputSize((img_bgr.shape[1], img_bgr.shape[0]))
    _, face_dets = _face_det.detect(img_bgr)
    if face_dets is not None:
        faces = len(face_dets)
        for fd in face_dets:
            x, y, fw, fh = fd[:4].astype(int)
            plate_boxes.append((x, y, x + fw, y + fh))

    # If nothing detected, return null
    if not plate_boxes and faces == 0:
        return None, None, [], 0

    # --- Build public and police images ---
    public = img_bgr.copy()
    police = img_bgr.copy()

    # Determine which boxes are plates vs faces (plates come from ALPR,
    # faces from YuNet).  We need to separate them to apply different blur.
    # Plate boxes are from ALPR results; face boxes from YuNet.

    # Public: blur plates AND faces
    for (x1, y1, x2, y2) in plate_boxes:
        # Add 15 % padding
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        dx, dy = x2 - x1, y2 - y1
        pad_x = int(dx * 0.15)
        pad_y = int(dy * 0.15)
        _blur_region(public,
                     max(0, x1 - pad_x), max(0, y1 - pad_y),
                     min(w, x2 + pad_x), min(h, y2 + pad_y))

    if face_dets is not None:
        for fd in face_dets:
            x, y, fw, fh = fd[:4].astype(int)
            cx, cy = x + fw // 2, y + fh // 2
            pad_x = int(fw * 0.15)
            pad_y = int(fh * 0.15)
            _blur_region(public,
                         max(0, x - pad_x), max(0, y - pad_y),
                         min(w, x + fw + pad_x), min(h, y + fh + pad_y))

    # Police: blur faces only (not plates)
    if face_dets is not None:
        for fd in face_dets:
            x, y, fw, fh = fd[:4].astype(int)
            cx, cy = x + fw // 2, y + fh // 2
            pad_x = int(fw * 0.15)
            pad_y = int(fh * 0.15)
            _blur_region(police,
                         max(0, x - pad_x), max(0, y - pad_y),
                         min(w, x + fw + pad_x), min(h, y + fh + pad_y))

    # Encode to JPEG (quality 90, no EXIF)
    def _encode(img: np.ndarray) -> str | None:
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok or buf is None:
            return None
        # Strip EXIF — imencode already doesn't add it by default
        return base64.b64encode(buf.tobytes()).decode("ascii")

    public_b64 = _encode(public) if not plate_boxes and faces == 0 else _encode(public)
    police_b64 = _encode(police) if faces == 0 else _encode(police)

    # If public has no changes, return null
    if public_b64 and np.array_equal(public, img_bgr):
        public_b64 = None

    return public_b64, police_b64, plates, faces


# Nudity: what holds a report for a moderator, with the lowest score that counts. Genitals and anus
# count from a lower score than breasts and buttocks, which a beach or a statue can show. A wrong
# hold costs a moderator's look; a missed one, an obscene photo on the map. (A marble statue's chest
# scores about 0.6 as a breast, seen in a quarter.)
_NSFW_THRESH = {
    "MALE_GENITALIA_EXPOSED": 0.35,
    "FEMALE_GENITALIA_EXPOSED": 0.35,
    "ANUS_EXPOSED": 0.35,
    "FEMALE_BREAST_EXPOSED": 0.6,
    "BUTTOCKS_EXPOSED": 0.6,
}


def nsfw_check(jpeg_bytes: bytes) -> list[dict]:
    """The nudity found in a JPEG, as [{"class", "score"}], highest score first."""
    img = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    # The model sees 320x320: on a whole street photo a person is a few pixels. So the whole image,
    # and for a larger one also its four quarters (overlapping by a fifth); the best score per class.
    views = [img]
    h, w = img.shape[:2]
    if max(h, w) > 640:
        th, tw = int(h * 0.6), int(w * 0.6)
        views += [img[y:y + th, x:x + tw] for y in (0, h - th) for x in (0, w - tw)]
    best: dict[str, float] = {}
    for view in views:
        for d in _nude.detect(view):
            if d["score"] >= _NSFW_THRESH.get(d["class"], 2):
                best[d["class"]] = max(best.get(d["class"], 0), float(d["score"]))
    return sorted(({"class": k, "score": round(v, 3)} for k, v in best.items()), key=lambda d: -d["score"])


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

_MAX_BODY = 15 * 1024 * 1024  # 15 MB


class _Handler(BaseHTTPRequestHandler):
    """Minimal request handler for the anonymiser API."""

    # Silence per-request logs
    def log_message(self, fmt, *args):
        pass

    # -- GET ---------------------------------------------------------------

    def do_GET(self):
        if self.path == "/health":
            self._health()
        else:
            self._not_found()

    def _health(self):
        ready = _alpr is not None and _face_det is not None and _nude is not None
        status = 200 if ready else 503
        body = json.dumps({
            "ok": ready,
            "models": {
                "alpr": "yolo-v9-t-384-license-plate-end2end + cct-xs-v2-global-model",
                "face": "face_detection_yunet_2023mar.onnx",
                "nsfw": "nudenet 3.4.2 320n",
            },
        })
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    # -- POST --------------------------------------------------------------

    def do_POST(self):
        if self.path == "/anonymise":
            self._anonymise()
        else:
            self._not_found()

    def _anonymise(self):
        content_type = self.headers.get("Content-Type", "")
        if "image/jpeg" not in content_type:
            self._error(415, "Content-Type must be image/jpeg")
            return

        length = int(self.headers.get("Content-Length", 0))
        if length > _MAX_BODY:
            self._error(413, f"Body too large (max {_MAX_BODY >> 20} MB)")
            return

        if length == 0:
            self._error(400, "Missing Content-Length")
            return

        body = self.rfile.read(length)

        try:
            public_b64, police_b64, plates, face_count = anonymise_image(body)
            nsfw = nsfw_check(body)
        except Exception:
            log.exception("anonymise failed")
            self._error(500, "Internal error during anonymisation")
            return

        # Format plate results
        plate_json = []
        for text, text_raw, conf, box in plates:
            plate_json.append({
                "text": text,
                "text_raw": text_raw,
                "confidence": round(conf, 4),
                "box": list(box),
            })

        resp = {
            "public": public_b64,
            "police": police_b64,
            "plates": plate_json,
            "faces": face_count,
            "nsfw": nsfw,
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())

    # -- helpers -----------------------------------------------------------

    def _error(self, code: int, message: str):
        body = json.dumps({"error": message})
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def _not_found(self):
        self._error(404, "Not found")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _init_models()
    addr = ("0.0.0.0", 8080)
    server = ThreadingHTTPServer(addr, _Handler)
    log.info("Listening on %s:%d", *addr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
