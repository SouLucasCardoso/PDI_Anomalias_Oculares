import unittest
import numpy as np
from matcher_hdbif_fft import prepare,distances,best_score

class MatcherTests(unittest.TestCase):
    def test_agrees_with_exhaustive_masked_hamming(self):
        rng=np.random.default_rng(42)
        a=rng.random((5,48,512))>.5; b=rng.random(a.shape)>.5
        ma=rng.random((64,512))>.25; mb=rng.random(ma.shape)>.3
        raw,normalized,overlap=distances(prepare(a,ma*255),prepare(b,mb*255))
        for shift in (-256,-16,0,7,16,255):
            intersection=ma[8:-8]&np.roll(mb[8:-8],shift,axis=1)
            total=intersection.sum()*5
            expected=((a^np.roll(b,shift,axis=2))&intersection[None]).sum()/total
            self.assertAlmostEqual(raw[shift%512],expected,places=12)
            self.assertEqual(overlap[shift%512],total)
            self.assertAlmostEqual(normalized[shift%512],.5-(.5-expected)*np.sqrt(total/(20603*5)),places=12)

    def test_wide_rotation_recovers_template_outside_default_range(self):
        a=np.random.default_rng(7).random((5,48,512))>.5
        mask=np.full((64,512),255,dtype=np.uint8)
        raw,_,_=distances(prepare(a,mask),prepare(np.roll(a,70,axis=2),mask))
        self.assertEqual(best_score(raw,None),1.)
        self.assertLess(best_score(raw,16),.6)

    def test_no_common_bits_is_rejection(self):
        code=np.zeros((5,48,512),dtype=bool); mask=np.zeros((64,512),dtype=np.uint8)
        raw,_,_=distances(prepare(code,mask),prepare(code,mask))
        self.assertEqual(best_score(raw,None),-2.)

if __name__=='__main__': unittest.main()
