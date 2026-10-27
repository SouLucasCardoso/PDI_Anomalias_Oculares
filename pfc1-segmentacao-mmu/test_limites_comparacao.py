import unittest
import numpy as np
from diagnosticar_limites_comparacao import describe

class LimitsTests(unittest.TestCase):
    def test_separated_and_failed_queries(self):
        scores=np.array([[.9,.1],[.1,.9],[.9,.1]])
        r=describe(scores,np.array([0,1,0]),np.array([True,True,False]),.5)
        self.assertEqual(r['correct'],2)
        self.assertEqual(r['diagnostic_accepted'],2)
        self.assertEqual(r['extraction_failures'],1)
        self.assertEqual(r['diagnostic_fmr'],0)
    def test_ties_cannot_be_accepted_for_free(self):
        r=describe(np.ones((4,2)),np.zeros(4,dtype=int),np.ones(4,bool),1.)
        self.assertEqual(r['diagnostic_accepted'],0)
        self.assertEqual(r['diagnostic_fmr'],0)
        self.assertEqual(r['genuine_tied_hardest_impostor'],4)
if __name__=='__main__':unittest.main()
