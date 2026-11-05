import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import analisar_sam3_area as report


class AreaEvidenceTests(unittest.TestCase):
    def test_intervention_uses_exact_pixel_count_and_keeps_empty_references(self):
        rows = [dict(image='a', reference_pixels=3, fraction_defined=True, affected_fraction=1/3),
                dict(image='b', reference_pixels=0, fraction_defined=False, affected_fraction=0.)]
        result = report.intervention_area(rows, 'oclusao_superior', 20, ['a', 'b'])
        self.assertEqual(result['defined_queries'], 1)
        self.assertEqual(result['undefined_queries_retained_in_identity'], 1)
        self.assertAlmostEqual(result['actual_retained_percent_min_mean_max'][1], 200/3)
        rows[0]['affected_fraction'] = .2
        with self.assertRaises(ValueError):
            report.intervention_area(rows, 'oclusao_superior', 20, ['a', 'b'])
        with self.assertRaises(ValueError):
            report.intervention_area(rows[:1], 'oclusao_superior', 20, ['a', 'b'])

    def test_missing_level_and_late_recovery_never_extend_the_approved_prefix(self):
        losses = [0, 10, 20, 30]
        rows = {('novo', 'original', 0): {'passed': True}}
        for orientation in report.ORIENTATIONS:
            for loss in (10, 30):
                rows[('novo', orientation, loss)] = {'passed': True}
        partial = report.area_frontier(rows, losses)
        self.assertFalse(partial['minimum_assigned'])
        self.assertIsNone(partial['orientations']['both_orientations']['minimum_on_complete_grid_percent'])
        for orientation in report.ORIENTATIONS:
            rows[('novo', orientation, 20)] = {'passed': False}
        full = report.area_frontier(rows, losses)
        self.assertTrue(full['minimum_assigned'])
        self.assertEqual(full['orientations']['both_orientations']['minimum_on_complete_grid_percent'], 90)
        rows[('novo', 'original', 0)]['passed'] = False
        self.assertFalse(report.area_frontier(rows, losses)['minimum_assigned'])

    def test_replay_rejects_changed_evidence_without_any_clinical_references(self):
        with tempfile.TemporaryDirectory(prefix='pfc-s3-area-test-') as temp:
            root = Path(temp);base = root/'base';out = base/'analysis'
            evidence = base/'identidade/evidencias/novo_original_0'
            evidence.mkdir(parents=True);out.mkdir()
            def save(path, value):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding='utf-8')
            manifest = root/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
            rows = [dict(subject=i+1, side='L', session=1, image=f'g{i}.png') for i in range(16)]
            rows += [dict(subject=i%16+1, side='L', session=2, image=f'q{i}.png') for i in range(482)]
            save(manifest, {'val': rows})
            frozen = root/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
            save(frozen, {'frozen_threshold': .8})
            criteria = report.read(report.ROOT/'criterios_prontidao_anomalias.json')
            save(root/'criterios_prontidao_anomalias.json', criteria)
            (base/'candidato_epoca_01.pt').write_bytes(b'synthetic-test-only')
            candidate = report.sha(base/'candidato_epoca_01.pt')
            save(base/'CONCLUIDO.json', {'development_smoke_only': False, 'checkpoint_sha256': candidate, 'best_epoch': 1})
            (evidence/'source.py').write_bytes(b'synthetic-frozen-source')
            sources = {'avaliar_candidato_congelado.py': report.sha(evidence/'source.py')}
            save(evidence/'ADAPTADOR_SAM3.json', {'sources': sources, 'versions': {'numpy': 'test'}, 'candidate_sha256': candidate})
            save(evidence/'protocolo.json', {'split': 'val', 'fixed_geometry_diagnostic': False,
                'queries': 482, 'candidates': 16, 'condition': 'original', 'occluded_percent': 0,
                'unet_sha256': candidate, 'threshold': .8, 'frozen_sha256': report.sha(frozen)})
            labels = np.arange(482)%16;scores = np.zeros((482, 16));scores[np.arange(482), labels] = .9
            valid = np.ones(482, bool);valid[0] = False
            counts, rates, _, vectors = report.measure(scores, labels, valid, .8)
            np.savez(evidence/'scores_finais.npz', scores=scores, labels=labels, valid=valid,
                     correct=vectors['rank1'], accepted=vectors['tar'])
            save(evidence/'interventions.json', [])
            save(base/'identidade/novo_original_0.json', {'condition': 'original', 'loss_percent': 0,
                'checkpoint_sha256': candidate, 'counts': counts, 'rates': rates, 'passed_new_readiness_criterion': True})
            training = {'frozen': {'manifest_sha256': report.sha(manifest)}}
            flow = {'area_loss_grid': [0, 10], 'sources': sources, 'versions': {'numpy': 'test'}}
            with patch.multiple(report, ROOT=root, BASE=base, OUT=out):
                audited = report.audit_identity(training, flow)
                self.assertEqual(audited['records'][0]['counts']['extraction_failures'], 1)
                self.assertEqual(audited['records'][0]['counts']['queries'], 482)
                self.assertFalse(audited['frontier']['minimum_assigned'])
                self.assertFalse((root/'outputs/revisao_clinica_2026-11-03').exists())
                save(out/'AUDITORIA.json', audited)
                (evidence/'interventions.json').write_text('[ ]', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Evidencia mudou'):
                    report.audit_identity(training, flow)
                (base/'identidade/novo_original_0.json').unlink()
                with self.assertRaisesRegex(ValueError, 'desapareceram'):
                    report.audit_identity(training, flow)


if __name__ == '__main__':
    unittest.main()
