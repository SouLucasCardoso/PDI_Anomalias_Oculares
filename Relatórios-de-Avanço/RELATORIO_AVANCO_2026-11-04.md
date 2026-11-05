# Relatório de avanço — 4 de novembro de 2026

**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Dia:** quarta-feira  
**Registro retrospectivo:** elaborado em 05/11/2026, com distinção entre resultados concluídos no dia e rodadas apenas iniciadas.

## Objetivo do dia

Auditar o treinamento SAM3.1, verificar seu efeito sobre identificação e investigar refinamentos de segmentação sem alterar o reconhecedor ou recalibrar o limiar nos resultados observados.

## Treino concluído e auditado

Foram concluídas 20 épocas; a regra registrada selecionou a época **15**, com checkpoint SHA-256 `cf8a718e0160c14408d1533445ff611b00a79c75d2c0fd07fb7540150e59db99`.

| Condição de validação | Dice inicial | Dice selecionado |
|---|---:|---:|
| Original | 86,09% | 88,62% |
| Zoom 3× | 83,18% | 86,51% |
| Oblíqua | 85,54% | 87,61% |
| Óculos sintéticos | 85,18% | 88,21% |

Cada condição usa 1.652 imagens. A meta de 90% em todas as condições não foi atingida. A seleção foi reproduzida a partir das contagens; o ganho não isola a contribuição causal do SAM de mudanças no treino do ramo RGB e na perda.

Uma divergência de hash entre duas serializações do mesmo estado foi investigada. A igualdade dos tensores e demais estados foi conferida; a cópia foi reconciliada com o arquivo canônico e a evidência anterior preservada.

## Reconhecimento e refinamentos

| Condição limpa — 482 consultas | Resultado |
|---|---:|
| Rank-1 correto | 431/482 — 89,42% |
| Aceitação genuína | 432/482 — 89,63% |
| Correto e aceito simultaneamente | 419/482 — 86,93% |
| Falsas correspondências | 76/7.230 — 1,051% |

As três falhas de extração foram mantidas. O candidato reprovou sem oclusão: a grade completa de área não foi aberta e nenhum novo mínimo foi atribuído. A validação já reutilizada não é confirmação independente.

Foi executado um piloto de viabilidade com 32 imagens de treino, sem usar anotação para construir as previsões. O Dice médio foi 91,96% no adaptador global, 90,50% ao retirar a pupila proposta pelo SAM, 89,44% no recorte local e 88,14% combinando recorte local e retirada da pupila. Nenhuma variante foi encaminhada à validação completa. Esses valores de treino não são taxas de reconhecimento.

As duas primeiras máscaras clínicas revisadas pelo usuário foram inspecionadas separadamente. A revisão permanece parcial e não autoriza uma conclusão sobre patologias.

## Código e operação

- Implementação da perda com peso adicional para negativos internos já anotados; não foram criados rótulos anatômicos independentes de pupila.
- Início, às 20h30, da continuação supervisionada da época 15, usando o mesmo cache fechado e a revisão oficial novamente conferida. Oito testes direcionados e um teste curto real na GPU foram registrados.
- Implementação de retomada de pesos/otimizador e salvamento por lotes, prevenção de duplicação de processos e execução persistente.
- Correção operacional para que falha de escrita do relatório não encerre o trabalhador científico. A alteração separou observador e treino; preservou fontes, ambiente e parâmetros da instância ativa.

A continuação com negativos internos **terminou em 05/11**, após quatro épocas sem ganho elegível. Não é apresentada como concluída neste dia.

## Registros técnicos

- [Auditoria e resultados pós-treino](../pfc1-segmentacao-mmu/POS_TREINO_SAM3_2026-11-04.md).
- [Continuação e histórico operacional](../pfc1-segmentacao-mmu/CONTINUACAO_SAM3_2026-11-04.md).
- [Auditoria do treinamento](../pfc1-segmentacao-mmu/outputs/sam31_iris_adaptacao_2026-11-03/auditoria_treino_2026-11-04/RELATORIO.md).
- [Piloto de refinamento](../pfc1-segmentacao-mmu/outputs/sam31_refino_pupila_2026-11-04/RELATORIO.md).
- [Perda supervisionada](../pfc1-segmentacao-mmu/perda_negativos_internos.py).

O avanço consistiu em medir e rejeitar hipóteses que não atenderam aos critérios, além de tornar a execução mais recuperável. Não houve promoção de um novo reconhecedor ou demonstração de mínimo clínico.
