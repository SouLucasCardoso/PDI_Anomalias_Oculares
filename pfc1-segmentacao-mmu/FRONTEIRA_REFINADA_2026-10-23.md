# Fronteira refinada de aproveitamento nominal — 23/10/2026

## Resultado atual

Foi concluída a rodada limitada a dois novos pontos, sem treino ou recalibração. Na grade estudada, o menor aproveitamento nominal aprovado passou de 100% para **99,5% na oclusão superior**. Na inferior permanece em **99%**, agora com reprovação observada em 98,5%, além da anterior em 98%.

São limites observados deste processamento no UBIPr, não mínimos anatômicos universais. A meta exige simultaneamente Rank-1 ≥ 90%, TAR ≥ 90% e FMR empírico ≤ 1%, com limiar congelado 0,8581747485460748. O resultado sem oclusão permanece em 91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR.

## Tabela consolidada da fronteira

| Condição | Área nominal preservada | Rank-1 (%) | TAR (%) | FMR (%) | Critério |
|---|---:|---:|---:|---:|---|
| Original | 100% | 91,3580 | 92,3868 | 0,8779 | Passa |
| Superior, perda de 0,5% — nova | **99,5%** | **91,1523** | **92,3868** | **0,8916** | **Passa** |
| Superior, perda de 1% | 99% | 89,9177 | 92,3868 | 0,8779 | Reprova |
| Inferior, perda de 1% | **99%** | **90,9465** | **91,3580** | **0,9328** | **Passa** |
| Inferior, perda de 1,5% — nova | 98,5% | 89,0947 | 88,8889 | **1,0151** | Reprova |
| Inferior, perda de 2% | 98% | 87,4486 | 87,8601 | 1,2346 | Reprova |

A condição superior nova teve 443 identificações corretas e 449 genuínos aceitos em 486 consultas, com 65 impostores aceitos em 7.290 comparações. A inferior nova teve 433 identificações corretas, 432 genuínos aceitos e 74 impostores aceitos. O máximo inteiro de impostores aceitos compatível com 1% nessa avaliação é 72; portanto, 1,0151% não deve ser arredondado para 1% para obter aprovação.

## Condições e alcance do mínimo

Foram mantidos uma foto por consulta, lado do olho informado, 16 candidatos do mesmo lado e cadastro original da sessão 1. Todas as 486 consultas, incluindo duas falhas de extração, permaneceram no denominador. Há 480 referências de área definidas e seis vazias, mantidas inalteradas. Cinza 128 foi aplicado somente aos pixels de íris anotados, por contagem determinística; segmentação e geometria foram refeitas na foto alterada. A anotação não foi fornecida ao extrator.

O prefixo superior usa perdas testadas de 0; 0,5; 1; 10%. O inferior usa 0; 1; 1,5; 2; 10%. Trata-se de **grades irregulares explicitamente definidas**, não de uma varredura uniforme de 0,5 ponto percentual. A regra exige aprovação em todas as frações maiores que foram testadas; não pressupõe monotonicidade entre pontos ou abaixo da primeira falha.

**Não existe avaliação inferior de 0,5% nesta rodada.** Assim, 99,5% preservados não foram aprovados em ambas as orientações. Entre as frações avaliadas nas duas orientações, a única aprovada no prefixo comum continua sendo 100%. Não se deve tomar o máximo dos dois mínimos por orientação e anunciá-lo como limite comum confirmado.

Os resultados refinam o limite pontual do sistema. Não demonstram que 99,5% do tecido anatômico seja indispensável, nem que uma anomalia de 0,5% tenha esse efeito. A intervenção artificial mede perda selecionada de suporte e a reação do processamento completo, incluindo segmentação, recorte e normalização.

## Precisão da área e incerteza

Na condição superior de 0,5%, a perda efetiva média foi 0,4986%, variando de 0 a 0,5455% nas 480 referências definidas. Uma foto teve zero pixels selecionados por arredondamento e permaneceu igual à original. Na inferior de 1,5%, a média foi 1,5001%, variando de 1,4545 a 1,6949%, sem casos definidos de zero pixel. As seis referências vazias são adicionais e não entram nessas médias de área.

| Nova condição | IC95% Rank-1 (%) | IC95% TAR (%) | IC95% FMR (%) | Reamostras com aprovação conjunta |
|---|---:|---:|---:|---:|
| Superior 0,5% | 85,00–95,63 | 86,04–96,88 | 0,54–1,26 | 62,00% |
| Inferior 1,5% | 81,07–94,72 | 80,66–94,84 | 0,65–1,38 | 26,32% |

Foram usadas 5.000 reamostragens pareadas por participante, semente 20261001, com cadastro e limiar fixos e contagens inteiras para o critério. São intervalos pontuais descritivos, sem correção por comparações múltiplas, seleção de estratégias, exame anterior do teste ou possível sobreposição de pré-treinamento do ArcIris. As frequências de aprovação descrevem estabilidade de reamostragem; não são probabilidades populacionais de sucesso ou de validade de um mínimo clínico. A incerteza ampla impede atribuir precisão clínica aos decimais da grade.

## Conferência e arquivos

O protocolo dos dois pontos foi registrado antes da execução. Ambos foram executados independentemente do resultado do primeiro; nenhum ponto adicional foi acrescentado. Os pesos e as dependências foram conferidos contra o protocolo congelado original. As nove matrizes componentes de cada condição reproduziram a fusão com diferença máxima zero. Foram conferidos rótulos, decisões, limiar, contagens de intervenção e todas as entradas de cadastro e de referências vazias. As consultas com zero intervenção também reproduziram os escores originais.

Cinco testes direcionados de contagem fracionária e regra de fronteira passaram, incluindo a referência pequena que arredonda para zero. Não foi executada nova suíte completa nesta etapa.

- [Protocolo](outputs/fronteira_meio_ponto_2026-10-23/protocolo.json).
- [Resultados da rodada](outputs/fronteira_meio_ponto_2026-10-23/CONCLUIDO.json).
- [Auditoria, incerteza e grades explícitas](outputs/fronteira_meio_ponto_2026-10-23/AUDITORIA_FRONTEIRA.json).
- [Consultas superiores](outputs/fronteira_meio_ponto_2026-10-23/superior_0p5/consultas.csv).
- [Consultas inferiores](outputs/fronteira_meio_ponto_2026-10-23/inferior_1p5/consultas.csv).
- [Contagens por participante](outputs/fronteira_meio_ponto_2026-10-23/estatisticas_por_pessoa.csv).

A execução usou diretório temporário, sem alterar o Defender. Protocolos, tabelas e auditorias foram preservados no projeto pelo mecanismo de edição. Um pacote em 16 partes Base64 preserva os bytes originais dos escores NPZ, metadados e fontes, sem imagens de entrada ou duplicação dos pesos congelados. O pacote fica fora do Git; as cópias legíveis normalizam quebras de linha. A sincronização na nuvem não foi confirmada.

A restauração recuperou 37 arquivos, todos com SHA-256 conferido. As fusões das duas condições foram refeitas a partir dos nove componentes restaurados e coincidiram exatamente com os escores finais e os CSV. As 12 cópias textuais legíveis também foram conferidas. O ZIP tem 1.045.599 bytes e SHA-256 `b8f06abd2a368e4d98c4f420e805f9f63a6c76b6455b03d9a147be38d429cd65`. Ver [registro da preservação](backups/meio_ponto_2026-10-23/VERIFICACAO_PRESERVACAO.json).

## Encerramento desta rodada

Os dois pontos previstos foram concluídos. A próxima prioridade do plano é consolidar método, tabelas e discussão no artigo, incluindo os limites regionais, a incerteza e a distinção entre oclusão simulada e anomalias reais. Esta rodada não altera o modelo ou o resultado original e não constitui confirmação cega nova.
