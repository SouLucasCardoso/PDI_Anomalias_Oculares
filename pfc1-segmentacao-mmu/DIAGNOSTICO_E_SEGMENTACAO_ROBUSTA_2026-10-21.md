# Diagnóstico do pré-processamento e ajuste da segmentação — 21/10/2026

## Controle pareado concluído

Foram comparadas as oclusões superior e inferior de 10% no teste UBIPr, mantendo pesos de identidade, parâmetros de normalização, limiar e 486 consultas. No braço operacional, segmentação e geometria foram recalculadas sobre a imagem alterada. No controle, a máscara prevista na foto original não ocluída fixou suporte, caixa e elipses; os pixels alterados e a CLAHE continuaram sendo usados no reconhecimento.

| Oclusão de 10% | Pré-processamento | Rank-1 | TAR | FMR |
|---|---|---:|---:|---:|
| Superior |Recalculado|82,30%|84,98%|1,69%|
| Superior |Máscara e geometria originais fixas|89,71%|89,30%|1,12%|
| Inferior |Recalculado|58,23%|60,29%|2,61%|
| Inferior |Máscara e geometria originais fixas|84,77%|83,54%|1,39%|

A fixação recuperou36 identificações na oclusão superior (+7,41 pontos percentuais) e 129 na inferior (+26,54 pontos). Os IC95% descritivos pareados por pessoa para o ganho de Rank-1 foram 1,03–15,64 e 17,08–36,79 pontos, respectivamente. Para TAR, o intervalo superior incluiu zero (−1,85–11,32 pontos); o inferior foi 14,61–32,93 pontos. Esses intervalos são pontuais, sem correção de comparações múltiplas.

O controle não atingiu simultaneamente Rank-1≥90%, TAR≥90% e FMR≤1%. Ele mostra contribuição do bloco de segmentação, suporte, caixa e geometria; não separa o efeito de cada uma dessas partes. Mesmo com a geometria original, a perda de textura/contraste ainda afeta os descritores.

**Não é uma solução operacional:** a foto original não ocluída é uma informação adicional usada apenas neste diagnóstico. Nenhum novo resultado de foto única ou mínimo de área substitui o candidato congelado. O teste já foi examinado; este controle é posterior e exploratório. Os pesos externos continuam com população de pré-treinamento desconhecida.

A auditoria confirmou o mesmo limiar, todas as 486 consultas, igualdade da intervenção, validade idêntica à original e igualdade das entradas do cadastro e das seis consultas sem referência de área. A errata de descrição da primeira execução preserva o protocolo original e esclarece que a U-Net recebeu a foto original, enquanto o reconhecedor recebeu a imagem alterada.

## Ajuste concluído — apenas treino e validação

A U-Net original iniciou ajuste de até seis épocas com 7.716 imagens de 183 pessoas de treino e 1.652 imagens de 39 pessoas de validação. Em 50% dos exemplos de treino, pixels anotados de íris recebem cinza 128 em perdas superiores/inferiores aleatórias de 1% a 40% na entrada320×240. Os alvos anotados permanecem iguais: o modelo aprende a manter a região originalmente visível sob oclusão sintética, sem gerar ou restaurar textura RGB.

O checkpoint foi escolhido pela maximização do menor Dice de íris entre validação limpa, oclusão superior de 10% e inferior de 10%, exigindo que o Dice limpo não caia mais de 0,01 em relação ao original. A época 0 é incluída. Não há abertura ou inferência do teste nesse treinamento.

Após a seleção, o reconhecimento foi comparado apenas na validação, nas três condições registradas, com os mesmos pesos de identidade, limiar e normalização anteriores. Isso verifica utilidade prática da nova segmentação sem substituir automaticamente o candidato ou anunciar novo desempenho de teste.

## Evidências

- [Comparação e auditoria pareada](outputs/diagnostico_geometria_fixa_2026-10-21/CONCLUIDO.json).
- [Protocolo do controle](PROTOCOLO_DIAGNOSTICO_GEOMETRIA_2026-10-21.md).
- [Treinamento concluído](outputs/segmentacao_oclusao_2026-10-21/CONCLUIDO.json), checkpoint selecionado na época 3 de 6.
- [Comparação visual real](outputs/qa_segmentacao_oclusao_2026-10-21/comparacao_mascaras.png).

## Resultado da segmentação — checkpoint selecionado

| Condição da validação (1.652 imagens) | Dice da íris original | Dice da íris ajustada |
|---|---:|---:|
| Limpa |91,52%|91,42%|
| Oclusão superior de 10% |85,07%|92,19%|
| Oclusão inferior de 10% |77,65%|91,48%|

O Dice é sobreposição de máscara, não taxa de reconhecimento. Esta avaliação usa oclusão na grade de entrada320×240; a validação posterior do reconhecedor aplica a intervenção nos pixels nativos e segmenta novamente. A comparação de identificação foi concluída e está descrita a seguir.

![Máscaras antes e depois do ajuste](outputs/qa_segmentacao_oclusao_2026-10-21/comparacao_mascaras.png)

A imagem usa as primeiras consultas de quatro pessoas da validação com anotação não vazia, sem seleção por desempenho. O zoom baseado na anotação é apenas de exibição; a U-Net recebe a foto inteira reduzida, sem máscara de referência.

## Reconhecimento na validação — resultado concluído

São 482 consultas, 16 pessoas e 16 olhos candidatos do lado informado por consulta. Não confundir esta amostra com as 486 consultas do diagnóstico de teste ou as 1.652 imagens da seleção por Dice. Todos os casos permaneceram no denominador, inclusive falhas. Os pesos de identidade, normalização e limiar 0,8581747485460748 foram mantidos; a seleção da época foi feita somente por segmentação, antes desta comparação. Os templates do cadastro e as consultas foram regenerados com o respectivo segmentador.

| Segmentação | Condição | Rank-1 | TAR | FMR | Falhas |
|---|---|---:|---:|---:|---:|
|Original|Sem oclusão adicional|90,04%|90,66%|0,98%|4|
|Original|Oclusão superior de 10%|80,71%|78,01%|1,30%|4|
|Original|Oclusão inferior de 10%|59,96%|57,88%|2,41%|7|
|Ajustada|Sem oclusão adicional|88,59%|89,21%|0,98%|4|
|Ajustada|Oclusão superior de 10%|76,97%|71,37%|1,29%|4|
|Ajustada|Oclusão inferior de 10%|81,95%|79,25%|1,15%|4|

A segmentação ajustada melhorou a condição inferior em 21,99 pontos percentuais de Rank-1, mas reduziu o Rank-1 limpo de 90,04% para 88,59% e o superior de 80,71% para 76,97%. A melhora no Dice não se converteu em melhora geral da identificação. Não houve exclusão das falhas para recuperar métricas.

## Fusão fixa das duas segmentações da mesma foto

Hipótese exploratória registrada após observar a regressão limpa, antes do cálculo da fusão: média dos logits dos dois braços já normalizados por consulta e nova normalização por consulta, pesos iguais, mesmo limiar. A execução usa duas segmentações calculadas da mesma foto; não usa duas fotos, seleção por identidade ou detecção da condição de oclusão.

| Condição | Rank-1 | TAR | FMR |
|---|---:|---:|---:|
|Sem oclusão adicional|89,00%|90,46%|1,09%|
|Oclusão superior de 10%|80,71%|78,01%|1,16%|
|Oclusão inferior de 10%|74,48%|71,99%|1,44%|

A fusão também não satisfez o critério limpo de Rank-1≥90%, TAR≥90% e FMR≤1%; não foi promovida. Não foram testados outros pesos ou limiares para obter aprovação.

## Decisão e continuidade

O candidato congelado permanece inalterado: o teste anterior de 91,36% de Rank-1 e 92,39% de TAR e a fronteira de área já relatada continuam associados exclusivamente a ele. O novo segmentador e a fusão foram avaliados para identidade somente na validação, sem novo teste, confirmação independente ou novo mínimo de área.

O próximo desenvolvimento deve adaptar ou treinar o reconhecedor para as entradas do novo segmentador, incluindo oclusões e comparação das regiões válidas. A seleção precisa acompanhar identificação limpa e ocluída, além do Dice, usando treino/validação. O contraste entre Dice e reconhecimento desta rodada fornece evidência para esse desenho, mas não isola causalmente quais mudanças de suporte, caixa, elipse ou textura são responsáveis.

Foram aprovados63 testes, incluindo a preservação dos pixels ocluídos no controle fixo, a proibição de avaliar o novo segmentador no teste por este fluxo e a independência de consultas na fusão. Código, checkpoint, escores, protocolos e amostras foram preservados com verificação SHA-256.

- [Comparação pareada de reconhecimento](outputs/validacao_segmentacao_oclusao_identidade_2026-10-21/CONCLUIDO.json).
- [Fusão das duas segmentações](outputs/dupla_segmentacao_val_2026-10-21/CONCLUIDO.json).
