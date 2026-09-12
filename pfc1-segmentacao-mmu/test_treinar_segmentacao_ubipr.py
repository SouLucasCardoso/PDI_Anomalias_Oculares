import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import treinar_segmentacao_ubipr as ubipr


class UBIPrUtilitiesTest(unittest.TestCase):
    def test_parse_stem(self):
        self.assertEqual(ubipr.parse_stem("C259_S2_I15_R"), (259, 2, 15, "R"))

    def test_decode_native_levels(self):
        mask = Image.fromarray(np.array([[0, 85, 170, 255]], dtype=np.uint8))
        np.testing.assert_array_equal(ubipr.decode_mask(mask), [[0, 1, 2, 3]])

    def test_subject_split_has_no_leakage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for subject in range(1, 11):
                stem = f"C{subject}_S1_I1_L"
                Image.new("RGB", (8, 8)).save(root/f"{stem}.jpg")
                Image.new("L", (8, 8)).save(root/f"{stem}.png")
            splits = ubipr.split_by_subject(ubipr.build_manifest(root), 42)
            groups = [{sample.subject for sample in rows} for rows in splits.values()]
            self.assertFalse(groups[0] & groups[1]); self.assertFalse(groups[0] & groups[2]); self.assertFalse(groups[1] & groups[2])


if __name__ == "__main__":
    unittest.main()
