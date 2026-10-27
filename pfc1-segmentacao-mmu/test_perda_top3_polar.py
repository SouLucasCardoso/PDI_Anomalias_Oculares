import unittest
import numpy as np
import torch
from perda_top3_polar import top3_eye_scores,top3_hard_negative_loss
class TestTop3Loss(unittest.TestCase):
    def test_matches_real_comparator_including_negative_cosines_and_padding(self):
        from comparador_hdbif_lote import aggregate
        rng=np.random.default_rng(63);q=rng.normal(size=(5,3,8)).astype('float32');g=rng.normal(size=(3,5,8)).astype('float32');present=np.array([[True]*5,[True,False,False,False,False],[True,True,False,False,False]])
        q/=np.linalg.norm(q,axis=-1,keepdims=True);g/=np.linalg.norm(g,axis=-1,keepdims=True)
        scores=top3_eye_scores(torch.from_numpy(q),torch.from_numpy(g),torch.from_numpy(present)).numpy()
        flat=g.reshape(-1,8);expected=aggregate(q.reshape(-1,8)@flat.T,[np.flatnonzero(present[j])+j*5 for j in range(3)],'top3').reshape(5,3,3)
        np.testing.assert_allclose(scores,expected,rtol=0,atol=2e-7)
    def test_same_side_hardest_negative_frozen_gallery_and_int32_targets(self):
        gallery=torch.eye(3)[:,None].repeat(1,3,1).requires_grad_();present=torch.ones(3,3,dtype=torch.bool);sides=torch.tensor([0,0,1]);labels=torch.tensor([0],dtype=torch.int32);query=torch.tensor([True]);good=torch.tensor([[[1.,0.,0.]]*3],requires_grad=True);bad=torch.tensor([[[0.,1.,0.]]*3],requires_grad=True)
        a=top3_hard_negative_loss(good,labels,query,gallery,present,sides);b=top3_hard_negative_loss(bad,labels,query,gallery,present,sides);self.assertLess(float(a.detach()),float(b.detach()));b.backward();self.assertIsNone(gallery.grad);self.assertIsNotNone(bad.grad)
        changed=gallery.detach().clone();changed[2]=100;torch.testing.assert_close(a,top3_hard_negative_loss(good,labels,query,changed,present,sides),rtol=0,atol=0)
    def test_enrollment_rows_have_no_ranking_loss(self):
        pred=torch.randn(2,3,3,requires_grad=True);loss=top3_hard_negative_loss(pred,torch.tensor([0,1]),torch.zeros(2,dtype=torch.bool),torch.eye(3)[:,None],torch.ones(3,1,dtype=torch.bool),torch.tensor([0,0,1]));loss.backward();self.assertEqual(float(loss.detach()),0.);self.assertTrue(torch.equal(pred.grad,torch.zeros_like(pred)))
if __name__=='__main__':unittest.main()
