import unittest
import numpy as np
from validar_fusao_aparada import trimmed_fuse
from avaliar_candidato_congelado import fuse


class TrimmedFusionTests(unittest.TestCase):
    def inputs(self):
        scores=np.tile(np.linspace(-.1,.9,16),(3,1))
        return [dict(scores=scores.copy(),valid=np.array([True,True,False]),labels=np.array([0,1,2])) for _ in range(9)]

    def test_identical_groups_match_arithmetic(self):
        components=self.inputs();parameters=[[dict(mean=0.,std=1.) for _ in range(8)] for _ in range(2)]
        actual,valid=trimmed_fuse(components,parameters);expected,expected_valid=fuse(components,parameters)
        np.testing.assert_allclose(actual,expected,atol=1e-12);np.testing.assert_array_equal(valid,expected_valid)

    def test_labels_not_used_and_failures_retained(self):
        components=self.inputs();parameters=[[dict(mean=0.,std=1.) for _ in range(8)] for _ in range(2)]
        components[1]['scores'][0,4]=-2
        first,valid=trimmed_fuse(components,parameters)
        for c in components:c['labels'][:]=15
        second,_=trimmed_fuse(components,parameters)
        np.testing.assert_array_equal(first,second);self.assertEqual(first[0,4],-2);self.assertFalse(valid[2]);self.assertTrue((first[2]==-2).all())


if __name__=='__main__':unittest.main()
