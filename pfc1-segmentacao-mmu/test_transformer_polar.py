import unittest
from types import SimpleNamespace
import torch
from torch import nn
from reconhecedor_transformer_polar import Encoder

class FakeBackbone(nn.Module):
    def __init__(self):
        super().__init__();self.register_buffer('tokens',torch.randn(1,133,1024))
    def forward(self,pixel_values):return SimpleNamespace(last_hidden_state=self.tokens.expand(len(pixel_values),-1,-1))

class PolarTransformerTests(unittest.TestCase):
    def test_register_and_cls_tokens_are_not_projected_as_iris_patches(self):
        torch.manual_seed(49);backbone=FakeBackbone();model=Encoder(backbone).eval();x=torch.zeros(2,3,64,512)
        with torch.inference_mode():before=model(x);backbone.tokens[:,:5]+=100;after=model(x)
        self.assertEqual(before.shape,(2,256));torch.testing.assert_close(before,after)
        torch.testing.assert_close(torch.linalg.vector_norm(after,dim=1),torch.ones(2))

if __name__=='__main__':unittest.main()
