import unittest
import torch
from treinar_identidade_iris import AngularHead

class AngularMarginTests(unittest.TestCase):
    def test_zero_margin_is_scaled_cosine_classifier(self):
        torch.manual_seed(42); head=AngularHead(4,margin=0)
        features=torch.randn(3,256); labels=torch.tensor([0,2,1])
        expected=torch.nn.functional.linear(torch.nn.functional.normalize(features,dim=1),
                torch.nn.functional.normalize(head.weight,dim=1)).clamp(-1+1e-6,1-1e-6)*30
        torch.testing.assert_close(head(features,labels),expected)

    def test_margin_penalizes_target_and_has_finite_gradients(self):
        torch.manual_seed(7); head=AngularHead(4); plain=AngularHead(4,margin=0)
        plain.load_state_dict(head.state_dict())
        features=torch.randn(3,256,requires_grad=True); labels=torch.tensor([0,2,1])
        penalized=head(features,labels); original=plain(features,labels)
        self.assertTrue(torch.all(penalized[torch.arange(3),labels]<original[torch.arange(3),labels]))
        loss=torch.nn.functional.cross_entropy(penalized,labels); loss.backward()
        self.assertTrue(torch.isfinite(features.grad).all()); self.assertTrue(torch.isfinite(head.weight.grad).all())

if __name__=='__main__': unittest.main()
