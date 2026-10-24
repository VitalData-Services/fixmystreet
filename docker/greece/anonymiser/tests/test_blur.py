"""Tests for the blur_region function."""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import _blur_region


class TestBlurRegion:
    """Verify pixelation changes pixel values in the region."""

    def _make_plain_image(self):
        """Create a gradient image (solid color would not change after
        pixelation, since all pixels are the same)."""
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        for y in range(200):
            img[y, :, 0] = y  # gradient in R channel
        return img

    def test_blur_changes_pixels(self):
        """Blurring a region must change the pixel values."""
        img = self._make_plain_image()
        # Mark original values
        original_roi = img[50:100, 50:100].copy()

        _blur_region(img, 50, 50, 100, 100, max_blocks=8)

        new_roi = img[50:100, 50:100]
        assert not np.array_equal(original_roi, new_roi), \
            "Blurring should change pixel values"

    def test_blur_outside_roi_unchanged(self):
        """Pixels outside the blurred region must remain identical."""
        img = self._make_plain_image()
        original = img.copy()

        _blur_region(img, 50, 50, 100, 100, max_blocks=8)

        # Check corners outside the region
        assert np.array_equal(img[0:10, 0:10], original[0:10, 0:10])
        assert np.array_equal(img[150:190, 150:190], original[150:190, 150:190])

    def test_blur_affects_entire_roi(self):
        """The entire region passed to _blur_region must be changed."""
        img = self._make_plain_image()
        original = img.copy()

        _blur_region(img, 50, 50, 100, 100, max_blocks=8)

        # The full ROI must differ from original
        assert not np.array_equal(img[50:100, 50:100], original[50:100, 50:100])

    def test_empty_box_no_crash(self):
        """Zero-size box should not crash."""
        img = self._make_plain_image()
        original = img.copy()
        _blur_region(img, 50, 50, 50, 50)
        assert np.array_equal(img, original)

    def test_clamped_to_image(self):
        """Box extending beyond image bounds is clamped."""
        img = self._make_plain_image()
        original = img.copy()
        # Box goes beyond image
        _blur_region(img, 180, 180, 250, 250, max_blocks=4)
        # Top-left corner untouched
        assert np.array_equal(img[0:10, 0:10], original[0:10, 0:10])
