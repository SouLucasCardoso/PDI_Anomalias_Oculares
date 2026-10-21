import unittest
import numpy as np
from reconhecedor_convnext import contrast

class ContrastTests(unittest.TestCase):
    def test_preserves_black_exterior_and_geometry(self):
        image=np.zeros((128,128,3),np.uint8)
        image[32:96,32:96]=np.arange(32,96,dtype=np.uint8)[None,:,None]
        result=contrast(image);support=(image>0).any(2)
        self.assertEqual(result.shape,image.shape);self.assertEqual(result.dtype,np.uint8)
        np.testing.assert_array_equal(result[~support],np.zeros_like(result[~support]))
        self.assertTrue(np.any(result[support]!=image[support]))

if __name__=='__main__':unittest.main()
