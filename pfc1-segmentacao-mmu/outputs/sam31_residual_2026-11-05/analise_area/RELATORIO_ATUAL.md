# SAM3.1 — treino, reconhecimento e área

Atualizado em 2026-11-08T15:39:00.777514+00:00 (UTC).

**As revisões clínicas podem ser feitas depois; não são requisito para esta curva UBIPr.**

O extrator visual SAM3.1 é congelado; o decodificador RGB+SAM3 recebe treino supervisionado.

Treino concluído. Candidato selecionado: **época 8**.

| Época | Original | Zoom 3× | Oblíqua | Óculos |
|---:|---:|---:|---:|---:|
| 0 | 88.62% | 86.51% | 87.61% | 88.21% |
| 1 | 88.64% | 86.49% | 87.63% | 88.29% |
| 2 | 88.63% | 86.53% | 87.61% | 88.33% |
| 3 | 88.65% | 86.53% | 87.64% | 88.38% |
| 4 | 88.65% | 86.52% | 87.64% | 88.40% |
| 5 | 88.66% | 86.59% | 87.64% | 88.41% |
| 6 | 88.66% | 86.61% | 87.67% | 88.42% |
| 7 | 88.66% | 86.54% | 87.65% | 88.43% |
| 8 | 88.65% | 86.65% | 87.63% | 88.40% |
| 9 | 88.65% | 86.62% | 87.64% | 88.37% |
| 10 | 88.64% | 86.58% | 87.66% | 88.35% |
| 11 | 88.66% | 86.59% | 87.64% | 88.44% |
| 12 | 88.68% | 86.61% | 87.67% | 88.44% |
| 13 | 88.67% | 86.62% | 87.66% | 88.39% |
| 14 | 88.67% | 86.65% | 87.66% | 88.45% |

Todas as condições usam as 1.652 imagens de validação. A seleção consulta somente segmentação.

| Modelo/condição/perda | Rank-1 | TAR | Correto e aceito | FMR | Falhas | Critério |
|---|---:|---:|---:|---:|---:|---|
| novo / oclusao_inferior / 10% | 81.12% | 76.97% | 75.93% | 1.355% | 3 | Não passou |
| novo / oclusao_superior / 10% | 84.02% | 81.33% | 79.88% | 1.093% | 3 | Não passou |
| novo / original / 0% | 89.42% | 89.63% | 87.34% | 0.927% | 3 | Não passou |
| original / oclusao_inferior / 10% | 59.96% | 57.88% | 55.81% | 2.434% | 7 | Não passou |
| original / oclusao_superior / 10% | 80.91% | 78.01% | 76.35% | 1.286% | 4 | Não passou |
| original / original / 0% | 90.04% | 90.46% | 88.38% | 0.996% | 4 | Não passou |

Critério novo: Rank-1, TAR e acerto aceito simultâneo ≥90%; FMR ≤1%, comparados por contagens inteiras.

**Candidato reprovado sem oclusão. Nenhum novo mínimo foi atribuído.**

Os intervalos descritivos de 95%, com 5.000 reamostragens por pessoa e galeria fixa, estão em [AUDITORIA.json](AUDITORIA.json). Não são uma garantia simultânea da fronteira de área.

Oclusão cinza sintética e validação reutilizada no desenvolvimento. A área não representa a íris anatômica inteira ou a extensão de uma doença. Não houve nova inferência no teste ou demonstração de efeito clínico.

[Estado separado do piloto clínico](../../prontidao_anomalias_2026-11-03/PRONTIDAO.md).



Ensaio de 05/11: correção residual com 32 canais; adaptador-base selecionado na época 15 e extrator SAM3.1 congelados, incluindo as estatísticas BatchNorm do controle.

A cabeça de saída começa em zero e preserva os logits do controle na inicialização. A correção é limitada a ±4 por logit. Somente a cabeça de correção recebe gradientes.

Até 24 épocas, lotes de 8 e parada após 6 épocas sem ganho elegível. Perda original CE/Dice/Tversky; a penalização extra de negativos internos reprovada na rodada anterior não é usada.

São reutilizados os 22.040 mapas fechados, com hash a cada leitura. Época zero é medida novamente nas quatro condições; não é inferida a partir do teste curto.

Nenhuma referência clínica ou imagem de teste seleciona pesos. Os controles originais de identidade serão reutilizados após auditoria; o novo candidato usa cache exclusivo.

A sensibilidade mantém todas as 482 consultas na análise principal; 472 têm referência de área definida. Não foi alterado o limiar de reconhecimento.
