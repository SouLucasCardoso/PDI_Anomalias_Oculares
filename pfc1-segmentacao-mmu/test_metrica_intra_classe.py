import unittest
import numpy as np
from metrica_intra_classe import fit,transform

class WithinClassMetricTests(unittest.TestCase):
    def test_suppresses_high_within_eye_variation_and_normalizes(self):
        x=np.array([[-1,-10],[-1,10],[1,-10],[1,10]],float)
        mean,matrix=fit(x,[0,0,1,1])
        self.assertGreater(matrix[0,0],matrix[1,1])
        y=transform(x,mean,matrix)
        np.testing.assert_allclose(np.linalg.norm(y,axis=1),1)
        np.testing.assert_allclose(matrix,matrix.T,atol=1e-12)

    def test_requires_repeated_captures(self):
        with self.assertRaises(ValueError):fit(np.eye(3),[0,1,2])

if __name__=='__main__':unittest.main()
