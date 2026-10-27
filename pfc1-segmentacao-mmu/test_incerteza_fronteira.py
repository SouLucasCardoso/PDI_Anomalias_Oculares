import unittest
import numpy as np
from incerteza_fronteira_area import prefix_outcomes,clustered_draws,prefix_distribution

class BoundaryUncertaintyTests(unittest.TestCase):
    def test_failed_original_is_undefined_and_recovery_does_not_skip_failure(self):
        actual=prefix_outcomes([[False,True,True],[True,False,True],[True,True,False],[True,True,True]])
        np.testing.assert_array_equal(actual,[-1,100,99,98])
        categories=prefix_distribution([[False,True,True],[True,False,True],[True,True,False],[True,True,True]])
        self.assertEqual(categories['98_percent_on_available_grid']['draws'],1)
        self.assertEqual(sum(r['draws'] for r in categories.values()),4)
    def test_cluster_draw_weights_query_counts_and_pairs_conditions(self):
        subjects=np.array([1,1,2]);values=np.array([[[1.,1.,0.],[1.,1.,0.],[0.,0.,1.]],[[0.,0.,1.],[0.,0.,1.],[1.,1.,0.]]])
        samples,_,_,_=clustered_draws(values,subjects,reps=50,seed=1)
        self.assertTrue(np.allclose(samples[:,0,0]+samples[:,1,0],1.))
        self.assertTrue(all(any(abs(v-x)<1e-14 for x in [0.,2/3,1.]) for v in samples[:,0,0]))
        np.testing.assert_array_equal(samples,clustered_draws(values,subjects,reps=50,seed=1)[0])

if __name__=='__main__':unittest.main()
