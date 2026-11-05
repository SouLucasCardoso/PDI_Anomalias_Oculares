# Continuação SAM3.1 — 04/11/2026

**Encerrada em 05/11:** quatro épocas sem ganho; época zero selecionada, pesos anteriores preservados e nenhum novo mínimo. [Auditoria final](outputs/sam31_negativos_internos_2026-11-04/auditoria_fechamento_2026-11-05/RELATORIO.md). A nova rodada está em [SAM3 residual](SAM3_RESIDUAL_2026-11-05.md), com [relatório próprio](outputs/sam31_residual_2026-11-05/analise_area/RELATORIO_ATUAL.md). O texto abaixo preserva o histórico da rodada encerrada.

A avaliação anterior terminou. O candidato não atingiu os critérios sem oclusão; sua grade de área não foi iniciada e nenhum novo percentual mínimo foi atribuído. A nova rodada está em [relatório de acompanhamento](outputs/sam31_negativos_internos_2026-11-04/analise_area/RELATORIO_ATUAL.md).

| Resultado anterior, sem oclusão | Medido | Meta registrada |
|---|---:|---:|
| Identificação Rank-1 | 431/482 = 89,42% | ≥90% |
| Genuínos aceitos | 432/482 = 89,63% | ≥90% |
| Identificação correta e aceita | 419/482 = 86,93% | ≥90% |
| Falsas correspondências | 76/7.230 = 1,051% | ≤1% |

As três falhas de extração permanecem nos denominadores. O limiar congelado não foi recalibrado. O [fechamento auditado](outputs/sam31_iris_adaptacao_2026-11-03/FECHAMENTO_RECONHECIMENTO_2026-11-04.json) preserva as seis condições e as comparações pareadas. A validação já foi utilizada no desenvolvimento.

Foi executado um piloto pareado com 32 imagens de treino de pessoas distintas:

| Preparação no piloto de treino | Dice médio |
|---|---:|
| Adaptador global existente | 91,96% |
| Global com retirada da pupila proposta pelo SAM3 | 90,50% |
| Recorte local proposto pela previsão global | 89,44% |
| Recorte local com retirada da pupila | 88,14% |

Nenhuma variante foi encaminhada à validação completa. Estes números são de viabilidade em imagens de treino, não desempenho de validação ou reconhecimento. As predições foram produzidas sem consultar a anotação; a anotação entrou apenas nas métricas. [Resultados completos](outputs/sam31_refino_pupila_2026-11-04/CONCLUIDO.json).

O próximo ensaio continua os pesos selecionados na época 15, mantendo o extrator visual SAM3.1 congelado. Acrescenta peso aos pixels já anotados como não íris dentro de contornos fechados de íris. Não cria uma referência independente de pupila. Em uma amostra de 128 vistas de treino, 113 continham esses negativos internos; a mediana foi de 150 pixels.

São reutilizados os 22.040 arquivos do cache fechado, com verificação de hash a cada leitura. A semente das vistas continua 20261103; a nova semente 20261104 controla somente ordem e escolha entre os dois bancos existentes. O treino usa AdamW, taxa inicial 0,00003, até 12 épocas adicionais, lotes de 16 e parada após quatro épocas sem ganho elegível. A seleção maximiza o menor Dice das quatro condições, incluindo época zero, com proteção da condição original. Não usa resultados de identificação ou máscaras clínicas para escolher os pesos. [Protocolo do treino](outputs/sam31_negativos_internos_2026-11-04/protocolo.json).

O SAM3 oficial foi conferido novamente em 04/11: código `f1647e8d0c1d280991f4d1b7d974c2704537fe66` e checkpoint SAM3.1 na revisão `daa63191845a41281374e725f4c9e51c7a824460`. Ambos coincidem com o ambiente e cache existentes. [Consulta direta às APIs oficiais](outputs/tecnologias_atuais_2026-11-04/VERIFICACAO_OFICIAL.json).

Oito testes passaram, incluindo gradiente da perda, exclusão de pixels incertos, retomada exata de pesos/otimizador e uso da fotografia alterada no SAM3. Um treino curto real na GPU também terminou: os checkpoints canônico e espelhado têm bytes idênticos e foram recarregados estritamente. [Verificação do teste curto](outputs/sam31_negativos_internos_smoke_2026-11-04/VERIFICACAO.json). O teste curto não é promovido.

A tarefa `PFC_SAM3_Negativos_Internos_20261104` executa o fluxo local, retoma no login e evita instâncias duplicadas. Salva retomada a cada 25 lotes. Solicita vigília temporária durante o cálculo e libera ao terminar; a suspensão manual continua possível. Os processos seguem sem precisar enviar “continue” no chat enquanto o computador estiver ativo.

Se houver ganho selecionado, a avaliação de reconhecimento começa automaticamente em subprocesso separado, depois da liberação da GPU do treino. Os três controles da U-Net original são reutilizados somente após auditoria dos escores, fontes, ambiente e consultas; o novo candidato usa diretório temporário exclusivo. Se a época zero vencer, o fluxo registra ausência de melhora e encerra sem duplicar a avaliação dos mesmos pesos. [Protocolo do fluxo](outputs/sam31_negativos_internos_2026-11-04/fluxo/protocolo_fluxo.json).

A grade completa nas duas orientações depende da aprovação de Rank-1, aceitação e acerto aceito ≥90%, com FMR ≤1%, sem oclusão. O mínimo conservador também exige aprovação no estrato com referência de área definida. Todas as 482 consultas permanecem na análise principal; as dez referências vazias não recebem fração de área. O percentual é relativo à íris visível anotada, sem interpretação anatômica ou causal sobre doença.

As revisões humanas podem continuar posteriormente. Esta rodada não executa automaticamente inferência em anomalias, não utiliza o teste e não substitui o modelo em produção.

Para acompanhar: [relatório atualizado](outputs/sam31_negativos_internos_2026-11-04/analise_area/RELATORIO_ATUAL.md), [log do treino](outputs/sam31_negativos_internos_2026-11-04/execucao.log) e [estado do supervisor](outputs/sam31_negativos_internos_2026-11-04/fluxo/supervisor.json).

## Conferência de progresso e proteção operacional, 04/11 à noite

A primeira época processou as 7.716 imagens em 483 lotes; o ponto salvo confirma todos esses lotes e a perda média de treino de 0,321799. A validação da época ainda estava em andamento na conferência. A época zero reproduziu os quatro valores do candidato anterior; ela não representa ganho novo.

Às 21h00 houve uma falha de acesso ao substituir o arquivo Markdown do relatório. O supervisor anterior tratou esse erro de apresentação como falha do fluxo e encerrou o filho. Na conferência das 22h50, a tarefa estava ativa desde 22h36 e já havia retomado do ponto salvo, sem refazer os 483 lotes. Não foi determinada a causa do bloqueio de arquivo. O erro anterior foi preservado com hash em [histórico operacional](outputs/sam31_negativos_internos_2026-11-04/fluxo/controle_resiliente/historico_erros/ARQUIVAMENTO.json).

Uma entrada operacional externa foi registrada para separar o observador do processo científico. Erros ao escrever o relatório serão registrados sem encerrar treino ou reconhecimento. Três testes passaram, incluindo falha de permissão no observador, falha no log e preservação do código de erro do trabalhador científico. A entrada também foi validada com `pythonw.exe`.

Somente a ação da tarefa foi atualizada para as próximas inicializações/retomadas. A instância de treino ativa não foi interrompida: o mesmo PID foi confirmado antes e depois. Treinador, perda, avaliadores, ambiente, cache, seleção, limiar e protocolos científicos permanecem intactos. [Protocolo operacional](outputs/sam31_negativos_internos_2026-11-04/fluxo/controle_resiliente/protocolo_operacional.json) e [migração da tarefa com XML anterior preservado](outputs/sam31_negativos_internos_2026-11-04/fluxo/controle_resiliente/MIGRACAO_TAREFA.json).

Quando a nova entrada estiver em uso, o estado operacional ficará em `%TEMP%/pfc-s3-inner-20261104/supervisor_resiliente.json` e o log em `controle_resiliente.log` na mesma pasta. O relatório de acompanhamento mantém o endereço acima. A atualização operacional não altera resultados ou critérios científicos da rodada.
