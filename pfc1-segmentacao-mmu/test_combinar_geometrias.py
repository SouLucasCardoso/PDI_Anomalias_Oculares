import unittest
import numpy as np
from combinar_geometrias_sam31 import blend_component

class BlendGeometryTests(unittest.TestCase):
    def test_missing_sam_keeps_original_pair_and_query(self):
        a={'scores':np.array([[.8,.4],[.2,.7]]),'valid':np.array([True,True]),'labels':np.array([0,1])}
        b={'scores':np.array([[.6,-2.],[-2.,-2.]]),'valid':np.array([True,False]),'labels':np.array([0,1])}
        r=blend_component(a,b,.5)
        np.testing.assert_allclose(r['scores'],[[.7,.4],[.2,.7]])
        np.testing.assert_array_equal(r['valid'],a['valid'])
        np.testing.assert_array_equal(a['scores'],[[.8,.4],[.2,.7]])
    def test_labels_cannot_change_inference_scores(self):
        a={'scores':np.array([[.8,.4]]),'valid':np.array([True]),'labels':np.array([0])}
        b={'scores':np.array([[.6,.5]]),'valid':np.array([True]),'labels':np.array([0])}
        r=blend_component(a,b,.25)['scores'];a['labels'][0]=1;b['labels'][0]=1
        np.testing.assert_array_equal(r,blend_component(a,b,.25)['scores'])

if __name__=='__main__':unittest.main()
