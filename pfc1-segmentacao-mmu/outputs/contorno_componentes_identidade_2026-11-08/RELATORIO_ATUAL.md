# Identidade com remoção de fragmentos

Candidato elegível: **nenhum**.

| Grupo | Condição | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| reference | original | 90.04% | 90.46% | 0.996% | 88.38% |
| reference | oclusao_superior | 80.91% | 78.01% | 1.286% | 76.35% |
| reference | oclusao_inferior | 59.96% | 57.88% | 2.434% | 55.81% |
| polar_only | original | 89.83% | 90.66% | 0.996% | 88.38% |
| polar_only | oclusao_superior | 80.29% | 78.84% | 1.203% | 76.14% |
| polar_only | oclusao_inferior | 60.17% | 58.71% | 2.337% | 56.85% |
| native_only | original | 89.83% | 88.80% | 0.954% | 87.55% |
| native_only | oclusao_superior | 79.88% | 76.76% | 1.328% | 74.48% |
| native_only | oclusao_inferior | 60.79% | 57.26% | 2.379% | 56.02% |
| native_and_polar | original | 89.83% | 89.63% | 0.968% | 87.97% |
| native_and_polar | oclusao_superior | 80.50% | 77.18% | 1.272% | 75.10% |
| native_and_polar | oclusao_inferior | 61.20% | 58.30% | 2.434% | 57.26% |

Pesos e limiar fixos. Validação reutilizada no desenvolvimento, sem confirmação independente. Todas as 482 consultas e as falhas foram mantidas.