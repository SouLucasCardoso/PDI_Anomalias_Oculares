import unittest
import cv2,numpy as np,torch
from localizador_pupila import pupil_target,encode_roi,decode_circle,refined_textures
from textura_polar import prepare_texture
from preparar_polar_vermelho import red_texture


class LocatorTests(unittest.TestCase):
    def masks(self,hole=True):
        a=np.zeros((120,160),np.uint8);cv2.circle(a,(80,60),25,1,-1)
        if hole:cv2.circle(a,(78,59),8,0,-1)
        return a.astype(bool)
    def test_annotation_hole_and_roi_coordinates(self):
        mask=self.masks();target=pupil_target(mask);self.assertIsNotNone(target)
        self.assertAlmostEqual(target[0],78,places=1);self.assertIsNone(pupil_target(self.masks(False)))
        image=np.full((120,160,3),70,np.uint8);encoded,bounds=encode_roi(image,mask);self.assertEqual(encoded.shape,(64,64,4))
        self.assertEqual(decode_circle([.5,.5,.1],(10,20,110,100)),(60.,60.,8.))
    def test_existing_hole_never_calls_locator_or_changes_inputs(self):
        class Failing(torch.nn.Module):
            def forward(self,x):raise AssertionError('Locator should not run')
        mask=self.masks();image=np.random.default_rng(4).integers(0,255,(120,160,3),dtype=np.uint8)
        polar,red,geometry,changed=refined_textures(image,mask,Failing(),'cpu');self.assertFalse(changed)
        np.testing.assert_array_equal(polar,prepare_texture(image,mask)[0]);np.testing.assert_array_equal(red,red_texture(image,mask))
    def test_fallback_only_and_no_rgb_restoration(self):
        class Constant(torch.nn.Module):
            def forward(self,x):return torch.tensor([[.45,.5,.07]],device=x.device).repeat(len(x),1)
        mask=self.masks(False);image=np.random.default_rng(2).integers(0,255,(120,160,3),dtype=np.uint8);saved=image.copy()
        polar,red,geometry,changed=refined_textures(image,mask,Constant(),'cpu')
        self.assertTrue(changed);self.assertEqual(geometry['pupil_source'],'train_only_cnn_circle');self.assertEqual(polar.shape,(64,512,3));self.assertEqual(red.shape,polar.shape)
        np.testing.assert_array_equal(image,saved)


if __name__=='__main__':unittest.main()
