import unittest
import torch
from segmentador_sam3_iris import IrisSam3Adapter, SAM_REVISION, iris_loss
from segmentador_sam3_residual import IrisSam3Residual, MODEL_TYPE, MODEL_CONFIG, load_checkpoint


class ResidualTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        torch.manual_seed(41)

    def test_zero_head_preserves_parent_logits_and_frozen_batchnorm(self):
        parent = IrisSam3Adapter().eval()
        model = IrisSam3Residual()
        model.initialize(parent.state_dict())
        rgb, features = torch.rand(2, 3, 24, 32), torch.rand(2, 256, 6, 8)
        original = {k: v.clone() for k, v in model.base.state_dict().items()}
        with torch.no_grad():
            expected = parent(rgb, features)
            model.train()
            actual = model(rgb, features)
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
        self.assertFalse(model.base.training)
        self.assertTrue(all(not p.requires_grad for p in model.base.parameters()))
        for name, value in original.items():
            torch.testing.assert_close(model.base.state_dict()[name], value, rtol=0, atol=0)

    def test_only_correction_learns_and_roundtrip_is_strict(self):
        model = IrisSam3Residual().train()
        initial = {k: v.clone() for k, v in model.base.state_dict().items()}
        optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=1e-4)
        rgb, features = torch.rand(2, 3, 24, 32), torch.rand(2, 256, 6, 8)
        target = torch.zeros(2, 24, 32, dtype=torch.long)
        target[:, 5:20, 6:26] = 1
        for _ in range(2):
            optimizer.zero_grad()
            loss = iris_loss(model(rgb, features), target)
            loss.backward()
            optimizer.step()
        self.assertGreater(float(model.correction.enc1.block[0].weight.grad.abs().sum()), 0)
        for name, value in initial.items():
            torch.testing.assert_close(model.base.state_dict()[name], value, rtol=0, atol=0)
        state = {'model': model.state_dict(), 'model_type': MODEL_TYPE, 'configuration': MODEL_CONFIG,
                 'sam_revision': SAM_REVISION}
        restored = load_checkpoint(state)
        model.eval()
        with torch.no_grad():
            torch.testing.assert_close(restored(rgb, features), model(rgb, features), rtol=0, atol=0)
        state['configuration'] = {**MODEL_CONFIG, 'residual_channels': 16}
        with self.assertRaises(ValueError):
            load_checkpoint(state)


if __name__ == '__main__':
    unittest.main()
