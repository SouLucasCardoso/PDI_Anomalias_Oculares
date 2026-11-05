import unittest
from avaliar_prontidao_anomalias import identity_gate,fraction_pass


class ReadinessTests(unittest.TestCase):
    def test_separate_acceptance_and_rank1_are_not_joint_success(self):
        c={'minimum_rank1':.9,'minimum_tar':.9,'maximum_fmr':.01,'minimum_joint_correct_and_accepted':.9}
        counts={'correct':90,'accepted':90,'joint':80,'false_accepts':0,'queries':100,'impostors':1500}
        self.assertFalse(identity_gate(counts,c))
        self.assertTrue(identity_gate({**counts,'joint':90},c))
    def test_fractional_false_matches_do_not_round_to_pass(self):
        self.assertTrue(fraction_pass(72,7230,.01,True))
        self.assertFalse(fraction_pass(73,7230,.01,True))
        self.assertFalse(fraction_pass(0,0,.9))


if __name__=='__main__':unittest.main()
