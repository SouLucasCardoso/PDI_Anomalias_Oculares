# Geometria externa SAM3.1 — validação de identidade

Candidato elegível: False. Suporte U-Net e pupila preservados; altera apenas a amostragem externa polar. Todas as482consultas permanecem no denominador.

| Versão | Condição | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| baseline | original | 90.04% | 90.46% | 0.996% | 88.38% |
| baseline | oclusao_superior | 80.91% | 78.01% | 1.286% | 76.35% |
| baseline | oclusao_inferior | 59.96% | 57.88% | 2.434% | 55.81% |
| sam31_outer_geometry | original | 89.63% | 89.42% | 0.913% | 87.55% |
| sam31_outer_geometry | oclusao_superior | 80.50% | 79.05% | 1.162% | 77.39% |
| sam31_outer_geometry | oclusao_inferior | 67.01% | 64.94% | 2.006% | 62.66% |

Validação reutilizada no desenvolvimento. Sem inferência de teste, reconstrução de textura, referência clínica ou substituição automática.
