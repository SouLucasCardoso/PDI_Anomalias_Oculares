# Segmentação e identificação — acompanhamento

Atualizado em 2026-11-05T11:47:06.195931+00:00 (UTC).

Última época concluída: **30**. A seleção do candidato usa somente segmentação.

![Evolução da validação](evolucao_segmentacao.png)

Aumento sintético de escala, vista oblíqua e óculos. Esses resultados não medem doenças oculares.

Candidato final: **época 30**; 482 consultas de 16 pessoas, candidatos do mesmo lado informado.

| Segmentador/condição | Rank-1 | TAR | Correto e aceito | FMR | Falhas | Critério registrado |
|---|---:|---:|---:|---:|---:|---|
| original / original / perda 0% | 90.04% | 90.66% | 88.38% | 0.982% | 4 | Passou |
| original / oclusao_superior / perda 10% | 80.71% | 78.01% | 76.14% | 1.300% | 4 | Não passou |
| original / oclusao_inferior / perda 10% | 59.96% | 57.88% | 55.81% | 2.407% | 7 | Não passou |
| novo / original / perda 0% | 86.10% | 85.68% | 83.40% | 1.203% | 3 | Não passou |
| novo / oclusao_superior / perda 10% | 80.08% | 76.56% | 75.10% | 1.203% | 3 | Não passou |
| novo / oclusao_inferior / perda 10% | 70.33% | 70.95% | 66.60% | 2.254% | 3 | Não passou |

Critério: Rank-1 ≥ 90%, TAR ≥ 90% e FMR ≤ 1%, com contagens inteiras e todas as falhas no denominador. Acerto e aceitação simultâneos são mostrados separadamente; não alteram o critério registrado.

Diferenças pareadas: candidato menos original, em pontos percentuais. Intervalos de 95% por 5.000 reamostragens de pessoas, com galeria fixa. FMR positivo significa piora.

| Condição | Métrica | Diferença (pp) | Intervalo 95% (pp) |
|---|---|---:|---:|
| original 0% | rank1 | -3.94 | [-8.47, -0.41] |
| original 0% | tar | -4.98 | [-10.37, -0.62] |
| original 0% | joint | -4.98 | [-9.58, -1.24] |
| original 0% | fmr | +0.22 | [-0.11, +0.59] |
| oclusao_superior 10% | rank1 | -0.62 | [-5.62, +5.81] |
| oclusao_superior 10% | tar | -1.45 | [-7.08, +4.53] |
| oclusao_superior 10% | joint | -1.04 | [-6.67, +5.14] |
| oclusao_superior 10% | fmr | -0.10 | [-0.51, +0.29] |
| oclusao_inferior 10% | rank1 | +10.37 | [+1.88, +17.84] |
| oclusao_inferior 10% | tar | +13.07 | [+6.67, +19.50] |
| oclusao_inferior 10% | joint | +10.79 | [+3.12, +17.56] |
| oclusao_inferior 10% | fmr | -0.15 | [-0.87, +0.58] |

**Área visível:**

O candidato não passou no critério de reconhecimento sem oclusão. **Nenhum novo mínimo foi atribuído.**

A área é relativa à íris visível originalmente anotada. A oclusão cinza é sintética. A validação já foi usada no desenvolvimento e não é confirmação cega. Os intervalos são descritivos de cada comparação e não validam simultaneamente uma fronteira de área. Não foi estimado percentual anatômico ou efeito causal de anomalias clínicas.
