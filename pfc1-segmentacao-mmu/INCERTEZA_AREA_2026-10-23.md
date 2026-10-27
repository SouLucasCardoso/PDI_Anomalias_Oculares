# Fronteira de área e incerteza — 23/10/2026

## Avanço para a pergunta principal

Foi quantificada a incerteza das seis condições já avaliadas, sem novos treinos, inferências ou calibração. O achado mais direto para o artigo é a diferença entre regiões: com a mesma perda nominal de 10%, o Rank-1 superior foi 24,07 pontos percentuais maior que o inferior, com IC95% pareado de 10,83 a 36,25 pontos. A posição da intervenção teve efeito relevante no processamento completo estudado, que inclui nova segmentação e normalização.

A fronteira pontual da grade permanece em 100% de área nominal preservada para oclusão superior e 99% para inferior. A reanálise mostra que essa aprovação é sensível à amostra de participantes. Não estabelece um mínimo anatômico universal ou um percentual de comprometimento por doença.

## Método econômico e rastreável

Foram reaproveitadas as matrizes finais das condições original, superior de 1%, inferior de 1%, inferior de 2% e superior/inferior de 10%. Permaneceram o limiar 0,8581747485460748, o cadastro, os pesos e todos os 486 casos, com 16 participantes e 15 comparações impostoras por consulta. Há 480 consultas com área de referência definida; as outras seis continuam inalteradas nas intervenções e no denominador principal.

Foram feitas 5.000 reamostragens pareadas de participantes com reposição, semente 20261001. Cada sorteio foi compartilhado pelas condições e métricas; o denominador acompanha o número de consultas dos participantes sorteados. Os intervalos são percentis pontuais de 95%, com cadastro e limiar fixos. Não corrigem escolha de modelos, reutilização do teste ou possível sobreposição do pré-treinamento externo.

A regra de aprovação continua sendo simultaneamente Rank-1 ≥ 90%, TAR ≥ 90% e FMR ≤ 1%. Nas reamostragens, as comparações usam contagens inteiras para preservar exatamente os limites de 90% e 1%. Uma condição original reprovada é classificada como ausência de prefixo aprovado, nunca como mínimo de 100%. As grades de prefixo são apenas 0–1% na superior, 0–1–2% na inferior e 0–1% no critério comum. Não há interpolação ou pressuposto de monotonicidade fora dessa regra.

## Desempenho e intervalos

| Condição | Rank-1 (%) | IC95% Rank-1 (%) | TAR (%) | FMR (%) | Reamostras que passam os três critérios |
|---|---:|---:|---:|---:|---:|
| Original | 91,36 | 85,19–95,73 | 92,39 | 0,88 | 65,42% |
| Superior, perda de 1% | 89,92 | 84,36–94,38 | 92,39 | 0,88 | 50,50% |
| Inferior, perda de 1% | 90,95 | 83,95–95,68 | 91,36 | 0,93 | 50,46% |
| Inferior, perda de 2% | 87,45 | 79,22–93,78 | 87,86 | 1,23 | 7,64% |
| Superior, perda de 10% | 82,30 | 72,08–90,83 | 84,98 | 1,69 | 0,72% |
| Inferior, perda de 10% | 58,23 | 44,98–70,78 | 60,29 | 2,61 | 0,00% |

**Essas frequências descrevem estabilidade de reamostragem, não a probabilidade de o sistema funcionar na população ou de a hipótese ser verdadeira.** Elas também não substituem a aprovação pontual usada no protocolo original. O caso superior de 1% continua reprovado por um acerto; a condição inferior de 1% continua aprovada pontualmente.

Os intervalos da condição original para TAR e FMR foram 86,25–96,71% e 0,53–1,28%. Assim, mesmo a condição original aprovada pontualmente não sustenta afirmar que os limites populacionais foram garantidos pelos intervalos. A precisão é limitada, especialmente pelo número de participantes. Os pequenos ajustes em intervalos em relação a relatórios antigos decorrem do protocolo de reamostragem explicitado nesta análise; as contagens e medidas pontuais não mudaram.

## Diferenças pareadas e impacto da região

| Comparação com a condição original | Perda de Rank-1 (p.p.) | IC95% pareado (p.p.) |
|---|---:|---:|
| Superior 1% | 1,44 | 0,21–2,71 |
| Inferior 1% | 0,41 | −0,81–1,67 |
| Inferior 2% | 3,91 | 0,81–7,50 |
| Superior 10% | 9,05 | 2,50–17,68 |
| Inferior 10% | 33,13 | 23,13–43,62 |

A comparação direta entre superior e inferior com 10% de perda foi 24,07 p.p., IC95% 10,83–36,25. Esses intervalos são pontuais, exploratórios e sem correção por comparações múltiplas. A intervenção foi cinza artificial restrito à íris anotada; não é equivalente à extensão de uma anomalia clínica. A comparação inclui a reação da segmentação e do recorte, não somente a remoção de textura.

## Estabilidade da fronteira da grade disponível

| Categoria da grade inferior 0–1–2% de perda | Reamostras |
|---|---:|
| Condição original reprovada: sem prefixo aprovado | 34,58% |
| Menor área aprovada no prefixo: 100% | 15,56% |
| Menor área aprovada no prefixo: 99% | 42,22% |
| Menor área aprovada no prefixo: 98% | 7,64% |

Essas categorias somam 100% das reamostras e descrevem somente a grade disponível, não uma distribuição de mínimo anatômico. A grade comum às duas orientações teve 34,58% sem prefixo aprovado, 23,68% com prefixo restrito a 100% e 41,74% chegando a 99%. Nenhum desses valores muda o mínimo pontual observado ou permite aprovar áreas não avaliadas.

## Precisão de pixels e próximos passos

Também foi descrito o arredondamento que ocorreria em duas condições candidatas, sem executá-las no reconhecedor. Na perda nominal de 0,5%, a perda efetiva média seria 0,4986%, com faixa de 0 a 0,5455%: uma das 480 imagens teria zero pixels selecionados. Na nominal de 1,5%, a média seria 1,5001%, com faixa de 1,4545 a 1,6949%. As seis referências vazias permanecem à parte desse diagnóstico e dentro do denominador principal. **Não há resultado de reconhecimento em 0,5% ou 1,5% nesta etapa.**

O próximo refinamento, se executado, deve ser uma única rodada limitada aos dois pontos de meio de intervalo: superior 0,5% e inferior 1,5%, preservando modelo, limiar, denominador e os resultados antigos. Isso pode refinar a descrição pontual da grade; não resolve a incerteza populacional e não justifica casas decimais clínicas. Não será uma nova busca de reconhecedores ou de limiares. O [plano de fechamento](PLANO_FECHAMENTO_2026-10-23.md) prioriza consolidar o artigo no prazo.

## Verificação e arquivos

As contagens foram reproduzidas das seis matrizes já existentes. Uma segunda implementação refez a análise a partir de apenas 96 linhas de contagens por participante/condição, reproduzindo intervalos com diferença máxima de 2,23 × 10⁻¹⁶ ponto percentual, além de frequências, diferenças pareadas e todas as categorias do prefixo. Cinco testes direcionados de fronteira e reamostragem passaram. Não houve nova execução da suíte inteira nesta etapa; a anterior de 97 testes permanece registrada no relatório do transporte.

- [Protocolo](outputs/incerteza_fronteira_area_2026-10-23/protocolo.json).
- [Resumo completo](outputs/incerteza_fronteira_area_2026-10-23/CONCLUIDO.json).
- [Contagens por participante](outputs/incerteza_fronteira_area_2026-10-23/estatisticas_por_pessoa.csv).
- [Reprodução independente](outputs/incerteza_fronteira_area_2026-10-23/VERIFICACAO_REPLAY.json).

Uma primeira execução temporária omitiu a última categoria de cada tabela de prefixos. A falha foi corrigida, coberta por teste e a análise final foi executada em diretório separado; somente a versão conferida foi preservada no projeto. Nenhuma observação ou modelo mudou. Os artefatos desta etapa são textuais e permitem reprodução pelas contagens agregadas, sem novo modelo ou cache de imagens. A execução usou pasta temporária e os textos foram preservados pelo mecanismo de edição, sem alterações no Defender. A sincronização na nuvem não foi confirmada.
