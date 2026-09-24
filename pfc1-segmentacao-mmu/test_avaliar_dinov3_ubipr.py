import unittest
import numpy as np
from PIL import Image

from avaliar_dinov3_ubipr import eer, masked_crop


class Dinov3UtilitiesTest(unittest.TestCase):
    def test_masked_crop_removes_background(self):
        image = Image.fromarray(np.full((10, 12, 3), 200, dtype=np.uint8))
        mask = np.zeros((10, 12), dtype=bool); mask[4:6, 5:8] = True
        crop = np.asarray(masked_crop(image, mask, margin=0))
        self.assertEqual(int((crop == 200).all(axis=2).sum()), int(mask.sum()))
        self.assertGreater(int((crop == 0).all(axis=2).sum()), 0)

    def test_eer_is_zero_for_separated_scores(self):
        value, threshold = eer(np.array([0.8, 0.9]), np.array([0.1, 0.2]))
        self.assertEqual(value, 0.0)
        self.assertGreater(threshold, 0.2)


if __name__ == "__main__":
    unittest.main()
