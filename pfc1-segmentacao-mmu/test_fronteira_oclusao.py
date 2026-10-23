import unittest
from refinar_oclusao_congelada import prefix_minimum

class PrefixMinimumTests(unittest.TestCase):
    def test_recovery_after_failure_cannot_reduce_minimum(self):
        self.assertEqual(prefix_minimum([(1,True),(2,False),(3,True)]),99)
    def test_missing_larger_area_is_rejected(self):
        with self.assertRaises(ValueError):prefix_minimum([(2,True)])
    def test_first_loss_failure_requires_full_original(self):
        self.assertEqual(prefix_minimum([(1,False)]),100)

if __name__=='__main__':unittest.main()
