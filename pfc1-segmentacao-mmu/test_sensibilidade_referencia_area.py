import unittest
import numpy as np
from analisar_sensibilidade_referencia_area import stratify


CRITERIA = {'minimum_rank1': .9, 'minimum_tar': .9,
            'minimum_joint_correct_and_accepted': .9, 'maximum_fmr': .01}


class MissingReferenceTests(unittest.TestCase):
    def test_undefined_area_can_lift_global_gate_without_proving_defined_area(self):
        # 424/472 no grupo definido e 10/10 sem area: 434/482 passa apenas no total.
        scores = np.zeros((482, 16));labels = np.zeros(482, dtype=np.int64)
        scores[:, 1] = .7;scores[:424, 0] = .9;scores[472:, 0] = .9
        areas = np.r_[np.full(472, 100), np.zeros(10)].astype(np.int64)
        result = stratify(scores, labels, np.ones(482, bool), areas, .8, CRITERIA)
        self.assertTrue(result['all_queries']['passed'])
        self.assertFalse(result['defined_reference']['passed'])
        self.assertEqual(result['defined_reference']['counts']['joint'], 424)
        self.assertEqual(result['undefined_reference']['counts']['queries'], 10)

    def test_failures_are_kept_and_empty_stratum_never_passes(self):
        scores = np.array([[.9, 0], [.9, 0]])
        result = stratify(scores, np.zeros(2, dtype=np.int64), [True, False], [5, 5], .8, CRITERIA)
        self.assertEqual(result['defined_reference']['counts']['queries'], 2)
        self.assertEqual(result['defined_reference']['counts']['extraction_failures'], 1)
        self.assertFalse(result['defined_reference']['passed'])
        self.assertIsNone(result['undefined_reference']['counts'])
        self.assertFalse(result['undefined_reference']['passed'])
        with self.assertRaises(ValueError):
            stratify(scores, [0, 0], [True, True], [5], .8, CRITERIA)


if __name__ == '__main__':
    unittest.main()
