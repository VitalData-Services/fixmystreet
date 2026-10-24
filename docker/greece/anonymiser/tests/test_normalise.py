"""Tests for Greek plate normalisation."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import normalise_greek_plate


class TestNormaliseGreekPlate:
    """Verify Greek letter conversion and dash insertion."""

    def test_ikx(self):
        assert normalise_greek_plate("IKX1234") == "ΙΚΧ-1234"

    def test_aok(self):
        assert normalise_greek_plate("AOK4966") == "ΑΟΚ-4966"

    def test_mmh(self):
        assert normalise_greek_plate("MMH2807") == "ΜΜΗ-2807"

    def test_emh(self):
        assert normalise_greek_plate("EMH2807") == "ΕΜΗ-2807"

    def test_ky(self):
        """Two-letter prefix (ΚΥ) with 3 digits."""
        assert normalise_greek_plate("KY901") == "ΚΥ-901"

    def test_non_greek_stays(self):
        """Foreign plate with non-Greek letter (C) stays unchanged."""
        assert normalise_greek_plate("ABC123") == "ABC123"

    def test_single_letter_no_dash(self):
        """Only one letter before digits — doesn't match pattern."""
        assert normalise_greek_plate("T4987") == "T4987"

    def test_lowercase(self):
        """Lowercase input is uppercased."""
        assert normalise_greek_plate("ikx1234") == "ΙΚΧ-1234"

    def test_four_digits(self):
        """Four-digit plates get a dash too."""
        assert normalise_greek_plate("ABE1234") == "ΑΒΕ-1234"

    def test_three_letters(self):
        """Three-letter prefix."""
        assert normalise_greek_plate("ABE123") == "ΑΒΕ-123"
