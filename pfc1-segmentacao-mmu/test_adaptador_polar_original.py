import unittest
from treinar_adaptador_polar_original import advancement,eligible_clean
class TestOriginalAdapterGate(unittest.TestCase):
    def test_clean_guard_and_both_occlusion_metrics_and_fmr(self):
        from copy import deepcopy
        baseline={t:dict(rank1=.99 if t=='clean' else .5,tar=.99 if t=='clean' else .4,far=.009) for t in ['clean','upper10','lower10']}
        candidate=deepcopy(baseline)
        for t in ['upper10','lower10']:candidate[t].update(rank1=.6,tar=.5)
        self.assertTrue(advancement(candidate,baseline,1));self.assertFalse(advancement(candidate,baseline,0))
        candidate['clean']['rank1']=.98;self.assertFalse(eligible_clean(candidate,baseline));candidate['clean']['rank1']=.99
        candidate['lower10']['far']=.011;self.assertFalse(advancement(candidate,baseline,1));candidate['lower10']['far']=.009
        candidate['upper10']['tar']=.4;self.assertFalse(advancement(candidate,baseline,1))
if __name__=='__main__':unittest.main()
