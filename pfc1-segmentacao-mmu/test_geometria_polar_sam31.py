import unittest
import numpy as np
from geometria_polar_sam31 import polar_with_outer
from textura_polar import prepare_texture
from preparar_polar_vermelho import red_texture

class GeometryTests(unittest.TestCase):
    def test_same_global_ellipse_exactly_reproduces_both_original_bands(self):
        y,x=np.indices((240,320));mask=((x-160)**2/65**2+(y-120)**2/55**2<1)&((x-160)**2+(y-120)**2>20**2)
        rgb=np.dstack(((x*3+y)%256,(y*2)%256,(x+y*5)%256)).astype(np.uint8);saved=rgb.copy()
        original,geometry=prepare_texture(rgb,mask);yy,xx=np.where(mask)
        x0=max(0,int(xx.min())-max(2,round((np.ptp(xx)+1)*.5)));y0=max(0,int(yy.min())-max(2,round((np.ptp(yy)+1)*.5)))
        center,axes,angle=geometry['iris_ellipse'];global_ellipse=((center[0]+x0,center[1]+y0),axes,angle)
        band,red,detail=polar_with_outer(rgb,mask,global_ellipse)
        np.testing.assert_array_equal(band,original);np.testing.assert_array_equal(red,red_texture(rgb,mask));np.testing.assert_array_equal(rgb,saved)
        self.assertFalse(detail['support_mask_changed']);self.assertFalse(detail['photograph_reconstructed'])

if __name__=='__main__':unittest.main()
