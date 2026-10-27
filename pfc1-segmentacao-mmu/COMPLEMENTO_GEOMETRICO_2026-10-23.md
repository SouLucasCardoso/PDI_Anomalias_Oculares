# Complemento geométrico com ramo original preservado — 23/10/2026

Foi executado o próximo piloto: combinar o descritor polar original com o descritor da geometria externa corrigida, em vez de substituir o primeiro. O resultado limpo foi preservado, mas a robustez não melhorou de forma suficiente. O candidato foi rejeitado no monitor do treino, sem inferência na validação ou no teste e sem novo mínimo de área.

## Protocolo registrado antes da execução

O experimento utiliza as mesmas 960 fotos de 16 pessoas do monitor interno, com 480 consultas da segunda sessão e cadastro limpo da primeira. Os encoders congelados já viram essas pessoas anteriormente, e o monitor é reutilizado: não se trata de evidência independente de generalização.

A combinação concatena os descritores multiplicados pelas raízes de 0,75 e 0,25. Assim, a similaridade entre fotos atribui contribuição fixa de 75% ao original e 25% ao corrigido, antes da mesma agregação das três melhores fotos de cadastro. Não houve busca de pesos, treinamento adicional nem uso dos pesos do adaptador rejeitado. As duas extrações são da mesma foto de consulta; o lado informado restringe a comparação a 16 olhos candidatos. A foto limpa correspondente não é usada na inferência ocluída.

Para cada opção, o limiar é definido uma vez na condição limpa para FMR empírica de até 1% e mantido nas oclusões. Todas as consultas e falhas permanecem nos denominadores. A combinação exige extração válida dos dois ramos, sem substituição oportunista de ramo inválido. A intervenção cinza de 10% usa a anotação apenas para definir os pixels afetados; a segmentação do reconhecedor continua automática. As características são calculadas em FP32, com lote máximo de 32 fotos.

## Resultados do descritor polar no monitor

| Condição | Rank-1 original | Rank-1 combinado | TAR original | TAR combinado | FMR original | FMR combinado |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 0,9861% | 0,9861% |
| Perda superior de 10% | 396/480 (82,50%) | 394/480 (82,08%) | 372/480 (77,50%) | 371/480 (77,29%) | 1,5694% | 1,5000% |
| Perda inferior de 10% | 291/480 (60,63%) | 296/480 (61,67%) | 268/480 (55,83%) | 262/480 (54,58%) | 1,6528% | 1,3750% |

Houve uma falha de extração na condição limpa e na superior, e duas na inferior, em ambas as opções. O controle corrigido isolado reproduziu exatamente as métricas da rodada anterior; o controle original limpo também foi reproduzido.

O ganho inferior de cinco identificações veio acompanhado de seis aceitações genuínas a menos. Na condição superior houve duas identificações e uma aceitação a menos. Além disso, a FMR permaneceu acima de 1% em ambas as oclusões. Portanto, **o critério de avanço foi reprovado**, embora a condição limpa tenha sido preservada. A opção combinada também não atingiu a meta absoluta de 90% em Rank-1 e TAR nas oclusões.

Esses números são do componente polar no monitor interno, não da fusão completa do artigo. Não devem ser comparados como se fossem uma nova avaliação dos 91,36% do teste original.

## Verificação e preservação

Passaram seis testes direcionados: dois da combinação e quatro do adaptador/monitor reutilizado, incluindo o teste de cadastro limpo. A auditoria refez a combinação a partir dos descritores salvos e reproduziu exatamente os escores, decisões e reprovação do critério. O pacote restaurável exclui o cache de características, registrado por hash, e mantém os escores necessários para conferir as decisões sem nova inferência das redes.

Os registros estão em `outputs/complemento_geometrico_monitor_2026-10-23`; o pacote e seu inventário ficam em `backups/complemento_geometrico_monitor_2026-10-23`. A recuperação compacta confere os hashes e as decisões, sem repetir a extração de características. Não foi alterada nenhuma exceção do Defender e não foi verificada a conclusão do envio pelo OneDrive.

```powershell
.\executar.ps1 preservar_complemento_geometrico.py
.\executar.ps1 verificar_complemento_geometrico.py --root "$env:TEMP/pfc-complemento-restaurado-20261023"
```

## Consequência e direção seguinte

O piloto não sustenta usar esta combinação fixa. A referência principal permanece em 444/486 (91,36%) sem oclusão no teste, sem revisão das fronteiras de área já registradas. Uma próxima hipótese é trabalhar a tolerância do descritor à oclusão mantendo a normalização original, pois a troca de geometria continua introduzindo uma diferença de representação relevante. Isso exigirá protocolo próprio, preservação do controle limpo e seleção somente no treino; ainda não foi executado nesta rodada. Não será feita varredura de pesos nesta mesma amostra para tentar promover o resultado rejeitado.
