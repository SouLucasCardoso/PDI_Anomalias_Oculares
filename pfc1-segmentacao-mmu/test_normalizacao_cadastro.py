import unittest
import numpy as np
from normalizacao_cadastro import fit,transform

class EnrollmentNormalizationTests(unittest.TestCase):
    def test_genuine_gallery_pairs_do_not_fit_impostor_cohort(self):
        x=np.array([[.9,.1,.3],[.8,.2,.4],[.2,.9,.5],[.3,.8,.6],[.4,.3,.9],[.5,.4,.8]])
        labels=np.repeat(np.arange(3),2);valid=np.ones(6,bool)
        before=fit(x,labels,valid);x[np.arange(6),labels]+=1000;after=fit(x,labels,valid)
        for a,b in zip(before,after):np.testing.assert_allclose(a,b)
        y=transform(np.array([[.3,-2,.5]]),before[0],before[1]);self.assertEqual(y[0,1],-2)
        self.assertTrue(np.isfinite(y).all())

if __name__=='__main__':unittest.main()
