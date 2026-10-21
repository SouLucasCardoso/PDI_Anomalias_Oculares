import unittest
import cv2
import numpy as np
from normalizacao_eliptica import normalize,ellipse_endpoints

class EllipseTests(unittest.TestCase):
    def test_endpoints_obey_global_angles(self):
        x,y=ellipse_endpoints(((10,20),(80,40),0),np.array([0,np.pi/2,np.pi]))
        np.testing.assert_allclose(x,[50,10,-30],atol=1e-12)
        np.testing.assert_allclose(y,[20,40,20],atol=1e-12)

    def test_annulus_hole_fits_pupil(self):
        mask=np.zeros((200,240),np.uint8)
        cv2.ellipse(mask,(120,100),(70,50),20,0,360,255,-1)
        cv2.ellipse(mask,(120,100),(20,15),20,0,360,0,-1)
        polar,info=normalize(np.full(mask.shape,80,np.uint8),mask,[120,100,18])
        self.assertEqual(polar.shape,(64,512));self.assertEqual(info['pupil_source'],'largest_enclosed_mask_hole')
        np.testing.assert_allclose(info['iris_ellipse'][0],[120,100],atol=1)
        self.assertGreater(info['polar_mask_fraction'],.9)

    def test_no_hole_uses_explicit_fallback_and_empty_rejects(self):
        mask=np.zeros((120,160),np.uint8);cv2.circle(mask,(80,60),40,255,-1)
        _,info=normalize(mask,mask,[80,60,12]);self.assertEqual(info['pupil_source'],'circle_regressor_fallback')
        with self.assertRaises(ValueError):normalize(mask,np.zeros_like(mask),[80,60,12])

if __name__=='__main__':unittest.main()
