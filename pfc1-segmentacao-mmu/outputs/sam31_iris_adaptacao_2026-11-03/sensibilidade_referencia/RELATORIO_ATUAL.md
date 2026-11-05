# Sensibilidade às referências de área

Análise secundária especificada antes dos escores do novo candidato. A regra original, o limiar e os pesos permanecem iguais.

São 482 consultas: **472 com área anotada** e **10 sem pixels anotados como íris**. Uma referência vazia não comprova ausência anatômica de íris.

O resultado primário conserva todas as consultas. Esta análise separa os estratos, mantendo as falhas nos denominadores de cada um, para interpretar a quantidade de área efetivamente definida.

| Condição | Grupo | Consultas | Rank-1 | TAR | Correto e aceito | FMR |
|---|---|---:|---:|---:|---:|---:|
| novo_oclusao_inferior_10 | all_queries | 482 | 79.67% | 77.39% | 75.52% | 1.466% |
| novo_oclusao_inferior_10 | defined_reference | 472 | 80.51% | 77.97% | 76.27% | 1.469% |
| novo_oclusao_inferior_10 | undefined_reference | 10 | 40.00% | 50.00% | 40.00% | 1.333% |
| novo_oclusao_superior_10 | all_queries | 482 | 82.37% | 79.05% | 77.39% | 1.134% |
| novo_oclusao_superior_10 | defined_reference | 472 | 83.26% | 79.66% | 78.18% | 1.130% |
| novo_oclusao_superior_10 | undefined_reference | 10 | 40.00% | 50.00% | 40.00% | 1.333% |
| novo_original_0 | all_queries | 482 | 89.42% | 89.63% | 86.93% | 1.051% |
| novo_original_0 | defined_reference | 472 | 90.47% | 90.47% | 87.92% | 1.045% |
| novo_original_0 | undefined_reference | 10 | 40.00% | 50.00% | 40.00% | 1.333% |
| original_oclusao_inferior_10 | all_queries | 482 | 59.96% | 57.88% | 55.81% | 2.434% |
| original_oclusao_inferior_10 | defined_reference | 472 | 60.38% | 58.05% | 56.14% | 2.458% |
| original_oclusao_inferior_10 | undefined_reference | 10 | 40.00% | 50.00% | 40.00% | 1.333% |
| original_oclusao_superior_10 | all_queries | 482 | 80.91% | 78.01% | 76.35% | 1.286% |
| original_oclusao_superior_10 | defined_reference | 472 | 81.78% | 78.60% | 77.12% | 1.285% |
| original_oclusao_superior_10 | undefined_reference | 10 | 40.00% | 50.00% | 40.00% | 1.333% |
| original_original_0 | all_queries | 482 | 90.04% | 90.46% | 88.38% | 0.996% |
| original_original_0 | defined_reference | 472 | 91.10% | 91.31% | 89.41% | 0.989% |
| original_original_0 | undefined_reference | 10 | 40.00% | 50.00% | 40.00% | 1.333% |

Mínimo conservador interpretável na grade completa: **ainda não estabelecido**.

O grupo sem referência de íris recebe métricas de identificação descritivas, mas nenhuma fração de área. A interpretação conservadora exige aprovação do prefixo completo tanto no resultado geral quanto no grupo com referência definida, nas duas orientações.

O grupo de dez consultas é pequeno. Não há calibração por grupo, exclusão do resultado original, promoção de checkpoint ou inferência clínica a partir desta análise.

[Caracterização dos pixels da referência](../grade_area_ubipr/REFERENCIA_AREA.md).

[Resultado primário e progresso do SAM3](../analise_area/RELATORIO_ATUAL.md).