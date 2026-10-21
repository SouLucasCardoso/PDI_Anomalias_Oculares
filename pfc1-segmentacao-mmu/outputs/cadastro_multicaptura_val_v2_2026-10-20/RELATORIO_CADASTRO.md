# Cadastro multicaptura e recorte automático — validação de 20/10/2026

## 1. Execução concluída

Foram concluídas onze variantes, mantendo os pesos de identidade e segmentação congelados. A base de desenvolvimento tem 962 imagens de 16 pessoas e 32 olhos: 480 capturas da sessão 1 para cadastro e 482 consultas da sessão 2. Nenhum novo escore de teste ou oclusão foi gerado.

As variantes neurais comparam máscara de referência e máscara automática da U-Net, com cadastro de uma foto, máximo entre fotos, média das três melhores correspondências e centróide. O HDBIF usa o recorte de referência antes da normalização e as três primeiras regras de cadastro. Cada variante tem limiar próprio, calibrado na mesma validação para FMR empírica de até 1%. Não foi usado o limiar de cadastro único para favorecer o cadastro múltiplo.

## 2. Todas as variantes

| Configuração | Rank-1 | TAR | FMR | Identificação e aceitação conjuntas | Falhas de consulta |
|---|---:|---:|---:|---:|---:|
| Encoder / referência / uma foto | 48,76% | 38,38% | 0,94% | 34,23% | 10 |
| Encoder / referência / máximo | 61,62% | 51,45% | 0,98% | 47,10% | 10 |
| Encoder / referência / média top-3 | 64,11% | 53,94% | 0,98% | 49,17% | 10 |
| Encoder / referência / centróide | 65,77% | 56,02% | 0,98% | 50,83% | 10 |
| Encoder / automático / uma foto | 50,83% | 39,42% | 0,99% | 34,65% | 4 |
| Encoder / automático / máximo | 64,32% | 55,60% | 0,99% | 50,00% | 4 |
| Encoder / automático / média top-3 | 67,01% | 59,34% | 0,99% | 54,77% | 4 |
| Encoder / automático / centróide | 65,35% | 56,43% | 0,99% | 50,83% | 4 |
| HDBIF / referência / uma foto | 42,12% | 24,69% | 0,94% | 23,86% | 12 |
| HDBIF / referência / máximo | 6,43% | 1,45% | 0,96% | 1,24% | 12 |
| HDBIF / referência / média top-3 | 22,61% | 2,70% | 0,97% | 1,87% | 12 |

## 3. Comparações pareadas

Os ganhos abaixo usam as mesmas consultas. ICs de 95% pontuais foram calculados com 5.000 reamostragens de pessoas, mantendo galeria e limiares fixos. São análises de desenvolvimento, sem correção por múltiplas comparações.

| Comparação: nova − referência | Ganho Rank-1 (pp) | IC 95% | Ganho TAR (pp) | IC 95% |
|---|---:|---|---:|---|
| neural_reference_centroid − neural_reference_first | 17.01 | 10.58 a 24.27 | 17.63 | 8.92 a 26.46 |
| neural_automatic_top3 − neural_automatic_first | 16.18 | 9.54 a 23.33 | 19.92 | 12.50 a 27.80 |
| neural_automatic_top3 − neural_reference_top3 | 2.90 | -1.86 a 7.29 | 5.39 | 0.83 a 9.96 |
| neural_automatic_centroid − neural_reference_centroid | -0.41 | -5.14 a 3.94 | 0.41 | -4.77 a 5.79 |
| hdbif_reference_max − hdbif_reference_first | -35.68 | -50.83 a -20.83 | -23.24 | -38.13 a -9.87 |
| hdbif_reference_top3 − hdbif_reference_first | -19.50 | -30.21 a -9.34 | -21.99 | -35.69 a -9.71 |

## 4. Interpretação e limites

O cadastro múltiplo deve ser comparado com a foto única na mesma máscara e extrator. Comparar os números deste quadro com os 67,90% de Rank-1 anteriores sem explicar a partição é incorreto: aquele resultado é do teste; este é da validação. O centróide com referência já fazia parte do protocolo neural anterior. Reproduzi-lo aqui não constitui um novo avanço além daquele benchmark.

No HDBIF, o máximo multicaptura piorou Rank-1 de 42,12% para 6,43% e TAR de 24,69% para 1,45%; a média top-3 também piorou. Não será adotado como melhoria. Mais fotos ampliam a exposição a comparações espúrias; um diagnóstico posterior dos cadastros vencedores foi registrado separadamente, sem remoção retrospectiva. É necessário investigar suporte de máscara e sobreposição entre códigos antes de propor uma nova regra de comparação.

O controle automático é uma implementação completa de extração de máscara e comparação de identidade nas imagens originais. Não usa a referência para corrigir a previsão. O encoder, porém, foi treinado com referências; as máscaras previstas podem incluir textura externa ou omitir regiões. Um ganho no automático não comprova maior precisão anatômica nem reconhecimento exclusivamente da textura da íris. A boa métrica de segmentação, isoladamente, também não garante identidade correta.

As comparações automáticas e de referência não têm exatamente as mesmas falhas. No subconjunto secundário em que ambas as extrações top-3 são válidas, há **472 consultas**. Nesse subconjunto, Rank-1 automático é 68.01% e de referência 65.47%; TAR automático é 60.17% e de referência 55.08%. Esses números não substituem a tabela operacional de todas as 482 consultas.

O limiar é recalibrado por variante na própria validação; diferenças de TAR refletem o sistema completo, não apenas uma mudança causal de máscara. Os mesmos dados já foram usados para selecionar o checkpoint e orientar desenvolvimento. Escolher o maior resultado entre onze variantes pode sobreajustar a validação; ainda é necessária confirmação independente.

## 5. Situação do percentual mínimo

Nenhuma variante alcançou simultaneamente 90% de Rank-1 e TAR no original. O mínimo global permanece **não determinado**. Esta rodada não atualiza a curva de oclusão nem autoriza transferir um ganho no original para um percentual de área tolerada.

A próxima melhoria deve considerar treinamento com a distribuição de máscaras automáticas e robustez a pequenas diferenças de recorte; para HDBIF, permanece importante revisar os limites da normalização polar. Um novo treinamento só deve usar treino e validação. Antes de anunciar mínimo ou ganho confirmado, precisa existir avaliação independente do conjunto usado para essas escolhas.

## 6. Verificação e preservação

Vinte e quatro testes automatizados passaram. O comparador HDBIF em lote foi conferido contra o escalar, incluindo sobreposição vazia; os controles de foto única reproduzem os escores das rodadas anteriores dentro da tolerância numérica. Os escores negativos válidos do encoder são preservados, e a sentinela de falha -2 é tratada separadamente.

A replicação neural permite diferença absoluta de até 0,000001 por arredondamento FP32 e alteração da dimensão da multiplicação matricial; o máximo observado está registrado no JSON de replicação. As decisões Rank-1, aceitação e validade devem ser idênticas às anteriores. A replicação HDBIF usa tolerância de 0,000000000001.

![Consultas e recortes automáticos com os três cadastros do candidato](exemplos_multicaptura.png).

Os exemplos são as primeiras consultas de quatro pessoas distintas na ordem do manifesto, sem seleção por acerto. As três fotos mostradas são do candidato encontrado, que pode ser incorreto. Aceitação genuína refere-se ao escore da identidade verdadeira; Rank-1 indica a posição do candidato correto.

- [Protocolo](../../PROTOCOLO_CADASTRO_MULTICAPTURA_2026-10-20.md).
- [Registro anterior à execução](protocolo.json).
- [Resultados completos](CONCLUIDO.json).
- [Resumo CSV](resumo.csv).
- [Comparações pareadas e análise secundária](comparacoes_pareadas.json).
