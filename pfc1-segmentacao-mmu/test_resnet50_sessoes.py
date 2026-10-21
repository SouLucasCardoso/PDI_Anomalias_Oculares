import unittest
import numpy as np
import torch
from reconhecedor_resnet50 import SessionBatches,supervised_contrastive

class SessionLearningTests(unittest.TestCase):
    def test_each_eye_balances_sessions_when_available(self):
        labels=np.repeat(np.arange(4),6);sessions=np.tile([1,1,1,2,2,2],4)
        for batch in SessionBatches(labels,sessions,p=4,rounds=2):
            for eye in range(4):
                selected=np.array(batch)[labels[batch]==eye]
                self.assertEqual(len(set(selected)),4)
                np.testing.assert_array_equal(np.sort(sessions[selected]),[1,1,2,2])

    def test_contrastive_penalizes_collapse_and_backpropagates(self):
        labels=torch.tensor([0,0,1,1]);good=torch.tensor([[1.,0.],[1.,0.],[-1.,0.],[-1.,0.]],requires_grad=True)
        collapsed=torch.ones(4,2)
        loss=supervised_contrastive(good,labels)
        self.assertLess(float(loss.detach()),float(supervised_contrastive(collapsed,labels)))
        loss.backward();self.assertTrue(torch.isfinite(good.grad).all())
        with self.assertRaises(ValueError):supervised_contrastive(torch.eye(3),torch.arange(3))

if __name__=='__main__':unittest.main()
