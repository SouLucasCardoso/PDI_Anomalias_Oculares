# Correções espaciais no último bloco do encoder polar — 23/10/2026

## Conclusão

Foi concluído um piloto de oito épocas com correções treináveis dentro das quatro convoluções do último bloco do ResNet18 polar. A época 6 foi selecionada. Preservou o resultado limpo e melhorou o TAR nas duas oclusões frente ao encoder sem adaptação. Porém, a FMR ficou em **1,5833% e 1,3056%**, acima de 1%. O candidato foi barrado antes da validação, sem uso do teste ou mudança do mínimo de área.

Este piloto **não libera todos os pesos do último bloco**. Treina correções de baixa ordem, com 145.408 parâmetros, mantendo os kernels originais congelados. Seu resultado não demonstra que um ajuste completo do bloco seja ineficaz; testa somente esta formulação de custo controlado.

## Arquitetura e controle de custo

Cada convolução de `layer4` recebeu uma correção aditiva: convolução 3×3 com oito canais intermediários, seguida de convolução 1×1 para o número original de saídas. A convolução de saída inicia em zero, preservando a função original antes do ajuste. As quatro correções totalizam 145.408 parâmetros.

Permanecem congelados o prefixo até `layer3`, os kernels originais de `layer4`, a redução de dimensão do bloco, a projeção e todos os parâmetros e estatísticas de BatchNorm. Somente os pesos das novas correções recebem gradientes. Os checkpoints preservam essas correções; a reconstrução requer o checkpoint polar original, identificado pelo SHA256 no protocolo e presente durante a verificação.

Foi criado um cache FP32 de mapas 256×4×32: 7.716 fotos limpas mais duas condições ocluídas das 2.222 fotos S2, totalizando 12.160 mapas e **1.593.835.648 bytes**. O cadastro S1 permanece limpo. As três referências de entrada para uma foto S1 apontam ao mesmo mapa limpo; assim, sua perda de alinhamento continua limpa. A referência de elegibilidade das 6.665 fotos de ajuste foi mantida, sem ampliar a amostra por essa mudança.

As oclusões foram aplicadas na foto nativa, antes da U-Net e da normalização polar originais, afetando exatamente 10% da área anotada superior/inferior. A anotação apenas define a intervenção; o reconhecedor extrai sua própria máscara. O cache terminou em aproximadamente 169 segundos, reproduzindo os descritores limpos anteriores com diferença máxima zero. A validade das extrações ocluídas S2 também foi reproduzida. O cache será reaproveitável em novos pilotos do bloco, sem repetir o prefixo e a segmentação.

## Ajuste e seleção

O ajuste usa as mesmas 6.665 fotos de 167 pessoas e cadastro limpo de 4.955 fotos S1 de 334 olhos. A perda de comparação atua apenas nas 1.729 consultas S2 elegíveis do ajuste. A cada início de época, o cadastro é recalculado com a correção corrente e congelado durante a época. O escore usa média das três melhores fotos por olho e o impostor de maior escore do mesmo lado; o cadastro não recebe gradiente nessa perda.

A perda é alinhamento ao descritor limpo da mesma foto + 0,1 × margem top3 contra o maior impostor + 1e-4 × soma das médias dos pesos de saída das correções ao quadrado. As condições limpa/superior/inferior têm pesos 4/1/1. Mantêm-se margem e temperatura de 0,1 na comparação. Foram fixados semente 63, FP32, AdamW 1e-4, decaimento 1e-4, lote de 16 fotos e máximo de oito épocas, com parada após três épocas sem melhora, a partir da quarta. Não houve varredura de rank, taxa ou pesos de perda.

O monitor preserva todas as 960 fotos e 480 consultas de 16 pessoas distintas do ajuste, com falhas, cadastro limpo, uma foto por consulta e lado informado. Esses participantes já foram vistos pelos encoders, e o monitor é reutilizado: não é uma avaliação independente. Um único limiar é calibrado na condição limpa de cada época e aplicado sem alteração às duas oclusões. A elegibilidade exige preservar Rank-1/TAR limpos e FMR limpa de até 1%; a seleção prioriza passar ao critério completo e depois maximiza o desempenho da pior oclusão, conforme registrado.

## Resultado do componente polar no monitor — 480 consultas

| Condição | Rank-1 sem adaptação | Rank-1 espacial selecionado | TAR sem adaptação | TAR espacial selecionado | FMR sem adaptação | FMR espacial selecionada |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 0,9861% | 0,9861% |
| Perda superior de 10% | 396/480 (82,50%) | 399/480 (83,13%) | 372/480 (77,50%) | 387/480 (80,63%) | 1,5694% | 1,5833% |
| Perda inferior de 10% | 291/480 (60,63%) | 327/480 (68,13%) | 268/480 (55,83%) | 289/480 (60,21%) | 1,6528% | 1,3056% |

Foram três e 36 identificações corretas adicionais e 15 e 21 aceitações genuínas adicionais frente ao encoder sem adaptação. As aceitações impostoras ficaram em **114 e 94**, sobre 7.200 comparações por condição, ainda acima do máximo de 72 correspondente a 1%. O limiar selecionado foi 0,2832773824532827. Permaneceu uma falha de extração limpa/superior e duas inferiores.

Frente ao piloto top3 global anterior, o TAR melhora de 78,54%/59,79% para 80,63%/60,21%, mas o Rank-1 cai de 84,17%/68,33% para 83,13%/68,13%, e a FMR piora de 1,4861%/1,2917% para 1,5833%/1,3056%. Portanto, não há superioridade conjunta. A época final 8 teve mais acertos ocluídos, mas não substitui a época 6 selecionada pelo critério registrado; seus pesos e escores foram preservados separadamente.

Os cossenos auxiliares agora incluem cadastros S1 sempre limpos nas condições ocluídas. Não são diretamente comparáveis aos diagnósticos dos pilotos anteriores que também alteravam S1 antes de substituí-lo por limpo na montagem do escore. A regra biométrica sempre usou cadastro limpo; a referência sem correções reproduziu exatamente suas métricas anteriores. Nenhum cosseno auxiliar é usado como escore de identificação da consulta.

## Verificação e preservação

Passaram 12 testes direcionados, incluindo equivalência inicial com o encoder original, somente correções treináveis, BatchNorm em avaliação, invariância dos pesos congelados após atualização e restauração das correções, além dos testes da comparação top3 e do monitor. O treinamento conferiu o hash de todos os parâmetros e buffers congelados antes e depois do ajuste: permaneceram iguais.

A auditoria refez o avanço do último bloco nos mapas armazenados e reproduziu escores, cossenos e seleção. Conferiu também a origem exclusiva dos cadastros nas pessoas de ajuste e a reconstrução sobre os pesos originais. Não refez as oito épocas de treinamento. A validação condicional foi encerrada sem inferência pelo bloqueio de FMR.

Os registros legíveis estão em `outputs/encoder_polar_espacial_2026-10-23` e `outputs/encoder_polar_espacial_val_2026-10-23`. O pacote em `backups/encoder_polar_espacial_2026-10-23` contém 33 arquivos em 32 partes, incluindo correções selecionadas/finais, escores, cadastros, protocolos e código. O cache de mapas e seus índices foram excluídos do pacote e registrados por hash. A restauração verifica cada arquivo e permite reproduzir seleção e decisões sem nova inferência de fotos. Ela depende do checkpoint original identificado no protocolo; não contém uma segunda cópia dele. Não foram alteradas exceções do Defender, e o envio pelo OneDrive não foi verificado.

```powershell
.\executar.ps1 preservar_encoder_espacial.py
.\executar.ps1 verificar_encoder_espacial.py --root "$env:TEMP/pfc-encoder-espacial-restaurado-20261023"
```

## Consequência para a pesquisa

O piloto mostra que é viável treinar correções espaciais dentro do orçamento, sem modificar os pesos congelados ou perder o controle limpo. Não resolveu, contudo, o desempenho sob oclusão ou a FMR exigida. Os resultados pertencem ao componente polar no monitor interno, não à fusão principal ou ao teste.

O próximo trabalho deve examinar a relação entre calibração, comparação e fusão nas pessoas de treino antes de ampliar novamente o treinamento. Não há evidência nesta rodada para relaxar o critério, recalibrar nas oclusões do monitor ou promover este candidato. A referência principal permanece em **444/486 (91,36%)** sem oclusão no teste, sem novo mínimo de área aceito.
