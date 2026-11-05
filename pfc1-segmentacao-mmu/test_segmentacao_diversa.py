import unittest
import numpy as np
import torch
from treinar_segmentacao_diversa import geometry, add_glasses, diverse_loss, IGNORE, decode_native_fast
from PIL import Image


class DiverseSegmentationTests(unittest.TestCase):
    def test_fast_decoder_matches_reference_and_rejects_unknown(self):
        from treinar_segmentacao_ubipr import decode_mask
        native=np.random.default_rng(3).choice([0,85,170,255],(73,91)).astype(np.uint8)
        im=Image.fromarray(native)
        np.testing.assert_array_equal(decode_native_fast(im),decode_mask(im))
        native[0,0]=86
        with self.assertRaises(ValueError):decode_native_fast(Image.fromarray(native))
    def test_geometry_preserves_class_ids_and_alignment(self):
        mask = np.zeros((64, 80), np.uint8); mask[20:40, 30:50] = 1
        image = np.repeat((mask*255)[...,None], 3, axis=2)
        rgb, target = geometry(image, mask, 80, 64, 1.5, 15, .7, .1, -.1)
        self.assertLessEqual(set(np.unique(target)), {0, 1, IGNORE})
        self.assertGreater(((rgb[...,0] > 200)&(target == 1)).sum()/(target == 1).sum(), .8)
        self.assertTrue((target == IGNORE).any())

    def test_glasses_remove_hidden_iris_but_preserve_unknown_padding(self):
        image = np.full((80, 96, 3), 100, np.uint8)
        target = np.ones((80,96), np.uint8);target[:5] = IGNORE
        changed, label = add_glasses(image, target, np.random.default_rng(1))
        support = (changed != image).any(2)&(target != IGNORE)
        self.assertTrue(support.any());self.assertTrue((label[support] == 0).all())
        self.assertTrue((label[:5] == IGNORE).all())

    def test_ignored_pixels_do_not_change_loss_and_empty_is_finite(self):
        target = torch.zeros((1, 8, 8), dtype=torch.long);target[:, :4] = IGNORE
        original = torch.zeros((1,4,8,8), requires_grad=True)
        changed = original.detach().clone();changed[:,1,:4] = 100
        self.assertAlmostEqual(float(diverse_loss(original, target).detach()), float(diverse_loss(changed, target)), places=6)
        loss = diverse_loss(original, target);self.assertTrue(torch.isfinite(loss));loss.backward()
        self.assertEqual(float(original.grad[:,:,:4].abs().sum()), 0.)


if __name__ == '__main__': unittest.main()
