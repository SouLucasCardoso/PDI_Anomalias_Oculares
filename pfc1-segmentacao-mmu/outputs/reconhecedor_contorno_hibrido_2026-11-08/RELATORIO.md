# Contorno por grupo de descritores

Candidato elegível: polar_only. Ablação exploratória de validação; pesos e limiar históricos mantidos.

| Grupo | Condição | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| nearest | original | 90.04% | 90.46% | 0.996% | 88.38% |
| nearest | oclusao_superior | 80.91% | 78.01% | 1.286% | 76.35% |
| nearest | oclusao_inferior | 59.96% | 57.88% | 2.434% | 55.81% |
| rgb_only | original | 88.59% | 88.38% | 0.954% | 86.51% |
| rgb_only | oclusao_superior | 78.42% | 74.27% | 1.203% | 72.61% |
| rgb_only | oclusao_inferior | 61.41% | 57.05% | 2.379% | 56.43% |
| polar_only | original | 90.25% | 90.46% | 0.982% | 88.59% |
| polar_only | oclusao_superior | 80.50% | 78.42% | 1.189% | 76.35% |
| polar_only | oclusao_inferior | 60.17% | 58.92% | 2.282% | 56.43% |
| native_only | original | 89.83% | 88.80% | 0.954% | 87.55% |
| native_only | oclusao_superior | 79.88% | 76.76% | 1.300% | 74.48% |
| native_only | oclusao_inferior | 60.79% | 57.26% | 2.379% | 56.02% |