import unittest
import numpy as np
from avaliar_complemento_geometrico import complementary_vectors

class TestComplement(unittest.TestCase):
    def test_cosine_is_fixed_weighted_sum_before_aggregation(self):
        rng=np.random.default_rng(63);a=rng.normal(size=(7,256)).astype('float32');b=rng.normal(size=(7,256)).astype('float32')
        a/=np.linalg.norm(a,axis=1,keepdims=True);b/=np.linalg.norm(b,axis=1,keepdims=True)
        joined=complementary_vectors(a,b)
        np.testing.assert_allclose(joined@joined.T,.75*(a@a.T)+.25*(b@b.T),atol=4e-7)
        np.testing.assert_allclose(np.linalg.norm(joined,axis=1),1,atol=2e-7)
    def test_bad_shapes_and_weights_rejected(self):
        with self.assertRaises(ValueError):complementary_vectors(np.zeros((2,3)),np.zeros((2,4)))
        with self.assertRaises(ValueError):complementary_vectors(np.zeros((2,3)),np.zeros((2,3)),0)
if __name__=='__main__':unittest.main()
