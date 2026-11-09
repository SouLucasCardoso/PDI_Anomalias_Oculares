# Reconhecedor sob oclusoes — comparacao de desenvolvimento

Validação: 482 consultas,16 candidatos do mesmo lado; mesmos pesos, calibração e limiar. Sem nova inferência de teste.

| Contorno | Condição | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| nearest | original | 90.04% | 90.46% | 0.996% | 88.38% |
| continuous | original | 89.00% | 88.59% | 1.010% | 86.51% |
| nearest | oclusao_superior | 80.91% | 78.01% | 1.286% | 76.35% |
| continuous | oclusao_superior | 78.84% | 75.52% | 1.134% | 73.65% |
| nearest | oclusao_inferior | 59.96% | 57.88% | 2.434% | 55.81% |
| continuous | oclusao_inferior | 61.20% | 59.54% | 2.365% | 58.30% |

O resultado de segmentação não determina a decisão biométrica. O contorno novo só será candidato se preservar Rank-1/TAR limpos, melhorar a média do acerto e aceitação conjuntos nas três condições e não aumentar FMR nas oclusões. Para aprovação completa, FMR≤1% em todas as condições. Avaliação de desenvolvimento repetida, sem independência clínica.
