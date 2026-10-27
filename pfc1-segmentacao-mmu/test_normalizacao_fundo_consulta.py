import unittest
import numpy as np
from normalizacao_fundo_consulta import fuse_background

class BackgroundTests(unittest.TestCase):
    def components(self,x):return [dict(scores=np.array([x],float),valid=np.array([True])) for _ in range(9)]
    def test_rank_preserved_and_no_label_input(self):
        x=[.1,.2,.4,.9];p=[[dict(mean=0,std=1)]*8]*2;y,v=fuse_background(self.components(x),p)
        self.assertTrue(v[0]);np.testing.assert_array_equal(np.argsort(y[0]),np.argsort(x))
    def test_genuine_peak_does_not_set_background_scale(self):
        p=[[dict(mean=0,std=1)]*8]*2;a,_=fuse_background(self.components([.1,.2,.4,.9]),p);b,_=fuse_background(self.components([.1,.2,.4,.7]),p)
        np.testing.assert_array_equal(a[0,:3],b[0,:3])
    def test_constant_background_is_failure(self):
        p=[[dict(mean=0,std=1)]*8]*2;y,v=fuse_background(self.components([.1,.1,.1,.9]),p);self.assertFalse(v[0]);self.assertTrue((y==-2).all())
if __name__=='__main__':unittest.main()
