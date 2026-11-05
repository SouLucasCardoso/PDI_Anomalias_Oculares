import unittest
import numpy as np
from refinamento_sam3_pupila import remove_pupil,guard_roi,local_box


class PupilGuardTests(unittest.TestCase):
    def test_highest_valid_score_is_used_without_adding_iris(self):
        iris=np.zeros((100,100),bool);iris[20:80,20:80]=True
        outside=np.zeros_like(iris);outside[:10,:10]=True
        pupil=np.zeros_like(iris);pupil[40:60,40:60]=True
        result,selected,meta=remove_pupil(iris,np.stack([outside,pupil]),[.99,.8])
        self.assertEqual(meta['chosen_index'],1)
        self.assertEqual(int((iris & ~result).sum()),400)
        self.assertFalse((result & ~iris).any())
        np.testing.assert_array_equal(selected,pupil)

    def test_oversized_masks_or_missing_detection_preserve_coarse_prediction(self):
        iris=np.zeros((100,100),bool);iris[20:80,20:80]=True
        result,_,meta=remove_pupil(iris,iris[None],[.99])
        np.testing.assert_array_equal(result,iris);self.assertTrue(meta['fallback_unchanged'])
        result,_,_=remove_pupil(iris,np.zeros((0,100,100),bool),[])
        np.testing.assert_array_equal(result,iris)

    def test_empty_and_disjoint_roi_do_not_create_a_replacement(self):
        iris=np.zeros((100,100),bool);iris[20:40,20:40]=True
        self.assertIsNotNone(local_box(iris));self.assertIsNone(local_box(np.zeros_like(iris)))
        proposal=np.zeros_like(iris);proposal[70:90,70:90]=True
        result,meta=guard_roi(iris,proposal)
        self.assertFalse(meta['accepted']);np.testing.assert_array_equal(result,iris)
        with self.assertRaises(ValueError):remove_pupil(iris,np.zeros((1,99,100)),[.8])


if __name__=='__main__':unittest.main()
