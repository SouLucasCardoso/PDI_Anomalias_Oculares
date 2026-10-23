import unittest
import numpy as np
from diagnosticar_erros_validacao import decisions,transitions


class ErrorAuditTests(unittest.TestCase):
    def test_failures_never_correct_and_negative_scores_valid(self):
        data=dict(scores=np.array([[-2.,-2.],[-.8,-.4],[.9,.1]]),labels=np.array([0,1,0]),valid=np.array([False,True,False]))
        np.testing.assert_array_equal(decisions(data)[1],[False,True,False])

    def test_paired_transitions_partition_queries(self):
        result=transitions([True,True,False,False],[True,False,True,False])
        self.assertEqual(result,dict(both_correct=1,lost_correct=1,recovered=1,both_wrong=1))
        with self.assertRaises(ValueError):transitions([True],[True,False])


if __name__=='__main__':unittest.main()
