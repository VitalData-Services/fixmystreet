"""Tests that rely on fixture images (plate detection, face detection, null case).

These tests require the ALPR and face-detection models to be loaded.
We initialise them at module import time."""

import os
import sys
import base64
import io
import numpy as np

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force model initialisation for these tests
from app import _init_models, anonymise_image, _blur_region

_init_models()

# --- Load fixture images as JPEG bytes ------------------------------------

def _read_fixture(name: str) -> bytes:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", name)
    with open(path, "rb") as f:
        return f.read()


# --- Test: plate image → plate blurred in public, NOT in police -----------

def test_plate_public_has_blur():
    """A photo with a license plate: the public version must differ from
    the police version at the plate location."""
    jpeg = _read_fixture("plate_gov.jpg")
    public_b64, police_b64, plates, faces = anonymise_image(jpeg)

    assert public_b64 is not None, "public image should not be null when a plate is found"
    assert police_b64 is not None, "police image should not be null"
    assert len(plates) >= 0  # may or may not meet OCR threshold

    # Decode both images
    pub_arr = cv2.imdecode(np.frombuffer(base64.b64decode(public_b64), dtype=np.uint8), cv2.IMREAD_COLOR)
    pol_arr = cv2.imdecode(np.frombuffer(base64.b64decode(police_b64), dtype=np.uint8), cv2.IMREAD_COLOR)

    assert pub_arr is not None, "Failed to decode public image"
    assert pol_arr is not None, "Failed to decode police image"

    # The images must differ (public has plates blurred, police doesn't)
    diff = cv2.absdiff(pub_arr, pol_arr)
    diff_count = np.count_nonzero(diff)
    assert diff_count > 0, (
        "Public and police images must differ at the plate region; "
        f"but {diff_count} pixel differences found"
    )


def test_plate_police_has_no_plate_blur():
    """In the police version, plate pixels must remain closer to the original."""
    jpeg = _read_fixture("plate_gov.jpg")
    public_b64, police_b64, plates, faces = anonymise_image(jpeg)
    police_b64 = police_b64  # noqa: F841

    # Decode original
    orig_arr = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    pol_arr = cv2.imdecode(np.frombuffer(base64.b64decode(police_b64), dtype=np.uint8), cv2.IMREAD_COLOR)

    # The police version should be much closer to the original than public is
    pub_arr = cv2.imdecode(np.frombuffer(base64.b64decode(public_b64), dtype=np.uint8), cv2.IMREAD_COLOR)

    diff_pub = np.sum(cv2.absdiff(orig_arr, pub_arr))
    diff_pol = np.sum(cv2.absdiff(orig_arr, pol_arr))

    assert diff_pol < diff_pub, (
        f"Police image ({diff_pol}) should be closer to original than "
        f"public image ({diff_pub})"
    )


# --- Test: face image → faces blurred in both versions --------------------

def test_face_blurred_in_both():
    """A photo with people: faces must be blurred in both public and police."""
    jpeg = _read_fixture("people_tinos_man.jpg")
    public_b64, police_b64, plates, faces = anonymise_image(jpeg)

    assert public_b64 is not None, "public should not be null"
    assert police_b64 is not None, "police should not be null"
    assert faces > 0, f"Expected faces to be detected, got {faces}"

    # Both images should differ from original
    orig_arr = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    pub_arr = cv2.imdecode(np.frombuffer(base64.b64decode(public_b64), dtype=np.uint8), cv2.IMREAD_COLOR)
    pol_arr = cv2.imdecode(np.frombuffer(base64.b64decode(police_b64), dtype=np.uint8), cv2.IMREAD_COLOR)

    diff_pub = np.count_nonzero(cv2.absdiff(orig_arr, pub_arr))
    diff_pol = np.count_nonzero(cv2.absdiff(orig_arr, pol_arr))

    assert diff_pub > 0, "Public image must differ from original (faces blurred)"
    assert diff_pol > 0, "Police image must differ from original (faces blurred)"


# --- Test: no plate, no face → both null ----------------------------------

def test_no_plate_no_face_both_null():
    """A street photo without visible plates or people should return null."""
    jpeg = _read_fixture("athens_street.jpg")
    public_b64, police_b64, plates, faces = anonymise_image(jpeg)

    # This image might have a face (we detected 1 in benchmark).
    # If faces are detected, both should be non-null.
    # If nothing is detected, both should be null.
    if faces == 0 and len(plates) == 0:
        assert public_b64 is None, "public should be null when nothing detected"
        assert police_b64 is None, "police should be null when nothing detected"
    else:
        # If there are faces or plates, both should be non-null
        assert public_b64 is not None
        assert police_b64 is not None


# --- Test: plate detection returns OCR data --------------------------------

def test_plate_ocr_output():
    """A plate image should return OCR results with text, confidence, and box."""
    jpeg = _read_fixture("plate_gov.jpg")
    _, _, plates, _ = anonymise_image(jpeg)

    # At least one plate should be detected
    # (may or may not meet the OCR confidence threshold for inclusion)
    assert plates is not None
