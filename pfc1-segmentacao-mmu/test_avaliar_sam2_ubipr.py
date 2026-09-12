import unittest
import numpy as np
from PIL import Image

from avaliar_sam2_ubipr import calibrate, load_iris


class Sam2UBIPrUtilitiesTest(unittest.TestCase):
    def test_iris_is_only_native_value_85(self):
        image = Image.fromarray(np.array([[0, 85, 170, 255]], dtype=np.uint8))
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"mask.png"; image.save(path)
            np.testing.assert_array_equal(load_iris(path), [[False, True, False, False]])

    def test_calibration_ignores_empty_iris_masks(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (32, 24), 128).save(root/"empty.jpg")
            Image.new("L", (32, 24), 0).save(root/"empty.png")
            Image.new("RGB", (32, 24), 128).save(root/"iris.jpg")
            mask = np.zeros((24, 32), dtype=np.uint8); mask[8:16, 10:22] = 85
            Image.fromarray(mask).save(root/"iris.png")
            result = calibrate([{"image": str(root/"empty.jpg"), "mask": str(root/"empty.png")}, {"image": str(root/"iris.jpg"), "mask": str(root/"iris.png")}])
            self.assertGreater(result["width"], 0)


if __name__ == "__main__":
    unittest.main()
