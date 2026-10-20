import unittest
from analisar_tolerancia_condicional import query_minima

class ConditionalTests(unittest.TestCase):
    def test_no_recovery_after_failure_and_no_imputation_for_original_failure(self):
        levels=[(10,[True,False,True]),(20,[False,True,True]),(30,[True,True,True])]
        self.assertEqual(query_minima([True,True,False],levels),[90,100,None])

    def test_success_at_every_tested_level_preserves_lowest_grid_value(self):
        self.assertEqual(query_minima([True],[(i,[True]) for i in range(10,100,10)]),[10])

if __name__=='__main__': unittest.main()
