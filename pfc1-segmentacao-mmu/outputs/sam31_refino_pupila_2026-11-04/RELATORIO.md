# Piloto de refinamento SAM3

**Somente viabilidade em treino; sem novo minimo de area ou validacao clinica.**

32 imagens de pessoas distintas do treino; todas preservadas.

| Metodo | Dice macro | IoU macro | Casos Dice<50% |
|---|---:|---:|---:|
| global | 91.96% | 87.66% | 1 |
| global_pupil | 90.50% | 85.07% | 1 |
| roi | 89.44% | 83.30% | 1 |
| roi_pupil | 88.14% | 81.07% | 1 |

Variante sugerida para validacao completa: **nenhuma**.

A regra previa exige ganho de pelo menos0,5pp no treino, sem aumento de falhas graves ou falsos positivos em referencias vazias. Essa regra nao substitui validacao nas quatro condicoes, reconhecimento ou os criterios clinicos.

O SAM3 recebe texto pupil of the eye, sem cliques ou caixas de referencia. A selecao usa apenas escores previstos e restricoes geometricas. A ROI parte da previsao global, usa pixels nativos e retorna ao sistema de coordenadas comum. Todas as variantes usam os mesmos pesos congelados.

Apenas a mascara anotada de iris e usada na medicao de Dice. Nao foi inventada uma referencia independente de pupila. Os candidatos sem confianca ou plausibilidade mantem a previsao global.