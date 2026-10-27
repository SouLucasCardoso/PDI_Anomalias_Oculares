import unittest
import numpy as np
from piloto_sam_guiado import automatic_prompts,dice_iou
class TestGuidedSam(unittest.TestCase):
    def test_prompts_respect_observed_mask_and_hole(self):
        y,x=np.indices((60,80));mask=((x-40)**2+(y-30)**2<20**2)&((x-40)**2+(y-30)**2>8**2)
        p=automatic_prompts(mask)
        for point,label in zip(p['points'],p['labels']):self.assertEqual(bool(mask[round(point[1]),round(point[0])]),bool(label))
        self.assertEqual(sum(p['labels']),4);self.assertIn([40.,30.],p['points'])
    def test_empty_prediction_retained_as_failure(self):
        with self.assertRaises(ValueError):automatic_prompts(np.zeros((20,30),bool))
        self.assertEqual(dice_iou(np.zeros((2,2),bool),np.ones((2,2),bool)),dict(dice=0.,iou=0.))
if __name__=='__main__':unittest.main()
