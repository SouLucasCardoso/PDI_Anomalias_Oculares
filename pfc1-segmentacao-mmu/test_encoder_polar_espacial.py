import unittest
import torch
from encoder_polar_espacial import SpatialTail,prefix_model
class TestSpatialTail(unittest.TestCase):
    def test_zero_correction_matches_original_and_only_corrections_train(self):
        from treinar_identidade_iris import IdentityEncoder
        torch.set_num_threads(2);torch.manual_seed(63);encoder=IdentityEncoder().eval();tail=SpatialTail(encoder).train();x=torch.randn(2,3,64,512)
        with torch.no_grad():features=prefix_model(encoder)(x);expected=encoder(x);actual=tail(features)
        torch.testing.assert_close(actual,expected,atol=1e-6,rtol=1e-6)
        parameters=[(n,p) for n,p in tail.named_parameters() if p.requires_grad];self.assertTrue(parameters);self.assertTrue(all('.low_' in n for n,p in parameters));self.assertEqual(sum(p.numel() for n,p in parameters),145408)
        self.assertTrue(all(not m.training for m in tail.modules() if isinstance(m,(torch.nn.BatchNorm1d,torch.nn.BatchNorm2d))))
        frozen=tail.frozen_digest();optimizer=torch.optim.AdamW([p for n,p in parameters],lr=1e-4);loss=(tail(features)*torch.randn(2,256)).sum();loss.backward();optimizer.step();self.assertEqual(tail.frozen_digest(),frozen)
        restored=SpatialTail(encoder);restored.load_adapters(tail.adapters())
        with torch.no_grad():torch.testing.assert_close(tail(features),restored(features),rtol=0,atol=0)
if __name__=='__main__':unittest.main()
