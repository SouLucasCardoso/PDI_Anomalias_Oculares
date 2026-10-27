import unittest
import torch
from torch.nn import functional as F
from perda_vistas_validas import valid_losses,reduce_views
from perda_top3_polar import top3_hard_negative_loss
from perda_fmr_polar import top3_absolute_loss


class ValidLossTest(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)
        self.p=F.normalize(torch.randn(4,3,8,dtype=torch.float64),dim=-1).detach().requires_grad_()
        self.t=F.normalize(torch.randn(4,8,dtype=torch.float64),dim=-1)
        self.labels=torch.tensor([0,1,2,3]);self.q=torch.tensor([True,True,True,False])
        self.g=F.normalize(torch.randn(4,4,8,dtype=torch.float64),dim=-1)
        self.present=torch.ones(4,4,dtype=torch.bool);self.sides=torch.tensor([0,0,1,1])

    def loss(self,valid):
        return valid_losses(self.p,self.t,self.labels,self.q,self.g,self.present,self.sides,.3,valid)

    def test_all_valid_matches_legacy_values_and_gradients(self):
        new=self.loss(torch.ones(4,3,dtype=torch.bool))
        old=(((1-(self.p*self.t[:,None]).sum(-1))*self.p.new_tensor([4.,1.,1.])).sum(1).mean()/6,
             top3_hard_negative_loss(self.p,self.labels,self.q,self.g,self.present,self.sides),
             top3_absolute_loss(self.p,self.labels,self.q,self.g,self.present,self.sides,.3))
        for a,b in zip(new,old):
            torch.testing.assert_close(a,b,rtol=1e-12,atol=1e-12)
            ga=torch.autograd.grad(a,self.p,retain_graph=True)[0];gb=torch.autograd.grad(b,self.p,retain_graph=True)[0]
            torch.testing.assert_close(ga,gb,rtol=1e-12,atol=1e-12)

    def test_invalid_views_zero_gradient_all_terms(self):
        valid=torch.ones(4,3,dtype=torch.bool);valid[0,1]=False;valid[2,2]=False
        for loss in self.loss(valid):
            grad=torch.autograd.grad(loss,self.p,retain_graph=True)[0]
            self.assertEqual(float(grad[~valid].abs().sum()),0.)
            self.assertGreater(float(grad[valid].abs().sum()),0.)

    def test_no_valid_views_zero_losses(self):
        for loss in self.loss(torch.zeros(4,3,dtype=torch.bool)):
            self.assertEqual(float(loss),0.)
            self.assertEqual(float(torch.autograd.grad(loss,self.p,retain_graph=True)[0].abs().sum()),0.)

    def test_missing_view_does_not_reweight_other_views(self):
        x=torch.ones(2,3,dtype=torch.float64);v=torch.ones_like(x,dtype=torch.bool);v[:,1]=False
        self.assertAlmostEqual(float(reduce_views(x,v)),5/6)

    def test_no_queries_only_alignment(self):
        losses=valid_losses(self.p,self.t,self.labels,torch.zeros_like(self.q),self.g,self.present,self.sides,.3,torch.ones(4,3,dtype=torch.bool))
        self.assertGreater(float(losses[0]),0.);self.assertEqual(float(losses[1]+losses[2]),0.)

if __name__=='__main__':unittest.main()
