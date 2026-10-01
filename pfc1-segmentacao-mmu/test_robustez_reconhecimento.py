import unittest
import numpy as np
from PIL import Image
from avaliar_robustez_reconhecimento import perturb, operating_threshold, metrics, paired_ci, make_gallery
from treinar_segmentacao_ubipr import Sample


class ProtocolTests(unittest.TestCase):
    def test_perturbation_preserves_context_and_exact_coverage(self):
        a=np.full((20,20,3),200,dtype=np.uint8); m=np.zeros((20,20),bool); m[5:15,5:15]=True
        for kind,level in [('oclusao_superior',20),('oclusao_inferior',60),('desfoque_iris',3),('contraste_iris',50)]:
            changed,meta=perturb(Image.fromarray(a),m,kind,level)
            self.assertTrue(np.array_equal(np.asarray(changed)[~m],a[~m]))
            if kind.startswith('oclusao'):
                self.assertEqual(int(np.any(np.asarray(changed)!=a,axis=2).sum()),level)
                self.assertAlmostEqual(meta['affected_fraction'],level/100)

    def test_threshold_rejects_ties_to_respect_far(self):
        x=np.r_[np.zeros(95),np.ones(5)]
        threshold=operating_threshold(x,.01)
        self.assertGreater(threshold,1)
        self.assertLessEqual((x>=threshold).mean(),.01)
        scores=np.array([[1.,1.],[1.,1.]],dtype=np.float32)
        result,_,_=metrics(scores,np.array([0,1]),threshold,np.array([True,True]))
        self.assertEqual(result['far'],0.)

    def test_failures_are_rejected_and_count_as_identification_error(self):
        scores=np.array([[.9,.1],[.1,.9]])
        result,correct,accept=metrics(scores,np.array([0,1]),.5,np.array([True,False]))
        self.assertEqual(result['rank1'],.5); self.assertEqual(result['tar'],.5)
        self.assertEqual(result['extraction_failures'],1); self.assertEqual(result['far'],0)

    def test_eye_sides_have_distinct_gallery(self):
        rows=[Sample('','',1,1,1,'L'),Sample('','',1,1,1,'R')]
        g,ids,failed=make_gallery(np.eye(2),np.array([True,True]),rows)
        self.assertEqual(ids,['1_L','1_R']); self.assertFalse(failed)
        self.assertTrue(np.array_equal(g,np.eye(2)))

    def test_paired_ci_zero_and_complete_loss(self):
        self.assertEqual(paired_ci(np.ones(4),np.ones(4),np.array([1,1,2,2]),50),[0.,0.])
        self.assertEqual(paired_ci(np.ones(4),np.zeros(4),np.array([1,1,2,2]),50),[100.,100.])


if __name__=='__main__': unittest.main()
