import unittest
import numpy as np
from normalizacao_coorte_polar import cohort_stats,symmetric_scores

class CohortTests(unittest.TestCase):
    def test_symmetric_formula(self):
        q=np.array([[1.,0.]]);g=np.array([[1.,0.],[0.,1.]])
        result=symmetric_scores(q,g,np.array([[.2,.1]]),np.array([[.1,.2],[.3,.1]]))
        np.testing.assert_allclose(result,[[6.25,-2.5]])
    def test_opposite_side_cannot_change_statistics(self):
        vectors=np.array([[1.,0.]]);valid=np.array([True]);sides=np.array([0]);cohort=np.array([[1.,0.],[0.,1.],[-1.,0.]])
        one=cohort_stats(vectors,valid,sides,cohort,np.ones(3,bool),np.array([0,0,1]),[[0],[1],[2]])
        cohort[2]=[100.,100.];two=cohort_stats(vectors,valid,sides,cohort,np.ones(3,bool),np.array([0,0,1]),[[0],[1],[2]])
        np.testing.assert_array_equal(one,two)
    def test_constant_cohort_uses_fixed_floor(self):
        x=np.ones((1,2));c=np.ones((2,2));r=cohort_stats(x,np.array([True]),np.array([0]),c,np.ones(2,bool),np.zeros(2,int),[[0],[1]])
        self.assertEqual(r[0,1],.05)
if __name__=='__main__':unittest.main()
