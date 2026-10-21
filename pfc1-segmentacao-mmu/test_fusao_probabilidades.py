import unittest
import numpy as np
from validar_fusao_probabilidades import mean_probabilities

class ProbabilityFusionTests(unittest.TestCase):
    def test_query_independence_missing_candidates_and_failures(self):
        z=np.array([[2.,0.,100.],[1.,2.,3.],[4.,5.,6.]])
        available=np.array([[True,True,False],[True,True,True],[True,True,True]])
        result=mean_probabilities([z,z*.5],available,np.array([True,True,False]))
        only=mean_probabilities([z[:1],z[:1]*.5],available[:1],np.array([True]))
        np.testing.assert_allclose(result[:1],only)
        self.assertEqual(result[0,2],-2);self.assertEqual(result[0,:2].sum(),1)
        np.testing.assert_array_equal(result[2],[-2,-2,-2])

if __name__=='__main__':unittest.main()
