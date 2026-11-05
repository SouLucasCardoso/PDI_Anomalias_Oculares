# Preparação do piloto com anomalias — 03/11/2026

**Estado atualizado em 04/11:** a avaliação anterior foi concluída sem aprovação para a grade de área. A nova rodada com SAM3.1 está em execução: [relatório atual](outputs/sam31_negativos_internos_2026-11-04/analise_area/RELATORIO_ATUAL.md), [resultados e parâmetros](CONTINUACAO_SAM3_2026-11-04.md). O conteúdo abaixo descreve a preparação e o histórico da rodada anterior.

O projeto tem agora um treino supervisionado com características visuais do SAM3.1, um editor de referências humanas e avaliações encadeadas. **Os critérios mínimos ainda não foram atingidos.** O estado que se atualiza durante a execução está em [PRONTIDAO.md](outputs/prontidao_anomalias_2026-11-03/PRONTIDAO.md).

**Atualização de 04/11:** o treino completou 20 épocas e selecionou a época 15. A avaliação de reconhecimento foi retomada após reconciliar a serialização da cópia do checkpoint, com igualdade exata de todos os tensores e preservação do arquivo anterior. A auditoria, os ganhos de segmentação, a retomada e a inspeção das duas primeiras referências clínicas estão em [POS_TREINO_SAM3_2026-11-04.md](POS_TREINO_SAM3_2026-11-04.md).

## Resultado que motivou a nova adaptação

A rodada anterior terminou as 30 épocas. Seu candidato final melhorou a tolerância ao zoom e à oclusão inferior, mas prejudicou a identificação sem oclusão:

| Validação, 482 consultas | U-Net original | Candidato diverso, época 30 |
|---|---:|---:|
| Identificação correta, Rank-1 | 90,04% | 86,10% |
| Genuínos aceitos, TAR | 90,66% | 85,68% |
| Correto e aceito simultaneamente | 88,38% | 83,40% |
| Falsas correspondências, FMR | 0,982% | 1,203% |

O candidato diverso não substituiu o reconhecedor. Nenhum novo mínimo de área foi atribuído. As contagens completas, as seis condições pareadas e os intervalos por pessoa estão no [relatório da rodada concluída](outputs/segmentacao_area_2026-10-27/analise/RELATORIO_ATUAL.md).

## Treino SAM3.1 em execução

O extrator visual usa o código oficial SAM3 na revisão `f1647e8d0c1d280991f4d1b7d974c2704537fe66` e os pesos SAM3.1 com SHA256 `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`. As versões e restrições de compatibilidade estão em [TECNOLOGIAS_ATUAIS_2026-11-03.md](TECNOLOGIAS_ATUAIS_2026-11-03.md).

O backbone SAM3.1 permanece congelado. Um decodificador supervisionado combina RGB e mapas visuais SAM3 para prever as quatro classes nativas do UBIPr. Isso é uma adaptação de íris com SAM3; não é ajuste integral do SAM3 nem uso da máscara textual original como referência. A projeção SAM começa nula, reproduzindo o controle RGB antes de aprender. A perda acrescenta penalização de falsos positivos; a classe de fundo do UBIPr inclui a pupila, sem inventar uma anotação separada dela.

São 7.716 imagens de treino e 1.652 de validação, com pessoas separadas. O teste não recebe nova inferência. Duas versões fixas por imagem de treino, original e diversificada, alternam de forma determinística entre épocas. A validação mede original, zoom3×, vista oblíqua e óculos simulados. Os aumentos sintéticos não demonstram cobertura de todas as poses e óculos reais.

A primeira etapa calcula 22.040 mapas visuais em disco, aproximadamente 70 GB, para não repetir o backbone grande a cada época na GPU de 6 GB. Depois são executadas até 20 épocas, com recuperação a cada 25 lotes e parada após seis épocas sem melhora. A seleção maximiza o menor Dice macro entre as quatro condições, protegendo a condição original contra queda superior a 0,5 ponto percentual em relação à época zero. As referências clínicas e os escores de reconhecimento não selecionam os pesos. Se a época zero continuar sendo a melhor, o resultado deverá ser interpretado como ausência de ganho selecionado com a adaptação.

Um ensaio de integração com quatro imagens por partição completou extração real na GPU, treino e validação. Ele verifica o funcionamento; seu resultado é marcado como `development_smoke_only` e não pode liberar o piloto. O [protocolo completo](outputs/sam31_iris_adaptacao_2026-11-03/protocolo.json) conserva fontes, ambiente, checkpoint e parâmetros da rodada real.

## Sua primeira revisão

Você confirmou que fará a primeira revisão. O editor está disponível em **[http://127.0.0.1:8766/](http://127.0.0.1:8766/)**, também aberto no navegador integrado do VS Code. O lote contém 30 fotografias normais de 30 pessoas e todas as seis fotografias de desenvolvimento com diagnóstico envolvendo íris, pertencentes a cinco pessoas. O conjunto externo foi excluído; as pessoas dos casos com anomalias não entram nos 30 controles normais. Uma primeira revisão já estava registrada nesta verificação; o contador atualizado aparece no relatório de prontidão.

1. Informe quem está revisando. Para uma referência nova, use “Iniciar com fundo 0” apenas se todo o fundo puder ser considerado conhecido; a classe incerta está disponível para regiões duvidosas.
2. Marque a íris visível, a pupila e os oclusores com pincel ou polígono. A pupila não faz parte da íris. Preserve como incerto aquilo que não conseguir delimitar.
3. Confira as opções de visibilidade e use “Concluir minha primeira revisão” ao terminar. “Salvar rascunho” preserva o trabalho sem tratá-lo como referência concluída.

As máscaras são salvas na resolução da fotografia, com índices de classe, nome do revisor, data e hashes. Cada salvamento cria uma versão; as revisões anteriores permanecem preservadas em [revisoes](outputs/revisao_clinica_2026-11-03/revisoes/). Não há preenchimento de referência por previsão do modelo. A primeira revisão do usuário fica identificada separadamente de uma confirmação anatômica por especialista.

## Critérios registrados antes das novas avaliações

Estes são **alvos de engenharia propostos para o projeto**, não um padrão clínico validado. O [arquivo de critérios](criterios_prontidao_anomalias.json) distingue a prontidão para segmentar casos com anomalias da prontidão para estudar identificação.

| Etapa | Requisitos |
|---|---|
| Segmentação UBIPr | Dice macro ≥90% em cada uma das quatro condições, com todas as 1.652 imagens de validação. |
| Controles clínicos normais | 30 referências concluídas de pelo menos 15 pessoas; ao menos 20 pupilas visíveis anotadas; todas as 30 referências com íris visível; Dice macro ≥90%, percentil 10 ≥75%, nenhum caso com Dice <50%; vazamento médio sobre a pupila ≤2%; incerteza na região de íris/pupila ≤5%. |
| Identificação | Mesmo checkpoint, limiar e reconhecedores fixados: Rank-1, TAR e acerto aceito simultâneo ≥90%; FMR ≤1%; todas as falhas mantidas nos denominadores. |

O piloto exploratório de **segmentação** depende das duas primeiras linhas. O estudo **biométrico** com anomalias também depende da terceira. O requisito de acerto aceito simultâneo é adicional nesta nova preparação e não altera retroativamente o critério da rodada anterior.

## Execução automática e evidências

Três tarefas locais estão registradas: `PFC_SAM3_Iris_Adaptacao_20261103` para o treino; `PFC_Iris_Revisao_Clinica_20261103` para o editor; `PFC_SAM3_Prontidao_Anomalias_20261103` para acompanhar referências e executar as avaliações seguintes. Elas retomam no login do mesmo usuário e evitam instâncias duplicadas. O treino pede ao Windows que permaneça ativo durante sua execução; suspensão manual ou desligamento interrompem o trabalho e exigem retomada.

O acompanhamento encadeia as seguintes etapas após o treino:

1. Produzir previsões dos 30 controles normais a partir das fotografias, sem consultar as referências humanas durante a inferência.
2. Reexecutar os controles original/superior10%/inferior10% com U-Net original e novo candidato no mesmo ambiente atualizado. As 482 consultas, 16 candidatos do lado informado, nove componentes e limiar congelado permanecem fixos.
3. Se o novo candidato passar na identificação sem oclusão, avaliar perdas de 1%, 2%, 5%, 10%, 20%, …, 90%, nas duas orientações, inclusive após falhas intermediárias. O mínimo é descritivo do prefixo aprovado na grade registrada, sem interpolação.
4. Atualizar as métricas clínicas conforme as revisões forem concluídas. Somente após aprovação da segmentação e dos controles normais, produzir o piloto das seis imagens com anomalias. Não há promoção automática do modelo ao reconhecedor.

Na avaliação de área, tanto RGB quanto SAM3 recebem a fotografia já alterada. A anotação original define apenas os pixels da intervenção e sua quantidade. Segmentação e geometria são recalculadas. O teste automatizado dessa ligação verificou que o extrator SAM recebe a consulta alterada e conserva todos os registros.

O [protocolo do fluxo](outputs/prontidao_anomalias_2026-11-03/protocolo_fluxo.json) congela fontes e versões antes das avaliações. Os resultados ficam em [sam31_iris_adaptacao_2026-11-03](outputs/sam31_iris_adaptacao_2026-11-03/) e o [estado legível por máquina](outputs/prontidao_anomalias_2026-11-03/estado.json) informa cada requisito pendente. O acompanhamento atual dura até 23 horas por execução; o treino e a avaliação têm seus próprios estados de recuperação.

## Continuação independente das revisões clínicas

Você autorizou continuar e poderá fazer a revisão manual posteriormente. A busca de área no UBIPr usa as referências já existentes dessa base; a falta de revisões clínicas concluídas não bloqueia o treino, a identificação ou a grade de oclusão. O piloto clínico mantém seus requisitos separados.

O novo [relatório de treino, reconhecimento e área](outputs/sam31_iris_adaptacao_2026-11-03/analise_area/RELATORIO_ATUAL.md) mostra o progresso dos mapas SAM3 e das épocas, audita as matrizes de reconhecimento quando forem produzidas e calcula intervalos descritivos de 95% por pessoa. Enquanto não houver escores do candidato final, não há novos intervalos ou mínimo de área. A tarefa local `PFC_SAM3_Analise_Area_20261103` atualiza esse relatório a cada minuto, sem inferência ou uso da GPU.

O observador confere as 482 consultas, os 16 candidatos, os protocolos, os hashes, as decisões e o número exato de pixels ocultados. Também calcula a fronteira comum às duas orientações. Uma grade parcial, aprovação isolada após uma reprovação ou mudança de evidências não pode gerar um mínimo válido. Três testes passaram: arredondamento exato e referências vazias; grade incompleta e recuperação não monotônica; reprodução de escores com retenção de falhas e detecção de alterações, sem arquivos de revisão clínica. As fontes do treino e do fluxo de avaliação continuam preservadas.

Durante a continuação, os nove componentes de reconhecimento passaram por uma verificação em CPU com duas fotografias de validação predeterminadas. As entradas e saídas foram exatamente iguais nos ambientes anterior e atualizado. A [comparação registrada](outputs/tecnologias_atuais_2026-11-03/COMPARACAO_CPU_IDENTIDADE.json) verifica compatibilidade; não calcula taxa de identificação, não avalia o decodificador SAM3 e não substitui a comparação completa em CUDA. A GPU permaneceu dedicada à extração dos mapas SAM3.

## Conferência da área anotada e análise de sensibilidade

A [caracterização de referência](outputs/sam31_iris_adaptacao_2026-11-03/grade_area_ubipr/REFERENCIA_AREA.md) conferiu as 482 consultas de 16 pessoas e 32 olhos, com 241 consultas de cada lado. Há **472 referências com pixels anotados como íris e 10 referências vazias**. A tabela de pixels mínimos, medianos e máximos por percentual usa as 472 referências positivas; o CSV preserva todas as 482 consultas e identifica os denominadores indefinidos.

Entre as referências positivas, a área original varia de 31 a 28.952 pixels, com mediana de 7.054. Portanto, o mesmo percentual representa quantidades diferentes de pixels entre fotografias. São pixels na resolução nativa, antes do redimensionamento da entrada do modelo. Não são pixels do mapa visual SAM3 nem uma medida de área anatômica.

Uma referência vazia não comprova ausência anatômica de íris. Nesses dez casos, a intervenção baseada na anotação mantém a fotografia inalterada e a fração de área fica indefinida. **As dez consultas continuam no resultado primário**, conforme o protocolo original; não houve exclusão, recalibração ou alteração do treino. As contagens das 482 referências e o arredondamento da perda de 10% foram reproduzidos contra as evidências anteriores nas duas orientações, totalizando 964 conferências de intervenção.

Foi registrada, antes dos escores do novo candidato, uma [análise secundária de sensibilidade](outputs/sam31_iris_adaptacao_2026-11-03/sensibilidade_referencia/RELATORIO_ATUAL.md). Ela mostra identificação no conjunto completo, nas 472 consultas com referência definida e nas dez sem referência de íris. As falhas permanecem nos denominadores de cada grupo. O grupo sem referência não recebe percentual de área.

Além do resultado primário registrado, a interpretação conservadora de um mínimo exige aprovação tanto no conjunto completo quanto no grupo com área definida, no prefixo completo da grade e nas duas orientações. A análise não seleciona checkpoint, não modifica o critério original e não promove o modelo. Dois testes passaram, incluindo um caso em que as referências indefinidas elevam o resultado geral acima de 90%, embora o grupo com área definida fique abaixo dessa meta.

A tarefa `PFC_SAM3_Sensibilidade_Area_20261103` executa uma leitura curta dos resultados a cada cinco minutos por 48 horas e também no login. Ela não usa GPU, não executa inferência e não depende das revisões clínicas. Enquanto o novo candidato não produzir escores auditados, o relatório mostra a análise como pendente.

O percentual de área é relativo à íris visível originalmente anotada. A validação já foi usada no desenvolvimento e não é confirmação cega. Seis fotografias com anomalias permitem inspeção exploratória, mas não estabelecem efeito causal, percentual anatômico ou perda de identificação pela doença: isso exige referências revisadas e capturas comparáveis do mesmo olho com controles de identidade.
