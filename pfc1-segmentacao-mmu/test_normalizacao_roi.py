import unittest
import numpy as np
from PIL import Image
from validar_melhoria_normalizacao import iso_pair

class GeometryTests(unittest.TestCase):
    def test_mask_padding_cannot_create_valid_iris(self):
        image=Image.new('L',(30,90),200)
        mask=Image.new('L',image.size,255)
        out,valid=iso_pair(image,mask,False)
        self.assertEqual(out.size,(640,480))
        self.assertEqual(set(np.unique(valid)),{0,255})
        self.assertTrue((np.asarray(valid)[:,0]==0).all())
        self.assertTrue((np.asarray(valid)[:,320]==255).all())

    def test_roi_preserves_alignment_and_pixel_values(self):
        mask=np.zeros((120,200),np.uint8); mask[45:65,90:110]=255
        image=Image.fromarray(mask)
        out,valid=iso_pair(image,image,True)
        a=np.asarray(out); b=np.asarray(valid)>0
        self.assertGreater(b.mean(),.1)
        self.assertGreater(float(a[b].mean()),240)
        self.assertEqual(set(np.unique(valid)),{0,255})

if __name__=='__main__': unittest.main()
