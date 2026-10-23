import unittest
import numpy as np
from avaliar_candidato_congelado import fuse
from normalizar_consulta import normalize

class FrozenFusionTests(unittest.TestCase):
    def test_equal_views_fixed_weights_and_missing_failure(self):
        rng=np.random.default_rng(11)
        arrays=[rng.uniform(.1,.9,(3,16)) for _ in range(9)]
        for x in arrays:x[0,2]=-2
        valid=np.array([True,False,True]);components=[dict(scores=x,valid=valid) for x in arrays]
        calibration=[[dict(mean=.3+i*.01,std=.2+i*.01) for i in range(8)] for _ in range(2)]
        calibration[1][-1]=dict(mean=.45,std=.13)
        actual,av=fuse(components,calibration)
        base=sum((arrays[i]-calibration[0][i]['mean'])/calibration[0][i]['std']/8 for i in range(7))
        arc=sum((arrays[7+j]-calibration[j][7]['mean'])/calibration[j][7]['std']/16 for j in range(2))
        expected=1/(1+np.exp(-(base+arc)));expected[0,2]=-2;expected,ev=normalize(expected,valid)
        np.testing.assert_allclose(actual,expected,atol=1e-14);np.testing.assert_array_equal(av,ev)
        self.assertTrue((actual[1]==-2).all());self.assertEqual(actual[0,2],-2)

    def test_queries_independent_and_no_label_input(self):
        rng=np.random.default_rng(12);components=[dict(scores=rng.uniform(.1,.9,(2,16)),valid=np.ones(2,bool)) for _ in range(9)]
        calibration=[[dict(mean=.2,std=.3) for _ in range(8)] for _ in range(2)]
        full,_=fuse(components,calibration)
        for q in range(2):
            isolated=[dict(scores=c['scores'][q:q+1],valid=c['valid'][q:q+1]) for c in components]
            one,_=fuse(isolated,calibration);np.testing.assert_array_equal(one[0],full[q])

if __name__=='__main__':unittest.main()
