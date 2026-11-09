# Fechamento da melhoria do reconhecedor — 08/11/2026

A comparação encontrou ganhos localizados, mas nenhum substituto preservou todos os critérios da grade. O reconhecedor de referência foi mantido. O artigo inclui os experimentos concluídos e conserva 30 páginas de conteúdo mais 4 de referências.

## Ganho medido na grade completa

O contorno contínuo somente nos descritores polares foi escolhido na validação antes da inferência dos 13 cenários. As 486 consultas e os 7.290 pares impostores por cenário foram preservados, inclusive falhas.

| Condição | Versão | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| Sem perda adicional | Referência | 91,15% | 92,39% | 0,864% | 89,51% |
| Sem perda adicional | Candidato polar | 91,15% | 92,80% | 0,837% | 89,92% |
| Perda superior de 1% | Referência | 89,92% | 92,18% | 0,878% | 88,48% |
| Perda superior de 1% | Candidato polar | 91,15% | 92,59% | 0,796% | 89,71% |
| Perda inferior de 31% | Referência | 32,51% | 29,42% | 3,525% | 27,57% |
| Perda inferior de 31% | Candidato polar | 30,25% | 30,45% | 3,690% | 27,57% |

Com 1% de perda superior, houve seis acertos Rank-1 líquidos adicionais: +1,23 ponto percentual, com intervalo descritivo de 95% de 0,42 a 2,03 pontos, obtido por reamostragem de pessoas. A grade já foi reutilizada no desenvolvimento; esse intervalo não elimina o viés de seleção. A piora nas condições mais severas impediu a promoção geral.

[Grade completa, contagens e critérios](outputs/reconhecedor_confirmacao_2026-11-08/analise/RESULTADO_PARA_DEFESA.md). [Curva comparativa](outputs/reconhecedor_confirmacao_2026-11-08/analise/curva_comparacao_reconhecedor.png).

## SAM3.1 e treinamento final

A geometria externa do SAM3.1, mantendo o suporte e a pupila originais, elevou o Rank-1 de validação com 10% de perda inferior de 59,96% para 67,01%, reduzindo a FMR de 2,43% para 2,01%. No controle limpo, o Rank-1 caiu de 90,04% para 89,63%; por isso, a geometria não foi promovida. Misturas e ablações também falharam na regra completa.

O ajuste supervisionado polar posterior usou 1.028 fotografias de 183 pessoas de treino, em três versões por imagem. Encerrou após seis épocas sem candidato elegível. A auditoria recontou a seleção da época zero até a sexta, confirmou que as pessoas de treino não se sobrepõem às de validação ou teste e verificou igualdade bit a bit dos 108 tensores congelados do checkpoint final. Todas as 482 consultas de validação permaneceram no denominador.

[Resultado do treino polar](outputs/polar_sam31_adaptacao_entrega_2026-11-08/RELATORIO_ATUAL.md). [Auditoria dos pesos e da seleção](outputs/polar_sam31_adaptacao_entrega_2026-11-08/analise/AUDITORIA_TREINO_FINAL.json).

A média de características em quatro rotações fixas da faixa polar, combinada ao componente original com proporções de 50% e 100%, também não preservou o TAR limpo. Nenhum desses dois candidatos iniciou nova inferência de teste. O ajuste RGB anterior e suas interpolações de pesos foram igualmente rejeitados.

[Comparação das rotações](outputs/rotacoes_polares_entrega_2026-11-08/RELATORIO_ATUAL.md).

## Resultado que pode ser defendido

A referência sem perda adicional obteve 91,15% de Rank-1, 92,39% de TAR e 0,864% de FMR. Com 31% de perda do suporte anotado, o Rank-1 foi 69,34% na posição superior e 32,51% na inferior. A localização da oclusão, a textura removida e a estabilidade da segmentação influenciaram o resultado. A diferença entre 30% e 31% não demonstrou ruptura justamente em 70% de suporte nominal restante.

Esses valores descrevem esta população, esta cadeia e este denominador. O suporte originalmente anotado não é o anel estimado da exigência de qualidade da ISO. Não foi estabelecido percentual mínimo universal nem efeito causal de patologias. Os resultados clínicos anteriores e suas pequenas amostras permanecem separados.

O controle passou pelos três alvos nas estimativas pontuais, mas seus intervalos descritivos ultrapassam os limites. O artigo explicita Rank-1 de 84,79% a 95,83%, TAR de 86,25% a 96,75% e FMR de 0,514% a 1,278%. Essa incerteza impede tratar a aprovação como garantia populacional. O [guia para a defesa](outputs/defesa_consolidada_final_2026-11-08/GUIA_DEFESA.md) separa os critérios marginais, o evento conjunto e a incerteza, com respostas às principais perguntas.

## Arquivos finais

- [Artigo no modelo UniSatc](artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx): 30 páginas de conteúdo, 4 de referências, 31 referências, 12 tabelas e 5 figuras.
- [Texto de trabalho atualizado](artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md).
- [Verificação de paginação, pacote e evidências](artigo/verificacao_2026-11-08/VERIFICACAO_FINAL.json).
- [Registro de versões oficiais do SAM3.1](outputs/tecnologias_geometria_2026-11-08_1830.json).

Os treinos e a sequência condicional desta rodada terminaram. Como o último treino não selecionou candidato, a sequência encerrou sem outra grade de teste. Nenhum modelo do aplicativo ou resultado histórico foi substituído.
