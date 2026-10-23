import unittest
import numpy as np
from normalizar_consulta import normalize
from validar_dupla_segmentacao import combine

class DualSegmentationTests(unittest.TestCase):
    def test_identical_branches_preserve_rank_and_scores(self):
        scores,valid=normalize(np.array([[.1,.3,.8],[.8,.2,.4]]),np.ones(2,bool));data=dict(scores=scores,valid=valid,labels=np.array([2,0]));result=combine(data,data)
        np.testing.assert_allclose(result['scores'],scores,atol=1e-14);np.testing.assert_array_equal(result['scores'].argmax(1),scores.argmax(1))
    def test_queries_independent_and_either_failure_rejected(self):
        rng=np.random.default_rng(20);left=dict(scores=rng.uniform(.1,.9,(3,16)),valid=np.array([True,True,False]),labels=np.array([0,1,2]));right=dict(scores=rng.uniform(.1,.9,(3,16)),valid=np.array([True,False,True]),labels=left['labels']);left['scores'][0,3]=-2
        result=combine(left,right);self.assertEqual(result['scores'][0,3],-2);self.assertTrue((result['scores'][1:]==-2).all());self.assertEqual(result['valid'].tolist(),[True,False,False])
        one=combine({k:v[:1] for k,v in left.items()},{k:v[:1] for k,v in right.items()});np.testing.assert_array_equal(one['scores'][0],result['scores'][0])

if __name__=='__main__':unittest.main()
