import tempfile
from pathlib import Path
import unittest
import numpy as np
import torch
from torch.utils.data import Dataset
from treinar_segmentacao_area import order_for_epoch,save_checkpoint,train_pass


class TinyEyes(Dataset):
    epoch_index=0
    mode='train'
    def __len__(self):return 6
    def __getitem__(self,index):
        rng=np.random.default_rng([17,self.epoch_index,index])
        return torch.from_numpy(rng.random((3,8,8),dtype=np.float32)),torch.from_numpy(rng.integers(0,4,(8,8),dtype=np.int64))


class RecoveryTests(unittest.TestCase):
    def test_order_is_reproducible_and_complete(self):
        order=order_for_epoch(17,127,1)
        self.assertEqual(sorted(order),list(range(17)))
        self.assertEqual(order,order_for_epoch(17,127,1))
        self.assertNotEqual(order,order_for_epoch(17,127,2))

    def test_adam_and_data_resume_mid_epoch_match_uninterrupted(self):
        torch.manual_seed(7);initial=torch.nn.Conv2d(3,4,1).state_dict();device=torch.device('cpu')
        def make():
            model=torch.nn.Conv2d(3,4,1);model.load_state_dict(initial)
            return model,torch.optim.AdamW(model.parameters(),lr=1e-3)
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);model,opt=make()
            full=train_pass(model,TinyEyes(),device,opt,2,1,127,0,{'loss_sum':0.,'samples':0},1,lambda *x:None,out)
            expected={k:v.clone() for k,v in model.state_dict().items()}
            partial,po=make()
            def stop(step,totals):
                save_checkpoint(out/'recovery.pt',{'model':partial.state_dict(),'optimizer':po.state_dict(),'step':step,'totals':dict(totals)})
                if step==1:raise InterruptedError('test interruption')
            with self.assertRaises(InterruptedError):
                train_pass(partial,TinyEyes(),device,po,2,1,127,0,{'loss_sum':0.,'samples':0},1,stop,out)
            state=torch.load(out/'recovery.pt',weights_only=True);resumed,ro=make()
            resumed.load_state_dict(state['model']);ro.load_state_dict(state['optimizer'])
            result=train_pass(resumed,TinyEyes(),device,ro,2,1,127,state['step'],state['totals'],1,lambda *x:None,out)
            for name,value in resumed.state_dict().items():torch.testing.assert_close(value,expected[name],rtol=0,atol=0)
            self.assertEqual(result,full)


if __name__=='__main__':unittest.main()
