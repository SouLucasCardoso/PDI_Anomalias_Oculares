import unittest
import numpy as np
from validar_consenso_geometrias import consensus
from normalizar_consulta import normalize

class TestConsensus(unittest.TestCase):
    def test_identical_branches_match_normalization_and_keep_failures(self):
        branch={'scores':np.array([[.1,.7,.4],[-2.,-2.,-2.]]),'valid':np.array([True,False])}
        expected,valid=normalize(branch['scores'],branch['valid'])
        actual,actual_valid=consensus(branch,branch)
        np.testing.assert_allclose(actual,expected,atol=1e-12)
        np.testing.assert_array_equal(actual_valid,valid)
        np.testing.assert_array_equal(actual[1],[-2.,-2.,-2.])
    def test_unavailable_candidate_cannot_be_recovered_by_other_branch(self):
        a={'scores':np.array([[.4,.5,-2.]]),'valid':np.array([True])}
        b={'scores':np.array([[.6,.3,.9]]),'valid':np.array([True])}
        values,valid=consensus(a,b)
        self.assertTrue(valid[0]);self.assertEqual(values[0,2],-2.)

if __name__=='__main__':unittest.main()
