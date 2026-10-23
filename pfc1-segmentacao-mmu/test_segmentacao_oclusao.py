import unittest
import numpy as np
from treinar_segmentacao_oclusao import occlude

class OcclusionTrainingTests(unittest.TestCase):
    def test_exact_pixels_only_iris_and_target_unchanged(self):
        image=np.full((12,10,3),37,np.uint8);target=np.zeros((12,10),np.uint8);target[2:10,2:8]=1;target[5:7,4:6]=2;before=target.copy()
        for lower in [False,True]:
            altered=occlude(image,target,25,lower);changed=(altered!=image).any(2)
            self.assertEqual(int(changed.sum()),round(int((target==1).sum())*.25));self.assertTrue((target[changed]==1).all());np.testing.assert_array_equal(target,before)
            self.assertTrue((altered[changed]==128).all());np.testing.assert_array_equal(image,np.full_like(image,37))
    def test_empty_reference_kept_without_inventing_pixels(self):
        image=np.full((8,8,3),41,np.uint8);target=np.zeros((8,8),np.uint8)
        np.testing.assert_array_equal(occlude(image,target,40,False),image)

if __name__=='__main__':unittest.main()
