from pathlib import Path
import tempfile
import unittest
import hashlib
import numpy as np
import torch
from perda_negativos_internos import inner_noniris,inner_penalty,checkpoint,supervised_loss
from segmentador_sam3_iris import IrisSam3Adapter


class InnerNegativeTests(unittest.TestCase):
    def test_closed_hole_only_known_background_and_no_open_cavity(self):
        target=np.zeros((9,9),np.uint8);target[2:7,2:7]=1;target[3:6,3:6]=0;target[4,4]=255
        inside=inner_noniris(target)
        self.assertEqual(int(inside.sum()),8);self.assertFalse(inside[4,4]);self.assertFalse(inside[0,0])
        target[2:5,4]=0
        self.assertFalse(inner_noniris(target).any())

    def test_gradient_penalizes_iris_only_on_known_inner_negatives(self):
        target=torch.zeros((1,9,9),dtype=torch.long);target[:,2:7,2:7]=1;target[:,3:6,3:6]=0
        logits=torch.zeros((1,4,9,9),requires_grad=True)
        loss=inner_penalty(logits,target);loss.backward()
        self.assertGreater(float(logits.grad[0,1,4,4]),0)
        self.assertEqual(float(logits.grad[0,1,0,0]),0)
        empty=inner_penalty(logits,torch.zeros_like(target));self.assertEqual(float(empty.detach()),0)

    def test_checkpoint_bytes_match_under_distinct_filenames(self):
        with tempfile.TemporaryDirectory(prefix='pfc-checkpoint-test-') as tmp:
            a,b=Path(tmp)/'canonical.pt',Path(tmp)/'mirror_epoch_12.pt'
            state={'model':{'weight':torch.arange(12).reshape(3,4)},'epoch':12}
            checkpoint(a,state);checkpoint(b,state)
            self.assertEqual(hashlib.sha256(a.read_bytes()).digest(),hashlib.sha256(b.read_bytes()).digest())
            torch.testing.assert_close(torch.load(b,weights_only=True)['model']['weight'],state['model']['weight'])

    def test_real_adapter_optimizer_resume_and_best_weights_are_independent(self):
        torch.set_num_threads(2);torch.manual_seed(37)
        model=IrisSam3Adapter();optimizer=torch.optim.AdamW(model.parameters(),lr=3e-5)
        rgb=torch.rand(2,3,24,32);features=torch.rand(2,256,6,8)
        target=torch.zeros(2,24,32,dtype=torch.long);target[:,4:20,6:26]=1;target[:,9:15,12:20]=0
        def step(m,o):
            m.train();o.zero_grad();loss=supervised_loss(m(rgb,features),target);loss.backward();o.step()
        step(model,optimizer)
        best={k:v.detach().clone() for k,v in model.state_dict().items()}
        with tempfile.TemporaryDirectory(prefix='pfc-resume-test-') as tmp:
            path=Path(tmp)/'resume.pt'
            checkpoint(path,{'model':model.state_dict(),'optimizer':optimizer.state_dict(),'best':best})
            step(model,optimizer)
            other=IrisSam3Adapter();other_optimizer=torch.optim.AdamW(other.parameters(),lr=3e-5)
            state=torch.load(path,weights_only=True);other.load_state_dict(state['model']);other_optimizer.load_state_dict(state['optimizer'])
            step(other,other_optimizer)
            for key,value in model.state_dict().items():
                torch.testing.assert_close(value,other.state_dict()[key],rtol=0,atol=0)
                torch.testing.assert_close(best[key],state['best'][key],rtol=0,atol=0)
            self.assertTrue(any(not torch.equal(v,model.state_dict()[k]) for k,v in best.items()))


if __name__=='__main__':unittest.main()
