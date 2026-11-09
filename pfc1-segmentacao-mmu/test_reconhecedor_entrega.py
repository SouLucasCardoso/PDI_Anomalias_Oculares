import unittest
import numpy as np
from PIL import Image
from avaliar_contorno_integrado import native_mask
from treinar_reconhecedor_entrega import eligibility,selection_key

class EntregaRecognitionTests(unittest.TestCase):
    def baseline(self):
        return {t:{'rank1':.9,'tar':.91,'far':.009 if t=='original' else .02,'joint_success':.85 if t=='original' else .6}
                for t in ('original','oclusao_superior','oclusao_inferior')}
    def test_more_correct_does_not_justify_more_false_matches(self):
        b=self.baseline();c={t:r.copy() for t,r in b.items()}
        c['oclusao_inferior']['joint_success']=.8;c['oclusao_inferior']['far']=.021
        self.assertFalse(eligibility(c,b))
    def test_clean_regression_rejected_even_with_large_occlusion_gain(self):
        b=self.baseline();c={t:r.copy() for t,r in b.items()}
        c['oclusao_inferior']['joint_success']=.8;c['original']['tar']=.90
        self.assertFalse(eligibility(c,b))
    def test_positive_paired_gain_and_epoch_zero_control(self):
        b=self.baseline();self.assertFalse(eligibility(b,b))
        c={t:r.copy() for t,r in b.items()};c['oclusao_inferior']['joint_success']=.65
        self.assertTrue(eligibility(c,b));self.assertGreater(selection_key(c),selection_key(b))
    def test_confidence_boundary_preserves_holes_without_nearest_blocks(self):
        field=np.full((32,32),-2.,np.float32);field[4:28,4:28]=3;field[12:20,12:20]=-4
        result=native_mask(field,(128,128))
        self.assertFalse(result[64,64]);self.assertFalse(result[0,0]);self.assertTrue(result[24,24])
        self.assertEqual(result.dtype,np.bool_)

if __name__=='__main__':unittest.main()
