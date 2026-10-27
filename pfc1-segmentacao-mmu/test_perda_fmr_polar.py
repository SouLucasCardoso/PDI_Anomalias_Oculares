import unittest
import numpy as np
import torch
from perda_fmr_polar import fit_impostor_reference,top3_absolute_loss
class TestAbsoluteLoss(unittest.TestCase):
    def test_reference_excludes_genuine_and_failed_query(self):
        scores=np.array([[.8,.2,.1],[.3,.8,.2],[.99,.99,.99]]);labels=np.array([0,1,2]);valid=np.array([True,True,False]);t,n=fit_impostor_reference(scores,labels,valid)
        changed=scores.copy();changed[np.arange(3),labels]=-100;changed[2]=100
        self.assertEqual((t,n),fit_impostor_reference(changed,labels,valid));self.assertEqual(n,4)
    def test_penalizes_absolute_impostor_and_low_genuine(self):
        gallery=torch.eye(3)[:,None].requires_grad_();present=torch.ones(3,1,dtype=torch.bool);sides=torch.tensor([0,0,1]);label=torch.tensor([0],dtype=torch.int32);query=torch.tensor([True])
        safe=torch.tensor([[[.8,.1,0.]]*3],requires_grad=True);high=torch.tensor([[[.8,.5,0.]]*3],requires_grad=True);low=torch.tensor([[[.1,.1,0.]]*3],requires_grad=True)
        fn=lambda x,g=gallery:top3_absolute_loss(x,label,query,g,present,sides,.3)
        self.assertEqual(float(fn(safe).detach()),0.);self.assertGreater(float(fn(high).detach()),0.);self.assertGreater(float(fn(low).detach()),0.);fn(high).backward();self.assertIsNone(gallery.grad);self.assertIsNotNone(high.grad)
        altered=gallery.detach().clone();altered[2]=100;torch.testing.assert_close(fn(high),fn(high,altered),rtol=0,atol=0)
    def test_enrollment_only_has_zero_loss_and_gradient(self):
        pred=torch.randn(2,3,3,requires_grad=True);loss=top3_absolute_loss(pred,torch.tensor([0,1]),torch.zeros(2,dtype=torch.bool),torch.eye(3)[:,None],torch.ones(3,1,dtype=torch.bool),torch.tensor([0,0,1]),.3);loss.backward();self.assertEqual(float(loss.detach()),0.);self.assertTrue(torch.equal(pred.grad,torch.zeros_like(pred)))
if __name__=='__main__':unittest.main()
