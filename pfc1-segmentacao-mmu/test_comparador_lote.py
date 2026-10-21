import unittest
import numpy as np
from matcher_hdbif_fft import prepare,distances,best_score
from comparador_hdbif_lote import gallery_batch,scores_batch,aggregate

class BatchTests(unittest.TestCase):
    def test_matches_scalar_with_mask_and_rotations(self):
        rng=np.random.default_rng(42)
        q=prepare(rng.integers(0,2,(5,12,64)),rng.integers(0,2,(16,64))*255)
        gs=[prepare(rng.integers(0,2,(5,12,64)),rng.integers(0,2,(16,64))*255) for _ in range(7)]
        actual=scores_batch(q,gallery_batch(gs))
        expected=[best_score(distances(q,g)[0],16) for g in gs]
        np.testing.assert_allclose(actual,expected,atol=1e-12,rtol=0)

    def test_empty_overlap_rejects(self):
        q=prepare(np.ones((5,12,64)),np.zeros((16,64)))
        np.testing.assert_array_equal(scores_batch(q,gallery_batch([q,q])),[-2,-2])

    def test_aggregation_does_not_accept_failed_enrollment(self):
        s=np.array([[-2,.4,.6,.8],[-2,-2,-2,-2]])
        np.testing.assert_allclose(aggregate(s,[[0,1,2],[3]],'top3'),[[.5,.8],[-2,-2]])
        np.testing.assert_array_equal(aggregate(s,[[0,1,2],[3]],'first'),[[-2,.8],[-2,-2]])

    def test_negative_cosines_are_valid_comparisons(self):
        np.testing.assert_allclose(aggregate(np.array([[-2,-.4,-.6]]),[[0,1,2]],'top3'),[[-.5]])

if __name__=='__main__': unittest.main()
