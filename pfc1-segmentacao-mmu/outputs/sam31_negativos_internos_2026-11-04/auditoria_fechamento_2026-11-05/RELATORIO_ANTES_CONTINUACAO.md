# SAM3.1 — treino, reconhecimento e área

Atualizado em 2026-11-05T03:10:28.369611+00:00 (UTC).

**As revisões clínicas podem ser feitas depois; não são requisito para esta curva UBIPr.**

O extrator visual SAM3.1 é congelado; o decodificador RGB+SAM3 recebe treino supervisionado.

Treino concluído. Candidato selecionado: **época 0**.

A época zero foi selecionada: não houve ganho selecionado com a adaptação supervisionada.

| Época | Original | Zoom 3× | Oblíqua | Óculos |
|---:|---:|---:|---:|---:|
| 0 | 88.62% | 86.51% | 87.61% | 88.21% |
| 1 | 86.19% | 83.26% | 84.22% | 85.35% |
| 2 | 86.23% | 84.11% | 84.70% | 85.49% |
| 3 | 86.94% | 84.34% | 85.28% | 86.30% |
| 4 | 86.08% | 83.67% | 84.21% | 85.27% |

Todas as condições usam as 1.652 imagens de validação. A seleção consulta somente segmentação.

**Ainda não há percentual mínimo novo:** aguardar identificação sem oclusão e a grade completa das duas orientações.

Os intervalos descritivos de 95%, com 5.000 reamostragens por pessoa e galeria fixa, estão em [AUDITORIA.json](AUDITORIA.json). Não são uma garantia simultânea da fronteira de área.

Oclusão cinza sintética e validação reutilizada no desenvolvimento. A área não representa a íris anatômica inteira ou a extensão de uma doença. Não houve nova inferência no teste ou demonstração de efeito clínico.

[Estado separado do piloto clínico](../../prontidao_anomalias_2026-11-03/PRONTIDAO.md).

Continuação de 04/11: pesos da época15 anterior; até12 épocas adicionais, com parada após4 sem ganho.

A perda adicional pesa pixels já anotados como não íris dentro de contornos fechados de íris. Não constitui anotação independente de pupila.

Os22.040 mapas anteriores são reutilizados com seus hashes; não há nova extração de mapas neste treino.

Os três controles originais de reconhecimento serão reutilizados após auditoria dos escores, fontes e ambiente. As inferências do novo candidato terão cache exclusivo.

A seleção usa apenas segmentação nas quatro condições. As metas de identificação e o limiar congelado permanecem registrados.

Sensibilidade registrada:472 referências de área definidas e10 indefinidas; todas482 permanecem na análise principal.

**Rodada encerrada sem ganho selecionado: época0 manteve os pesos anteriores. Não foi executada nova identificação ou grade de área.**
