# Relatório de avanço — 24/10/2026

## Objetivo e referência

Determinar a menor fração nominal de íris aprovada no protocolo UBIPr de perda simulada, com uma foto por consulta, lado informado e controle de falsas aceitações. Não se estima um mínimo anatômico ou clínico universal. A referência principal permanece em 444/486 (91,36%) no teste anteriormente examinado. As rodadas abaixo são desenvolvimento no treino; não alteram essa referência ou a fronteira anterior.

## Recuperação do trabalho pendente

O Acesso Controlado a Pastas bloqueou os executáveis do Codex ao modificar o projeto no OneDrive. O usuário revisou e permitiu os bloqueios. Após essa liberação, o mecanismo de edição voltou a gravar e a leitura foi confirmada por `outputs/VERIFICACAO_LIBERACAO_2026-10-24.txt`. Nenhuma configuração ou exceção foi alterada pelo agente.

Foram preservados no projeto os 104 arquivos do pacote de retomada: ZIP de 2.267.778 bytes, SHA-256 `062333028da8169998d64065da0ae7aa663f209efbe4c9258d7d8e57855e2c02`, distribuído em quatro partes. A restauração conferiu o ZIP e o inventário de cada arquivo. As métricas legíveis e o auditor de fundo foram incorporados ao projeto. A gravação local não comprova sincronização com a nuvem.

## Rodadas auditadas, registradas em 23/10

A rodada com penalização de impostores dividiu as pessoas de treino em 151 para ajuste, 16 para calibração interna limpa e 16 do monitor antigo para avaliação após congelar os pesos. A calibração interna tem 120 consultas; o monitor tem 480. Os encoders anteriores já viram essas populações e o monitor é reutilizado: não há confirmação independente. Foram oito épocas, selecionadas pela perda de ajuste com preservação do limpo interno, sem consultar o monitor ou as oclusões internas a cada época.

| Estratégia no monitor | Condição | Rank-1 | TAR | FMR |
|---|---|---:|---:|---:|
| Polar com penalização e calibração separada | Limpa | 99,79% | 99,79% | 0,5278% |
| Polar com penalização e calibração separada | Superior 10% | 83,13% | 77,92% | 1,0556% |
| Polar com penalização e calibração separada | Inferior 10% | 68,75% | 57,08% | 1,0000% |
| Fusão completa com polar ajustado | Limpa | 99,79% | 99,79% | 1,8056% |
| Fusão completa com polar ajustado | Superior 10% | 96,88% | 98,75% | 4,6528% |
| Fusão completa com polar ajustado | Inferior 10% | 89,38% | 97,08% | 7,4861% |
| Mesma fusão com normalização de fundo | Limpa | 99,79% | 99,79% | 1,6250% |
| Mesma fusão com normalização de fundo | Superior 10% | 96,88% | 95,63% | 1,1944% |
| Mesma fusão com normalização de fundo | Inferior 10% | 89,38% | 85,00% | 1,2778% |

A coorte de 151 pessoas de ajuste também foi testada como normalização simétrica do polar e rejeitada por piorar a FMR. A fusão manteve os outros oito componentes e os pesos de combinação fixos. Cada método usou um único limiar definido apenas no conjunto interno limpo, com alvo de calibração de 0,5% de FMR, aplicado sem mudança às oclusões e ao monitor. A normalização de fundo exclui o maior escore ao estimar a escala de cada consulta, sem saber sua identidade. Seus ganhos de FMR vêm acompanhados de perda de TAR; não houve aprovação conjunta.

## Auditoria e limites

A auditoria do ajuste separado reconstruiu escores e seleção, e confirmou ausência do monitor na escolha por época. As auditorias da coorte, da fusão e da normalização de fundo reproduziram escores, parâmetros e métricas. A restauração do pacote pendente permite repetir fusão e decisões sem nova inferência de imagens. Não houve treino ou avaliação na validação/teste nestas rodadas, nem troca automática do reconhecedor. A FMR de 1% em uma única condição não representa aprovação da meta conjunta.

```powershell
.\executar.ps1 restaurar_pendencias_2026-10-24.py
.\executar.ps1 auditar_fusao_treino_separado.py --root "$env:TEMP/pfc-pendencias-restauradas-20261024"
.\executar.ps1 auditar_fundo_consulta.py --root "$env:TEMP/pfc-pendencias-restauradas-20261024"
```

## Continuidade

Não elevar o limiar usando os casos que falharam no monitor. A próxima hipótese deve ser registrada antes de qualquer novo resultado e separar explicitamente dados usados para calibração dos dados usados para avaliação. O alcance continua exploratório, com atenção ao prazo de 09/11 e sem presumir que mais tentativas garantam generalização.

## Novas rodadas de 24/10, após a recuperação

### Diversidade das intervenções durante o ajuste

Foi concluído outro piloto registrado antes do preparo e do treino: substituir as intervenções fixas de 10% por perdas sorteadas de 1% a 20%, com preenchimentos 32/64/128/192/224, somente nas consultas de ajuste. Mantiveram-se rede, perda, divisão de pessoas, otimização e oito épocas do controle com penalização e calibração separada. O cadastro fica limpo; os grupos interno/monitor continuam com perdas fixas de 10%. O sorteio por foto é fixo durante as épocas, com semente 20261024.

Foram preparadas 3.222 simulações para 1.611 consultas S2 de ajuste, resultando em 422,31 MB adicionais de mapas, sem duplicar o cache original. Dez vistas tiveram falha de extração e foram mantidas com entrada neutra; a manutenção da perda de identidade dessas vistas é uma limitação da formulação. A época 8 foi selecionada pela perda de ajuste com preservação do limpo interno, sem consultar o monitor durante a seleção.

No monitor, o limpo preservou 479/480 (99,79%) acertos e aceitações. Nas perdas superior/inferior de 10%, o Rank-1 foi **398/480 (82,92%) e 315/480 (65,63%)**, contra 83,13%/68,75% do controle fixo. O TAR foi 78,96%/57,92%, mas a FMR subiu para **1,4028%/1,2917%**, com 101/93 falsas aceitações sobre 7.200 comparações, acima das 72 permitidas. Não houve superioridade conjunta, e o modelo foi barrado antes da validação.

Três testes passaram. A auditoria reproduziu o plano, as contagens de pixels, os escores, o limiar e a seleção, e verificou que as simulações pertencem somente ao ajuste. O primeiro lote de 32 imagens foi reprocessado na ordem do cache, sem seleção por escore: mapa automático e características coincidiram, com diferença máxima zero. Isso não é regeneração de todos os mapas. O pacote de 40 arquivos no ZIP, 32.765.878 bytes em 44 partes, foi restaurado com hashes e decisões conferidos, incluindo os dois checkpoints sem quantização. Não houve nova validação/teste ou alteração do mínimo de área.

Foi solicitada uma clarificação de escopo sobre eventual estudo separado de decisão exclusiva do melhor candidato. Até uma orientação diferente, mantém-se o protocolo atual: Rank-1 e FMR por pares. Uma FMR reduzida por restringir aceitações por consulta não será apresentada como melhoria equivalente de verificação. Ver [método e limites do piloto](../pfc1-segmentacao-mmu/DIVERSIDADE_OCLUSAO_2026-10-24.md).

### Limiar global calibrado em perturbações internas

Foi registrado um protocolo novo de calibração: usar as três condições do grupo interno — limpa, perda superior de 10% e inferior de 10% — para definir um único limiar global, como o máximo dos limiares de FMR interna de 0,5%. Esse limiar é o mesmo para todas as pessoas e condições na avaliação. Não é um limiar escolhido por condição na captura, nem uma alteração retroativa dos protocolos anteriores. Nenhum caso do monitor foi usado para estimá-lo. Dois testes direcionados passaram.

O limiar foi 0,9592531099730544. No monitor reutilizado de 480 consultas, a FMR ficou em **0,0417% no limpo, 0,0972% na perda superior e 0,2222% na inferior**. O limpo preservou Rank-1/TAR de 99,79%; a superior atingiu Rank-1 de 96,88% e TAR de 92,50%. Na inferior, porém, Rank-1/TAR foram 89,38%/76,25%. Portanto, controlar a FMR não resolveu a meta conjunta. A auditoria reproduziu o limiar a partir apenas dos dados internos e todas as métricas.

### Avaliação limpa da validação com parâmetros de treino congelados

Antes de extrair novos níveis de oclusão, foi registrada e executada a porta limpa da validação: 482 consultas e 16 olhos candidatos do mesmo lado. As identidades não receberam gradientes neste ajuste nem participaram da calibração de treino; a validação já foi examinada em pesquisas anteriores e não é confirmação cega. Oito componentes originais foram reutilizados, com o polar ajustado em FP32, calibração e limiar do treino congelados, sem ajuste aos novos escores.

O resultado foi **436/482 (90,46%) de Rank-1, 310/482 (64,32%) de TAR e 0,2075% de FMR**, com quatro falhas mantidas. A porta limpa falhou e não foram executadas oclusões ou teste final desse pipeline. Um diagnóstico descritivo da ROC encontrou TAR máximo empírico de **77,59% a FMR ≤1%** nesses escores: mesmo um limiar privilegiado não resolveria a meta limpa. Esse diagnóstico não foi usado como calibração nem promoção de candidato. O limiar original permaneceu inalterado. A auditoria reproduziu a fusão e as decisões.

### Controle de troca isolada com os parâmetros originais

Para separar o efeito da nova calibração do efeito do polar, foi registrado um controle que preserva exatamente os parâmetros do sistema principal: oito componentes, calibração, normalização de consulta e limiar 0,8581747485460748 originais. Só o polar é substituído pelo modelo ajustado no treino; nenhuma estatística ou limiar foi recalculado na validação.

O controle original reproduziu **434/482 (90,04%) de Rank-1, 437/482 (90,66%) de TAR e 0,9820% de FMR**. A troca isolada obteve **433/482 (89,83%) de Rank-1, 435/482 (90,25%) de TAR e 1,0235% de FMR**. Também falhou no limpo; não foram abertas as condições ocluídas. A auditoria reproduziu ambos os resultados com os parâmetros originais exatos.

### Decisão e limite desta linha

Nenhuma das novas variantes foi promovida. O ganho do polar no monitor não se confirmou como melhoria limpa da fusão na validação. Ajustar novamente o limiar ou escolher outros pesos usando esses casos violaria o objetivo de reduzir seleção sobre os mesmos resultados. Esta linha de calibração/ajuste polar foi encerrada; uma próxima linha deve resolver discriminação/transferência e definir avaliação antes de novos resultados. Não há evidência para declarar o objetivo completo atingido ou um novo mínimo de área. O teste principal e a referência anterior permanecem preservados.

Os artefatos das três novas rodadas foram auditados e reunidos para recuperação por hashes, sem duplicar imagens, caches ou pesos originais. A conferência de gravação local após a liberação foi positiva; sincronização na nuvem não foi verificada.
