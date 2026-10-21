import unittest
import numpy as np
import cv2
from textura_polar import prepare_texture,cyclic_roll

class PolarTextureTests(unittest.TestCase):
    def test_input_shape_channels_and_empty_mask(self):
        image=np.zeros((200,240,3),np.uint8)
        image[:,:,0]=np.arange(240,dtype=np.uint8)[None,:]
        mask=np.zeros((200,240),np.uint8)
        cv2.ellipse(mask,(120,100),(65,45),0,0,360,255,-1)
        cv2.circle(mask,(120,100),15,0,-1)
        polar,info=prepare_texture(image,mask)
        self.assertEqual(polar.shape,(64,512,3))
        np.testing.assert_array_equal(polar[:,:,0],polar[:,:,1])
        self.assertEqual(info['pupil_source'],'largest_enclosed_mask_hole')
        with self.assertRaises(ValueError):prepare_texture(image,np.zeros_like(mask))

    def test_shift_wraps_without_zero_padding(self):
        x=np.arange(12,dtype=np.uint8).reshape(2,6,1)
        shifted=cyclic_roll(x,2)
        np.testing.assert_array_equal(shifted[:,0],x[:,-2])
        np.testing.assert_array_equal(cyclic_roll(shifted,-2),x)

if __name__=='__main__':unittest.main()
