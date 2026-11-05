# Fechamento auditado — 05/11/2026

A rodada terminou após quatro épocas sem ganho elegível. Foi selecionada a época zero, preservando o adaptador SAM3.1 anterior. Os 96 tensores de parâmetros e buffers do modelo selecionado são exatamente iguais aos do candidato anterior, época 15. Os arquivos têm metadados e contêineres diferentes; isso explica hashes de arquivo distintos e não representa mudança dos pesos. O checkpoint canônico coincide em bytes com seu espelho.

| Época | Original | Zoom 3× | Oblíqua | Óculos |
|---:|---:|---:|---:|---:|
| 0, selecionada | 88,62% | 86,51% | 87,61% | 88,21% |
| 1 | 86,19% | 83,26% | 84,22% | 85,35% |
| 2 | 86,23% | 84,11% | 84,70% | 85,49% |
| 3 | 86,94% | 84,34% | 85,28% | 86,30% |
| 4 | 86,08% | 83,67% | 84,21% | 85,27% |

Cada célula foi conferida contra as contagens de pixels dos 1.652 registros de sua condição. Na condição original, a época 3 reduziu falsos positivos de 393.302 para 369.461 pixels, mas aumentou falsos negativos de 195.000 para 314.523 pixels. Nenhuma das quatro condições atingiu a meta de Dice macro de 90%. Esses resultados descrevem a rodada completa; não isolam o efeito causal da perda em relação à nova ordem de treino e à continuação da otimização.

A retomada final contém 1.932 passos em todos os estados AdamW, exatamente quatro vezes os 483 lotes. O agendador está na época 4, com taxa 0,00002325. O aviso `scheduler.step before optimizer.step` ocorreu ao retomar depois de todos os lotes da primeira época; o marcador de chamada do otimizador pertence ao processo anterior. As contagens e a taxa registrada são consistentes com a sequência esperada. Não houve evidência de passos de treino omitidos.

Não foi repetido reconhecimento dos mesmos pesos. O último resultado medido permanece Rank-1 431/482, TAR 432/482, correto e aceito 419/482 e FMR 76/7.230. Ele não passa nos critérios registrados; nenhuma grade nova de área ou mínimo foi atribuído. Nenhum modelo foi promovido e não houve inferência no teste ou em anomalias.

[Auditoria em JSON](AUDITORIA.json). A continuação agora usa uma cabeça de correção maior, com base congelada: [relatório da nova rodada](../../sam31_residual_2026-11-05/analise_area/RELATORIO_ATUAL.md).
