import unittest
import numpy as np
from classificador_cadastro import fit,predict

class EnrollmentClassifierTests(unittest.TestCase):
    def test_unseen_capture_correct_without_query_fitting(self):
        x=np.array([[-1,0],[-1,.1],[1,0],[1,.1]]);labels=np.array([0,0,1,1])
        state=fit(x,labels,2);q=np.array([[-.9,.05],[.9,.05]])
        np.testing.assert_array_equal(predict(q,state).argmax(1),[0,1])
        # Centering makes the fitted prediction invariant to a shared offset.
        shifted=fit(x+7,labels,2)
        np.testing.assert_allclose(predict(q+7,shifted),predict(q,state),atol=1e-12)

if __name__=='__main__':unittest.main()
