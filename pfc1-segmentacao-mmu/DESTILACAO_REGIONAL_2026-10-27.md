# Piloto estrutural de descritores regionais aprendidos — 27/10/2026

## Motivação e método

O comparador regional congelado de 23/10 teve Rank-1 limpo de 77,29%: as características intermediárias, treinadas para agregação global, não eram reconhecedores locais suficientes. O novo piloto aprende oito transformações regionais para aproximar descritores de identidade, em vez de repetir a comparação congelada ou ajustar novamente o limiar do piloto anterior.

Cada mapa original de 256 × 4 × 32 é dividido em oito setores angulares de quatro colunas, com média radial. Para cada setor, uma regressão ridge aprende a prever o descritor polar global limpo da mesma foto. A padronização, intercepto e coeficientes usam somente 151 pessoas de ajuste. A regularização é fixa em 0,01, sem busca. As 6.067 fotos e seus três mapas são mantidos, com pesos 4/1/1 e peso zero nas dez vistas inválidas. As intervenções de treino são exatamente as 3.222 preparadas no piloto de diversidade. A foto limpa pareada só serve de alvo no ajuste; não é usada para pontuar consultas na avaliação.

Na comparação, os oito descritores são normalizados por L2; o escore regional é a média das seis maiores concordâncias de setores correspondentes para cada par de fotos. O cadastro agrega as três melhores fotos S1 por olho, como o controle global. A hipótese primária usa **75% do escore global original e 25% do regional**, fixados antes do ajuste. São reportados controles global, regional isolado e fusão com todos os oito setores, sem escolher retrospectivamente o melhor deles. O descarte por par pode favorecer impostores e não representa remoção de 25% da área física: os campos receptivos são amplos e sobrepostos.

Há precedentes para comparação por regiões, por exemplo [Boyd et al., WACVW 2023](https://openaccess.thecvf.com/content/WACV2023W/XAI4B/html/Boyd_Human_Saliency-Driven_Patch-Based_Matching_for_Interpretable_Post-Mortem_Iris_Recognition_WACVW_2023_paper.html). Esse trabalho usa saliência humana e imagens pós-morte, condições diferentes das nossas. O piloto aqui é uma hipótese de engenharia própria, sem implementação ou validação equivalente àquele artigo e sem reconstrução de textura ausente.

## Protocolo e verificações

O protocolo foi salvo antes do ajuste e dos escores. Além das 151 pessoas de ajuste, há 16 para calibração interna limpa e 16 do monitor reutilizado. O limiar de cada método é calculado uma vez no grupo interno limpo, visando FMR de 0,5%, e aplicado sem mudança ao monitor. A avaliação tem uma consulta por foto, lado informado e 16 olhos candidatos do mesmo lado. Todas as falhas permanecem no denominador. Os encoders já viram essas populações: não se trata de confirmação independente.

A porta limpa exigia preservar Rank-1/TAR do controle global e FMR de até 1%, antes de avaliar qualquer oclusão do monitor. A fusão primária passou essa porta; somente então foram abertas as duas condições com perda de 10%. Para avançar, exigiam-se ganhos estritos de Rank-1 e TAR nas duas, com FMR de até 1% em todas as condições. Não houve inferência em validação ou teste.

Quatro testes passaram: ordenação dos setores, influência nula de linhas com peso zero, descarte fixo e agregação top-3, e invariância à ordem dos candidatos. A auditoria reconstruiu exatamente entradas de ajuste, coeficientes, escores, limiares e decisões.

## Resultados no monitor de treino — 480 consultas

| Método | Condição | Rank-1 | TAR | FMR |
|---|---|---:|---:|---:|
| Global original | Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 55/7200 (0,7639%) |
| Fusão primária, seis setores | Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 49/7200 (0,6806%) |
| Global original | Superior 10% | 396/480 (82,50%) | 369/480 (76,88%) | 97/7200 (1,3472%) |
| Fusão primária, seis setores | Superior 10% | 397/480 (82,71%) | 363/480 (75,63%) | 66/7200 (0,9167%) |
| Global original | Inferior 10% | 291/480 (60,63%) | 259/480 (53,96%) | 91/7200 (1,2639%) |
| Fusão primária, seis setores | Inferior 10% | 297/480 (61,88%) | 247/480 (51,46%) | 61/7200 (0,8472%) |

O limiar primário foi 0,29319307073536854. Houve pequeno ganho de identificação e redução de impostores, mas também rejeição adicional de genuínos. O critério completo falhou: **não foi promovido um candidato** e não foi encontrado novo mínimo de área. As diferenças pequenas não demonstram superioridade estatística.

O regional isolado teve 403/480 (83,96%) de Rank-1 e 284/480 (59,17%) de TAR no limpo, inferior ao global. Na fusão com todos os oito setores, o Rank-1 foi idêntico ao primário nas três condições; o TAR foi idêntico no limpo/superior e dois genuínos maior no inferior. A FMR ocluída foi 0,9444%/0,9167%. Portanto, este controle não demonstra vantagem conjunta de descartar setores; não se deve atribuir a queda de FMR exclusivamente à seleção das seis regiões.

Os percentuais são do monitor do componente polar, não do sistema principal nem de um teste independente. Em particular, a FMR abaixo de 1% aqui não significa que o objetivo do projeto foi atingido. O piloto corrigido anterior atingia maior Rank-1 inferior (65,42%), com FMR pior; a nova estratégia não o domina. A referência de teste principal continua 91,36% e as fronteiras nominais continuam 99,5% superior e 99% inferior.

## Decisão e arquivos

Encerrar esta formulação sem varrer proporções, quantidades de setores, regularização ou limiares no monitor. O descritor regional ainda é pouco discriminativo isoladamente; aumentar sua participação não tem justificativa por estes resultados. Uma representação local aprendida de ponta a ponta seria outro estudo, que exigiria novo protocolo e tempo de treinamento, sem garantia de terminar antes da entrega.

Código: `descritor_regional_aprendido.py`, `piloto_destilacao_regional.py`, `auditar_destilacao_regional.py`. Resultados legíveis: `outputs/destilacao_regional_treino_2026-10-27`. O modelo e os escores compactos são preservados em pacote local recuperável. O cache grande e a evidência de ajuste regenerável são identificados por hash, sem duplicação no pacote. Não houve mudança na segurança do Windows ou comprovação de sincronização do OneDrive.

O pacote de 26 arquivos, ZIP de 4.644.720 bytes em sete partes, foi restaurado com todos os hashes conferidos. A auditoria compacta sobre os arquivos restaurados também reproduziu as métricas, calibração e decisão de rejeição, sem depender dos mapas grandes.
