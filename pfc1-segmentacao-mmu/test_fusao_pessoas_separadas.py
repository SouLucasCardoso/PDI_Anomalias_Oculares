import unittest
import numpy as np
from treinar_fusao_pessoas_separadas import person_split,query_z,fuse


class PersonSplitFusionTests(unittest.TestCase):
    def test_person_partition_deterministic_and_complete(self):
        rows=[dict(subject=s,side=side,session=session) for s in range(60) for side in ['L','R'] for session in [1,2]]
        rows += [dict(subject=100+s,side='L',session=1) for s in range(10)]
        result=person_split(rows);self.assertEqual(result,person_split(rows))
        self.assertEqual(len(result['fusion_fit']),20);self.assertEqual(len(result['encoder_monitor']),16);self.assertEqual(len(result['encoder_fit']),34)
        self.assertEqual(set().union(*(set(v) for v in result.values())),set(range(60))|set(range(100,110)))
        self.assertFalse(set(result['fusion_fit'])&set(result['encoder_fit']));self.assertFalse(set(result['fusion_fit'])&set(result['encoder_monitor']))
        self.assertTrue(set(range(100,110))<=set(result['encoder_fit']))

    def test_features_candidate_equivariance_and_constants(self):
        values=np.random.default_rng(3).normal(size=(2,16,3))
        np.testing.assert_array_equal(query_z(values[:,::-1]),query_z(values)[:,::-1])
        np.testing.assert_allclose(query_z(values*2+7),query_z(values),atol=1e-6)
        np.testing.assert_array_equal(query_z(np.ones((1,16,3))),0)

    def test_fusion_never_reads_identity_and_preserves_failures(self):
        rng=np.random.default_rng(7)
        components=[dict(scores=rng.uniform(0,1,(3,16)),labels=np.array([0,1,2]),valid=np.array([True,True,False])) for _ in range(3)]
        components[0]['scores'][0,4]=-2
        before,valid=fuse(components,np.full(3,1/3))
        for c in components:c['labels'][:]=15
        after,_=fuse(components,np.full(3,1/3));np.testing.assert_array_equal(before,after)
        self.assertEqual(before[0,4],-2);self.assertFalse(valid[2]);self.assertTrue((before[2]==-2).all())
        with self.assertRaises(ValueError):fuse(components,np.ones(3))


if __name__=='__main__':unittest.main()
