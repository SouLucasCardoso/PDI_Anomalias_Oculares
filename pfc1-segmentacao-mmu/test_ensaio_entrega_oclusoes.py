import unittest
import numpy as np
from PIL import Image
from ensaio_entrega_oclusoes import PRIOR,score,fit
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import perturb,operating_threshold

class EnsaioEntregaTests(unittest.TestCase):
    def test_gray_occlusion_exact_area_and_unchanged_exterior(self):
        rgb=np.full((40,50,3),42,np.uint8);mask=np.zeros((40,50),bool);mask[4:36,5:45]=True
        for side in ('oclusao_superior','oclusao_inferior'):
            for level in (1,5,10,20,30,31):
                image,meta=perturb(Image.fromarray(rgb),mask,side,level)
                altered=np.any(np.asarray(image)!=rgb,axis=2)
                self.assertEqual(altered.sum(),round(mask.sum()*level/100))
                self.assertFalse(altered[~mask].any())
                self.assertAlmostEqual(meta['affected_fraction'],altered.sum()/mask.sum())
                self.assertTrue(np.all(np.asarray(image)[altered]==128))

    def test_empty_reference_kept_unchanged(self):
        original=np.full((8,8,3),42,np.uint8)
        image,meta=perturb(Image.fromarray(original),np.zeros((8,8),bool),'oclusao_superior',31)
        np.testing.assert_array_equal(np.asarray(image),original)
        self.assertEqual(meta['affected_fraction'],0)

    def test_prior_reproduces_historical_fusion(self):
        rng=np.random.default_rng(8);x=rng.normal(size=(21,16,9))
        valid=np.ones(21,bool);valid[0]=False
        available=np.ones((21,16),bool)
        calibration=[[{'mean':0.,'std':1.} for _ in range(8)] for _ in range(2)]
        components=[{'scores':.05*x[:,:,i]+.5,'valid':valid} for i in range(9)]
        expected,ev=fuse(components,calibration)
        actual,av=score(.05*x+.5,PRIOR,valid,available)
        np.testing.assert_allclose(actual,expected,atol=1e-12)
        np.testing.assert_array_equal(av,ev)

    def test_learning_and_ties_safe_threshold(self):
        rng=np.random.default_rng(4);x=rng.normal(0,.1,(40,4,9));y=np.arange(40)%4
        x[np.arange(40),y,2]+=3
        w=fit(x,y,np.ones(40,bool),np.ones((40,4),bool),.1)
        self.assertGreater(w[2],PRIOR[2]);self.assertTrue((w>=0).all());self.assertAlmostEqual(w.sum(),1)
        t=operating_threshold(np.array([.2]*98+[.9]*2),.01)
        self.assertLessEqual(np.mean(np.array([.2]*98+[.9]*2)>=t),.01)

if __name__=='__main__':unittest.main()
