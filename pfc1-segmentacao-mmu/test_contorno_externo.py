import unittest
import numpy as np
import torch
from contorno_externo import covariance,ellipse_vector,vector_ellipse,OuterCorrection,segmentation_features

class TestOuterContour(unittest.TestCase):
    def test_affine_roundtrip_for_non_square_photograph(self):
        source=((412.,287.),(144.,91.),37.)
        restored=vector_ellipse(ellipse_vector(source,1077,743),1077,743)
        np.testing.assert_allclose(source[0],restored[0],atol=1e-4)
        np.testing.assert_allclose(covariance(source),covariance(restored),rtol=2e-6)
    def test_zero_residual_preserves_every_baseline_parameter(self):
        model=OuterCorrection();baseline=torch.randn(3,5)
        torch.testing.assert_close(model(torch.randn(3,2048),baseline),baseline,atol=0,rtol=0)
    def test_exposed_features_leave_segmentation_logits_exact(self):
        from treinar_segmentacao_ubipr import MulticlassUNet
        torch.set_num_threads(2);model=MulticlassUNet(8).eval();x=torch.rand(2,3,64,96)
        with torch.inference_mode():actual,features=segmentation_features(model,x);expected=model(x)
        torch.testing.assert_close(actual,expected,atol=0,rtol=0)
        self.assertEqual(tuple(features.shape),(2,2048))
    def test_invalid_vector_is_rejected(self):
        with self.assertRaises(ValueError):vector_ellipse(np.array([0,0,np.nan,0,0]),320,240)
    def test_zero_or_invalid_correction_preserves_original_pixels_exactly(self):
        import cv2
        from contorno_externo import outer_ellipse,refined_textures
        from textura_polar import prepare_texture
        from preparar_polar_vermelho import red_texture
        rgb=np.random.default_rng(61).integers(0,256,(100,140,3),dtype=np.uint8)
        mask=np.zeros((100,140),np.uint8)
        cv2.ellipse(mask,(70,50),(35,28),15,0,360,1,-1)
        cv2.circle(mask,(70,50),9,0,-1);mask=mask.astype(bool)
        old,geometry=prepare_texture(rgb,mask);oldred=red_texture(rgb,mask)
        base=ellipse_vector(outer_ellipse(mask),140,100)
        for vector in [base,np.array([0,0,np.nan,0,0])]:
            new,newred,_,applied,_=refined_textures(rgb,mask,vector)
            self.assertFalse(applied)
            np.testing.assert_array_equal(old,new);np.testing.assert_array_equal(oldred,newred)

if __name__=='__main__':unittest.main()
