# Diagnostico de erros e fusao aparada — 21/10/2026

O aplicativo mobile permanece fora do escopo desta etapa. Foram concluidas uma auditoria dos erros e uma hipotese adicional de fusao. Nenhuma inferencia nova no teste, nenhuma alteracao do candidato congelado e nenhum novo percentual minimo declarado.

## Auditoria da validacao

Todas as482 consultas foram mantidas: uma foto por consulta, lado informado,16 candidatos. A analise usa os escores ja salvos, sem ajustar modelos ou limiares.

| Segmentador / condicao | Identificacoes corretas | Erros | Erros em que algum componente acertava |
|---|---:|---:|---:|
| Original / limpa |434|48|37|
| Original / superior10% |389|93|65|
| Original / inferior10% |289|193|129|
| Robusto / limpa |427|55|39|
| Robusto / superior10% |371|111|84|
| Robusto / inferior10% |395|87|64|

O fato de algum componente acertar e uma observacao feita COM conhecimento da identidade verdadeira. Nao representa um reconhecedor que saiba escolher esse componente na captura, nem desempenho atingido pelo sistema. Entretanto, mostra complementaridade que justifica estudar uma fusao aprendida apenas no treino.

Na validacao limpa original, participantes149 e361 concentram21 dos48 erros (43,75%). Essa concentracao deve ser investigada, sem excluir participantes, imagens ou falhas. A consulta individual e a matriz de confusoes estao nos CSVs completos da auditoria.

Trocar o segmentador original pelo robusto, usando os modelos de identidade e calibracao congelados:

- Limpa: recupera7 consultas, perde14, saldo-7.
- Superior10%: recupera26, perde44, saldo-18.
- Inferior10%: recupera123, perde17, saldo+106.

Essas transicoes sao pareadas por consulta e nao demonstram causa clinica. A oclusao artificial pode mudar a segmentacao, a geometria e a textura normalizada ao mesmo tempo.

## Hipotese de fusao aparada

Antes de calcular os resultados, registrou-se uma unica alternativa: padronizar os escores dos oito grupos de reconhecedores, retirar o menor e o maior por candidato, e calcular a media dos seis restantes. As duas vistas ArcIris permanecem um unico grupo. Nao houve busca da quantidade de componentes removidos, pesos ou filtros por participante.

Calibracao dos componentes e limiar apenas na validacao limpa, FMR empirica no maximo1%; parametros inalterados nas oclusoes. Cada ramo tem seu controle aritmetico equivalente. Validacao repetidamente usada em desenvolvimento; nao e confirmacao independente.

| Segmentador / fusao | Limpa: Rank-1 / TAR / FMR | Superior10%: Rank-1 / TAR / FMR | Inferior10%: Rank-1 / TAR / FMR |
|---|---|---|---|
| Original / aritmetica |90,04 /90,66 /0,98%|80,71 /78,01 /1,30%|59,96 /57,88 /2,41%|
| Original / aparada |88,59 /89,83 /0,98%|79,46 /76,97 /1,41%|59,96 /57,68 /2,54%|
| Robusto / aritmetica |88,59 /89,21 /0,98%|76,97 /71,37 /1,30%|82,16 /79,46 /1,16%|
| Robusto / aparada |88,17 /88,38 /0,98%|75,52 /70,75 /1,27%|81,54 /79,05 /1,26%|

Todos os valores sao percentuais. A hipotese nao melhorou o desempenho e nao foi promovida. O controle original limpo reproduz o limiar congelado0,8581747485460748 e os434 acertos. Dez testes automatizados passaram, incluindo falhas mantidas, transicoes pareadas, equivalencia de grupos identicos, disponibilidade de candidatos e independencia dos rotulos na inferencia da fusao.

## Proximo desenvolvimento

Preparar escores dos componentes com identidades exclusivamente do treino, separados por sessao, para aprender uma combinacao regularizada. A construcao de exemplos precisa preservar o lado informado e diferenciar treino dos reconhecedores de generalizacao da fusao. Nao ajustar pesos diretamente aos37 erros identificados na validacao. Registrar antecipadamente uma arquitetura e um criterio de parada, manter os encoders congelados inicialmente, e avaliar todos os participantes da validacao com calibracao limpa unica. O protocolo definitivo e a execucao desse treinamento ainda estao pendentes.

## Arquivos e preservacao

Codigo: `diagnosticar_erros_validacao.py`, `validar_fusao_aparada.py` e respectivos testes. Protocolos e resumos completos em `outputs/diagnostico_erros_val_2026-10-21/` e `outputs/fusao_aparada_val_2026-10-21/`.

Os CSVs completos da auditoria e os escores binarios da fusao foram produzidos em `%TEMP%/pfc-tcc-resultados/`, nas pastas com os mesmos nomes. Os resumos e protocolos foram copiados ao projeto via editor; a copia binaria pelo Node encontrou timeout nesta sessao. A pasta temporaria nao substitui backup duravel.
