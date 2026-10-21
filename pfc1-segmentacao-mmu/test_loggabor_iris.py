import unittest
import numpy as np
from loggabor_iris import encode,normalized_scores
from matcher_hdbif_fft import prepare,distances
from comparador_hdbif_lote import gallery_batch

class LogGaborTests(unittest.TestCase):
    def test_circular_shift_equivariance(self):
        rng=np.random.default_rng(46);im=rng.integers(0,255,(64,512))
        a,ma=encode(im,np.ones_like(im,bool));b,mb=encode(np.roll(im,7,axis=1),np.ones_like(im,bool))
        np.testing.assert_array_equal(b,np.roll(a,7,axis=2));np.testing.assert_array_equal(mb,np.roll(ma,7,axis=1))

    def test_normalized_batch_matches_scalar_and_empty_rejects(self):
        rng=np.random.default_rng(47)
        q=prepare(rng.integers(0,2,(2,64,512)),np.ones((64,512))*255)
        g=prepare(rng.integers(0,2,(2,64,512)),np.ones((64,512))*255)
        raw,_,overlap=distances(q,g);d=.5-(.5-raw)*np.sqrt(overlap/(.5*64*512*2))
        expected=1-min(d[np.arange(-16,17)%512])
        self.assertAlmostEqual(float(normalized_scores(q,gallery_batch([g]))[0]),expected,places=12)
        empty=prepare(np.zeros((2,64,512)),np.zeros((64,512)))
        self.assertEqual(float(normalized_scores(empty,gallery_batch([g]))[0]),-2.)

if __name__=='__main__':unittest.main()
