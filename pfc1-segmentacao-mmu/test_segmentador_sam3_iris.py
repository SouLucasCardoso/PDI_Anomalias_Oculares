import unittest
import numpy as np
import torch
from segmentador_sam3_iris import IrisSam3Adapter,iris_loss,binary_metrics
from treinar_segmentacao_ubipr import MulticlassUNet


class Sam3AdapterTests(unittest.TestCase):
    def setUp(self):torch.set_num_threads(2)

    def test_initial_adapter_is_exact_rgb_control_with_arbitrary_sam_features(self):
        torch.manual_seed(13)
        control=MulticlassUNet(8).eval(); model=IrisSam3Adapter().eval()
        model.load_rgb_control(control.state_dict())
        rgb=torch.rand(2,3,32,40); features=torch.randn(2,256,8,8)
        with torch.no_grad():torch.testing.assert_close(model(rgb,features),control(rgb),rtol=0,atol=0)

    def test_supervision_updates_sam_connection_and_ignores_unknown_pixels(self):
        model=IrisSam3Adapter().eval();rgb=torch.rand(1,3,32,40)
        target=torch.zeros(1,32,40,dtype=torch.long);target[:,8:24,12:28]=1;target[:,:4]=255
        logits=model(rgb,torch.randn(1,256,8,8));logits.retain_grad()
        loss=iris_loss(logits,target);loss.backward()
        self.assertGreater(model.sam_projection[-1].weight.grad.abs().sum().item(),0)
        self.assertEqual(logits.grad[:,:,:4].abs().sum().item(),0)

    def test_empty_cases_are_retained_and_unknown_area_does_not_improve_score(self):
        target=np.array([[1,255],[0,0]],np.uint8)
        a=binary_metrics(np.array([[1,1],[0,0]]),target)
        self.assertEqual(a['dice'],1)
        self.assertEqual(binary_metrics(np.zeros((2,2),int),np.zeros((2,2),int))['dice'],1)
        self.assertLess(binary_metrics(np.ones((2,2),int),np.zeros((2,2),int))['dice'],.001)


if __name__=='__main__':unittest.main()
