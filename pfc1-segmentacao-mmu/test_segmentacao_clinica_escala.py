import unittest
import numpy as np
import torch
from PIL import Image
from segmentacao_clinica_escala import predict_clinical

class ScaleTest(unittest.TestCase):
    def test_padding_excluded_and_native_shape_restored(self):
        class Model:
            def __call__(self,x):
                self.x=x;out=torch.zeros(len(x),2,240,320);out[:,1]=1
                return out
        model=Model();photo=Image.fromarray(np.full((180,270,3),30,np.uint8));m=predict_clinical([photo],model,'cpu')[0]
        self.assertEqual(m.shape,(180,270));self.assertTrue(m.all())
        self.assertAlmostEqual(float(model.x[0,0,0,0]),128/255,places=6)
        self.assertAlmostEqual(float(model.x[0,0,120,160]),30/255,places=6)

    def test_padding_predictions_do_not_become_iris(self):
        class Model:
            def __call__(self,x):
                out=torch.zeros(len(x),2,240,320);out[:,1]=1;out[:,1,80:160,107:213]=-1
                return out
        m=predict_clinical([Image.new('RGB',(51,39))],Model(),'cpu')[0]
        self.assertFalse(m.any())

if __name__=='__main__':unittest.main()
