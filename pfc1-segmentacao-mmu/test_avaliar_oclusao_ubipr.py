import unittest

import numpy as np

from avaliar_oclusao_ubipr import binary_metrics, occlusion_rows, summarize


class OcclusionTest(unittest.TestCase):
    def test_occlusion_enters_from_requested_edge(self):
        iris = np.ones((10, 4), dtype=bool)
        top, top_fraction = occlusion_rows(iris, 0.30, "top")
        bottom, bottom_fraction = occlusion_rows(iris, 0.30, "bottom")
        self.assertTrue(top[:3].all())
        self.assertFalse(top[3:].any())
        self.assertTrue(bottom[-3:].all())
        self.assertFalse(bottom[:-3].any())
        self.assertAlmostEqual(top_fraction, 0.3)
        self.assertAlmostEqual(bottom_fraction, 0.3)

    def test_metrics_use_visible_and_original_references(self):
        original = np.array([[1, 1], [1, 1]], dtype=bool)
        visible = np.array([[0, 0], [1, 1]], dtype=bool)
        prediction = visible.copy()
        result = binary_metrics(prediction, visible, original)
        self.assertEqual(result["dice_visible"], 1.0)
        self.assertEqual(result["iris_original_preserved"], 0.5)

    def test_limit_follows_predeclared_success_criterion(self):
        rows = []
        for level, values in ((0, [0.9, 0.8]), (20, [0.8, 0.75]), (40, [0.8, 0.6])):
            for value in values:
                rows.append({"target_occlusion_percent": level, "actual_occlusion_percent": level,
                             "direction": "top", "dice_visible": value,
                             "iris_original_preserved": 1 - level / 100})
        result = summarize(rows, success_dice=0.7, success_rate=1.0)
        self.assertEqual(result["limiting_occlusion_percent"], 20)
        self.assertEqual(result["minimum_visible_iris_percent"], 80)


if __name__ == "__main__":
    unittest.main()
