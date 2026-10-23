from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
import torch
from treinar_identidade_oclusao import AdaptationInputs,occlude_crop

class IdentityOcclusionTests(unittest.TestCase):
    def test_occlusion_keeps_black_exterior_and_source(self):
        image=np.zeros((12,12,3),np.uint8);image[2:10,2:10]=37;before=image.copy();altered=occlude_crop(image,25,False);changed=(altered!=image).any(2)
        self.assertEqual(int(changed.sum()),9);self.assertTrue((altered[changed]==128).all());self.assertFalse(changed[:2].any());self.assertFalse(changed[:,10:].any());np.testing.assert_array_equal(image,before)
    def test_teacher_pair_survives_training_validity_filter(self):
        images=np.stack([np.full((8,8,3),v,np.uint8) for v in [37,71,99]]);rows=[SimpleNamespace(subject=i,side='L') for i in range(3)];teacher=np.arange(3,dtype=np.float32)[:,None]
        dataset=AdaptationInputs(images,np.array([False,True,True]),rows,{f'{i}_L':i for i in range(3)},teacher);dataset.transform=lambda image:torch.from_numpy(image.copy())
        with patch('random.random',return_value=1):image,label,reference=dataset[0]
        self.assertEqual(label,1);self.assertTrue((image==71).all());self.assertEqual(reference.item(),1.)

if __name__=='__main__':unittest.main()
