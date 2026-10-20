import unittest
from relatar_area_preservada import minimum_fraction

class AreaCriterionTests(unittest.TestCase):
    def test_no_minimum_when_original_cannot_identify(self):
        self.assertIsNone(minimum_fraction({'rank1':.89,'tar':1},[{'level':90,'rank1':1,'tar':1}]))

    def test_recovery_after_failure_does_not_allow_cherry_picking(self):
        rows=[{'level':10,'rank1':.95,'tar':.95},
              {'level':20,'rank1':.95,'tar':.89},
              {'level':30,'rank1':1,'tar':1}]
        self.assertEqual(minimum_fraction({'rank1':1,'tar':1},rows),90)

    def test_qualification_requires_both_measures(self):
        self.assertEqual(minimum_fraction({'rank1':.9,'tar':.9},[{'level':10,'rank1':1,'tar':.89}]),100)

if __name__=='__main__': unittest.main()
