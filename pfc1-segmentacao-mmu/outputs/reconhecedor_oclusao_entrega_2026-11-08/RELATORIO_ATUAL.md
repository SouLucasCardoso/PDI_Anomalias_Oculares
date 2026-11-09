# Resultado do ajuste do reconhecedor

Época selecionada: **0**. Ganho elegível pela regra registrada: **não**.

| Condição | Versão | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| original | baseline | 90.04% | 90.46% | 0.996% | 88.38% |
| original | selected | 90.04% | 90.46% | 0.996% | 88.38% |
| oclusao_superior | baseline | 80.91% | 78.01% | 1.286% | 76.35% |
| oclusao_superior | selected | 80.91% | 78.01% | 1.286% | 76.35% |
| oclusao_inferior | baseline | 59.96% | 57.88% | 2.434% | 55.81% |
| oclusao_inferior | selected | 59.96% | 57.88% | 2.434% | 55.81% |

Os pesos, a padronização e o limiar da fusão foram mantidos nesta comparação primária. Cada linha usa todas as482consultas de validação. Intervalos descritivos pareados por pessoa e contagens independentes constam de AUDITORIA.json. A validação foi reutilizada no desenvolvimento e na seleção; os intervalos não removem esse viés. Não houve teste independente, ensaio clínico ou estimativa de mínimo universal.

## Controle secundário de falsas correspondências

Aplicou-se às duas versões a mesma regra previamente registrada: calibrar em cada condição para FMR≤1% e usar o maior dos três limiares, fixo nas três condições. Este diagnóstico não escolheu a época nem os pesos. Seus valores são de calibração na própria validação, sem certificação fora dela.

| Condição | Versão | Limiar fixo | Rank-1 | TAR | FMR |
|---|---|---:|---:|---:|---:|
| original | baseline | 0.893739085 | 90.04% | 77.59% | 0.277% |
| original | selected | 0.893739085 | 90.04% | 77.59% | 0.277% |
| oclusao_superior | baseline | 0.893739085 | 80.91% | 64.32% | 0.443% |
| oclusao_superior | selected | 0.893739085 | 80.91% | 64.32% | 0.443% |
| oclusao_inferior | baseline | 0.893739085 | 59.96% | 45.02% | 0.996% |
| oclusao_inferior | selected | 0.893739085 | 59.96% | 45.02% | 0.996% |

Nenhum arquivo, modelo ou resultado do artigo já concluído foi substituído automaticamente. Um eventual novo ensaio de teste exige congelar o candidato e executar a grade completa, mantendo as falhas no denominador.
