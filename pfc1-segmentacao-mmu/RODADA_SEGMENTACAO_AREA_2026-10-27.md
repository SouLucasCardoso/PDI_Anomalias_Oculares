# Segmentação orientada ao percentual de íris necessário — 27/10/2026

O objetivo principal permanece medir a menor fração **visível e anotada** de íris que permite identificar o olho no protocolo definido, controlando falsas correspondências. Melhorar o recorte é um meio para esse objetivo. O percentual não será chamado de mínimo anatômico universal nem de extensão de uma doença.

## Continuidade do treino

Na verificação desta continuação, o processo da primeira rodada estava ausente. Seu último registro era época 1, lote 50/483, sem exceção gravada. Apenas o checkpoint da época 0 havia sido salvo; as atualizações da época parcial não estão disponíveis. Não se atribui progresso novo a esses pesos. A causa da interrupção não foi determinada.

A rodada foi preparada em um diretório novo, preservando a anterior. `treinar_segmentacao_area.py` salva pesos, estado do AdamW, scheduler, ordem de amostras, lote e histórico dentro da época. Aumentações dependem de pessoa/imagem e época por uma semente determinística. Um teste interrompe o treino no meio e confere que a retomada em CPU reproduz exatamente os pesos e a perda da execução contínua. Não é uma prova de determinismo bit a bit entre equipamentos CUDA diferentes.

A leitura das máscaras foi acelerada por tabela de consulta com as mesmas quatro classes; valores inválidos continuam provocando erro. A equivalência com o decodificador anterior foi testada. A validação da época 0 anterior é reaproveitada somente após conferir pessoas, pesos, manifesto, resolução, semente e as funções de geometria/aumentação/perda, evitando repetir uma medição idêntica. O novo treino continua com 7.716 fotos de 183 pessoas, 1.652 fotos de validação de outras 39 pessoas, até 30 épocas e a mesma regra de seleção por segmentação.

O lançamento preparado usa uma tarefa local do Windows, única, com limite de 24 horas e execução na conta interativa do usuário. Isso desacopla o processo da duração desta sessão de ferramentas. O programa tem retomada caso seja encerrado; a tarefa não é recorrente. O registro e o início efetivo precisam ser conferidos antes de considerar o treino ativo.

**Lançamento confirmado:** tarefa `PFC_Iris_Segmentacao_Area_20261027` registrada e execução efetiva observada em 27/10 às 23h08 (America/Sao_Paulo), época 1, processo de treino 9760, primeira atualização com perda finita de 2,4355. O registro UTC é 28/10 às 02h08; não corresponde a uma nova data local do experimento. A tarefa usa a conta do usuário e o nível limitado, sem recorrência ou credenciais gravadas no projeto. Passaram 11 testes direcionados e um teste de integração que gerou corretamente as quatro representações do reconhecedor com entrada 416×320. O ensaio curto completou uma época e salvou um candidato; seus escores não são resultados da rodada completa.

## Ligação com identificação e área

O protocolo foi registrado em [protocolo_rodada.json](outputs/segmentacao_area_2026-10-27/protocolo_rodada.json) antes do lançamento:

1. Selecionar o candidato final somente pelo Dice de segmentação nas quatro condições já definidas, mantendo a proteção de desempenho original. Se o melhor continuar na época 0, registrar ausência de candidato treinado elegível.
2. Comparar segmentador original e candidato no reconhecimento da validação: foto original e perdas superior/inferior de 10%. Manter os mesmos reconhecedores, galeria da sessão 1, consultas individuais da sessão 2, lado informado, fusão, calibração e limiar congelado. Todas as consultas e falhas permanecem no denominador.
3. Somente se o candidato sem oclusão atender simultaneamente Rank-1 ≥ 90%, TAR ≥ 90% e FMR ≤ 1%, executar as perdas predefinidas de 1%, 2%, 5%, 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80% e 90%, nas duas orientações. A grade inteira é medida, mesmo após uma reprovação.
4. Estimar o menor aproveitamento aprovado no **prefixo da grade testada**, separadamente por orientação e também em ambas. Uma aprovação isolada abaixo de uma reprovação não estabelece mínimo. Se a condição original falhar, o mínimo fica indeterminado.
5. Relatar contagens inteiras e intervalos de confiança por reamostragem de pessoas. Não arredondar um FMR acima de 1% para obter aprovação. A validação já foi explorada; esta etapa é desenvolvimento, sem novo teste cego ou promoção automática do modelo.

Foi corrigida a entrada do avaliador: o novo checkpoint usa a resolução de treino 416×320; a referência continua em 320×240. Sem isso, a comparação poderia perder a adaptação de escala antes de alcançar o reconhecedor. O protocolo de cada inferência agora registra a resolução.

## Relação com anomalias reais

Oclusão artificial mede perda controlada de suporte e a resposta do processamento completo. Catarata, alterações corneanas, reflexos, deformação da pupila e lesões da íris podem afetar nitidez, contraste, forma e textura sem remover a mesma porcentagem de área. A relação entre área e identificação precisa ser separada desses mecanismos.

Os quatro casos SLP-VLD, incluindo controles `Normal eye`, continuam como inspeção qualitativa dos recortes. Para concluir quanto uma anomalia interfere, precisamos de máscaras revisadas, diagnóstico da fonte e capturas comparáveis do mesmo olho, além de controles de aquisição e qualidade. Não transformar falhas de segmentação em porcentagem de tecido perdido, nem usar previsões da rede como verdade clínica.

Arquivos principais: `avaliar_area_segmentador_diverso.py` orquestra treino e avaliação; `status_segmentacao_diversa.ps1` informa estado e detecta processo ausente; logs e resultados ficam em `outputs/segmentacao_area_2026-10-27/`. O diretório ativo, com checkpoints retomáveis, é `%TEMP%/pfc-segmentacao-area-20261027/`. O lançamento não altera os resultados congelados do artigo.
