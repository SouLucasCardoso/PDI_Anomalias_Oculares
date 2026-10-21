import unittest
import numpy as np
import torch
from torch import nn
from adaptar_reconhecedor_cadastro import enrollment_step
from treinar_identidade_iris import AngularHead

class EnrollmentTrainingStepTests(unittest.TestCase):
    def test_windows_int32_labels_and_inference_teacher_backpropagate(self):
        torch.manual_seed(48);tail=nn.Linear(3,256);head=AngularHead(2,margin=.15,scale=20.)
        cached=torch.randn(4,3);targets=np.array([0,0,1,1],dtype=np.int32)
        with torch.inference_mode():teacher=nn.functional.normalize(tail(cached),dim=1)
        optimizer=torch.optim.AdamW(list(tail.parameters())+list(head.parameters()),lr=1e-3)
        before=tail.weight.detach().clone()
        loss=enrollment_step(tail,head,cached,targets,teacher,optimizer,[0,1,2,3])
        self.assertTrue(np.isfinite(loss));self.assertFalse(torch.equal(before,tail.weight))
        self.assertTrue(torch.isfinite(tail.weight.grad).all())

if __name__=='__main__':unittest.main()
