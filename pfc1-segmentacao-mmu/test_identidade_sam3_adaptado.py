from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import torch
from treinar_segmentacao_ubipr import Sample
from avaliar_robustez_reconhecimento import perturb
from segmentador_sam3_iris import IrisSam3Adapter,SAM_REVISION
import avaliar_identidade_sam3_adaptado as adapter


class AlteredPhotoTests(unittest.TestCase):
    def test_sam3_receives_altered_query_and_keeps_every_extraction(self):
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory(prefix='pfc-s3-id-test-') as temp:
            root=Path(temp);rgb=np.full((96,128,3),75,np.uint8);rgb[:,:,1]=np.arange(128,dtype=np.uint8)
            target=np.zeros((96,128),np.uint8);target[25:75,40:100]=85;target[40:60,60:80]=0
            Image.fromarray(rgb).save(root/'photo.png');Image.fromarray(target).save(root/'mask.png')
            state={'model':IrisSam3Adapter().state_dict(),'model_type':'sam3_visual_iris_adapter','sam_revision':SAM_REVISION}
            torch.save(state,root/'head.pt')
            seen=[]
            class FeatureSpy:
                def __init__(self,*args):pass
                def __call__(self,image):seen.append(image.copy());return np.zeros((256,72,72),np.float16)
            rows=[Sample(str(root/'photo.png'),str(root/'mask.png'),1,1,1,'L'),
                  Sample(str(root/'photo.png'),str(root/'mask.png'),1,2,2,'L')]
            with patch.object(adapter,'Sam3VisualFeatures',FeatureSpy):
                arrays,rv,pv=adapter.prepare_sam3(rows,torch.device('cpu'),root/'prepared','oclusao_superior',10,False,root/'head.pt')
            changed,_=perturb(Image.fromarray(rgb),target==85,'oclusao_superior',10)
            np.testing.assert_array_equal(seen[0],np.asarray(Image.fromarray(rgb).resize((416,320),Image.Resampling.BILINEAR)))
            np.testing.assert_array_equal(seen[1],np.asarray(changed.resize((416,320),Image.Resampling.BILINEAR)))
            self.assertFalse(np.array_equal(seen[0],seen[1]))
            self.assertEqual(len(rv),2);self.assertEqual(len(pv),2);self.assertEqual(arrays['polar'].shape,(2,64,512,3))
            for value in arrays.values():value._mmap.close()


if __name__=='__main__':unittest.main()
