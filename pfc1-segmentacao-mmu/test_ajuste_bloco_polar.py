import unittest
import torch
from ajuste_bloco_polar import FullTail

class FullTailTests(unittest.TestCase):
    def test_original_equivalence_trainable_scope_and_restore(self):
        from treinar_identidade_iris import IdentityEncoder
        torch.set_num_threads(2);torch.manual_seed(63);encoder=IdentityEncoder().eval();model=FullTail(encoder).train();x=torch.randn(2,256,4,32)
        with torch.no_grad():expected=torch.nn.functional.normalize(encoder.projection(encoder.backbone.layer4(x).mean((-2,-1))),dim=1)
        torch.testing.assert_close(model(x),expected,rtol=0,atol=0)
        names={n for n,p in model.named_parameters() if p.requires_grad};self.assertEqual(len(names),5);self.assertTrue(all(n.startswith('block.') and n.endswith('.weight') for n in names));self.assertEqual(sum(p.numel() for p in model.parameters() if p.requires_grad),8388608)
        self.assertTrue(all(not m.training for m in model.modules() if isinstance(m,(torch.nn.BatchNorm1d,torch.nn.BatchNorm2d))))
        frozen=model.frozen_digest();self.assertEqual(float(model.anchor_loss()),0.)
        opt=torch.optim.SGD([p for p in model.parameters() if p.requires_grad],lr=1e-4);loss=(model(x)*torch.randn(2,256)).sum();loss.backward();opt.step();self.assertEqual(model.frozen_digest(),frozen);self.assertGreater(float(model.anchor_loss().detach()),0.)
        restored=FullTail(encoder);restored.load_adapters(model.adapters())
        with torch.no_grad():torch.testing.assert_close(model(x),restored(x),rtol=0,atol=0)
if __name__=='__main__':unittest.main()
