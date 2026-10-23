"""O controle fixa a segmentacao, mas nao restaura os pixels ocluidos."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from PIL import Image
import torch
from avaliar_candidato_congelado import prepare

class GeometryControlTests(unittest.TestCase):
    def test_new_segmenter_cannot_open_test(self):
        from avaliar_candidato_congelado import main
        with patch('sys.argv',['evaluation','--split','test','--output-root','unused','--segmenter','not_opened.pt']):
            with self.assertRaisesRegex(ValueError,'validation'):main()

    def test_original_segmentation_input_altered_recognition_input(self):
        inputs=[]
        class FakeSegmenter(torch.nn.Module):
            def load_state_dict(self,state):pass
            def forward(self,x):
                inputs.append(x.clone())
                scores=torch.zeros((len(x),2,240,320));scores[:,0]=1;scores[:,1,60:180,80:240]=2
                return scores
        with TemporaryDirectory() as temporary:
            folder=Path(temporary);rgb=np.full((64,64,3),(40,80,120),dtype=np.uint8);mask=np.zeros((64,64),np.uint8);mask[16:48,16:48]=1
            Image.fromarray(rgb).save(folder/'image.png');Image.fromarray(mask).save(folder/'mask.png')
            rows=[SimpleNamespace(image=str(folder/'image.png'),mask=str(folder/'mask.png'),session=s) for s in [1,2]]
            with patch('treinar_segmentacao_ubipr.MulticlassUNet',side_effect=lambda _:FakeSegmenter()),patch('torch.load',return_value={'model':{}}),patch('treinar_segmentacao_ubipr.decode_mask',side_effect=lambda im:np.asarray(im)):
                fixed,_,_=prepare(rows,torch.device('cpu'),folder/'fixed','oclusao_superior',10,True)
                dynamic,_,_=prepare(rows,torch.device('cpu'),folder/'dynamic','oclusao_superior',10,False)
            torch.testing.assert_close(inputs[0][0],inputs[0][1],rtol=0,atol=0)
            self.assertFalse(torch.equal(inputs[1][0],inputs[1][1]))
            self.assertFalse(np.array_equal(fixed['rgb'][0],fixed['rgb'][1]))
            np.testing.assert_array_equal(fixed['rgb'][0],dynamic['rgb'][0])
            # Constant fake prediction makes geometry equal: only source pixels differ.
            np.testing.assert_array_equal(fixed['rgb'][1],dynamic['rgb'][1])
            # Windows requires closing memory maps before TemporaryDirectory cleanup.
            for arrays in [fixed,dynamic]:
                for array in arrays.values():array._mmap.close()

if __name__=='__main__':unittest.main()
