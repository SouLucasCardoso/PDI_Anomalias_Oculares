import unittest
import numpy as np
import torch
from validar_textura_local import reliability, weighted_scores
from validar_correspondencia_espacial import spatial_scores


class LocalTextureTests(unittest.TestCase):
    def test_entropy_not_fill_detector(self):
        for value in (0, 127, 128, 255):
            np.testing.assert_array_equal(reliability(np.full((1,64,512,3),value,np.uint8)),0)
        pattern=np.tile(np.arange(16,dtype=np.uint8)*16,(1,64,32))
        np.testing.assert_allclose(reliability(np.repeat(pattern[...,None],3,-1)),1)

    def test_uniform_equivalence(self):
        generator=torch.Generator().manual_seed(5)
        q=torch.nn.functional.normalize(torch.randn(2,8,4,32,generator=generator),dim=1)
        g=torch.nn.functional.normalize(torch.randn(3,8,4,32,generator=generator),dim=1)
        torch.testing.assert_close(weighted_scores(q,g,torch.ones(2,4,32),torch.ones(3,4,32)),spatial_scores(q,g,0))

    def test_empty_and_unreliable_locations(self):
        q=torch.tensor([[[[1.,-1.]]]])
        g=torch.ones(1,1,1,2)
        torch.testing.assert_close(weighted_scores(q,g,torch.tensor([[[1.,0.]]]),torch.ones(1,1,2)),torch.ones(1,1))
        torch.testing.assert_close(weighted_scores(q,g,torch.zeros(1,1,2),torch.ones(1,1,2)),torch.full((1,1),-2.))


if __name__=='__main__':unittest.main()
