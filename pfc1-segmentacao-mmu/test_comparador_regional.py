import unittest
import numpy as np
from comparador_regional import compare,regions

class RegionalTests(unittest.TestCase):
    def test_fixed_trim_discards_eight_worst(self):
        q=np.zeros((1,32,256),np.float32);q[:,:,0]=1;g=q.copy();g[:,:8,0]=-1
        self.assertEqual(float(compare(q,g,24)[0,0]),1.)
        self.assertEqual(float(compare(q,g,32)[0,0]),.5)
    def test_zero_map_is_finite(self):
        x=regions(np.zeros((2,256,4,32)),np.zeros(256),np.ones(256))
        self.assertEqual(x.shape,(2,32,256));self.assertTrue(np.isfinite(x).all());self.assertEqual(float(compare(x,x).sum()),0.)
    def test_gallery_permutation_only_permutes_scores(self):
        rng=np.random.default_rng(63);x=regions(rng.normal(size=(3,256,4,32)),np.zeros(256),np.ones(256))
        np.testing.assert_allclose(compare(x,x)[...,[2,0,1]],compare(x,x[[2,0,1]]),atol=1e-7)
if __name__=='__main__':unittest.main()
