import unittest
import torch
from perda_identidade_polar import session_identity_loss,selection_key
class TestIdentityLoss(unittest.TestCase):
    def test_correct_eye_and_same_side_and_frozen_prototypes(self):
        prototypes=torch.eye(3,requires_grad=True);sides=torch.tensor([0,0,1]);labels=torch.tensor([0]);query=torch.tensor([True]);good=torch.tensor([[[1.,0.,0.]]*3],requires_grad=True);bad=torch.tensor([[[0.,1.,0.]]*3],requires_grad=True)
        a=session_identity_loss(good,labels,query,prototypes,sides);b=session_identity_loss(bad,labels,query,prototypes,sides);self.assertLess(float(a.detach()),float(b.detach()));b.backward();self.assertIsNone(prototypes.grad);self.assertIsNotNone(bad.grad)
        torch.testing.assert_close(a,session_identity_loss(good,labels.int(),query,prototypes,sides),rtol=0,atol=0)
        changed=prototypes.detach().clone();changed[2]=torch.tensor([100.,100.,100.]);torch.testing.assert_close(a,session_identity_loss(good,labels,query,changed,sides),rtol=0,atol=0)
    def test_enrollment_rows_do_not_enter_identity_loss(self):
        pred=torch.randn(2,3,3,requires_grad=True);loss=session_identity_loss(pred,torch.tensor([0,1]),torch.tensor([False,False]),torch.eye(3),torch.tensor([0,0,1]));loss.backward();self.assertEqual(float(loss.detach()),0.);self.assertTrue(torch.equal(pred.grad,torch.zeros_like(pred)))
    def test_compliant_epoch_beats_larger_noncompliant_tar(self):
        base={t:dict(rank1=.5,tar=.4,far=.009) for t in ['clean','upper10','lower10']};good={t:dict(rank1=.6,tar=.5,far=.009) for t in base};bad={t:dict(rank1=.8,tar=.7,far=.012 if t!='clean' else .009) for t in base};cos={t:1. for t in base};self.assertGreater(selection_key(good,cos,base,1),selection_key(bad,cos,base,1))
if __name__=='__main__':unittest.main()
