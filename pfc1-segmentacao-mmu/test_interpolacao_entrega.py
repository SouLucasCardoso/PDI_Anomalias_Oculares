import unittest
import torch
from avaliar_interpolacao_encoder_entrega import interpolate

class InterpolationTests(unittest.TestCase):
    def test_frozen_values_and_integer_buffers_preserved_exactly(self):
        a={'backbone.layer1.weight':torch.tensor([.123456789]),'projection.num_batches_tracked':torch.tensor(17),'backbone.layer4.weight':torch.tensor([2.])}
        b={k:v.clone() for k,v in a.items()};b['backbone.layer4.weight']=torch.tensor([6.])
        c=interpolate(a,b,.25)
        self.assertTrue(torch.equal(c['backbone.layer1.weight'],a['backbone.layer1.weight']))
        self.assertTrue(torch.equal(c['projection.num_batches_tracked'],a['projection.num_batches_tracked']))
        self.assertEqual(c['backbone.layer4.weight'].item(),3.)
    def test_rejects_changed_running_statistics(self):
        with self.assertRaises(ValueError):interpolate({'backbone.layer4.bn.running_mean':torch.tensor([0.])},{'backbone.layer4.bn.running_mean':torch.tensor([1.])},.5)
    def test_rejects_changes_outside_authorized_blocks(self):
        with self.assertRaises(ValueError):interpolate({'backbone.layer1.weight':torch.tensor([0.])},{'backbone.layer1.weight':torch.tensor([1.])},.5)

if __name__=='__main__':unittest.main()
