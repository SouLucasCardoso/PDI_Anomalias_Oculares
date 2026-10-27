import unittest
import numpy as np
import torch
from pupila_eliptica import EllipticShape,encode_shape,decode_shape,contained
from normalizacao_eliptica import ellipse_endpoints

class EllipseShapeTests(unittest.TestCase):
    def test_roundtrip_orientation_and_axis_swap(self):
        original=((10.,20.),(30.,12.),37.)
        vector=encode_shape(original)
        equivalent=((10.,20.),(12.,30.),127.)
        np.testing.assert_allclose(vector,encode_shape(equivalent),atol=1e-7)
        reconstructed=decode_shape(original[0],np.sqrt(30*12)/2,vector)
        angles=np.arange(512)*2*np.pi/512
        for before,after in zip(ellipse_endpoints(original,angles),ellipse_endpoints(reconstructed,angles)):
            np.testing.assert_allclose(before,after,atol=1e-5)
    def test_shape_preserves_center_and_equivalent_area(self):
        center=(15.,25.);radius=4.
        ellipse=decode_shape(center,radius,np.array([.4,-.2]))
        self.assertEqual(ellipse[0],center)
        self.assertAlmostEqual(ellipse[1][0]*ellipse[1][1],4*radius**2,places=10)
    def test_isotropic_initialization(self):
        model=EllipticShape();self.assertEqual(sum(p.numel() for p in model.parameters()),8194)
        with torch.no_grad():np.testing.assert_array_equal(model(torch.ones(2,4096)).numpy(),np.zeros((2,2)))
        ellipse=decode_shape((0.,0.),5.,np.zeros(2));self.assertEqual(ellipse[1],(10.,10.))
    def test_full_containment_beyond_center(self):
        outer=((0.,0.),(20.,8.),0.)
        self.assertFalse(contained(((0.,0.),(16.,16.),0.),outer))
        self.assertTrue(contained(((0.,0.),(12.,4.),0.),outer))

if __name__=='__main__':unittest.main()
