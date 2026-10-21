import unittest
import numpy as np
from validar_alinhamento_fotometrico import aggregate_views

class PhotometricAlignmentTests(unittest.TestCase):
    def test_maximizes_views_after_same_eye_enrollment_aggregation(self):
        views=[np.array([[.9,.7,.3,.1]]),np.array([[.3,.1,.9,.7]])]
        result=aggregate_views(views,[[0,1],[2,3]])
        np.testing.assert_allclose(result,[[.8,.8]])
        self.assertTrue(np.all(result>=aggregate_views(views[:1],[[0,1],[2,3]])))

if __name__=='__main__':unittest.main()
