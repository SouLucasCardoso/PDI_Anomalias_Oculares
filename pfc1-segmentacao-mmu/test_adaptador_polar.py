import unittest
import numpy as np
import torch
from adaptador_polar import PolarAdapter,apply_adapter

class TestPolarAdapter(unittest.TestCase):
    def test_zero_residual_preserves_descriptor_and_unit_norm(self):
        model=PolarAdapter();base=torch.nn.functional.normalize(torch.randn(4,256),dim=1)
        result,residual=model(torch.randn(4,512),base)
        torch.testing.assert_close(result,base,atol=1e-6,rtol=1e-6)
        torch.testing.assert_close(residual,torch.zeros_like(residual),atol=0,rtol=0)
        torch.testing.assert_close(result.norm(dim=1),torch.ones(4))
    def test_batch_application_uses_fixed_training_standardization(self):
        model=PolarAdapter().eval();raw=np.random.default_rng(63).normal(size=(5,512)).astype('float32');base=torch.nn.functional.normalize(torch.randn(5,256),dim=1).numpy()
        mean=np.full(512,.2,np.float32);std=np.full(512,.7,np.float32)
        actual=apply_adapter(model,raw,base,mean,std,'cpu',batch=2)
        with torch.inference_mode():expected=model(torch.from_numpy((raw-mean)/std),torch.from_numpy(base))[0].numpy()
        np.testing.assert_allclose(actual,expected,atol=1e-6)
    def test_monitor_keeps_failed_query_and_freezes_clean_threshold(self):
        from types import SimpleNamespace
        from treinar_adaptador_polar import monitor_scores
        rows=[SimpleNamespace(subject=s,side='R',session=session,image=f'{s}_{session}.jpg') for session in [1,2] for s in [1,2]]
        clean=np.array([[1.,0.],[0.,1.],[1.,0.],[0.,1.]],np.float32)
        lower=clean.copy();lower[2]=[0.,1.]
        vectors={'clean':clean,'upper10':clean,'lower10':lower}
        valid={'clean':np.ones(4,bool),'upper10':np.ones(4,bool),'lower10':np.array([True,True,True,False])}
        measured,_=monitor_scores(vectors,valid,rows)
        self.assertEqual({r['threshold'] for r in measured.values()},{measured['clean']['threshold']})
        self.assertTrue(all(r['queries']==2 for r in measured.values()))
        self.assertEqual(measured['clean']['tar'],1.)
        self.assertEqual(measured['lower10']['extraction_failures'],1)
        self.assertEqual(measured['lower10']['tar'],0.)
        self.assertEqual(measured['lower10']['far'],.5)
    def test_occluded_gallery_is_replaced_by_clean_enrollment(self):
        from types import SimpleNamespace
        from treinar_adaptador_polar import monitor_scores
        rows=[SimpleNamespace(subject=s,side='R',session=session,image=f'{s}_{session}.jpg') for session in [1,2] for s in [1,2]]
        clean=np.array([[1.,0.],[0.,1.],[1.,0.],[0.,1.]],np.float32)
        changed=clean.copy();changed[:2]=changed[:2][::-1]
        vectors={'clean':clean,'upper10':changed,'lower10':changed}
        valid={k:np.ones(4,bool) for k in vectors}
        measured,_=monitor_scores(vectors,valid,rows)
        self.assertTrue(all(r['rank1']==1. and r['tar']==1. for r in measured.values()))
if __name__=='__main__':unittest.main()
