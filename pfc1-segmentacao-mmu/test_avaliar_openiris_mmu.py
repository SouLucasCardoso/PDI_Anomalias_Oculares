import unittest

import numpy as np
from PIL import Image

from avaliar_openiris_mmu import compose_mask, preprocess, resize_probabilities


class TestOpenIrisUtilities(unittest.TestCase):
    def test_preprocess_formato_do_model_card(self):
        image = Image.new("RGB", (320, 240), color=(128, 128, 128))
        result = preprocess(image)
        self.assertEqual(result.shape, (1, 3, 480, 640))
        self.assertEqual(result.dtype, np.float32)

    def test_composicao_remove_pupila_e_cilios(self):
        probabilities = np.zeros((4, 3, 3), dtype=np.float32)
        probabilities[1] = 1.0
        probabilities[2, 1, 1] = 1.0
        probabilities[3, 0, 0] = 1.0
        iris_only = compose_mask(probabilities, 0.5, "iris_only")
        without_pupil = compose_mask(probabilities, 0.5, "iris_minus_pupil")
        usable = compose_mask(probabilities, 0.5, "usable_iris")
        self.assertEqual(int(iris_only.sum()), 9)
        self.assertEqual(int(without_pupil.sum()), 8)
        self.assertEqual(int(usable.sum()), 7)

    def test_resize_preserva_numero_de_classes(self):
        probabilities = np.zeros((4, 12, 16), dtype=np.float32)
        resized = resize_probabilities(probabilities, (32, 24))
        self.assertEqual(resized.shape, (4, 24, 32))


if __name__ == "__main__":
    unittest.main()
