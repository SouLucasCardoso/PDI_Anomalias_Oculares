import unittest
import numpy as np
from treinar_identidade_residual import fit_residual,correct

class ResidualIdentityTests(unittest.TestCase):
    def test_constant_training_features_keep_unpenalized_offset_finite(self):
        x=np.ones((5,4));delta=np.tile([.2,-.1],(5,1));parameters=fit_residual(x,delta,np.array([2.,1.,1.,1.,1.]));base=np.tile([1.,0.],(2,1));actual=correct(np.ones((2,4)),base,parameters);expected=np.array([1.2,-.1]);expected/=np.linalg.norm(expected)
        self.assertTrue(np.isfinite(actual).all());np.testing.assert_allclose(actual,np.tile(expected,(2,1)),atol=1e-12);np.testing.assert_allclose(parameters['matrix'],0,atol=1e-12)
    def test_correction_is_independent_of_other_queries(self):
        rng=np.random.default_rng(5);x=rng.normal(size=(20,4));parameters=fit_residual(x,rng.normal(size=(20,3))*.1,np.ones(20));raw=rng.normal(size=(2,4));base=rng.normal(size=(2,3));actual=correct(raw,base,parameters)
        np.testing.assert_allclose(actual[0],correct(raw[:1],base[:1],parameters)[0],atol=1e-14);np.testing.assert_allclose(np.linalg.norm(actual,axis=1),1,atol=1e-14)

if __name__=='__main__':unittest.main()
