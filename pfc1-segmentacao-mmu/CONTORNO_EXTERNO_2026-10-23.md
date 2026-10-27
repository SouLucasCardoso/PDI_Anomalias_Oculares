# Correção do contorno externo em 23 de outubro de 2026

A rodada produziu uma geometria mais estável e melhorou a identificação na oclusão inferior de 10%, mas **não produziu um substituto aprovado para o reconhecedor original**. A condição limpa e a superior pioraram. Não houve avaliação no teste, alteração do limiar original ou novo mínimo de área.

## Método e separação dos dados

Foi implementado um módulo residual com aproximadamente 264 mil parâmetros. Ele recebe 2.048 características do encoder da U-Net congelada e cinco parâmetros da elipse externa atual. As coordenadas referem-se à fotografia inteira; a conversão entre elipse e vetor considera a diferença entre largura e altura, sem usar a caixa do recorte como sistema de referência.

A preparação considerou as 7.716 imagens da partição original de treino. A supervisão geométrica exigiu uma elipse de referência válida e um contorno predito utilizável nas três condições. Permaneceram **6.623 fotos de 167 pessoas para ajuste e 951 fotos de 16 pessoas para monitoramento**. Foram excluídas 142 fotos somente dessa etapa geométrica: 133 do ajuste e nove do monitor. As condições foram limpa, perda superior de 10% e perda inferior de 10%, aplicadas nos pixels nativos antes do redimensionamento.

As pessoas do ajuste e do monitor são distintas, mas o monitor já foi reutilizado em outros experimentos e foi visto pela U-Net original. Os alvos são aproximações derivadas das máscaras visíveis, sem anotação anatômica independente. A seleção geométrica não constitui confirmação de generalização biométrica.

## Duas formulações registradas

A primeira formulação tentou aproximar a elipse externa da anotação original, acrescentando consistência entre as três condições. O treino encerrou após quatro épocas. Embora o erro sob oclusão tenha diminuído, todas as épocas treinadas violaram o limite de aumento de 5% do erro limpo. Foi selecionada a época zero, que mantém a referência; nenhuma inferência biométrica foi executada para esse primeiro candidato.

A segunda formulação usou a **elipse predita da foto limpa de treino como professora** das três versões da mesma imagem, com penalização explícita de alterações no comportamento limpo. As características já preparadas foram reaproveitadas. A foto limpa funciona como professora somente durante o ajuste; na inferência, o módulo recebe uma única fotografia. Não há reconstrução de textura. As anotações foram mantidas como referência auxiliar de seleção geométrica, e o critério de aceitação não foi relaxado.

Foi selecionada a época 12 da segunda formulação. O erro auxiliar é SmoothL1 ponderado dos cinco parâmetros, e a variação entre condições é um erro quadrático ponderado. Esses números não correspondem a porcentagens de identificação ou de área anatômica.

| Medida do monitor | Referência | Segunda formulação | Variação relativa |
|---|---:|---:|---:|
| Erro geométrico limpo | 0,0002086002 | 0,0002145841 | +2,87% |
| Erro geométrico superior 10% | 0,0003579090 | 0,0003092733 | −13,59% |
| Erro geométrico inferior 10% | 0,0005145756 | 0,0003965881 | −22,93% |
| Variação limpa–superior | 0,0003401357 | 0,0002159836 | −36,50% |
| Variação limpa–inferior | 0,0007101746 | 0,0004402601 | −38,01% |

São estimativas descritivas no monitor reutilizado. O controle geométrico autorizou a avaliação biométrica; não autorizou a promoção do candidato.

## Avaliação biométrica concluída

A avaliação manteve todas as **482 consultas de validação**, 480 imagens de cadastro, uma foto por consulta, lateralidade informada e 16 candidatos do mesmo lado. O limiar e as estatísticas dos componentes do candidato foram calibrados somente na validação limpa e reutilizados sem alteração nas duas oclusões. A calibração antiga foi preservada como controle secundário, sem selecionar o controle mais favorável.

Somente a elipse externa dos ramos polares foi alterada. Os recortes RGB/nativos, a máscara de suporte, a elipse interna da pupila, os pesos de identidade e os pesos dos oito grupos de fusão foram mantidos. Se a nova elipse não contém a pupila ou não satisfaz as verificações geométricas, retorna-se à geometria antiga. As falhas continuam nos denominadores.

| Método | Condição | Rank-1 (%) | TAR (%) | FMR (%) |
|---|---|---:|---:|---:|
| Referência | Limpa | 90,04 | 90,66 | 0,9820 |
| Correção externa | Limpa | 89,21 | 89,83 | 0,9820 |
| Referência | Superior 10% | 80,71 | 78,01 | 1,3001 |
| Correção externa | Superior 10% | 78,84 | 77,39 | 1,2033 |
| Referência | Inferior 10% | 59,96 | 57,88 | 2,4066 |
| Correção externa | Inferior 10% | 63,49 | 61,62 | 2,0747 |

Na condição inferior, as identificações corretas passaram de **289 para 306**, com 17 acertos adicionais; os genuínos aceitos passaram de **279 para 297**, e os impostores aceitos caíram de **174 para 150** em 7.230 comparações. O Rank-1 aumentou 3,53 pontos percentuais e o TAR, 3,73 pontos. A FMR permaneceu acima do limite de 1%.

Na condição limpa, houve 430 identificações corretas e 433 genuínos aceitos, contra 434 e 437 da referência. São necessários pelo menos 434 para atingir 90% entre 482 consultas. Na superior, os acertos caíram de 389 para 380. Portanto, o candidato não passou o critério registrado, nem o alvo absoluto de Rank-1 e TAR de pelo menos 90% com FMR de até 1% nas três condições.

O módulo foi aplicado a 951, 949 e 926 imagens nas condições limpa, superior e inferior. As demais mantiveram a referência por falha polar original ou por contenção da pupila. As consultas com falha permaneceram em quatro, quatro e sete, respectivamente, como no controle. As entradas do cadastro foram conferidas entre as condições.

## Verificação e preservação

Nove testes direcionados passaram, incluindo os cinco novos testes de coordenadas afins, preservação da U-Net, controle de correção nula e retorno exato às texturas antigas para correções inválidas. Não houve nova execução da suíte completa.

A auditoria reproduziu a seleção das épocas, os controles geométricos, a padronização calculada somente nas fotos limpas de ajuste e todas as fusões e decisões biométricas. As previsões geométricas selecionadas foram reproduzidas com diferença zero; os CSVs e os escores finais foram conferidos exatamente. Os pesos originais de identidade permaneceram com os hashes esperados.

Os registros legíveis estão em `outputs/contorno_externo_2026-10-23`, `outputs/contorno_externo_val_2026-10-23`, `outputs/contorno_consistente_2026-10-23` e `outputs/contorno_consistente_val_2026-10-23`. A conclusão biométrica legível omite somente a lista extensa de parâmetros por imagem; o campo de proveniência aponta para o arquivo completo no pacote de preservação.

O pacote em `backups/contorno_externo_2026-10-23` contém **60 arquivos em 88 partes**, incluindo os dois checkpoints. Foram restaurados com hashes conferidos. O ZIP reconstruído tem 4.196.415 bytes e SHA256 `9d169aaeb6bda550259df0b8c5c8e50a26573475078e7ed939608c067a336bce`. A partir dos arquivos restaurados, foram reproduzidos os controles geométricos, as fusões, os escores e as decisões. Os caches de características e imagens foram excluídos do pacote e registrados por hash; não foram recalculados nessa verificação de recuperação.

```powershell
.\executar.ps1 preservar_contorno_externo.py
.\executar.ps1 verificar_recuperacao_contorno.py --restored-root "$env:TEMP\pfc-contorno-restaurado-20261023"
```

As partes `.b64` seguem a exclusão existente do Git. Não foram adicionadas exceções ao Defender. O envio efetivo ao OneDrive não foi verificado. Não houve commit ou push.

## Implicação para a continuidade

O contorno externo mais estável produziu um ganho localizado sob oclusão inferior, mas não demonstrou melhoria global do reconhecedor. A adaptação posterior dos descritores foi executada e rejeitada no monitor interno por não preservar a referência limpa original. Ver [adaptação polar e resultados](ADAPTACAO_POLAR_2026-10-23.md).

O candidato original continua sendo a referência, com os resultados de teste e a fronteira anteriormente registrada preservados. O Word consolidado anterior não foi reexportado nesta rodada de desenvolvimento.
