import unittest
from types import SimpleNamespace
import numpy as np
from testar_casos_oculares_reais import local_subset

class RealCaseTest(unittest.TestCase):
    def test_side_specific_genuine_not_shared_subject_list(self):
        rows=[SimpleNamespace(subject=f'P{i:04}',side=side,session=1) for side,offset in [('L',0),('R',16)] for i in range(offset,offset+16)]
        rows+=[SimpleNamespace(subject='P0007',side='L',session=2),SimpleNamespace(subject='P0022',side='R',session=2),SimpleNamespace(subject='P0007',side='L',session=2),SimpleNamespace(subject='P0022',side='R',session=2)]
        full=np.tile(np.arange(32),(4,1));scores,labels=local_subset(full,rows)
        np.testing.assert_array_equal(labels,[7,6,7,6]);self.assertEqual(scores.shape,(4,16))
        np.testing.assert_array_equal(scores[np.arange(4),labels],[7,22,7,22])

if __name__=='__main__':unittest.main()
