# SAM3.1 — treino, reconhecimento e área

Atualizado em 2026-11-08T15:39:00.490931+00:00 (UTC).

**As revisões clínicas podem ser feitas depois; não são requisito para esta curva UBIPr.**

O extrator visual SAM3.1 é congelado; o decodificador RGB+SAM3 recebe treino supervisionado.

Treino concluído. Candidato selecionado: **época 15**.

| Época | Original | Zoom 3× | Oblíqua | Óculos |
|---:|---:|---:|---:|---:|
| 0 | 86.09% | 83.18% | 85.54% | 85.18% |
| 1 | 87.70% | 85.22% | 86.83% | 86.69% |
| 2 | 88.21% | 85.60% | 87.24% | 87.38% |
| 3 | 88.33% | 85.79% | 87.31% | 87.49% |
| 4 | 88.40% | 86.05% | 87.40% | 87.66% |
| 5 | 88.29% | 86.23% | 87.39% | 87.55% |
| 6 | 88.41% | 86.05% | 87.34% | 87.74% |
| 7 | 88.52% | 86.24% | 87.59% | 87.87% |
| 8 | 88.52% | 86.37% | 87.61% | 87.95% |
| 9 | 88.58% | 86.43% | 87.48% | 87.96% |
| 10 | 88.55% | 86.38% | 87.62% | 87.94% |
| 11 | 88.55% | 86.37% | 87.48% | 87.82% |
| 12 | 88.63% | 86.46% | 87.60% | 88.12% |
| 13 | 88.57% | 86.37% | 87.65% | 88.09% |
| 14 | 88.60% | 86.42% | 87.60% | 87.91% |
| 15 | 88.62% | 86.51% | 87.61% | 88.21% |
| 16 | 88.63% | 86.50% | 87.67% | 88.15% |
| 17 | 88.61% | 86.49% | 87.60% | 87.85% |
| 18 | 88.63% | 86.47% | 87.60% | 88.15% |
| 19 | 88.63% | 86.48% | 87.61% | 88.11% |
| 20 | 88.65% | 86.51% | 87.65% | 88.18% |

Todas as condições usam as 1.652 imagens de validação. A seleção consulta somente segmentação.

| Modelo/condição/perda | Rank-1 | TAR | Correto e aceito | FMR | Falhas | Critério |
|---|---:|---:|---:|---:|---:|---|
| novo / oclusao_inferior / 10% | 79.67% | 77.39% | 75.52% | 1.466% | 3 | Não passou |
| novo / oclusao_superior / 10% | 82.37% | 79.05% | 77.39% | 1.134% | 3 | Não passou |
| novo / original / 0% | 89.42% | 89.63% | 86.93% | 1.051% | 3 | Não passou |
| original / oclusao_inferior / 10% | 59.96% | 57.88% | 55.81% | 2.434% | 7 | Não passou |
| original / oclusao_superior / 10% | 80.91% | 78.01% | 76.35% | 1.286% | 4 | Não passou |
| original / original / 0% | 90.04% | 90.46% | 88.38% | 0.996% | 4 | Não passou |

Critério novo: Rank-1, TAR e acerto aceito simultâneo ≥90%; FMR ≤1%, comparados por contagens inteiras.

**Candidato reprovado sem oclusão. Nenhum novo mínimo foi atribuído.**

Os intervalos descritivos de 95%, com 5.000 reamostragens por pessoa e galeria fixa, estão em [AUDITORIA.json](AUDITORIA.json). Não são uma garantia simultânea da fronteira de área.

Oclusão cinza sintética e validação reutilizada no desenvolvimento. A área não representa a íris anatômica inteira ou a extensão de uma doença. Não houve nova inferência no teste ou demonstração de efeito clínico.

[Estado separado do piloto clínico](../../prontidao_anomalias_2026-11-03/PRONTIDAO.md).