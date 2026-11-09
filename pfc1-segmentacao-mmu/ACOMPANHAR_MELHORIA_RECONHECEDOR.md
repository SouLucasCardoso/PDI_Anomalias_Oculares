# Melhoria do reconhecedor para a entrega

**Atualização final:** a [grade densa de todos os inteiros de 1% a 31%](RESULTADO_GRADE_DENSA_2026-11-08.md) terminou com 63 condições por versão, auditoria e artigo atualizado. O [acompanhamento da grade](ACOMPANHAR_GRADE_1A31.md) contém os links finais. O texto abaixo documenta a etapa anterior, com 13 condições.

Prioridade confirmada: reconhecimento sob oclusões para o artigo. Rodada encerrada em 08/11/2026. Os modelos do aplicativo e os resultados históricos foram preservados.

## Situação final

O [relatório consolidado](RESULTADO_MELHORIA_RECONHECEDOR_2026-11-08.md) reúne o ganho localizado e as reprovações. Nenhum candidato preservou todos os critérios da grade; o reconhecedor de referência foi mantido. O artigo foi atualizado com os ensaios concluídos e continua com 30 páginas de conteúdo e 4 de referências.

O [guia para a defesa](outputs/defesa_consolidada_final_2026-11-08/GUIA_DEFESA.md) traz as contagens, os intervalos descritivos e respostas sobre área mínima, 70%, SAM3.1 e patologias. A consolidação conferiu os 13 cenários sem novo ajuste ou inferência. A aprovação pontual não constitui garantia populacional; os intervalos de incerteza agora estão explícitos no artigo.

- [Estado final do treino](outputs/polar_sam31_adaptacao_entrega_2026-11-08/estado.json).
- [Log da preparação e do treino](outputs/polar_sam31_adaptacao_entrega_execucao.log).
- [Histórico por época](outputs/polar_sam31_adaptacao_entrega_2026-11-08/historico.json).
- [Estado da sequência automática](outputs/polar_sam31_adaptacao_entrega_2026-11-08/FECHAMENTO.json).
- [Plano registrado](outputs/polar_sam31_adaptacao_entrega_2026-11-08/PLANO_FECHAMENTO.json).
- [Auditoria final dos pesos e da seleção](outputs/polar_sam31_adaptacao_entrega_2026-11-08/analise/AUDITORIA_TREINO_FINAL.json).

O último ajuste polar preparou 1.028 fotografias de treino, cada uma sem alteração e com oclusão superior e inferior, totalizando 3.084 entradas. Treinou somente o último bloco e a projeção do encoder polar, usando o encoder original como professor. Encerrou após seis épocas sem ganho elegível, mantendo todas as 482 consultas de validação. A auditoria verificou a separação de pessoas e os 108 tensores congelados.

A sequência automática encerrou com o estado `concluido_sem_candidato_aprovado`, sem iniciar outra grade de teste. A comparação adicional de quatro rotações polares também terminou sem candidato aprovado. Não há treino desta rodada aguardando outra mensagem ou ainda em execução.

## Resultados já concluídos

| Experimento | Resultado e decisão |
|---|---|
| Contorno contínuo em todos os nove descritores | Melhor Dice, mas Rank-1 limpo de validação de 90,04% para 89,00%. Rejeitado para reconhecimento. |
| Ajuste supervisionado do encoder RGB | Nenhuma época superou os critérios; preservada a época zero. Interpolações de pesos também não passaram. |
| Contorno contínuo somente no ramo polar | Na grade completa, com 1% de oclusão superior, Rank-1 de 89,92% para 91,15%, TAR de 92,59% e FMR de 0,796%. Houve piora em outras condições; não aprovado como substituto geral. |
| SAM3.1 somente na geometria externa polar | Na validação com 10% de perda inferior, Rank-1 de 59,96% para 67,01% e FMR de 2,43% para 2,01%. Houve queda no controle limpo; não promovido. |
| Misturas e ablações da geometria SAM3.1 | Nenhuma variante preservou todos os critérios de validação. Não executaram novo teste. |
| Ajuste supervisionado polar com geometria SAM3.1 | Seis épocas sem candidato elegível; pesos congelados e seleção auditados. |
| Média de quatro rotações polares | As duas proporções fixas não preservaram o TAR limpo. Sem nova inferência de teste. |

O [resultado auditado da grade completa](outputs/reconhecedor_confirmacao_2026-11-08/analise/RESULTADO_PARA_DEFESA.md) informa os ganhos e as perdas em todas as 13 condições. A [avaliação direta da geometria SAM3.1](outputs/sam31_geometria_identidade_2026-11-08/RELATORIO_ATUAL.md) mantém todas as 482 consultas de validação, incluindo falhas. O [ajuste RGB encerrado](outputs/reconhecedor_oclusao_entrega_2026-11-08/analise/RESULTADO.md) preserva a seleção original e a auditoria da conversão do metadado do checkpoint.

## Como interpretar

O limiar e os pesos de fusão permanecem fixos. Para selecionar uma nova época, exigimos preservar Rank-1 e TAR limpos, FMR limpo de no máximo 1%, não aumentar a FMR nas duas condições ocluídas e elevar a média do evento correto e aceito. A aprovação relativa de um candidato e o atendimento absoluto de todos os alvos são informados separadamente.

As oclusões usam 1%, 5%, 10%, 20%, 30% e 31% do suporte de íris originalmente anotado e são aplicadas à fotografia antes de segmentar. Esse denominador não é o anel estimado do requisito de qualidade da ISO. Os dados de validação e teste foram reutilizados no desenvolvimento: os resultados são descritivos, não uma confirmação independente nem um mínimo universal ou clínico de área.
