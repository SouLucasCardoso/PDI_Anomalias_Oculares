import unittest

import numpy as np

from avaliar_sam3_1_ubipr import collapse_masks, metrics


class Sam31UtilitiesTest(unittest.TestCase):
    def test_multiple_instances_are_combined(self):
        masks = np.zeros((2, 3, 3), dtype=bool)
        masks[0, 0, 0] = True
        masks[1, 2, 2] = True
        result = collapse_masks(masks, (3, 3))
        self.assertEqual(int(result.sum()), 2)

    def test_empty_prediction_has_zero_dice(self):
        truth = np.ones((2, 2), dtype=bool)
        result = metrics(np.zeros_like(truth), truth)
        self.assertEqual(result["dice"], 0.0)
        self.assertEqual(result["recall"], 0.0)


if __name__ == "__main__":
    unittest.main()
