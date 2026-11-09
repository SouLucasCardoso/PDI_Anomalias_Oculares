# Misturas fixas do novo contorno

Candidato elegível: **polar_only_alpha0.5**.

| Candidato | Condição | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| reference | original | 90.04% | 90.46% | 0.996% | 88.38% |
| reference | oclusao_superior | 80.91% | 78.01% | 1.286% | 76.35% |
| reference | oclusao_inferior | 59.96% | 57.88% | 2.434% | 55.81% |
| polar_only_alpha0.25 | original | 90.04% | 90.66% | 0.996% | 88.59% |
| polar_only_alpha0.25 | oclusao_superior | 80.71% | 78.42% | 1.259% | 76.35% |
| polar_only_alpha0.25 | oclusao_inferior | 60.58% | 58.09% | 2.490% | 56.43% |
| polar_only_alpha0.5 | original | 90.25% | 90.66% | 0.968% | 88.59% |
| polar_only_alpha0.5 | oclusao_superior | 80.50% | 78.42% | 1.217% | 76.14% |
| polar_only_alpha0.5 | oclusao_inferior | 60.58% | 57.68% | 2.393% | 56.22% |
| native_only_alpha0.25 | original | 89.83% | 89.83% | 0.996% | 88.17% |
| native_only_alpha0.25 | oclusao_superior | 80.71% | 77.80% | 1.272% | 75.73% |
| native_only_alpha0.25 | oclusao_inferior | 60.79% | 57.68% | 2.462% | 56.43% |
| native_only_alpha0.5 | original | 89.83% | 89.83% | 1.010% | 88.17% |
| native_only_alpha0.5 | oclusao_superior | 80.50% | 77.59% | 1.259% | 75.52% |
| native_only_alpha0.5 | oclusao_inferior | 61.00% | 57.68% | 2.448% | 56.43% |
| native_and_polar_alpha0.25 | original | 90.04% | 90.25% | 0.954% | 88.38% |
| native_and_polar_alpha0.25 | oclusao_superior | 80.71% | 77.80% | 1.272% | 75.93% |
| native_and_polar_alpha0.25 | oclusao_inferior | 60.79% | 57.68% | 2.448% | 56.43% |
| native_and_polar_alpha0.5 | original | 90.25% | 90.25% | 0.954% | 88.59% |
| native_and_polar_alpha0.5 | oclusao_superior | 80.50% | 78.01% | 1.314% | 75.73% |
| native_and_polar_alpha0.5 | oclusao_inferior | 60.79% | 57.88% | 2.434% | 56.43% |

Sem ajuste do limiar ou descarte de consultas. Exploração adicional em validação reutilizada, sem confirmação independente.