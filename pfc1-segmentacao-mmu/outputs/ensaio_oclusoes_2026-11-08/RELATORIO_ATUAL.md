# Influência da área preservada — ensaio de 08/11/2026

**CONCLUÍDO**

Área preservada = 100 × (1 − pixels ocluídos / pixels da íris originalmente anotada). Não é a fração do anel anatômico da ISO. Cadastro original; uma fotografia por consulta; 16 candidatos do mesmo lado. Todas as 486 consultas e falhas são mantidas. Teste reutilizado no histórico: análise exploratória, sem confirmação cega.

| Modelo | Posição | Oclusão | Área nominal | Rank-1 | TAR | Correto e aceito | FMR | Falhas | Critério |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| historico | original | 0% | 100% | 91.15% | 92.39% | 89.51% | 0.864% | 2 | Passou |
| fusao_validacao | original | 0% | 100% | 91.15% | 92.39% | 89.51% | 0.864% | 2 | Passou |
| historico | oclusao_superior | 1% | 99% | 89.92% | 92.18% | 88.48% | 0.878% | 2 | Não passou |
| fusao_validacao | oclusao_superior | 1% | 99% | 89.92% | 92.18% | 88.48% | 0.878% | 2 | Não passou |
| historico | oclusao_inferior | 1% | 99% | 90.95% | 91.15% | 88.89% | 0.892% | 2 | Passou |
| fusao_validacao | oclusao_inferior | 1% | 99% | 90.95% | 91.15% | 88.89% | 0.892% | 2 | Passou |
| historico | oclusao_superior | 5% | 95% | 87.86% | 88.89% | 85.60% | 1.303% | 2 | Não passou |
| fusao_validacao | oclusao_superior | 5% | 95% | 87.86% | 88.89% | 85.60% | 1.303% | 2 | Não passou |
| historico | oclusao_inferior | 5% | 95% | 74.07% | 77.78% | 71.40% | 1.879% | 2 | Não passou |
| fusao_validacao | oclusao_inferior | 5% | 95% | 74.07% | 77.78% | 71.40% | 1.879% | 2 | Não passou |
| historico | oclusao_superior | 10% | 90% | 82.30% | 84.57% | 80.25% | 1.674% | 2 | Não passou |
| fusao_validacao | oclusao_superior | 10% | 90% | 82.30% | 84.57% | 80.25% | 1.674% | 2 | Não passou |
| historico | oclusao_inferior | 10% | 90% | 58.23% | 60.91% | 55.56% | 2.565% | 2 | Não passou |
| fusao_validacao | oclusao_inferior | 10% | 90% | 58.23% | 60.91% | 55.56% | 2.565% | 2 | Não passou |
| historico | oclusao_superior | 20% | 80% | 69.96% | 72.63% | 67.90% | 2.154% | 2 | Não passou |
| fusao_validacao | oclusao_superior | 20% | 80% | 69.96% | 72.63% | 67.90% | 2.154% | 2 | Não passou |
| historico | oclusao_inferior | 20% | 80% | 40.74% | 40.33% | 37.24% | 3.224% | 3 | Não passou |
| fusao_validacao | oclusao_inferior | 20% | 80% | 40.74% | 40.33% | 37.24% | 3.237% | 3 | Não passou |
| historico | oclusao_superior | 30% | 70% | 69.96% | 69.96% | 66.46% | 2.099% | 4 | Não passou |
| fusao_validacao | oclusao_superior | 30% | 70% | 69.96% | 69.96% | 66.46% | 2.099% | 4 | Não passou |
| historico | oclusao_inferior | 30% | 70% | 33.54% | 32.30% | 29.63% | 3.471% | 5 | Não passou |
| fusao_validacao | oclusao_inferior | 30% | 70% | 33.54% | 32.51% | 29.84% | 3.471% | 5 | Não passou |
| historico | oclusao_superior | 31% | 69% | 69.34% | 70.99% | 66.26% | 2.016% | 5 | Não passou |
| fusao_validacao | oclusao_superior | 31% | 69% | 69.34% | 70.99% | 66.26% | 2.030% | 5 | Não passou |
| historico | oclusao_inferior | 31% | 69% | 32.51% | 29.42% | 27.57% | 3.525% | 5 | Não passou |
| fusao_validacao | oclusao_inferior | 31% | 69% | 32.51% | 29.42% | 27.57% | 3.525% | 5 | Não passou |

Critério nominal: Rank-1 ≥90%, TAR ≥90%, FMR ≤1%. O sucesso conjunto é informado separadamente. Os intervalos de 95% são descritivos por pessoa, com galeria fixa; não certificam simultaneamente toda a curva.

O limiar e os pesos de cada sistema permanecem fixos em todos os níveis. Todos os níveis registrados são executados, inclusive após falha. 30% e 31% de oclusão produzem 70% e 69% do suporte anotado, sem ensaio de conformidade ISO ou conclusão sobre doença.

[Progresso detalhado](estado.json) · [Protocolo](protocolo.json) · [Fusão congelada](FUSAO_CONGELADA.json) · [Resultados completos](resultados.json)
