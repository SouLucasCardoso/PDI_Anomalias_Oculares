import unittest

import numpy as np

from avaliar_sam2_mmu import (
    aggregate,
    clamp_box,
    compute_metrics,
    mask_geometry,
    processor_prompt,
    useful_selection_score,
)


class TestMetricasAproveitamento(unittest.TestCase):
    def test_metricas_distinguem_cobertura_e_pureza(self):
        truth = np.zeros((5, 5), dtype=bool)
        truth[1:3, 1:3] = True
        prediction = np.zeros_like(truth)
        prediction[1:3, 1:4] = True
        metrics = compute_metrics(prediction, truth)
        self.assertEqual(metrics["aproveitamento_percentual"], 100.0)
        self.assertAlmostEqual(metrics["pureza_percentual"], 100.0 * 4 / 6)
        self.assertAlmostEqual(metrics["contaminacao_percentual"], 100.0 * 2 / 6)
        self.assertAlmostEqual(metrics["dice"], 0.8)

    def test_geometria_e_caixa_sao_limitadas_a_imagem(self):
        mask = np.zeros((10, 20), dtype=bool)
        mask[2:8, 5:15] = True
        geometry = mask_geometry(mask)
        self.assertEqual(geometry, {"cx": 9.5, "cy": 4.5, "width": 10.0, "height": 6.0})
        self.assertEqual(clamp_box(1, 1, 10, 8, 20, 10), [0.0, 0.0, 6.0, 5.0])

    def test_prompt_negativo_marca_centro_como_fundo(self):
        geometry = {
            "box": [1, 2, 8, 9],
            "ring_points": [[2, 5], [7, 5], [5, 3], [5, 8]],
            "negative_center": [5, 5],
        }
        prompt = processor_prompt(geometry, "box_ring_points")
        self.assertEqual(prompt["input_labels"], [[[1, 1, 1, 1, 0]]])
        self.assertEqual(prompt["input_points"][0][0][-1], [5, 5])

    def test_agregacao_preserva_percentuais(self):
        row = {
            "dice": 1.0,
            "iou": 1.0,
            "aproveitamento_percentual": 100.0,
            "pureza_percentual": 100.0,
            "contaminacao_percentual": 0.0,
            "perda_iris_percentual": 0.0,
            "razao_area_prevista_referencia": 1.0,
            "preenchimento_pupila_percentual": None,
            "sam_predicted_iou": 0.9,
        }
        result = aggregate([row])
        self.assertEqual(result["aproveitamento_percentual"]["mean"], 100.0)
        self.assertIsNone(result["preenchimento_pupila_percentual"])

    def test_indice_util_penaliza_pupila_preenchida(self):
        metrics = {
            "dice": {"mean": 0.8},
            "preenchimento_pupila_percentual": {"mean": 75.0},
        }
        self.assertAlmostEqual(useful_selection_score(metrics), 0.2)


if __name__ == "__main__":
    unittest.main()
