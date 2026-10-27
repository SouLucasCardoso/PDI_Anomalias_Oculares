import unittest
import numpy as np
from calibracao_multicondicao import calibrate_robust
from treinar_bloco_fmr_separado import measured

class RobustCalibrationTests(unittest.TestCase):
    def test_single_threshold_rejects_shifted_impostors(self):
        domains={}
        for tag,wrong in [('clean',.1),('upper10',.3),('lower10',.4)]:domains[tag]=dict(scores=np.array([[.9,wrong],[wrong,.9]]),labels=np.array([0,1]),valid=np.ones(2,bool))
        threshold,parts=calibrate_robust(domains)
        self.assertEqual(threshold,max(parts.values()))
        for data in domains.values():m,_=measured(data,threshold);self.assertEqual(m['far'],0.);self.assertEqual(m['tar'],1.);self.assertEqual(m['threshold'],threshold)
    def test_no_extra_evaluation_domain_allowed(self):
        with self.assertRaises(ValueError):calibrate_robust({'monitor':{}})
if __name__=='__main__':unittest.main()
