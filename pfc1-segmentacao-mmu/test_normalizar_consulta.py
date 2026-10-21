import unittest
import numpy as np
from normalizar_consulta import normalize

class SingleQueryNormalizationTests(unittest.TestCase):
    def test_row_order_preserved_and_independent_queries(self):
        x=np.array([[.2,.8,.4],[.7,.1,-2],[-2,-2,-2]])
        y,valid=normalize(x,[True,True,False]);single,_=normalize(x[:1],[True])
        np.testing.assert_allclose(y[:1],single)
        np.testing.assert_array_equal(y[:2].argmax(1),x[:2].argmax(1))
        np.testing.assert_array_equal(valid,[True,True,False]);self.assertEqual(y[1,2],-2)
        np.testing.assert_array_equal(y[2],[-2,-2,-2])

if __name__=='__main__':unittest.main()
