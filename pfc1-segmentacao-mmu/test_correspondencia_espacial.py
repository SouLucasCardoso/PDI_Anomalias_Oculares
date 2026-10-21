import unittest
import torch
from validar_correspondencia_espacial import spatial_scores

class SpatialTests(unittest.TestCase):
    def test_known_angular_shift_recovered_without_radial_shift(self):
        torch.manual_seed(48)
        gallery=torch.nn.functional.normalize(torch.randn(2,8,3,16),dim=1)
        query=torch.roll(gallery[:1],2,dims=-1)
        corrected=spatial_scores(query,gallery,2)
        self.assertAlmostEqual(float(corrected[0,0]),1.,places=6)
        self.assertGreater(float(corrected[0,0]),float(corrected[0,1]))
        self.assertLess(float(spatial_scores(query,gallery,0)[0,0]),.9)

if __name__=='__main__':unittest.main()
