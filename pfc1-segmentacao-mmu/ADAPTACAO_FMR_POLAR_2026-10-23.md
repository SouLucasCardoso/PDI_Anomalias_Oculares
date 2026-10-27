# Penalização absoluta de escores impostores — 23/10/2026

## Conclusão

O piloto concluiu oito épocas, com parada antecipada e seleção da época 4. A penalização direta reduziu ligeiramente a FMR frente ao treino top3 anterior, mas perdeu identificação e TAR. O candidato **não passou ao critério de avanço**: as duas FMR continuam acima de 1%. A validação foi encerrada sem inferência; não houve uso do teste, substituição da referência principal ou novo mínimo de área.

## Referência calculada somente no ajuste

Antes de qualquer atualização de pesos, foi calculada uma referência de similaridade com os descritores originais limpos das 6.756 fotos das 167 pessoas de ajuste. Essas fotos contêm 1.742 consultas S2; 1.732 tiveram extração utilizável na condição limpa. As 287.512 comparações impostoras utilizáveis, restritas ao mesmo lado, definiram a referência de FMR empírica de até 1% pela função já usada no projeto: **0,27272370457649237**. As falhas de consulta foram mantidas no conjunto; não fornecem escores impostores para a estimativa.

Essa referência é um parâmetro fixo da perda, não o limiar de avaliação. Não utiliza fotos ou rótulos do monitor, validação ou teste. O limiar de avaliação do monitor continua sendo calculado somente na condição limpa de cada época e reaplicado às duas oclusões, como nos pilotos anteriores.

## Treinamento

As características existentes foram reutilizadas, sem nova inferência de imagens. Permanecem congelados a U-Net, o encoder e a normalização original. O novo adaptador começa com residual zero e semente 63; não reutiliza pesos rejeitados.

Mantêm-se 6.665 fotos válidas para ajuste, com 1.729 consultas S2 elegíveis para a perda de comparação, e 4.955 fotos limpas S1 de cadastro, agrupadas em 334 olhos. O cadastro é atualizado no início da época e permanece sem gradiente durante ela. A regra top3 e a margem contra o maior impostor do mesmo lado permanecem.

A nova parcela penaliza o quadrado de `relu((impostor - referência) / 0,1)`, na média dos piores ceil(1% × 166) olhos impostores por consulta: dois olhos. Acrescenta a proteção genuína `relu((referência + 0,05 - genuíno) / 0,1)` ao quadrado. Os escores por olho continuam sendo a média das melhores três fotos de cadastro, ou das disponíveis quando há menos de três.

A perda total combina alinhamento ao professor + 0,01 × residual ao quadrado + 0,1 × margem top3 + 0,1 × penalização absoluta. As condições limpa/superior/inferior mantêm pesos 4/1/1. AdamW 3e-4, decaimento 1e-4, lote 128 e FP32 permanecem fixos. O limite era 12 épocas, com parada após quatro épocas sem melhora da seleção, a partir da quinta; a execução parou na oitava. Não houve varredura de coeficientes, referências ou limiares.

O monitor mantém 480 consultas de 16 pessoas distintas do ajuste, com falhas, cadastro limpo, uma foto por consulta e lado informado. É reutilizado e já foi visto pelos encoders congelados; não constitui confirmação independente. A seleção mantém o controle limpo e prioriza passar ao critério completo antes dos indicadores ocluídos. A época selecionada foi a 4, e os pesos finais da época 8 foram preservados separadamente.

## Resultado do componente polar no monitor

| Condição | Rank-1 top3 anterior | Rank-1 com penalização | TAR top3 anterior | TAR com penalização | FMR anterior | FMR com penalização |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 0,9861% | 0,9861% |
| Perda superior de 10% | 404/480 (84,17%) | 401/480 (83,54%) | 377/480 (78,54%) | 376/480 (78,33%) | 1,4861% | 1,4167% |
| Perda inferior de 10% | 328/480 (68,33%) | 320/480 (66,67%) | 287/480 (59,79%) | 284/480 (59,17%) | 1,2917% | 1,2778% |

As aceitações impostoras passaram de 107 para 102 na superior e de 93 para 92 na inferior, sobre 7.200 comparações por condição. O máximo correspondente a 1% é 72: ainda há 30 e 20 acima desse limite. A redução veio com três e oito identificações corretas a menos e uma e três aceitações genuínas a menos, respectivamente.

Frente ao controle sem adaptação desta rodada, o Rank-1 ainda sobe de 82,50% para 83,54% na superior e de 60,63% para 66,67% na inferior. Isso não basta: o controle de FMR e a meta de 90% em Rank-1/TAR ocluídos continuam reprovados. O limiar de avaliação selecionado foi **0,28666180372238165**, diferente da referência fixa usada na perda. Uma falha de extração permaneceu na condição limpa e superior, e duas na inferior.

## Diagnóstico dos escores já calculados

O diagnóstico não treinou, filtrou consultas ou recalibrou limiares. Na condição superior, 93 das 480 consultas apresentam alguma aceitação impostora; 73 consultas respondem por 80% das 102 aceitações. Na inferior, são 83 consultas com alguma aceitação impostora, e 65 respondem por 80% das 92 aceitações. Portanto, os erros não estão restritos a um punhado de consultas extremas.

Além disso, 73 aceitações impostoras superiores e 42 inferiores ocorrem em consultas cujo Rank-1 está correto. Uma consulta pode ter escore genuíno maior que os impostores e ainda exceder o limiar para algum olho incorreto; Rank-1 e FMR medem aspectos diferentes. Esses resultados não justificam excluir consultas difíceis nem demonstram uma causa clínica ou geométrica dos erros.

## Verificação e preservação

Passaram 14 testes direcionados, incluindo exclusão de genuínos/falhas na referência, penalização de impostor alto, proteção genuína, ausência de gradiente no cadastro fixo, negativos do mesmo lado e equivalência top3 com o comparador. A auditoria refez a referência somente nas pessoas de ajuste e reproduziu exatamente os escores selecionados/finais, a época 4 selecionada e o bloqueio de avanço. Não refez as oito épocas de treinamento.

Os registros ficam em `outputs/adaptador_polar_fmr_2026-10-23` e `outputs/adaptador_polar_fmr_val_2026-10-23`. O pacote em `backups/adaptador_polar_fmr_2026-10-23` preserva 38 arquivos em 54 partes, incluindo pesos, cadastros, matriz da referência de ajuste, escores, diagnóstico e código. Todos foram restaurados com hashes conferidos. O cache externo de características é reaproveitado por hash, sem duplicação. A recuperação compacta reproduziu referência, seleção e decisões sem repetir as redes ou o treinamento. Não foram alteradas exceções do Defender; o envio pelo OneDrive não foi verificado.

```powershell
.\executar.ps1 preservar_adaptador_fmr.py
.\executar.ps1 verificar_adaptador_fmr.py --root "$env:TEMP/pfc-adaptador-fmr-restaurado-20261023"
```

## Consequência para a pesquisa

O ganho desta alteração é pequeno e acompanhado de perdas; ela não deve substituir o candidato anterior. Nenhuma das pequenas adaptações do descritor congelado demonstrou alcançar os critérios sob oclusão. O piloto posterior de correções espaciais no último bloco foi executado, mantendo o controle limpo e os kernels originais congelados. Melhorou o TAR, mas não passou ao critério de FMR. Ver [escopo, resultados e preservação](ENCODER_ESPACIAL_2026-10-23.md). Isso não constitui um teste de liberação completa de todos os pesos do bloco, nem uma conclusão causal sobre o gargalo.

Os números desta rodada pertencem a um componente no monitor de treino. Os **444/486 (91,36%)** do teste principal, a fusão e as fronteiras de área anteriormente registradas permanecem inalterados. Não há novo mínimo de área aceito.
