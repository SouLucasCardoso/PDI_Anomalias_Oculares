import unittest
import torch
from atencao_polar import AttentionTail

class AttentionTests(unittest.TestCase):
    def test_initial_equivalence_frozen_weights_and_restore(self):
        from treinar_identidade_iris import IdentityEncoder
        torch.set_num_threads(2);torch.manual_seed(63);encoder=IdentityEncoder().eval();model=AttentionTail(encoder).train();x=torch.randn(3,256,4,32)
        with torch.no_grad():expected=torch.nn.functional.normalize(encoder.projection(encoder.backbone.layer4(x).mean((-2,-1))),dim=1);actual=model(x)
        torch.testing.assert_close(actual,expected,atol=1e-6,rtol=1e-6)
        self.assertEqual(sum(p.numel() for p in model.parameters() if p.requires_grad),16449)
        self.assertTrue(all(n.startswith('attention.') for n,p in model.named_parameters() if p.requires_grad))
        frozen=model.frozen_digest();opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1e-3);loss=(model(x)*torch.randn(3,256)).sum();loss.backward();opt.step();self.assertEqual(model.frozen_digest(),frozen)
        restored=AttentionTail(encoder);restored.load_adapters(model.adapters())
        with torch.no_grad():torch.testing.assert_close(model(x),restored(x),rtol=0,atol=0)
    def test_attention_keeps_uniform_floor_and_unit_sum(self):
        from treinar_identidade_iris import IdentityEncoder
        model=AttentionTail(IdentityEncoder());torch.nn.init.normal_(model.attention[-1].weight,std=10);x=torch.randn(2,512,2,16);w=model.weights(x)
        self.assertTrue(bool((w>=.5/32).all()));torch.testing.assert_close(w.sum((1,2,3)),torch.ones(2));self.assertTrue(torch.isfinite(w).all())
if __name__=='__main__':unittest.main()
