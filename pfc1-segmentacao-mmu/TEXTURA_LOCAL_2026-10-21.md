# Comparacao local por confiabilidade de textura — 21/10/2026

Experimento exploratorio encerrado, sem promover novo modelo. Apenas validacao UBIPr: 482 consultas de uma unica foto, lado informado, 16 olhos candidatos e 7.230 comparacoes impostoras. Nenhuma nova inferencia no teste. Todas as consultas e falhas foram mantidas.

Foi testada uma ponderacao do cosseno local pela entropia da imagem polar: 16 niveis, blocos de 16 por 16 pixels, entropia normalizada elevada ao quadrado, peso do par pela media geometrica das confiabilidades. CNN, prototipos de cadastro, deslocamento angular zero e pesos da fusao permaneceram fixos. Essa medida representa textura, nao percentual anatomico visivel. O protocolo foi gravado antes da extracao dos resultados, sem busca de hiperparametros.

Cada estrategia foi calibrada uma vez na validacao limpa; os mesmos parametros e limiar foram usados nas duas oclusoes artificiais de 10%. A validacao ja foi reutilizada no desenvolvimento e nao constitui confirmacao independente.

## Resultados da fusao

| Segmentador / comparador | Sem oclusao: Rank-1 / TAR / FMR | Superior10%: Rank-1 / TAR / FMR | Inferior10%: Rank-1 / TAR / FMR |
|---|---|---|---|
| Original / uniforme | 90,04 / 90,66 / 0,98% | 80,71 / 78,01 / 1,30% | 59,96 / 57,88 / 2,41% |
| Original / textura | 89,83 / 90,46 / 0,98% | 80,50 / 78,42 / 1,29% | 59,54 / 57,68 / 2,39% |
| Robusto / uniforme | 88,59 / 89,21 / 0,98% | 76,97 / 71,37 / 1,30% | 82,16 / 79,46 / 1,16% |
| Robusto / textura | 88,38 / 89,21 / 0,98% | 77,18 / 71,58 / 1,24% | 82,57 / 79,25 / 1,11% |

Todos os valores da tabela estao em percentual. Rank-1 e TAR sao criterios distintos, nao sucesso conjunto. A pequena melhora no Rank-1 inferior do ramo robusto veio acompanhada de queda no TAR e nao atingiu os criterios de aceitacao: Rank-1 e TAR de pelo menos90%, FMR no maximo1%. Com segmentacao original, a nova ponderacao perdeu uma consulta correta no caso limpo (433/482 contra434/482).

## Verificacao e conclusao

Os seis controles uniformes reproduziram os escores espaciais anteriores com diferenca maxima exatamente zero. Tres testes automatizados passaram: entropia de regioes constantes independentemente da cor, equivalencia com pesos uniformes, e tratamento de regioes sem confiabilidade. A ponderacao por textura nao foi suficiente; o candidato congelado continua preservado.

O resultado anterior de teste permanece 91,36% Rank-1 e92,39% TAR sem oclusao, FMR0,88%. Na grade explorada, o menor aproveitamento nominal aprovado permanece100% para oclusao superior e99% para inferior. Isso nao demonstra um minimo anatomico ou clinico universal.

Resultados completos em `outputs/textura_local_val_2026-10-21/CONCLUIDO.json`. O pacote completo com protocolo, copia do codigo, parametros e escores foi produzido em `%TEMP%/pfc-tcc-resultados/textura_local_val_2026-10-21`; a copia binaria para o projeto encontrou novamente dificuldade de gravacao no OneDrive. O resumo JSON e este documento foram preservados no projeto pelo editor.

O proximo desenvolvimento deve tratar representacao e comparacao com oclusao durante o treinamento, com controle da perda de desempenho limpo. Repetir ajustes na mesma validacao nao substitui uma confirmacao independente; nenhum novo percentual minimo deve ser declarado a partir desta rodada.
