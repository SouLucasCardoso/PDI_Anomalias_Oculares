import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import torch

import treinar_segmentacao_mmu as iris


class SegmentationUtilitiesTest(unittest.TestCase):
    def test_enclosed_background_finds_only_the_internal_hole(self) -> None:
        mask = np.zeros((12, 12), dtype=bool)
        mask[2:10, 2:10] = True
        mask[5:7, 5:7] = False

        hole = iris.enclosed_background(mask)

        self.assertEqual(int(hole.sum()), 4)
        self.assertTrue(hole[5:7, 5:7].all())

    def test_boundary_tversky_has_finite_gradient(self) -> None:
        logits = torch.randn(2, 1, 24, 32, requires_grad=True)
        targets = (torch.rand(2, 1, 24, 32) > 0.8).float()

        loss = iris.boundary_tversky_loss(logits, targets)
        loss.backward()

        self.assertTrue(torch.isfinite(loss))
        self.assertIsNotNone(logits.grad)
        self.assertTrue(torch.isfinite(logits.grad).all())

    def test_geometric_matching_recovers_shuffled_masks(self) -> None:
        centers = [(50, 55), (65, 60), (80, 65), (95, 70), (110, 75)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            images = []
            masks = []
            for index, center in enumerate(centers, start=1):
                image = Image.new("L", (160, 120), 220)
                draw = ImageDraw.Draw(image)
                x, y = center
                draw.ellipse((x - 22, y - 18, x + 22, y + 18), fill=110)
                draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=5)
                image_path = root / f"image_{index}.bmp"
                image.save(image_path)
                images.append(image_path)

                mask = Image.new("L", (160, 120), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((x - 22, y - 18, x + 22, y + 18), fill=255)
                draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=0)
                mask_path = root / f"mask_{index}.bmp"
                mask.save(mask_path)
                masks.append(mask_path)

            shuffled = [masks[position] for position in (3, 0, 4, 1, 2)]
            matches = iris.match_masks_by_geometry(images, shuffled)

            for image_path, mask_path, distance in matches:
                image_position = images.index(image_path)
                mask_position = masks.index(mask_path)
                self.assertEqual(image_position, mask_position)
                self.assertLess(distance, 3.0)


if __name__ == "__main__":
    unittest.main()
