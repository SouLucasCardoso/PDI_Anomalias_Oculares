import unittest
from types import SimpleNamespace
import numpy as np
import torch
from treinar_identidade_automatica import AutomaticCrops,evaluate

class ConstantEncoder(torch.nn.Module):
    def forward(self,x):
        return torch.tensor([1.,0.,0.],device=x.device).expand(len(x),-1)

class AutomaticTrainingTests(unittest.TestCase):
    def test_empty_crops_excluded_only_in_training(self):
        rows=[SimpleNamespace(subject=1,side='L'),SimpleNamespace(subject=2,side='R')]
        images=np.zeros((2,128,128,3),np.uint8); valid=np.array([True,False])
        labels={'1_L':0,'2_R':1}
        training=AutomaticCrops(images,valid,rows,labels,True)
        validation=AutomaticCrops(images,valid,rows,labels,False)
        self.assertEqual(len(training),1);self.assertEqual(len(validation),2)
        self.assertEqual(training[0][1],0);self.assertEqual(validation[1][1],1)

    def test_failed_queries_and_enrollment_not_removed(self):
        rows=[SimpleNamespace(subject=eye,side='L',session=session,image=f'{eye}_{session}.jpg') for session in (1,2) for eye in (1,2)]
        valid=np.array([False,True,False,True]);images=np.zeros((4,128,128,3),np.uint8)
        measured,scores=evaluate(ConstantEncoder(),images,valid,rows,torch.device('cpu'))
        self.assertEqual(measured['queries'],2)
        self.assertEqual(measured['extraction_failures'],1)
        self.assertFalse(scores['correct'][0]);self.assertFalse(scores['accepted'][0])
        self.assertTrue((scores['scores'][:,0]==-2).all())

if __name__=='__main__':unittest.main()
