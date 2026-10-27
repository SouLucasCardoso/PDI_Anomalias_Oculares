import unittest
import numpy as np
from descritor_regional_aprendido import sectors,fit_ridge,transform,pair_scores,eye_scores


class RegionalTest(unittest.TestCase):
    def test_sector_order_and_constant_maps(self):
        x=np.zeros((1,256,4,32),np.float32)
        for j in range(8):x[:,:,:,j*4:j*4+4]=j
        np.testing.assert_array_equal(sectors(x)[0,:,0],np.arange(8))

    def test_ridge_zero_weight_rows_have_no_effect(self):
        rng=np.random.default_rng(9);x=rng.normal(size=(12,8,256));y=rng.normal(size=(12,256));w=np.ones(12);w[-1]=0
        a=fit_ridge(x,y,w);x[-1]=999;y[-1]=-999;b=fit_ridge(x,y,w)
        for k in a:np.testing.assert_allclose(a[k],b[k],rtol=0,atol=1e-12)
        self.assertTrue(np.isfinite(transform(x,a)).all())

    def test_trim_and_gallery_top3(self):
        q=np.ones((1,8,256),np.float32)/16;g=q.copy();g[:,0:2]*=-1
        self.assertAlmostEqual(float(pair_scores(q,g,6)[0,0]),1.)
        self.assertAlmostEqual(float(pair_scores(q,g,8)[0,0]),.5)
        np.testing.assert_array_equal(eye_scores(q,np.repeat(g,4,axis=0),[[0],[1,2,3]],6),[[1.,1.]])

    def test_candidate_permutation(self):
        rng=np.random.default_rng(3);q=rng.normal(size=(2,8,256));g=rng.normal(size=(4,8,256));p=[2,0,3,1]
        np.testing.assert_allclose(pair_scores(q,g[p]),pair_scores(q,g)[:,p],rtol=1e-12,atol=1e-12)

if __name__=='__main__':unittest.main()
