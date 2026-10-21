import unittest
import numpy as np
import torch
from treinar_metrica_automatica import BalancedBatches,batch_hard

class MetricTests(unittest.TestCase):
    def test_balanced_batches_have_repeated_distinct_eyes(self):
        labels=np.repeat(np.arange(20),5)
        for batch in BalancedBatches(labels,people_per_batch=8,captures_per_eye=4,rounds=2):
            eyes,counts=np.unique(labels[batch],return_counts=True)
            self.assertEqual(len(eyes),8);np.testing.assert_array_equal(counts,np.full(8,4))
            self.assertEqual(len(set(batch)),32)

    def test_separated_triplets_zero_and_collapsed_penalized(self):
        labels=torch.tensor([0,0,1,1])
        separated=torch.tensor([[1.,0.],[1.,0.],[-1.,0.],[-1.,0.]])
        self.assertAlmostEqual(float(batch_hard(separated,labels)),0.)
        collapsed=torch.ones((4,2),requires_grad=True)
        loss=batch_hard(collapsed,labels);self.assertAlmostEqual(float(loss.detach()),.2,places=6)
        loss.backward();self.assertTrue(torch.isfinite(collapsed.grad).all())

    def test_unpaired_batch_rejected(self):
        with self.assertRaises(ValueError):batch_hard(torch.eye(3),torch.arange(3))

if __name__=='__main__':unittest.main()
