import unittest
from unittest.mock import patch
import torch
from torch import nn
from validar_segmentacao_multivista import SegmentTTA

class TestSegmentTTA(unittest.TestCase):
    def test_flip_is_undone_and_probabilities_are_averaged(self):
        class PixelModel(nn.Module):
            def forward(self,x):return torch.cat((x[:,:1],-x[:,:1]),dim=1)
        x=torch.tensor([[[[.1,.4,.9]]]])
        with patch('validar_segmentacao_multivista.contrast_tensor',lambda value:value):
            actual=SegmentTTA(PixelModel())(x).exp()
        torch.testing.assert_close(actual,PixelModel()(x).softmax(1))
        torch.testing.assert_close(actual.sum(1),torch.ones_like(x[:,0]))

    def test_state_loading_preserves_frozen_model_keys(self):
        model=nn.Conv2d(3,4,1);wrapper=SegmentTTA(nn.Conv2d(3,4,1))
        wrapper.load_state_dict(model.state_dict())
        for key,value in model.state_dict().items():torch.testing.assert_close(value,wrapper.model.state_dict()[key])

if __name__=='__main__':unittest.main()
