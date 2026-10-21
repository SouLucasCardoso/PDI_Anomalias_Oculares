# Controle exploratório de suporte polar — 20/10/2026

## Motivação e escopo

Após a avaliação multicaptura, um cadastro com apenas 0,153% de máscara polar válida venceu incorretamente em 138 consultas; outro, com 1,273%, venceu em 95. Essa associação motivou um controle posterior, sem excluir retrospectivamente as consultas do experimento anterior. A fração de máscara polar não é a sobreposição efetiva de um par nem a fração anatômica de íris.

Foi registrado um novo protocolo de desenvolvimento com suporte polar mínimo de 10% como controle principal e 20% como análise de sensibilidade. As comparações já calculadas são reaproveitadas; templates abaixo do limiar são tratados como indisponíveis tanto no cadastro quanto na consulta. **Todas as 482 consultas e os 32 olhos continuam no denominador.** O limiar biométrico é recalibrado na validação para cada variante.

## Resultados

| Suporte mínimo | Cadastro | Rank-1 | TAR | FMR | Falhas de consulta | Capturas de cadastro indisponíveis |
|---:|---|---:|---:|---:|---:|---:|
| 10% | first | 42,12% | 29,67% | 0,93% | 17 | 19 |
| 10% | max | 20,54% | 0,83% | 0,96% | 17 | 19 |
| 10% | top3 | 37,14% | 26,76% | 0,96% | 17 | 19 |
| 20% | first | 42,12% | 29,88% | 0,93% | 19 | 24 |
| 20% | max | 47,30% | 33,20% | 0,96% | 19 | 24 |
| 20% | top3 | 51,24% | 36,31% | 0,96% | 19 | 24 |

## Interpretação

Sem esse controle, o HDBIF máximo multicaptura havia obtido 6,43% de Rank-1 e 1,45% de TAR. O controle principal de 10% elevou o Rank-1 para 20,54%, mas a TAR foi de apenas 0,83%; portanto, não resolveu o problema. Na sensibilidade de 20%, a média top-3 atingiu 51,24% de Rank-1 e 36,31% de TAR, com 0,96% de FMR e 19 falhas de consulta.

A sensibilidade de 20% é promissora para reduzir o efeito de cadastros com suporte muito pequeno, mas foi explorada depois de observar o problema e não constitui confirmação independente. Também permanece abaixo do encoder automático top-3 desta validação (67,01% de Rank-1 e 59,34% de TAR). Não foi escolhida uma regra universal de qualidade nem substituído o reconhecedor principal com base nessa busca.

**Os 10% e 20% desta tabela NÃO são o mínimo de íris para identificação.** São limiares de disponibilidade da máscara após normalização, em outra escala geométrica. Não representam oclusão de 90%/80%, área anatômica remanescente ou sucesso no critério de 90% de reconhecimento. Nenhuma variante alcançou esse critério.

A fração individual de máscara é apenas um primeiro controle. A sobreposição válida entre dois códigos também precisa ser considerada em uma próxima implementação, sem usar os resultados de teste para ajustar o filtro. Antes de aplicar o método em uma confirmação, é necessário congelar a configuração escolhida na validação e definir uma avaliação independente.

## Artefatos

- [Protocolo anterior ao novo cálculo](protocolo.json).
- [Resultados das seis variantes](CONCLUIDO.json).
- [Rodada multicaptura original, mantida](../cadastro_multicaptura_val_v2_2026-10-20/RELATORIO_CADASTRO.md).
- [Diagnóstico posterior dos cadastros](../cadastro_multicaptura_val_v2_2026-10-20/diagnostico_cadastros.json).
