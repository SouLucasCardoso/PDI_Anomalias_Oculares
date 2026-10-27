import unittest
import numpy as np
from oclusao_diversa_polar import paint,HybridMaps

class DiverseTests(unittest.TestCase):
    def test_exact_native_support_and_direction(self):
        image=np.zeros((10,10,3),np.uint8);mask=np.ones((10,10),bool)
        for kind,row in [('upper',0),('lower',9)]:
            photo,support=paint(image,mask,kind,10,192);self.assertEqual(int(support.sum()),10);self.assertTrue(support[row].all());self.assertTrue((np.asarray(photo)[support]==192).all());self.assertTrue((np.asarray(photo)[~support]==0).all())
    def test_empty_reference_does_not_change_photo(self):
        image=np.full((4,5,3),128,np.uint8);photo,support=paint(image,np.zeros((4,5),bool),'upper',20,32);self.assertFalse(support.any());np.testing.assert_array_equal(np.asarray(photo),image)
    def test_hybrid_indexing_preserves_order_and_repeats(self):
        base=np.arange(6).reshape(3,2);extra=np.arange(6,10).reshape(2,2);maps=HybridMaps(base,extra);np.testing.assert_array_equal(maps[[4,0,3,0]],np.concatenate([base,extra])[[4,0,3,0]]);np.testing.assert_array_equal(maps[1],base[1])
        with self.assertRaises(IndexError):maps[5]
if __name__=='__main__':unittest.main()
