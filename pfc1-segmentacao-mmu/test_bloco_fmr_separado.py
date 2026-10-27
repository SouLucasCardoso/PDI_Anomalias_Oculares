import unittest
import numpy as np
from treinar_bloco_fmr_separado import clean_eligible,calibrate,measured

class SeparatedTests(unittest.TestCase):
    def test_clean_guard_rejects_degradation(self):
        baseline=dict(rank1=.99,tar=.98,far=.004)
        self.assertTrue(clean_eligible(baseline,baseline))
        self.assertFalse(clean_eligible(dict(rank1=.98,tar=.98,far=.001),baseline))
        self.assertFalse(clean_eligible(dict(rank1=.99,tar=.98,far=.006),baseline))
    def test_clean_threshold_frozen_for_altered_scores(self):
        scores=np.full((200,4),.1);scores[:,0]=.9;scores[0,1]=.8
        clean=dict(scores=scores,labels=np.zeros(200,dtype=int),valid=np.ones(200,bool));threshold=calibrate(clean)
        altered=dict(**clean);altered['scores']=scores.copy();altered['scores'][:,1]=.99
        m,_=measured(altered,threshold);self.assertEqual(m['threshold'],threshold);self.assertGreater(m['far'],.01)
    def test_failed_query_remains_rejected(self):
        d=dict(scores=np.array([[.9,.1],[.9,.1]]),labels=np.zeros(2,dtype=int),valid=np.array([True,False]));m,_=measured(d,.5)
        self.assertEqual(m['queries'],2);self.assertEqual(m['accepted'],1);self.assertEqual(m['extraction_failures'],1)
if __name__=='__main__':unittest.main()
