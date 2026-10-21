import unittest
from types import SimpleNamespace
import numpy as np
from validar_lateralidade_informada import subset

class SideConditionTests(unittest.TestCase):
    def test_keeps_genuine_eye_and_excludes_opposite_side(self):
        ids=['1_L','1_R','2_L','2_R']
        rows=[SimpleNamespace(subject=1,side='L',session=2),SimpleNamespace(subject=2,side='R',session=2)]
        scores=np.array([[.8,.99,.2,.1],[.4,.2,.99,.8]])
        result,labels,columns=subset(scores,rows,ids)
        np.testing.assert_array_equal(result,[[.8,.2],[.2,.8]])
        np.testing.assert_array_equal(labels,[0,1]);self.assertEqual(result.shape[1]-1,1)

if __name__=='__main__':unittest.main()
