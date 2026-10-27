# Ajuste dos kernels do último bloco polar

## Pergunta e protocolo

Os pilotos anteriores treinaram correções de baixa ordem ou pooling de atenção. Este piloto testa uma hipótese distinta: ajustar os cinco kernels convolucionais originais de layer4, incluindo downsample 1×1, mantendo prefixo, projeção e todos os parâmetros/estatísticas BatchNorm congelados. São **8.388.608 pesos treináveis**. A inicialização usa somente o checkpoint polar original, sem incorporar pesos rejeitados. O descritor continua usando a média global, sem novo segmentador, atenção ou comparador local.

O protocolo foi registrado antes do treino. São 6.665 fotos elegíveis de ajuste de 167 pessoas, com cadastro limpo S1 de 4.955 fotos/334 olhos. O monitor tem 480 consultas de 16 pessoas separadas do ajuste, mas vistas pelos encoders anteriores e reutilizadas no desenvolvimento. Não é confirmação independente. Uma consulta usa uma foto e lado informado, com 16 olhos candidatos do mesmo lado. O cadastro pode conter várias fotos limpas.

Foram reutilizados por hash os 12.160 mapas FP32 de layer3 do piloto espacial. As perdas superior/inferior de 10% já estavam aplicadas na foto nativa, antes da segmentação automática e normalização polar originais. A referência só define a intervenção simulada. Cadastro S1 sempre limpo; a foto limpa correspondente à consulta não participa do escore na inferência. Não houve nova extração de imagens ou uso da validação/teste.

Semente 63, AdamW 1e-5, decaimento 1e-4, lote de 16 fotos com três condições, máximo de oito épocas e parada após três sem melhora, a partir da quarta. A perda é alinhamento ao descritor limpo da mesma foto durante o treino, com pesos 4/1/1, mais 0,1 da perda top3 contra o maior impostor do mesmo lado e 1e-4 da soma dos deslocamentos médios quadráticos dos kernels em relação ao original. Cadastro atualizado no início de cada época, sem gradiente na perda de identidade; esta atua apenas nas consultas S2 do ajuste. Não houve busca de taxa, pesos, arquitetura ou épocas adicionais após observar os resultados.

O controle inicial reproduziu as métricas do encoder original. Cada época calibra um limiar somente no monitor limpo, aplicado sem alteração às duas oclusões. Seleção e bloqueio seguem a regra registrada: preservar Rank-1/TAR limpos e FMR ≤1%; para avançar, melhorar Rank-1/TAR em ambas as oclusões mantendo FMR ≤1%. A elegibilidade limpa não equivale a aprovação completa.

## Resultado do componente polar no monitor de treino

Foram concluídas oito épocas; a época 8 foi selecionada.

| Condição | Rank-1 original | Rank-1 ajustado | TAR original | TAR ajustado | FMR original | FMR ajustada |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 99,79% | 99,79% | 0,9861% | 0,9861% |
| Superior 10% | 396/480 (82,50%) | 407/480 (84,79%) | 77,50% | 81,67% | 1,5694% | 1,6389% |
| Inferior 10% | 291/480 (60,63%) | 342/480 (71,25%) | 55,83% | 61,88% | 1,6528% | 1,3472% |

Na superior, foram 11 identificações e 20 aceitações genuínas adicionais; na inferior, 51 identificações e 29 aceitações genuínas adicionais. As falsas aceitações passaram de 113 para 118 na superior e de 119 para 97 na inferior, sobre 7.200 comparações por condição. O máximo permitido é 72. São 46 e 25 acima desse limite. O limiar selecionado foi 0,27963910500208544, calibrado somente no limpo; uma falha limpa/superior e duas inferiores foram mantidas.

Para Rank-1 de 90%, são necessárias 432 consultas corretas: faltam 25 na superior e 90 na inferior. Para TAR de 90%, faltam 40 e 135 aceitações genuínas. Esses déficits descrevem este monitor, sem estimar esforço ou garantir que sejam corrigíveis com mais épocas. Ajustar o limiar não altera Rank-1.

Frente à correção de baixa ordem anterior, o Rank-1 passou de 83,13%/68,13% para 84,79%/71,25%, com TAR de 81,67%/61,88% contra 80,63%/60,21%. Porém, a FMR ficou ligeiramente pior nas duas condições que nesse piloto anterior. Portanto, não há superioridade conjunta. Os ganhos no monitor reutilizado não demonstram generalização ou efeito clínico.

**Decisão: barrado antes da validação por FMR.** O ajuste dos kernels trouxe ganho de identificação sob oclusão, principalmente inferior, e preservou o limpo. Não resolveu os critérios completos. Não serão recalibrados limiares sobre o monitor ocluído para promover este candidato. A referência principal e os 444/486 (91,36%) do teste continuam inalterados; não há novo mínimo de área aprovado.

## Verificação e preservação

O teste direcionado passou, verificando equivalência inicial exata, cinco kernels/contagem de parâmetros treináveis, BatchNorm em avaliação, congelamento após atualização, regularização em relação ao original e restauração dos kernels. O treino conferiu os hashes dos parâmetros e buffers congelados antes/depois. A auditoria refez os descritores selecionados/finais nos mapas e reproduziu exatamente escores, cossenos, seleção, cadastros de ajuste e bloqueio. Não refez as oito épocas.

O PyTorch e a GPU executaram sem novo bloqueio de DLL nesta rodada. Uma tentativa de escrever diretamente via Python no diretório do OneDrive falhou; as saídas permaneceram em TEMP e foram preservadas pelo mecanismo de edição, sem alterar exceções de segurança. Não foi comprovado upload na nuvem.

O pacote de 31.591.947 bytes foi preservado em 43 partes base64, com 28 arquivos no ZIP. Inclui o checkpoint selecionado de 33,56 MB e uma diferença binária XOR reversível para o checkpoint final, evitando duplicação dos mesmos tensores. A reconstrução recupera os bytes exatos de ambos, com SHA-256 conferido; não há quantização ou mudança de pesos. O cache e os pesos do encoder original permanecem como dependências identificadas por hash. Duas partes divergentes na cópia inicial foram corrigidas antes da validação final do pacote. A restauração e a auditoria compacta passaram.

```powershell
.\executar.ps1 preservar_ajuste_bloco_polar.py
.\executar.ps1 auditar_ajuste_bloco_polar.py --root "$env:TEMP/pfc-bloco-restaurado-20261023"
```

Os registros legíveis estão em `outputs/ajuste_bloco_polar_treino_2026-10-23`; pesos e escores, em `backups/ajuste_bloco_polar_treino_2026-10-23`. Nenhum commit ou envio ao GitHub foi realizado nesta rodada.
