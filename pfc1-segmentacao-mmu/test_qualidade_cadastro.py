import unittest
import cv2
import numpy as np
from qualidade_cadastro import quality

class EnrollmentQualityTests(unittest.TestCase):
    def test_exterior_does_not_create_sharpness_and_blur_reduces_texture(self):
        image=np.zeros((128,128,3),np.uint8)
        gray=np.tile((np.arange(80)//3%2)*60+80,(80,1)).astype(np.uint8)
        image[24:104,24:104]=gray[:,:,None]
        blurred=image.copy();blurred[24:104,24:104]=cv2.GaussianBlur(image[24:104,24:104],(9,9),2)
        self.assertGreater(quality(image,128)['score'],quality(blurred,128)['score'])
        self.assertEqual(quality(np.zeros_like(image),128)['score'],0)

if __name__=='__main__':unittest.main()
