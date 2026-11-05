# Auditoria do treino SAM3.1

As 20 epocas foram concluidas. A regra original de selecao reproduziu a **epoca 15**, sem consultar identidade.

| Condicao | Epoca zero | Epoca 15 | Delta Dice (pp) | Intervalo descritivo 95% (pp) | Falhas Dice<50%: antes / depois |
|---|---:|---:|---:|---:|---:|
| clean | 86.09% | 88.62% | +2.53 | [+1.33, +3.93] | 121 / 104 |
| zoom3 | 83.18% | 86.51% | +3.34 | [+2.43, +4.36] | 141 / 116 |
| oblique | 85.54% | 87.61% | +2.07 | [+1.20, +3.07] | 120 / 110 |
| glasses | 85.18% | 88.21% | +3.03 | [+1.77, +4.54] | 124 / 102 |

Todas as condicoes usam as mesmas 1.652 imagens e transformacoes da epoca zero. Os intervalos sao descritivos, agrupados por pessoa e calculados apos selecao na mesma validacao.

**A meta de Dice macro >=90% nas quatro condicoes ainda nao foi atingida.** A avaliacao biometrica continua separada e nao e substituida por este resultado.

| Condicao | Referencias positivas | Referencias vazias | Dice nas positivas: antes / depois | Falsos positivos nas vazias: antes / depois |
|---|---:|---:|---:|---:|
| clean | 1621 | 31 | 87.37% / 89.76% | 25 / 22 |
| zoom3 | 1594 | 58 | 85.77% / 88.97% | 51 / 47 |
| oblique | 1621 | 31 | 86.99% / 88.98% | 28 / 26 |
| glasses | 1621 | 31 | 86.43% / 89.22% | 25 / 20 |

Os grupos sao apenas diagnosticos; nenhuma imagem foi removida da metrica principal ou do treino. Referencia vazia nao demonstra ausencia anatomica de iris.

O ganho compara o pacote treinado com a sua epoca zero. O ramo RGB, a projecao SAM3 e a perda participaram da adaptacao; esta comparacao nao isola a contribuicao causal do SAM3 de mais epocas ou do novo objetivo de perda. Isso exigiria um controle de treino RGB pareado.

[Acompanhamento da avaliacao de reconhecimento](../analise_area/RELATORIO_ATUAL.md).