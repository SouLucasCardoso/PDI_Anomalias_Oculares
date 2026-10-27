# Cadastro múltiplo e negativos difíceis no adaptador polar — 23/10/2026

## Resultado

Foi concluído um piloto de 12 épocas que aproxima a perda do comparador real: média das três melhores similaridades por olho e competição contra o olho impostor mais semelhante do mesmo lado. A época 11 foi selecionada pelo critério registrado. Reduziu a FMR frente à perda com protótipos médios, mas ficou acima de 1% nas duas oclusões e perdeu alguns acertos. **O candidato foi barrado antes da validação**, sem inferência no teste ou mudança do mínimo de área.

## Método e limites

Foram reutilizadas as características já extraídas das 7.716 fotos do treino original. O ajuste manteve 6.665 fotos válidas de 167 pessoas. O cadastro da perda contém 4.955 fotos limpas S1, agrupadas em 334 olhos, com até 17 fotos por olho. A perda de comparação usa apenas as 1.729 fotos S2 elegíveis do ajuste; as fotos S1 também participam do alinhamento ao professor limpo. As pessoas do monitor não fornecem gradientes ou cadastros à perda.

A cada início de época, os descritores do cadastro de ajuste são atualizados com o adaptador corrente, sem gradiente, e mantidos fixos durante essa época. O escore por olho é a média das melhores min(3, quantidade disponível) similaridades cosseno. O negativo difícil é o maior escore entre os outros olhos do mesmo lado. A perda adicional é `softplus((negativo + 0,1 - genuíno) / 0,1)`, ponderada em 0,1 na perda total. Mantêm-se o alinhamento ao professor e a regularização residual 0,01, com condições limpa/superior/inferior ponderadas em 4/1/1.

O cadastro fixo dentro de cada época é uma aproximação computacional: não há gradiente simultâneo pelos descritores de cadastro. No monitor, tanto consulta como cadastro são recalculados com o mesmo adaptador ao final da época. Isso aproxima a regra de agregação, mas não constitui uma reprodução exata de toda a otimização do sistema completo.

A normalização original, a U-Net e o encoder continuam congelados. O novo adaptador iniciou com residual zero, semente 63, AdamW 3e-4, decaimento 1e-4, FP32 e lote de 128 fotos. Não houve nova inferência das redes de imagens, alteração dos coeficientes ou busca de margens/temperatura. Os hashes dos cadastros atualizados foram registrados por época.

O monitor mantém todas as 960 fotos e 480 consultas de 16 pessoas distintas do ajuste, incluindo falhas. Cada consulta usa uma foto e lado informado, com 16 olhos candidatos; os cadastros permanecem limpos em todas as condições. Os encoders já viram essas pessoas, e o monitor é reutilizado: seus resultados não são uma confirmação independente. Cada época recebe um único limiar na condição limpa, reutilizado nas oclusões. A elegibilidade e a seleção seguem os critérios registrados da rodada anterior, priorizando passar ao critério completo antes de maximizar TAR e Rank-1 ocluídos.

## Resultado do componente polar no monitor

| Condição | Rank-1 sem adaptação | Rank-1 perda anterior | Rank-1 top3 selecionado | TAR top3 | FMR anterior | FMR top3 |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 0,9861% | 0,9861% |
| Perda superior de 10% | 396/480 (82,50%) | 407/480 (84,79%) | 404/480 (84,17%) | 377/480 (78,54%) | 1,6111% | 1,4861% |
| Perda inferior de 10% | 291/480 (60,63%) | 329/480 (68,54%) | 328/480 (68,33%) | 287/480 (59,79%) | 1,5000% | 1,2917% |

A perda anterior corresponde à entropia cruzada com protótipos médios. Seus TAR superior/inferior eram 79,17%/60,42%. A nova perda reduziu as aceitações impostoras de 116 para 107 na superior e de 108 para 93 na inferior, em 7.200 comparações por condição. Na superior, perdeu três identificações e três aceitações genuínas; na inferior, perdeu uma identificação e três aceitações genuínas. Para FMR de até 1% nesse denominador, seriam permitidas no máximo 72 aceitações impostoras: ainda há 35 e 21 acima desse limite. Isso não informa quais ajustes as eliminariam sem perda de TAR.

Frente ao controle sem adaptação, o candidato ainda ganha oito identificações na superior e 37 na inferior, e melhora o TAR nas duas. O limiar selecionado é 0,28729513287544256. As falhas permanecem uma na condição limpa/superior e duas na inferior. A época final 12 foi preservada, mas não substitui a época 11 selecionada: terminou com 404 e 324 acertos nas oclusões.

Nenhuma época passou ao critério completo: preservar o limpo, melhorar Rank-1/TAR nas duas oclusões e FMR de até 1% em ambas. O resultado também não atinge os 90% de Rank-1/TAR ocluídos. Os percentuais da tabela pertencem ao componente polar no monitor, não ao teste ou à fusão completa do artigo. O resultado principal segue em 444/486 (91,36%) sem oclusão no teste.

## Verificação e preservação

Passaram 11 testes direcionados, incluindo equivalência numérica entre a agregação diferenciável e o comparador real, cossenos negativos, padding, olhos com menos de três cadastros, negativos do mesmo lado, ausência de gradiente no cadastro fixo e rótulos int32/int64. A auditoria conferiu que os cadastros provêm somente de fotos S1 válidas das pessoas de ajuste, reproduziu a padronização e os escores selecionados/finais e confirmou a seleção da época 11. Os hashes dos cadastros por época estão registrados; a auditoria não refez as 12 épocas para reconstruí-los.

Os registros legíveis ficam em `outputs/adaptador_polar_top3_2026-10-23` e `outputs/adaptador_polar_top3_val_2026-10-23`; o pacote restaurável fica em `backups/adaptador_polar_top3_2026-10-23`. Foram preservados 33 arquivos em 25 partes, incluindo pesos selecionados/finais, índices dos cadastros, escores, protocolos e código. Todos foram restaurados com hashes conferidos. O cache externo é reaproveitado por hash e não duplicado. A recuperação compacta verifica seleção e decisões sem repetir o treinamento ou as redes. Não foram alteradas exceções do Defender, e o envio pelo OneDrive não foi verificado.

```powershell
.\executar.ps1 preservar_adaptador_top3.py
.\executar.ps1 verificar_adaptador_top3.py --root "$env:TEMP/pfc-adaptador-top3-restaurado-20261023"
```

## Direção seguinte

A margem entre escore genuíno e maior impostor melhora ordenação relativa, mas não impõe diretamente uma taxa absoluta de aceitações impostoras com limiar limpo. O piloto posterior de penalização absoluta com referência definida somente no ajuste foi executado: reduziu ligeiramente a FMR, com perda de identificação/TAR, e permaneceu barrado antes da validação. Ver [penalização e diagnóstico](ADAPTACAO_FMR_POLAR_2026-10-23.md). Não será recalibrado um limiar nas oclusões do monitor para promover este candidato rejeitado.
