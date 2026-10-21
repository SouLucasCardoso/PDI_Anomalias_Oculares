# Melhoria do reconhecedor — desenvolvimento na validação

## Hipótese e execução inicial

A íris ocupa uma região pequena da imagem periocular UBIPr. A primeira comparação mede se localizar a região de interesse antes do regressor de círculos melhora a normalização e a identificação HDBIF, em vez de aumentar imediatamente o treinamento ResNet.

Foram registradas duas variantes antes da extração: imagem inteira e caixa da referência com margem de 50% em cada eixo. Ambas mantêm a proporção da imagem, usam tons de cinza e geometria 640 × 480; imagem e máscara recebem exatamente a mesma transformação. A máscara tem padding zero, para não transformar margens em íris válida. A máscara de referência é um controle assistido; ainda não constitui fluxo automático.

O reconhecedor é a implementação pública [CVRL HDBIF](https://github.com/CVRL/OpenSourceIrisRecognition), com os pesos já registrados no projeto, normalização polar 64 × 512, cinco filtros 17 × 17 e Hamming mascarado com busca de ±16 colunas. A versão de pesos de círculos 027 difere do nome 1543 citado na configuração original, conforme documentação anterior. Não foi estabelecida independência entre a população de pré-treinamento público e a base atual.

## Avaliação e interpretação

- Somente pessoas de validação UBIPr. Nenhum novo escore de teste nesta comparação.
- Galeria: primeira captura em ordem lexicográfica da sessão 1 por olho; consultas: todas as capturas elegíveis da sessão 2. Sem seleção por qualidade ou escore.
- Falhas permanecem no denominador; cadastros inválidos não são substituídos por outra foto.
- Limiar separado por variante, calibrado para FMR empírica de até 1% na própria validação. As taxas obtidas são de desenvolvimento, sem validade de teste independente.
- A galeria de uma captura difere do centróide do extrator neural anterior. Não atribuir eventual diferença de desempenho apenas ao reconhecedor.
- Registrar largura/altura da íris em pixels originais, fração polar válida, parâmetros dos círculos e exemplos visuais, antes de interpretar resultados.

Execução retomável: `executar.ps1 validar_melhoria_normalizacao.py`. Resultados e protocolo em `outputs/melhoria_normalizacao_val_gpu_2026-10-20`; conclusão indicada por `CONCLUIDO.json`. A existência dessa pasta não significa que a execução terminou. Um protocolo alterado exige nova pasta para preservar o experimento anterior. A primeira tentativa em CPU foi interrompida durante a extração, antes de escores, para acelerar a execução na GPU; seus arquivos parciais foram preservados na pasta sem o sufixo `gpu`.

## Sequência de trabalho

1. Concluir comparação e revisar a geometria da normalização.
2. Se houver sinal útil, comparar método e recorte automático na validação, com protocolo de galeria comum antes de anunciar superioridade.
3. Se o problema persistir, investigar representação específica em polar e treinamento adequado, usando somente treino/validação para ajustes.
4. Antes de confirmar qualquer ganho ou mínimo, definir avaliação independente; o teste UBIPr anterior foi examinado e não volta a ser intocado. Uma base adicional precisa de auditoria de identidade, condições de aquisição e sobreposição com treino.

Não há necessidade imediata de credenciais, assinatura ou novos arquivos do aluno para esta primeira execução. Nenhuma promessa de atingir 90% nem de mínimo universal é estabelecida.

## Resultado desta execução

Os quatro controles terminaram. Em 482 consultas de validação, o recorte prévio elevou o HDBIF de 28,84% para 42,12% de Rank-1 e de 11,62% para 24,69% de TAR. O encoder congelado com a mesma galeria de uma captura obteve Rank-1 de 48,76% em 128 pixels e 29,67% em 256. A entrada maior não foi retreinada. Nenhuma configuração atingiu o critério de mínimo global.

O [relatório de melhoria](outputs/melhoria_normalizacao_val_gpu_2026-10-20/RELATORIO_MELHORIA.md) inclui intervalos pareados, falhas, limites de comparação e imagem real de normalização. A galeria deste controle difere do centróide usado no benchmark anterior; não misturar suas taxas. A próxima direção é controlar cadastro com múltiplas capturas e melhorar a geometria, antes de investir em novo treinamento polar.

## Atualização: cadastro múltiplo e máscaras automáticas

A comparação multicaptura foi concluída em onze variantes: o encoder automático top-3 atingiu 67,01% de Rank-1 e 59,34% de TAR, contra 50,83% e 39,42% com uma foto, no mesmo conjunto de validação. O HDBIF máximo piorou; o diagnóstico identificou cadastros com suporte polar muito pequeno dominando erros. Seis controles posteriores de qualidade foram registrados separadamente e mantiveram as 482 consultas. O suporte de 20% com HDBIF top-3 obteve 51,24% de Rank-1 e 36,31% de TAR, ainda inferior ao encoder e explicitamente exploratório. Esse percentual de suporte não é mínimo de área anatômica.

Ver [relatório multicaptura e imagens](outputs/cadastro_multicaptura_val_v2_2026-10-20/RELATORIO_CADASTRO.md), [protocolo](PROTOCOLO_CADASTRO_MULTICAPTURA_2026-10-20.md) e [controle de suporte polar](outputs/suporte_polar_val_2026-10-20/RELATORIO_SUPORTE.md). Os 24 testes passaram. Permanecem treinamento adequado à máscara automática, melhoria da geometria e confirmação independente; não foram executados novos testes de oclusão nesta atualização.

## Atualização: duas tentativas de treinamento concluídas

Foram executados ajuste angular em máscaras automáticas e ajuste angular com perda triplet e lotes balanceados. Ambos pararam após seis épocas e mantiveram o checkpoint inicial pela TAR de validação: 59,34%, com Rank-1 de 66,80% nesta execução. A linha de base difere em uma decisão Rank-1 do controle anterior após mudanças dos lotes de inferência; não houve diferença de validade das consultas. Não foi adotado novo modelo nem gerada nova curva de oclusão.

O [relatório das duas rodadas](outputs/identidade_metrica_automatica_2026-10-20/RELATORIO_TREINAMENTOS.md) e o [protocolo de adaptação](PROTOCOLO_ADAPTACAO_AUTOMATICA_2026-10-20.md) registram hipóteses, parâmetros, resultados negativos e limitações. Os 29 testes passaram. O próximo caminho deve mudar a representação ou o reconhecedor de forma fundamentada, em vez de simplesmente prolongar essas configurações.

## Atualização: TripletIris e aproximação elíptica

Foi instalado o TripletIris público do CVRL, incluindo ConvNeXt-tiny e o regressor de círculos 1543 previsto na configuração dos autores. A distância foi conferida contra o comparador oficial. Foram concluídas nove variantes circulares e seis elípticas na validação UBIPr. No controle automático top-3, o TripletIris circular obteve 38,59% de Rank-1 e 12,86% de TAR; com elipses, 28,42% e 9,54%. O modelo anterior foi preservado, sem substituição.

Os resultados são de desenvolvimento; não foi estabelecida independência da população de pré-treinamento público. A faixa polar pode incluir região externa à íris segmentada e o encaixe elíptico acompanha o contorno visível, não a anatomia escondida. Nenhuma variante cumpriu o critério de mínimo, e não foi executado novo ensaio de oclusão. Os 32 testes passaram. Ver [relatório, tabela e imagens](outputs/tripletiris_elipse_validacao_2026-10-20/RELATORIO_RECONHECEDOR_POLAR.md) e [protocolo](PROTOCOLO_RECONHECEDOR_POLAR_2026-10-20.md).

## Atualização: treinamento polar próprio e fusões

Continuação posterior concluída: o encoder polar denso terminou 29 épocas, seleção na 21. Sua fusão fixa chegou a 78,84% de Rank-1 e 68,26% de TAR, sem melhora consistente frente à referência de 79,88% e 68,05%. Uma transformação linear ajustada só nas identidades de treino levou a fusão a 78,22% e 65,98%. Mantidos os resultados negativos e os pesos anteriores; 39 testes aprovados e recarregamento do checkpoint reproduzindo os escores exatamente. [Relatório da continuação](outputs/fusao_densa_val_2026-10-20/RELATORIO_CONTINUACAO.md).

O novo encoder polar foi treinado por 28 épocas, com seleção na 20, usando apenas pessoas de treino e máscaras automáticas. Isoladamente, atingiu 58,71% de Rank-1 e 49,59% de TAR na validação. O controle clássico de fase e a correspondência espacial foram executados separadamente. A fusão RGB/polar com pesos iguais atingiu 76,35% e 67,63%; a fusão de três vias incluindo descritor espacial atingiu 79,88% e 68,05%, com FMR de 0,99%. Os pesos de fusão não foram otimizados, mas a normalização de impostores e os limiares usam a validação, já repetidamente examinada.

Os 37 testes passaram e os parâmetros anteriores foram preservados. O candidato de três vias ainda está a 10,12 pp de Rank-1 e 21,95 pp de TAR do critério original. Não há nova curva de oclusão ou mínimo aprovado. O aluno confirmou **UBIPr como base principal e foto única de consulta**; várias imagens podem compor o cadastro, conforme o protocolo existente. Ver [relatório completo](outputs/fusao_espacial_val_2026-10-20/RELATORIO_AVANCO_POLAR_FUSAO.md) e [protocolo](PROTOCOLO_TREINO_POLAR_2026-10-20.md).
