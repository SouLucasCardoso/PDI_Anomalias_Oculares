import unittest
import numpy as np
from transportar_descritor_polar import apply_transport

class TransportTests(unittest.TestCase):
    def test_unchanged_rows_are_bit_exact_and_dtype_preserved(self):
        features=np.array([[1.,0.],[0.,1.],[.6,.8]],dtype=np.float32)
        parameters=dict(mean=np.zeros(2),std=np.ones(2),matrix=np.zeros((2,2)),offset=np.array([.2,-.1]))
        changed=np.array([False,True,False]);before=features.copy();result=apply_transport(features,changed,parameters)
        np.testing.assert_array_equal(result[~changed],features[~changed]);np.testing.assert_array_equal(features,before)
        self.assertEqual(result.dtype,np.float32);self.assertAlmostEqual(float(np.linalg.norm(result[1])),1.,places=6)
    def test_no_changed_geometry_does_not_need_model(self):
        features=np.array([[.6,.8]],dtype=np.float32)
        np.testing.assert_array_equal(apply_transport(features,np.array([False]),None),features)
    def test_single_query_is_independent_of_other_queries(self):
        features=np.array([[1.,0.],[0.,1.]],dtype=np.float32);parameters=dict(mean=np.zeros(2),std=np.ones(2),matrix=np.eye(2)*.1,offset=np.array([.01,-.01]))
        np.testing.assert_array_equal(apply_transport(features,np.array([True,True]),parameters)[0],apply_transport(features[:1],np.array([True]),parameters)[0])

if __name__=='__main__':unittest.main()
