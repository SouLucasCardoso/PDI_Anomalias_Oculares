# Continuação da rodada de segmentação e área — 27/10/2026

## Treino ativo e verificação dos controles

A tarefa persistente continuou ativa após o encerramento da sessão anterior. Nesta continuação, foram observados checkpoints incrementais na primeira época, com progresso até pelo menos o lote 275/483, correspondendo a 4.400 fotos. Não houve reinício do treino nem alteração dos parâmetros ou das fontes congeladas da rodada.

O snapshot imutável do lote 150 foi carregado em CPU: os tensores tinham as mesmas chaves e formas do modelo original e valores finitos; o AdamW registrava 150 atualizações, correspondentes a 2.400 fotos. O checksum do snapshot é `f10eff344b2ed6d53c5af44bb15b5d319b0aa6d50f8322ce9e8d8d432add3538`. Isso comprova atualizações e preservação do estado; não demonstra ganho de identificação.

Os três controles históricos de reconhecimento na validação foram auditados e preparados para reuso pela rodada atual. Foram conferidos pesos, limiar, código histórico, população de 482 consultas e 16 candidatos por consulta. As nove matrizes componentes reproduziram a fusão com diferença máxima **zero**, e as decisões e contagens dos 1.446 registros consulta/condição foram reproduzidas. Em cada condição, três fotografias fixadas antes da inferência reproduziram exatamente os quatro tipos de entrada do cache original e os indicadores de validade.

| Controle histórico de validação | Identificações corretas | Genuínos aceitos | Falsas correspondências | Identificação correta e aceitação simultâneas |
|---|---:|---:|---:|---:|
| Original | 434/482 | 437/482 | 71/7.230 | 426/482 |
| Perda superior de 10% | 389/482 | 376/482 | 94/7.230 | 367/482 |
| Perda inferior de 10% | 289/482 | 279/482 | 174/7.230 | 269/482 |

São resultados existentes auditados, sem nova inferência de identidade e sem recalibração. Os controles foram copiados para os diretórios de tentativas concluídas que o orquestrador já aceita reutilizar. A condição original recebeu apenas a lista vazia de intervenções esperada pelo avaliador atual; os arquivos históricos permaneceram intactos. A auditoria completa, incluindo fontes e hashes, está em [CONTROLES_AUDITADOS.json](outputs/segmentacao_area_2026-10-27/CONTROLES_AUDITADOS.json).

## Diagnóstico intermediário do novo segmentador

Foi registrado um diagnóstico pontual do snapshot da **época 1, lote 150**, usando as mesmas 16 pessoas sorteadas antes do ensaio SAM3.1. Nenhuma imagem foi filtrada pelo escore. São 64 entradas pareadas em quatro condições, com duas redes, totalizando 128 registros. Ambos os modelos usaram FP32 e interpolação bilinear em CPU; a referência recebeu entrada 320×240 e o snapshot recebeu a resolução de treino 416×320. Os 128 registros foram recalculados a partir das máscaras efetivamente gravadas.

| Condição | U-Net original, Dice macro | Snapshot intermediário, Dice macro | Diferença, pontos percentuais |
|---|---:|---:|---:|
| Escala original | 95,36% | 91,68% | −3,68 |
| Zoom 3× | 1,71% | 71,73% | +70,02 |
| Oblíqua simulada | 91,63% | 82,63% | −9,00 |
| Óculos simulados | 88,61% | 83,57% | −5,04 |

Há aprendizado de tolerância à escala, acompanhado por piora nas outras condições desta amostra. Isso reforça a necessidade de manter a proteção de desempenho original e a validação completa. Este snapshot **não foi selecionado como candidato**, e a inspeção não mudou o treinamento ou a regra de seleção. O critério registrado continua sendo o da rodada completa de segmentação, antes da avaliação de identidade.

As cifras diferem ligeiramente do controle do ensaio SAM3.1 porque esta checagem usa bilinear em ambas as redes e FP32 em CPU, conforme o protocolo desta inspeção. Não são resultados da validação inteira de 1.652 fotos, do reconhecimento ou de percentual mínimo de íris.

Nos quatro casos clínicos da prancha original, persistem falhas visíveis. O contorno previsto ficou mais amplo em P0005, mas com lacunas e inclusão inadequada de regiões centrais. P0007 ainda apresenta classificação da região da pupila e fragmentos periféricos como íris. P0803 inclui áreas externas ao alvo ocular. Sem máscaras clínicas revisadas, não foi calculado Dice ou percentual anatômico para esses casos.

- [Protocolo do diagnóstico](outputs/segmentacao_area_2026-10-27/diagnostico_epoca01_lote0150/protocolo.json).
- [Resultados e auditoria das máscaras](outputs/segmentacao_area_2026-10-27/diagnostico_epoca01_lote0150/CONCLUIDO.json).
- [Prancha dos quatro casos clínicos](outputs/segmentacao_area_2026-10-27/diagnostico_epoca01_lote0150/clinicos/comparacao_clinica.png).

## Próximo resultado necessário

Aguardar o candidato selecionado na validação completa e medir sua identificação com os controles acima. A varredura de área depende de aprovação sem oclusão, com Rank-1 ≥ 90%, TAR ≥ 90% e FMR ≤ 1%. Ganho de segmentação no zoom, isoladamente, não estabelece o percentual mínimo necessário nem a interferência de uma anomalia real.

## Retomada de 03/11/2026

Na verificação desta data, o processo anterior estava ausente. Foram preservadas 15 épocas completas e os primeiros 50 lotes da época 16, equivalentes a 800 imagens. O arquivo de recuperação e sua cópia imutável são idênticos; os pesos e o estado do AdamW são finitos. Os dez arquivos do protocolo continuam com seus hashes registrados. A auditoria está em [VERIFICACAO_RETOMADA_2026-11-03.json](outputs/segmentacao_area_2026-10-27/VERIFICACAO_RETOMADA_2026-11-03.json).

O melhor checkpoint até esse momento é o da época 15, selecionado exclusivamente por segmentação. Os resultados abaixo usam **todas as 1.652 imagens da validação** e Dice macro, com a mesma transformação determinística do controle da época zero:

| Condição | Controle da época zero | Melhor checkpoint até a época 15 |
|---|---:|---:|
| Escala original | 85,49% | 85,39% |
| Zoom 3× | 1,96% | 82,38% |
| Oblíqua simulada | 47,13% | 84,79% |
| Óculos simulados | 67,34% | 84,58% |

Esses resultados não são os da pequena amostra de 16 pessoas do diagnóstico anterior. A época 15 é provisória; o treino conserva o limite de 30 épocas e a parada por paciência de oito épocas. O reconhecimento do candidato final ainda precisa ser calculado.

A tarefa existente foi retomada em 03/11 às 12h25, horário de São Paulo. Sua configuração anterior foi exportada em XML antes da alteração. Um supervisor externo aos dez arquivos congelados verifica as fontes e chama o mesmo orquestrador, com os mesmos argumentos. A tarefa agora também dispara no login do mesmo usuário e permite três novas tentativas em caso de falha, separadas por dois minutos. O supervisor verifica o marcador final para evitar reiniciar uma rodada concluída.

Durante a execução, o supervisor solicita ao Windows que não suspenda por inatividade; essa solicitação é temporária e é liberada ao terminar. Não altera configurações permanentes de energia nem impede suspensão manual. Três verificações do supervisor passaram: rodada concluída não inicia outro processo; falha do filho preserva o código de erro e libera a solicitação; exceção também a libera. A sintaxe do script de configuração e os hashes científicos foram conferidos antes do lançamento. A evidência de inicialização está em `supervisor.log` e no registro `RETOMADA_PERSISTENTE_20261103T152547409Z.json`, dentro da pasta da rodada.

## Análise observacional e nova inspeção clínica em 03/11

O treino continuou sem reinício, ultrapassando o lote 275 da época 16. Foi preparado um relatório observacional separado, com fonte e semente registradas antes da avaliação de reconhecimento do candidato final: [protocolo da análise](outputs/segmentacao_area_2026-10-27/analise/protocolo_analise.json). Ele acompanha as épocas concluídas e aguarda `CONCLUIDO_RODADA.json`. A tarefa `PFC_Iris_Relatorio_Area_20261027` está configurada para acompanhar a execução atual e retomar no login do mesmo usuário; seu registro e log estão na pasta `analise`.

A análise recalcula as decisões diretamente das matrizes de escores, verifica rótulos, contagens, hashes e regra de área, arquiva os escores componentes e seus protocolos fora de TEMP e calcula diferenças pareadas entre o candidato e o controle. O bootstrap usa 5.000 reamostragens de pessoas com semente 127 e galeria fixa. Identificação correta e aceitação simultâneas são medidas separadamente; não substituem o critério registrado de Rank-1/TAR/FMR. Não há inferência adicional ou mudança de treinamento, pesos, limiar ou calibração por esse observador.

Quatro testes da análise passaram: retenção de falhas nos denominadores e distinção entre TAR e acerto aceito; comparação de limiar em precisão float64; direção e ponderação das diferenças pareadas; exclusão de olhos sem as duas sessões. Os 1.446 registros reais dos três controles históricos também reproduziram contagens, decisões e sucesso conjunto exatamente. O [relatório atual](outputs/segmentacao_area_2026-10-27/analise/RELATORIO_ATUAL.md) e o [gráfico da evolução](outputs/segmentacao_area_2026-10-27/analise/evolucao_segmentacao.png) serão atualizados pelo observador.

A inspeção intermediária do checkpoint imutável da época 15 usa os mesmos quatro casos clínicos previamente fixados: [prancha](outputs/segmentacao_area_2026-10-27/diagnostico_intermediario_epoca15_2026-11-03/comparacao_clinica.png), [proveniência](outputs/segmentacao_area_2026-10-27/diagnostico_intermediario_epoca15_2026-11-03/comparacao.json). SHA256 do checkpoint: `b848fee1be0f39e5815693d987f99f3121aa45a8c70d93e65f754384c166da94`.

Nos dois casos rotulados como normais pela base, a predição cobre uma região mais ampla que o modelo original, mas ainda inclui parte da pupila e deixa lacunas extensas na íris. Nos casos com anomalias também persistem exclusões e fragmentos externos, especialmente no caso P0803. Não há máscaras clínicas revisadas para medir Dice ou erro de área. Essa inspeção não selecionou o candidato final e não alterou o treino. Ela evidencia que o ganho de robustez no UBIPr não resolve, por si só, a generalização para fotografias clínicas.

O [complemento de referências](REFERENCIAS_SEGMENTACAO_DIVERSA_2026-10-27.md) acrescenta OcularSeg como 13ª referência e registra fontes adicionais de máscaras. A triagem identificou a dependência entre UBIPr e UBIRIS.v2: qualquer expansão futura precisa mapear as identidades aos grupos atuais antes do treino. Nenhuma das bases novas foi misturada à rodada em curso.

## Época 16 concluída e diagnóstico de prompts

A época 16 terminou em 03/11/2026, por volta de 12h54, horário de São Paulo, e a época 17 começou automaticamente. O observador atualizou o relatório para a época concluída 16. O novo melhor checkpoint foi escolhido pela mesma regra de segmentação, sem consulta aos escores de identidade.

| Condição fixa de validação | Época zero, Dice macro | Época 16, Dice macro |
|---|---:|---:|
| Escala original | 85,49% | 85,66% |
| Zoom 3× | 1,96% | 82,64% |
| Oblíqua simulada | 47,13% | 85,09% |
| Óculos simulados | 67,34% | 84,87% |

Todas as médias usam as mesmas 1.652 imagens da validação e não devem ser interpretadas como taxas de reconhecimento. Valores completos: [validação da época 16](outputs/segmentacao_area_2026-10-27/treino/validacao_epoca_16.json).

Foi executado um diagnóstico adicional, registrado antes da inferência, nos mesmos quatro casos clínicos. O checkpoint antigo do Iris-SAM especializado não foi encontrado em sua antiga pasta TEMP; nenhum resultado novo foi atribuído a ele. O controle efetivamente executado usa **SAM2.1 Hiera Tiny genérico**, já disponível localmente, em CPU FP32 com duas threads, sem downloads ou uso da GPU. Isso não é uma nova avaliação de SAM3.1 nem do Iris-SAM especializado.

A única comparação usa os mesmos prompts automáticos já implementados, derivados ora da máscara U-Net antiga, ora da máscara diversa da época 15. A época 15 foi fixada para este diagnóstico, mantendo a comparação clínica anterior; não representa seleção do checkpoint final. Pontos positivos, negativos e caixa vêm exclusivamente da previsão; não há cliques manuais nem máscaras de referência. Foi escolhida a máscara com maior IoU **previsto pelo SAM**, sem busca pelo resultado real. Esse escore do modelo não é uma medida de IoU clínico.

A [prancha completa](outputs/segmentacao_area_2026-10-27/diagnostico_sam2_prompts_2026-11-03/comparacao_prompts_clinicos.png) mostra uma mudança clara no contorno externo dos dois casos normais quando o suporte novo orienta o SAM. Entretanto, as máscaras continuam incluindo a pupila. No caso P0803, o suporte novo leva a uma expansão incorreta muito grande, incluindo tecido fora da íris. Todos os quatro casos e as oito saídas foram preservados, sem seleção visual dos melhores exemplos. Não foi calculado Dice, IoU real, percentual clínico de área ou reconhecimento; não houve promoção do método.

Houve um aviso de configuração `sam2_video` ao construir o caminho de imagem `Sam2Model`. A [auditoria da carga](outputs/segmentacao_area_2026-10-27/diagnostico_sam2_prompts_2026-11-03/AUDITORIA_CARGA.json) comparou os **309 tensores do caminho de imagem** ao checkpoint: todos idênticos, nenhum ausente ou diferente. Os outros 160 tensores pertencem às estruturas de memória/vídeo listadas na auditoria e não foram usados. Não foi avaliado rastreamento. A [auditoria das máscaras](outputs/segmentacao_area_2026-10-27/diagnostico_sam2_prompts_2026-11-03/AUDITORIA_MASCARAS.json) reproduziu os oito prompts e as contagens de pixels a partir das máscaras preservadas e conferiu imagens/fontes/hashes. Os dois testes existentes do gerador de prompts passaram.

Esse controle indica que a qualidade da localização automática afeta o contorno refinado, mas também mostra que melhorar a caixa não resolve a separação íris/pupila ou a robustez a anomalias. O treino e a avaliação registrados seguem inalterados.

## Diretriz posterior: SAM 3 e versões atuais

O usuário determinou usar SAM 3 e manter as tecnologias na versão mais atual possível. A preferência foi registrada no `AGENTS.md` da raiz. SAM2 e Iris-SAM passam a referências/controles históricos; os novos ensaios SAM usam a versão oficial mais recente da família3 verificada antes de cada rodada.

Em 03/11 foi preparado e validado um ambiente separado com SAM3.1, revisão oficial `f1647e8…`, PyTorch2.14.1/torchvision0.29.1 com CUDA13.0, Transformers5.22.1, Hub2.4.0 e Pillow13.0.0. Os limites oficiais de compatibilidade, incluindo NumPy<2 exigido pelo SAM3, estão documentados em [TECNOLOGIAS_ATUAIS_2026-11-03.md](TECNOLOGIAS_ATUAIS_2026-11-03.md). Não foram trocadas as versões da rodada ativa, que já avançou até a época28 sob seu protocolo original.

O novo [ensaio SAM3.1 atualizado](outputs/sam31_atual_prompts_2026-11-03/CONCLUIDO.json) executou na GPU os quatro casos fixos, com texto isolado e duas caixas automáticas por imagem. Foram carregados estritamente1.130 tensores sem ausentes/inesperados; o pico alocado foi aproximadamente3,90GiB. A [auditoria](outputs/sam31_atual_prompts_2026-11-03/AUDITORIA.json) reproduziu as12 máscaras e as8 caixas e verificou hashes e preservação das dez fontes da rodada ativa. A [prancha](outputs/sam31_atual_prompts_2026-11-03/comparacao_sam31_atual.png) mantém todas as saídas, inclusive os erros. Não há referência clínica de segmentação para medir Dice ou demonstrar ganho de reconhecimento, e a combinação texto/caixa ainda falha nos exemplos. O ambiente atualizado e SAM3 são o ponto de partida dos próximos ensaios, com calibração e adoção no reconhecedor dependentes de avaliação própria.

## Rodada concluída e adaptação supervisionada SAM3.1

A rodada completou as 30 épocas e escolheu a época 30 exclusivamente por segmentação. No conjunto completo de validação, os Dice macro foram 86,09% na condição original, 83,18% no zoom, 85,54% na vista oblíqua e 85,38% nos óculos simulados. Na identificação sem oclusão, o novo candidato atingiu Rank-1 de 86,10%, TAR de 85,68%, acerto aceito simultâneo de 83,40% e FMR de 1,203%. Ele não passou no critério registrado e não substituiu a referência. **Nenhum novo mínimo de área foi atribuído.** Os resultados pareados e intervalos estão no [relatório final da rodada](outputs/segmentacao_area_2026-10-27/analise/RELATORIO_ATUAL.md).

Foi iniciada uma nova rodada com backbone visual SAM3.1 congelado e decodificador supervisionado RGB+SAM3. O treino usa apenas as pessoas de treino do UBIPr; seleção por quatro condições de validação, sem escores de identidade ou referências clínicas. A etapa atual constrói 22.040 mapas visuais, seguida de até 20 épocas com recuperação periódica. O ensaio pequeno de integração completou extração real, treino e validação na GPU; é marcado como desenvolvimento e não conta para prontidão.

O usuário confirmou que fará a primeira revisão clínica. O [editor local](http://127.0.0.1:8766/) foi preparado com 30 controles normais de 30 pessoas e as seis fotografias de desenvolvimento com diagnóstico envolvendo íris, de cinco pessoas. Uma primeira revisão já estava registrada nesta verificação. Os rascunhos não entram como referências concluídas; salvamentos preservam versões e hashes, sem atribuir confirmação por especialista.

Os critérios propostos e o fluxo automatizado estão documentados em [PRONTIDAO_ANOMALIAS_2026-11-03.md](PRONTIDAO_ANOMALIAS_2026-11-03.md). O [relatório de prontidão](outputs/prontidao_anomalias_2026-11-03/PRONTIDAO.md) acompanha as revisões e o resultado do mesmo checkpoint. O piloto com anomalias depende de segmentação e controles clínicos; o estudo de identificação também exige as metas biométricas, incluindo acerto aceito simultâneo. São alvos de engenharia, sem equivalência com certificação clínica. As três tarefas locais de treino, editor e acompanhamento estão ativas, com retomada no login. As fontes científicas da rodada concluída e da rodada nova foram preservadas.
