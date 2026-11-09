import unittest
import numpy as np
import torch
from PIL import Image
from avaliar_contorno_continuo import continuous_mask
from recorte_iris_sam31_alta_res import automatic_points,enclosed_pupil_seed,retain_prompt_components,antialiased_crop,crop_box

class RefinoTests(unittest.TestCase):
    def test_native_label_uses_confidence_not_nearest_binary(self):
        class FixedModel:
            def __call__(self,x):
                logits=torch.zeros((1,4,240,320));logits[:,1,:,:160]=4;logits[:,1,:,160:]=-1
                return logits
        old,new=continuous_mask(FixedModel(),Image.new('RGB',(1280,960),'gray'))
        self.assertEqual(old.sum(),1280*960//2)
        self.assertTrue(new[:,640].all())
        self.assertFalse(old[:,640].any())
        self.assertFalse(new[:,645].any())

    def test_internal_points_never_use_background(self):
        y,x=np.ogrid[:120,:160];m=((x-80)**2+(y-60)**2<45**2)&((x-80)**2+(y-60)**2>18**2)
        p=automatic_points(m).astype(int)
        self.assertGreaterEqual(len(p),6);self.assertTrue(m[p[:,1],p[:,0]].all())
        pupil=enclosed_pupil_seed(m);self.assertTrue(pupil[60,80]);self.assertFalse((pupil&m).any())

    def test_open_background_is_not_pupil_and_debris_removed(self):
        m=np.zeros((100,100),bool);m[20:80,20:80]=True;m[2:6,2:6]=True
        self.assertIsNone(enclosed_pupil_seed(m))
        result=retain_prompt_components(m,np.array([[50,50]]))
        self.assertEqual(result.sum(),3600);self.assertFalse(result[3,3]);self.assertTrue(result[50,50])

    def test_visual_crop_preserves_native_rgb_and_hole(self):
        y,x=np.ogrid[:120,:160];m=((x-80)**2+(y-60)**2<45**2)&((x-80)**2+(y-60)**2>18**2)
        rgb=np.random.default_rng(5).integers(0,256,(120,160,3),dtype=np.uint8)
        crop=np.asarray(antialiased_crop(Image.fromarray(rgb),m));x0,y0,x1,y1=crop_box(m,.08)
        np.testing.assert_array_equal(crop[:,:,:3],rgb[y0:y1,x0:x1])
        self.assertEqual(crop[60-y0,80-x0,3],0)
        self.assertTrue(np.any((crop[:,:,3]>0)&(crop[:,:,3]<255)))

if __name__=='__main__':unittest.main()
