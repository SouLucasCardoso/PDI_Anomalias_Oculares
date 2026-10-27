# Perda de identidade no adaptador polar — 23/10/2026

## Conclusão

Foi executado o treinamento que combina alinhamento ao descritor limpo e separação supervisionada de identidades. A época 12 preservou o desempenho limpo, mas não reduziu suficientemente as aceitações impostoras. Frente à adaptação anterior, acrescentou dois acertos superiores e um inferior, com FMR ligeiramente pior nas duas oclusões. **Não foi aprovado o avanço à validação**, não houve inferência no teste e nenhum novo mínimo de área foi estabelecido.

## Método registrado antes do ajuste

Foram reutilizadas, com hash conferido, as características das 7.716 fotos do treino original nas três condições já preparadas: limpa e oclusão superior/inferior de 10%. Não houve nova segmentação, extração das redes ou alteração de geometria. Nenhum peso do adaptador rejeitado foi reutilizado: o novo adaptador começou com residual zero e semente 63.

O ajuste manteve 6.665 fotos válidas de 167 pessoas. O monitor contém as mesmas 960 fotos de 16 pessoas e 480 consultas, sem exclusão de falhas. O monitor já foi usado nas tentativas anteriores e seus participantes foram vistos pelos encoders congelados; não constitui confirmação independente.

Foi construído um protótipo por olho das pessoas de ajuste: média normalizada dos descritores limpos da primeira sessão, usando 4.955 fotos e formando 334 protótipos. Esses protótipos permaneceram congelados. A nova perda de entropia cruzada usa apenas as 1.729 fotos de segunda sessão elegíveis do ajuste, nas três condições, com negativos do mesmo lado do olho. As fotos de cadastro não entram nessa perda; continuam na perda de alinhamento ao professor. Nenhuma identidade do monitor fornece protótipos ou gradientes.

A perda total é alinhamento ao professor + 0,01 × média do residual ao quadrado + 0,1 × entropia cruzada de identidade, com temperatura fixa de 0,1. As condições limpa/superior/inferior são ponderadas em 4/1/1. Foram usadas 12 épocas, AdamW 3e-4, decaimento 1e-4, FP32 e lote de 128 fotos, sem varredura de coeficientes ou temperatura. A normalização das características utiliza somente fotos limpas do ajuste.

O controle limpo exige Rank-1/TAR pelo menos iguais à época zero e FMR de até 1%. Entre épocas elegíveis, a seleção prioriza passar ao critério completo do monitor; depois, o TAR da pior oclusão, o Rank-1 da pior oclusão, a menor pior FMR e o alinhamento médio ao professor nas oclusões. Um único limiar é calibrado na condição limpa de cada época e reaplicado às oclusões. O cadastro do monitor permanece limpo em todas as condições, com uma foto por consulta, lado informado e 16 olhos candidatos.

## Resultado do componente polar no monitor — 480 consultas

| Condição | Rank-1 sem adaptação | Adaptação anterior | Com perda de identidade | TAR com identidade | FMR com identidade |
|---|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 0,9861% |
| Perda superior de 10% | 396/480 (82,50%) | 405/480 (84,38%) | 407/480 (84,79%) | 380/480 (79,17%) | 1,6111% |
| Perda inferior de 10% | 291/480 (60,63%) | 328/480 (68,33%) | 329/480 (68,54%) | 290/480 (60,42%) | 1,5000% |

Na adaptação anterior, os TAR superior/inferior eram 79,17%/60,00%, e as FMR eram 1,5139%/1,4861%. A nova perda passou de 109 para 116 aceitações impostoras superiores e de 107 para 108 inferiores, sobre 7.200 comparações por condição. Portanto, **não demonstrou a redução de FMR buscada**, apesar do pequeno ganho de Rank-1. O limiar limpo selecionado foi 0,2907864352067312. Houve uma falha de extração limpa/superior e duas inferiores, todas contabilizadas.

Os números são do descritor polar isolado no monitor de treino, não da fusão principal ou de uma nova avaliação do teste. O resultado principal permanece 444/486 (91,36%) sem oclusão no teste, com as fronteiras nominais de área anteriores preservadas.

## Correção técnica e verificação

A primeira execução interrompeu na primeira chamada da entropia cruzada, antes de atualizar qualquer peso: os rótulos NumPy foram convertidos pelo Windows para tensores int32, mas a função exige int64. A conversão explícita para `torch.long` foi incluída e coberta por teste. O ajuste foi reiniciado do zero, com os mesmos parâmetros, na pasta `adaptador_polar_identidade_v2_2026-10-23`. O registro anterior permanece como interrupção técnica, não como resultado experimental.

Passaram oito testes direcionados, incluindo negativos do mesmo lado, protótipos sem gradiente, ausência de perda de identidade para fotos de cadastro, compatibilidade int32/int64, seleção do critério completo e manutenção do cadastro limpo. A auditoria reproduziu os protótipos a partir das pessoas de ajuste, a padronização, os escores selecionados/finais e a escolha da época 12. A validação condicional foi encerrada sem inferência pelo bloqueio de FMR.

Foram preservados **35 arquivos em 31 partes**, incluindo os pesos, protótipos, escores e registros da interrupção técnica. Todos foram restaurados com hashes conferidos; a verificação compacta reproduziu a seleção e as decisões. O cache externo de características foi reaproveitado e registrado por hash, sem duplicação. Não foram alteradas exceções do Defender, e o envio pelo OneDrive não foi verificado.

```powershell
.\executar.ps1 preservar_adaptador_identidade.py
.\executar.ps1 verificar_adaptador_identidade.py --root "$env:TEMP/pfc-adaptador-identidade-restaurado-20261023"
```

Os registros legíveis estão em `outputs/adaptador_polar_identidade_v2_2026-10-23` e `outputs/adaptador_polar_identidade_v2_val_2026-10-23`. A preservação está em `backups/adaptador_polar_identidade_v2_2026-10-23`. Para a auditoria completa no cache original, usa-se `verificar_adaptador_identidade.py --root "$env:TEMP/pfc-tcc-resultados" --features`; a recuperação compacta não repete o treinamento nem o avanço das redes.

## Direção seguinte

O protótipo médio usado na perda não reproduz exatamente o comparador, que agrega as três melhores fotos de cadastro por olho. O piloto posterior com múltiplos cadastros e negativos difíceis foi concluído: reduziu a FMR frente a esta formulação, mas permaneceu acima de 1% e foi barrado antes da validação. Ver [método top3 e resultados](ADAPTACAO_TOP3_POLAR_2026-10-23.md). Não será ajustado um limiar nas oclusões para promover este candidato rejeitado.
