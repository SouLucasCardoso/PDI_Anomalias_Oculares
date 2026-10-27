# Retomada das melhorias de robustez em 23 de outubro de 2026

O usuário solicitou novas melhorias após a consolidação inicial do artigo. Essa orientação reabre o desenvolvimento; o limite da rodada anterior de fechamento permanece como registro daquela rodada, não como impedimento para o trabalho agora autorizado. O candidato original e seus resultados não serão sobrescritos.

## Evidência utilizada

O diagnóstico de geometria fixa já havia sido executado em 21/10 e não foi repetido. Com perda superior de 10%, o Rank-1 passou de 82,30% para 89,71%; com perda inferior de 10%, de 58,23% para 84,77%. A geometria fixa depende da foto original sem oclusão e não constitui solução de consulta única. A diferença mostra sensibilidade à extração, sem isolar um mecanismo causal único ou eliminar o efeito da informação removida.

As adaptações anteriores do segmentador, do encoder, da pupila circular/elíptica e do transporte de descritores não demonstraram melhoria suficiente para substituir a referência. Não serão anunciadas novamente como estratégias novas.

## Piloto de segmentação com três vistas

Será utilizada a média de probabilidades da U-Net congelada em três vistas da mesma imagem: original, espelhada horizontalmente com saída realinhada e contraste CLAHE no canal L de LAB. Os pesos de cada vista são iguais e não serão ajustados por resultados. O reconhecimento continua recebendo pixels da fotografia consultada, sem reconstrução de textura ou acesso à fotografia sem oclusão. Não se trata de três capturas.

O piloto avalia todas as 482 consultas de validação, com lado informado e 16 candidatos do mesmo lado. O cadastro tem 480 imagens originais e recebe a mesma regra de pré-processamento. As anotações apenas delimitam as intervenções digitais. Falhas continuam nos denominadores.

O protocolo foi registrado antes da inferência de reconhecimento. Executam-se exatamente as condições limpa, superior 10% e inferior 10%. As médias/desvios dos componentes e o limiar do candidato são ajustados uma vez na condição limpa de validação e mantidos sob oclusão. A calibração antiga é um controle secundário, não outra oportunidade de escolher o resultado mais favorável.

Para considerar avanço elegível, exige-se Rank-1 e TAR limpos de pelo menos 90% e FMR de até 1%; nas duas oclusões, Rank-1 e TAR devem superar a referência e FMR deve permanecer em até 1%. Mesmo uma aprovação não promove automaticamente o candidato nem autoriza tratá-lo como confirmação independente. O teste não é utilizado neste piloto. A validação já foi reutilizada no desenvolvimento e sua incerteza de seleção permanece.

Código: `validar_segmentacao_multivista.py`. Dois testes direcionados passaram: realinhamento espacial do espelhamento com média de probabilidades e carregamento exato dos pesos congelados.

Resultados de execução: `%TEMP%\pfc-tcc-resultados\segmentacao_multivista_val_2026-10-23`. A inferência das três condições foi concluída. Nenhum novo mínimo de área foi estabelecido nesta retomada.

## Consenso de duas extrações da mesma fotografia

Após observar apenas a condição limpa da segmentação multivista, foi registrado um segundo piloto fixo: combinar em partes iguais os logits dos escores da referência e do candidato, seguidos da mesma normalização por consulta. O protocolo foi salvo antes de consultar os resultados ocluídos da nova segmentação. Não houve varredura de pesos ou escolha do melhor ramo por consulta. O limiar foi calibrado somente na condição limpa e mantido sob oclusão. Disponibilidade e validade exigiram os dois ramos; falhas não foram descartadas.

## Resultados concluídos

Os valores abaixo são da **validação**, com 482 consultas e 7.230 comparações impostoras por condição. Não devem ser confundidos com os 91,36% do teste original. Cada candidato usa uma calibração própria obtida somente na validação limpa. O controle com calibração antiga da segmentação multivista também foi preservado, sem usá-lo para escolher uma estratégia vencedora.

| Método | Condição | Rank-1 (%) | TAR (%) | FMR (%) |
|---|---|---:|---:|---:|
| Referência | Limpa | 90,04 | 90,66 | 0,9820 |
| Referência | Superior 10% | 80,71 | 78,01 | 1,3001 |
| Referência | Inferior 10% | 59,96 | 57,88 | 2,4066 |
| Segmentação multivista | Limpa | 89,83 | 89,42 | 0,9820 |
| Segmentação multivista | Superior 10% | 78,84 | 78,42 | 1,4523 |
| Segmentação multivista | Inferior 10% | 59,54 | 57,68 | 2,3513 |
| Consenso fixo 50/50 | Limpa | 90,66 | 89,63 | 0,9820 |
| Consenso fixo 50/50 | Superior 10% | 79,46 | 78,22 | 1,3140 |
| Consenso fixo 50/50 | Inferior 10% | 60,58 | 57,88 | 2,3513 |

O consenso produziu 437 identificações corretas na condição limpa, contra 434 da referência, mas aceitou 432 genuínos, contra 437. São necessários pelo menos 434 genuínos aceitos entre 482 para atingir TAR de 90%. Portanto, o ganho de três identificações não representa aprovação: o TAR limpo falhou e a robustez sob oclusão permaneceu insuficiente. A condição inferior teve dez falhas de extração nos candidatos, contra sete na referência; todas permaneceram nas métricas.

**Nenhum dos dois candidatos passou o critério registrado ou substituiu a referência.** Não houve inferência no teste, alteração dos resultados originais ou recalibração por condição ocluída. A fronteira anteriormente publicada continua associada exclusivamente ao reconhecedor original.

## Verificação e preservação

Quatro testes direcionados passaram. A auditoria reproduziu exatamente os escores da fusão e do consenso, as decisões, os limiares limpos e a reprovação dos critérios. Foram conferidos os arquivos CSV das seis avaliações da segmentação multivista e a igualdade exata das quatro entradas do cadastro entre as três condições.

Os registros legíveis estão em `outputs/segmentacao_multivista_val_2026-10-23` e `outputs/consenso_geometrias_val_2026-10-23`. Os componentes, escores finais, CSVs e códigos possuem pacote restaurável em `backups/robustez_multivista_2026-10-23`, em 43 partes. Os 55 arquivos foram restaurados com todos os hashes conferidos. O pacote tem 2.055.725 bytes. Os caches de imagens são reproduzíveis e não integram esse pacote. Nenhuma exceção foi adicionada ao Defender; o envio efetivo ao OneDrive não foi verificado. As partes `.b64` seguem a exclusão já existente do Git.

Para recuperar os artefatos compactos:

```powershell
.\executar.ps1 preservar_piloto_multivista.py
```

## Direção seguinte

Esses resultados não justificam insistir em médias de vistas ou ajustar seus pesos para recuperar a meta. A hipótese de aprender a geometria externa em coordenadas da fotografia foi implementada na rodada seguinte, com pessoas distintas de ajuste e monitoramento. A segunda formulação passou o controle geométrico e elevou o Rank-1 inferior de 59,96% para 63,49% na validação, mas prejudicou as condições limpa e superior e não foi promovida. Ver [treinamento, resultados e preservação do contorno externo](CONTORNO_EXTERNO_2026-10-23.md). Nenhuma nova avaliação no teste foi executada. Não há garantia antecipada de atingir 90% sob oclusão.
