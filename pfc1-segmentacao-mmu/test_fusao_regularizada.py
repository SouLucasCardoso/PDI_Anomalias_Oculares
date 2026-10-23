import unittest
import numpy as np
from treinar_fusao_regularizada import query_features,predict


class RegularizedFusionTests(unittest.TestCase):
    def test_features_are_scale_and_candidate_order_equivariant(self):
        rng=np.random.default_rng(4);scores=rng.normal(size=(2,16,9))
        z=query_features(scores)
        np.testing.assert_allclose(query_features(scores*3+4),z,atol=1e-6)
        np.testing.assert_array_equal(query_features(scores[:,::-1]),z[:,::-1])
        np.testing.assert_allclose(z[:,:,:7].mean(1),0,atol=1e-6)

    def test_constants_no_nan(self):
        np.testing.assert_array_equal(query_features(np.ones((1,16,9))),0)

    def test_labels_do_not_enter_prediction_and_failures_stay(self):
        rng=np.random.default_rng(6)
        components=[dict(scores=rng.uniform(0,1,(3,16)),valid=np.array([True,True,False]),labels=np.array([0,1,2])) for _ in range(9)]
        components[1]['scores'][0,4]=-2
        before,valid=predict(components,np.full(8,1/8))
        for c in components:c['labels'][:]=15
        after,_=predict(components,np.full(8,1/8))
        np.testing.assert_array_equal(before,after);self.assertEqual(before[0,4],-2);self.assertFalse(valid[2]);self.assertTrue((before[2]==-2).all())
        with self.assertRaises(ValueError):predict(components,np.ones(8))


if __name__=='__main__':unittest.main()
