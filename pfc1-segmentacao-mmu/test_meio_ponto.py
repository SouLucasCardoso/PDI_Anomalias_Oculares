import unittest
import numpy as np
from PIL import Image
from avaliar_robustez_reconhecimento import perturb

class MidpointInterventionTests(unittest.TestCase):
    def test_fractional_selected_counts_and_orientation(self):
        mask=np.ones((10,20),bool);image=Image.fromarray(np.full((10,20,3),220,np.uint8))
        for kind,level,count in [('oclusao_superior',.5,1),('oclusao_inferior',1.5,3)]:
            result,meta=perturb(image,mask,kind,level);changed=(np.asarray(result)!=220).any(2)
            self.assertEqual(int(changed.sum()),count);self.assertEqual(meta['affected_fraction'],count/200)
            self.assertEqual(int(np.where(changed)[0][0]),0 if kind.endswith('superior') else 9)
    def test_small_reference_can_round_to_zero_and_empty_reference_is_retained(self):
        image=Image.fromarray(np.full((1,59,3),220,np.uint8))
        for mask in [np.ones((1,59),bool),np.zeros((1,59),bool)]:
            result,meta=perturb(image,mask,'oclusao_superior',.5);np.testing.assert_array_equal(result,image);self.assertEqual(meta['affected_fraction'],0.)

if __name__=='__main__':unittest.main()
