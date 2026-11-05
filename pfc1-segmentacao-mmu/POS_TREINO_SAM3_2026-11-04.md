# Continuação após o treino SAM3.1 — 04/11/2026

**Atualização de encerramento:** a identificação terminou e reprovou o candidato sem oclusão (Rank-1 89,42%; FMR 1,051%). Nenhum novo mínimo de área foi atribuído. O piloto de quatro refinamentos também terminou, sem variante elegível. Uma nova continuação supervisionada foi iniciada: [resultados e próxima rodada](CONTINUACAO_SAM3_2026-11-04.md), [acompanhamento atual](outputs/sam31_negativos_internos_2026-11-04/analise_area/RELATORIO_ATUAL.md). As seções abaixo preservam a descrição das etapas anteriores.

As 20 épocas foram concluídas. A regra registrada selecionou a **época 15**, com checkpoint SHA256 `cf8a718e0160c14408d1533445ff611b00a79c75d2c0fd07fb7540150e59db99`. A auditoria reproduziu a seleção e recalculou Dice/IoU a partir das contagens de pixels de todas as 21 avaliações, incluindo a época zero, nas quatro condições de 1.652 imagens cada.

| Condição | Época zero | Candidato, época 15 | Ganho de Dice |
|---|---:|---:|---:|
| Original | 86,09% | 88,62% | +2,53 pp |
| Zoom 3× | 83,18% | 86,51% | +3,34 pp |
| Oblíqua | 85,54% | 87,61% | +2,07 pp |
| Óculos simulados | 85,18% | 88,21% | +3,03 pp |

**A meta de 90% nas quatro condições ainda não foi atingida.** A [auditoria do treino](outputs/sam31_iris_adaptacao_2026-11-03/auditoria_treino_2026-11-04/RELATORIO.md) apresenta contagens de falhas, estratos de referência e intervalos descritivos por pessoa. Os intervalos usam a mesma validação da seleção; não constituem confirmação independente. O ramo RGB também foi reajustado, portanto o ganho não isola a contribuição causal das características SAM3 em relação a mais épocas ou à perda adicional.

## Cópia do checkpoint reconciliada

A primeira avaliação pós-treino parou no teste de hash. O arquivo canônico `melhor_modelo.pt` correspondia ao hash declarado no resultado final; a cópia `candidato_epoca_15.pt` havia sido gravada por uma segunda chamada a `torch.save`, com outro nome.

A comparação confirmou igualdade exata dos **258 tensores**, dos **470 valores não tensoriais**, do otimizador, do agendador e do histórico. Todos os **264 conteúdos do ZIP**, após remover o diretório raiz do nome de cada entrada, também eram idênticos. Os nomes internos `melhor_modelo.pt` e `candidato_epoca_15.pt` explicavam os hashes diferentes dos contêineres.

A cópia anterior foi preservada em `auditoria_checkpoint/candidato_epoca_15_SERIALIZACAO_ORIGINAL.pt`. Depois foi substituída por uma cópia binária do arquivo canônico. O hash do espelho agora coincide com o que já estava registrado. **Nenhum peso, histórico, escolha de época ou hash declarado no resultado final foi alterado.**

- [Comparação antes da correção](outputs/sam31_iris_adaptacao_2026-11-03/auditoria_checkpoint/COMPARACAO_ANTES_REPARO.json).
- [Registro da reconciliação](outputs/sam31_iris_adaptacao_2026-11-03/auditoria_checkpoint/RECONCILIACAO.json).

As fontes congeladas do treino e da avaliação permanecem iguais. Em uma futura versão do treinador, o espelho deve receber os bytes do arquivo já serializado, por cópia atômica, em vez de serializar novamente o mesmo estado sob outro nome. A fonte da rodada atual foi preservada para manter a proveniência.

## Avaliação retomada

A tarefa `PFC_SAM3_Prontidao_Anomalias_20261103` foi retomada em 04/11, com um supervisor externo ao código científico. O XML anterior da tarefa foi exportado antes de trocar somente a entrada de execução pelo supervisor. O mesmo avaliador, os mesmos argumentos, pesos, limiar e fontes do protocolo continuam sendo usados.

O supervisor solicita vigília temporária enquanto houver cálculo de identidade ou piloto elegível pendente e libera a solicitação quando esse cálculo termina. Ele não mantém o computador acordado apenas aguardando referências humanas. Três testes passaram: preservação do código de erro e liberação de energia; encerramento do filho e liberação após exceção do supervisor; ausência de vigília ao aguardar revisões. A suspensão manual continua possível. O observador de resultados foi renovado para acompanhar toda a avaliação.

As etapas do fluxo são:

1. Prever os 30 controles clínicos normais sem consultar máscaras humanas durante a inferência. **Concluído**, com hashes de todas as previsões preservados.
2. Reexecutar os controles U-Net original e novo adaptador SAM3, nas condições original, oclusão superior de 10% e inferior de 10%, mantendo as 482 consultas e os nove componentes de identidade.
3. Se o novo candidato passar sem oclusão no critério registrado, avaliar toda a grade de área nas duas orientações. Caso contrário, registrar ausência de novo mínimo.
4. Apresentar os resultados gerais e a análise secundária das 472 consultas com referência de área definida. As dez referências vazias permanecem no resultado primário.

O [relatório principal](outputs/sam31_iris_adaptacao_2026-11-03/analise_area/RELATORIO_ATUAL.md) e a [análise de sensibilidade](outputs/sam31_iris_adaptacao_2026-11-03/sensibilidade_referencia/RELATORIO_ATUAL.md) se atualizam com os resultados concluídos. As revisões clínicas podem continuar depois; não bloqueiam a avaliação UBIPr ou a grade biométrica condicional.

## Controle reexecutado no ambiente atualizado

O primeiro controle completo preservou 434 identificações corretas em 482 consultas e 426 acertos aceitos. Houve uma mudança de aceitação genuína e uma de falsa correspondência em relação aos resultados históricos: agora são 436 genuínos aceitos e 72 falsas correspondências em 7.230 comparações, com quatro falhas de extração mantidas.

O máximo de diferença no escore fundido foi aproximadamente 0,0260; a média absoluta foi 0,00108. Não foi isolada a causa entre ambiente, preparação e execução numérica. O teste anterior de duas imagens em CPU não garantia equivalência da avaliação completa em CUDA. Por isso os controles estão sendo reexecutados no mesmo ambiente do novo candidato, sem recalibrar o limiar. A [comparação das matrizes e dos componentes](outputs/sam31_iris_adaptacao_2026-11-03/auditoria_treino_2026-11-04/REPLAY_CONTROLE_ATUALIZADO.json) preserva as diferenças.

## Inspeção clínica preliminar

As duas primeiras revisões de controles normais já permitem uma inspeção pareada com as previsões preservadas. São referências iniciais do usuário, com regiões incertas, sem confirmação por especialista e sem representatividade clínica populacional.

| Controle | Dice nos pixels conhecidos | Pupila incluída como íris | Incerteza na região de íris/pupila |
|---|---:|---:|---:|
| P0005 | 88,40% | 64,69% | 38,49% |
| P0007 | 78,34% | 71,89% | 15,33% |

A [prancha de comparação](outputs/sam31_iris_adaptacao_2026-11-03/clinica/inspecao_revisada_2026-11-04/comparacao_revisada.png) foi gerada com todas as primeiras revisões normais concluídas, sem escolher os melhores escores. A imagem completa, a referência, a previsão e os erros nos pixels conhecidos estão lado a lado. O zoom é apenas apresentação e não entrou na inferência. Os dados e hashes estão no [relatório da inspeção](outputs/sam31_iris_adaptacao_2026-11-03/clinica/inspecao_revisada_2026-11-04/RELATORIO.md).

A inclusão indevida da pupila persiste. Os limites clínicos de vazamento médio de 2%, incerteza de 5% na região anotada e quantidade de referências ainda não foram satisfeitos. **O piloto com anomalias não foi liberado nem houve promoção ao reconhecedor.** A curva de área UBIPr, caso aprovada pela identificação, continua sendo um experimento controlado de área visível anotada, sem conclusão causal sobre doença.
