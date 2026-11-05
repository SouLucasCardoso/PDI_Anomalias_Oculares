import unittest
import numpy as np
from diagnosticar_sam3_prompts_clinicos import normalized_box


class Sam3Boxes(unittest.TestCase):
    def test_xy_pixel_region_becomes_normalized_cxcywh(self):
        mask = np.zeros((40,60),bool)
        mask[10:30,20:40] = True
        np.testing.assert_allclose(normalized_box(mask),[.5,.5,.4,.6])

    def test_clips_to_image_and_retains_missing_support(self):
        np.testing.assert_allclose(normalized_box(np.ones((20,30),bool)),[.5,.5,1,1])
        self.assertIsNone(normalized_box(np.zeros((20,30),bool)))
        mask = np.zeros((20,30),bool)
        mask[0,:15] = True
        self.assertIsNone(normalized_box(mask))


if __name__ == '__main__':
    unittest.main()
