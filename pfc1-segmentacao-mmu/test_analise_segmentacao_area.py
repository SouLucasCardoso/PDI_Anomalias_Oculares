import unittest

import numpy as np

from analisar_rodada_segmentacao_area import measure, paired_difference, validation_queries


class ReportEvidenceTests(unittest.TestCase):
    def test_failures_remain_in_all_denominators_and_joint_is_distinct(self):
        scores = np.array([[.9, .8], [.9, .8], [.9, .8], [.2, .3]])
        counts, rates, passed, _ = measure(scores, np.array([0, 1, 0, 1]),
                                           np.array([True, True, False, True]), .75)
        self.assertEqual(counts, dict(correct=2, accepted=2, joint=1, false_accepts=2,
                                     queries=4, impostors=4, extraction_failures=1))
        self.assertEqual(rates, dict(rank1=.5, tar=.5, joint=.25, fmr=.5))
        self.assertFalse(passed)

    def test_float64_threshold_is_not_rounded_back_to_float32(self):
        scores = np.array([[.5, 0]], dtype=np.float32)
        _, _, _, vectors = measure(scores, np.array([0]), [True], np.nextafter(.5, np.inf))
        self.assertFalse(vectors['tar'][0])

    def test_person_weighted_pairing_has_correct_direction(self):
        result = paired_difference([0, 0, 0, 1], [1, 1, 1, 0], [1, 1, 1, 2])
        self.assertEqual(result['candidate_minus_original_pp'], 50)
        self.assertEqual(result['interval95_cluster_person_pp'], [-100, 100])

    def test_only_eyes_with_both_sessions_enter_validation(self):
        manifest = {'val': [dict(subject=2, side='L', session=1),
                            dict(subject=2, side='L', session=2),
                            dict(subject=2, side='R', session=2),
                            dict(subject=1, side='L', session=2)]}
        queries, people, labels = validation_queries(manifest)
        self.assertEqual(len(queries), 1)
        self.assertEqual(people, [2])
        self.assertEqual(labels.tolist(), [0])


if __name__ == '__main__':
    unittest.main()
