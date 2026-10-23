# Fusao com separacao de pessoas entre etapas — 21/10/2026

## Desenho registrado

Experimento piloto com tres reconhecedores novos: ResNet18, ResNet50-GeM3 e ConvNeXt-Tiny com CLAHE, todos sobre recortes RGB128. A escolha limita o custo da primeira avaliacao e aproveita as arquiteturas que receberam mais peso na fusao anterior. Nao e a mesma arquitetura de oito grupos do candidato aprovado; a comparacao controlada de aprendizagem e entre pesos uniformes e aprendidos nos mesmos tres modelos novos.

O conjunto de treino original foi subdividido por pessoa, com semente 55 e sem usar escores para escolher participantes:

| Papel | Pessoas | Uso |
|---|---:|---|
| Ajuste dos encoders |147|Gradientes, estatisticas de BatchNorm e cabeca de classificacao |
| Monitoramento interno |16|Escolha dos checkpoints e parada antecipada |
| Aprendizagem da fusao |20|Escores com encoders ja congelados, sem ajuste ou selecao desses encoders |

Todas as pessoas de uma mesma identidade, incluindo os dois olhos e sessoes, ficam no mesmo grupo. Os encoders partem dos pesos oficiais do ImageNet e de projecoes/cabecas novas; nenhum peso de identidade anteriormente ajustado ao UBIPr e reaproveitado. O ajuste tem 5.554 imagens, das quais 51 recortes invalidos sao excluidos apenas do treino, mantendo 5.503 exemplos validos e 294 classes de olho.

As 482 consultas originais de validacao, de 16 outras pessoas, sao usadas somente depois de fixar os encoders e os pesos da fusao. Nenhuma nova inferencia de teste e nenhuma substituicao automatica do candidato aprovado.

## Limite importante da separacao

A U-Net atual continua congelada e ja foi treinada com imagens dos grupos internos de monitoramento e metafusao. A separacao se aplica ao ajuste dos reconhecedores de IDENTIDADE, nao ao pipeline inteiro. Nao se deve descrever esses grupos como totalmente desconhecidos de todos os componentes. A populacao de pre-treinamento do ImageNet tambem nao foi auditada por identidade. A validacao externa ao treino ja foi reutilizada no desenvolvimento anterior e nao e confirmacao independente.

## Treinamento e controles

Os tres encoders usam lotes balanceados por olho e sessao, perda angular com aquecimento da margem e contraste supervisionado. Maximo de 30 epocas, paciencia 8 apos a epoca 10. A selecao usa primeiro a TAR limpa do monitor, depois a pior TAR entre limpa/superior 10%/inferior 10%, depois o Rank-1 limpo. Cada checkpoint recebe um limiar limpo de FMR empirica no maximo 1%, mantido nas oclusoes de monitoramento. Os escores das 20 pessoas da fusao sao extraidos apenas depois de concluir todas as selecoes.

A fusao aprende tres pesos nao negativos de soma 1, compartilhados entre pessoas e condicoes. Usa episodios de 16 candidatos do mesmo lado, com uma unica foto por consulta, padronizacao por consulta, 300 passos fixos de Adam e regularizacao em direcao aos pesos iguais. A aprendizagem usa apenas as pessoas da metafusao, nas condicoes limpa e oclusao superior/inferior 10%; nao ha escolha de hiperparametros na validacao final.

Controle principal: pesos iguais sobre os mesmos tres encoders. Referencia adicional: candidato congelado de oito grupos, que tem arquitetura e quantidade de pessoas de ajuste diferentes. Portanto, ganhos sobre essa referencia nao isolariam o efeito causal da separacao.

## Progresso

Protocolo e divisao registrados antes do treinamento. Execucao concluida em aproximadamente 16 minutos, em `%TEMP%/pfc-tcc-resultados/fusao_pessoas_separadas_2026-10-21`. ResNet18 treinou 15 epocas e selecionou a 7; ResNet50 treinou 23 e selecionou a 15; ConvNeXt treinou 21 e selecionou a 13. A parada antecipada seguiu o criterio registrado, sem alterar a paciencia apos observar resultados.

As 20 pessoas da fusao forneceram 602 consultas por condicao. Foram excluidas apenas da perda da fusao 6 consultas limpas, 7 superiores e 9 inferiores por falha de extracao/disponibilidade; nenhum caso foi retirado da validacao. Foram usados 7.136 episodios de 16 candidatos. Os pesos aprendidos foram ResNet18 4,50%, ResNet50 34,84% e ConvNeXt 60,66%.

## Resultados nas 482 consultas de validacao

| Estrategia | Limpa: Rank-1 / TAR / FMR | Superior10%: Rank-1 / TAR / FMR | Inferior10%: Rank-1 / TAR / FMR |
|---|---|---|---|
| Tres novos modelos, pesos iguais |78,84 / 73,65 / 0,98%|69,71 / 61,00 / 1,19%|58,51 / 50,41 / 1,59%|
| Tres novos modelos, pesos aprendidos |79,25 / 71,99 / 0,98%|71,37 / 63,07 / 1,15%|61,00 / 50,00 / 1,09%|
| Referencia congelada, oito grupos |90,04 / 90,66 / 0,98%|80,71 / 78,01 / 1,30%|59,96 / 57,88 / 2,41%|

Todos os valores sao percentuais. Rank-1 e TAR sao criterios distintos. A fusao aprendida identificou corretamente 382/482 consultas limpas, 344/482 superiores e 294/482 inferiores, contra 380, 336 e 282 do controle uniforme. O pequeno ganho de Rank-1 limpo veio acompanhado de 8 aceitacoes genuinas a menos (347 contra 355).

Os limiares foram definidos somente na validacao limpa: 0,8788488821346696 no controle e 0,8817208492021067 na fusao aprendida, mantidos nas duas oclusoes. As 4, 4 e 7 falhas de extracao permaneceram no denominador. Nenhuma condicao da nova fusao passou simultaneamente em Rank-1/TAR de pelo menos 90% e FMR no maximo 1%.

Na comparacao pareada com os mesmos tres modelos, os ganhos de Rank-1 foram +0,41 ponto percentual no limpo, IC95% [-1,87; 2,50]; +1,66 na superior, IC95% [-0,21; 3,53]; +2,49 na inferior, IC95% [-0,84; 5,99]. Os intervalos sao descritivos, com 5.000 reamostragens por pessoa, galeria e limiares fixos, sem correcao por escolha de estrategias. Nao demonstram melhora consistente e independente.

## Conclusao e limites

O piloto NAO substitui o candidato aprovado. Separar pessoas removeu o contato direto entre ajuste dos encoders e aprendizagem da fusao, mas nao foi suficiente para atingir os criterios. Nao se pode concluir que a separacao causou a queda em relacao ao candidato de oito grupos: tambem mudaram a arquitetura, a diversidade dos componentes, as pessoas de ajuste, as sementes e a regra de selecao dos checkpoints.

Os 91,36% anteriores de identificacao no teste permanecem como resultado do candidato congelado. Nao houve nova inferencia no teste nem mudanca no percentual minimo nominal previamente relatado. A U-Net continuou exposta a pessoas internas do monitoramento e da metafusao; nao existe nesta rodada uma prova de generalizacao do pipeline inteiro para pessoas desconhecidas de todos os componentes.

O resultado direciona o proximo desenvolvimento para a qualidade da representacao e a estabilidade da normalizacao, mantendo este desenho separado para avaliar qualquer nova fusao. Nao justifica simplesmente aumentar os passos da fusao, alterar pesos com base na validacao ou treinar repetidamente ate um resultado favoravel. Qualquer ampliacao para modelos polares/transformer exigira ajuste novamente com as mesmas exclusoes de pessoas e avaliacao controlada; nao foi executada neste piloto.

## Verificacao e backup

Foram aprovados 82 testes automatizados. A verificacao independente conferiu os grupos de pessoas, as classes das cabecas de treinamento, os hashes de inicializacao ImageNet, a selecao dos checkpoints pelo historico e os contadores de BatchNorm compativeis somente com os lotes de ajuste. A recarga dos tres modelos e a reextracao de componentes nas tres condicoes reproduziram os escores com diferenca maxima zero. As duas fusoes, os limiares limpos e todas as metricas publicadas tambem foram reproduzidos.

O arquivo `C:/Users/lucaz/pfc-tcc-backups/fusao_pessoas_separadas_2026-10-21.zip` preserva 40 arquivos, incluindo os tres checkpoints, cabecas, historicos, escores de metafusao/validacao, modelo de fusao, protocolo, fontes e verificacao. Possui 237.715.590 bytes e SHA256 `846004597db8803a601ebd32cf47451791473008ea980cdb3a5da62fb110507f`. O CRC e os SHA256 individuais dos 40 membros foram conferidos contra as origens.

O backup nao inclui imagens, U-Net, pesos ImageNet ou caches de entrada, que continuam necessarios para recomputar o processamento. Os JSON legiveis estao em `outputs/fusao_pessoas_separadas_2026-10-21`; os arquivos exatos e respectivos hashes de bytes estao no ZIP fora do OneDrive. Diferencas de terminadores de linha nas copias legiveis nao alteram os valores numericos.

Foi resolvida a preservacao fora do OneDrive: `C:/Users/lucaz/pfc-tcc-backups` recebeu o incremento anterior `pf_1021T204326.zip` e o pacote `fusao_regularizada_2026-10-21.zip`, ambos com SHA256 conferido. Essa pasta sera usada para guardar os novos checkpoints ao final, sem depender da pasta temporaria.
