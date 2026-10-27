import unittest
import numpy as np
from avaliar_irissam_ubipr import mask_box,affected_support,metrics
class TestIrisSamPreparation(unittest.TestCase):
    def test_box_uses_prediction_only_and_stays_in_frame(self):
        mask=np.zeros((20,30),bool);mask[3:13,4:25]=True;self.assertEqual(mask_box(mask),[4,3,24,12]);self.assertEqual(mask_box(mask,.05),[2,1,26,14]);self.assertIsNone(mask_box(np.zeros_like(mask)))
    def test_intervention_counts_and_direction(self):
        mask=np.ones((10,10),bool);upper=affected_support(mask,'upper10');lower=affected_support(mask,'lower10');self.assertEqual(int(upper.sum()),10);self.assertTrue(upper[0].all());self.assertTrue(lower[-1].all());self.assertFalse(affected_support(mask,'clean').any())
    def test_empty_failures_are_not_dropped(self):
        self.assertEqual(metrics(np.zeros((2,2),bool),np.ones((2,2),bool)),dict(dice=0.,iou=0.));self.assertEqual(metrics(np.zeros((2,2),bool),np.zeros((2,2),bool)),dict(dice=1.,iou=1.))
if __name__=='__main__':unittest.main()
