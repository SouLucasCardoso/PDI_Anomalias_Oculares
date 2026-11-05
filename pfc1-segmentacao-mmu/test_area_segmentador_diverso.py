import unittest
from avaliar_area_segmentador_diverso import criterion,prefix_minimum


class AreaProtocolTests(unittest.TestCase):
    def test_fractional_false_match_rate_is_not_rounded_to_pass(self):
        self.assertTrue(criterion(450,450,72,486,7290))
        self.assertFalse(criterion(450,450,73,486,7290))
        self.assertFalse(criterion(437,450,0,486,7290))

    def test_later_improvement_does_not_erase_prior_failure(self):
        self.assertEqual(prefix_minimum([0,1,2,5],[True,True,False,True]),99)
        self.assertIsNone(prefix_minimum([0,10],[False,True]))
        self.assertEqual(prefix_minimum([0,10,20],[True,True,True]),80)
        with self.assertRaises(ValueError):prefix_minimum([0,20,10],[True,True,True])


if __name__=='__main__':unittest.main()
