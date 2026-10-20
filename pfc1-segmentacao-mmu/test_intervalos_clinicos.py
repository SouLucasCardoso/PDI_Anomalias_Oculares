import unittest
from relatar_validacao_hdbif import cluster_interval

class ClinicalIntervalTests(unittest.TestCase):
    def test_constant_outcomes_have_zero_spread(self):
        self.assertEqual(cluster_interval([1,1,1],['a','a','b'],100),[1.,1.])

    def test_person_clusters_preserve_repeated_queries(self):
        # Resampling two people can select only the successful or only the failed person.
        self.assertEqual(cluster_interval([1,1,0],['a','a','b'],500),[0.,1.])

    def test_empty_input_is_not_reported_as_zero_uncertainty(self):
        with self.assertRaises(ValueError): cluster_interval([],[])

if __name__=='__main__': unittest.main()
