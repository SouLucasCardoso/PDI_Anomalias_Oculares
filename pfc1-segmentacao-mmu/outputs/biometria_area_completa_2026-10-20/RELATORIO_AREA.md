# AREA PRESERVADA — EXPERIMENTO COMPLETO

Estimativas restritas ao modelo, amostra e grade registrados.

| Ramo | Orientacao | Menor area testada aprovada | Rank-1 original | TAR original | FMR teste original |
|---|---|---:|---:|---:|---:|
| inteira | oclusao_superior | Nao determinado | 46.50% | 25.51% | 0.87% |
| inteira | oclusao_inferior | Nao determinado | 46.50% | 25.51% | 0.87% |
| iris_referencia | oclusao_superior | Nao determinado | 13.37% | 7.00% | 1.47% |
| iris_referencia | oclusao_inferior | Nao determinado | 13.37% | 7.00% | 1.47% |
| iris_unet | oclusao_superior | Nao determinado | 18.52% | 9.67% | 1.57% |
| iris_unet | oclusao_inferior | Nao determinado | 18.52% | 9.67% | 1.57% |

O criterio exige Rank-1 e TAR de pelo menos 90% no original e em todas as areas maiores. A FMR de teste e apresentada sem pressupor que coincida com a calibracao. A decisao usa estimativas pontuais e nao limites de confianca. A imagem inteira inclui contexto periocular.

Point estimate criterion; not a confidence-bound guarantee
Validation FMR <=1% does not guarantee test FMR <=1%
10 percentage point grid; no universal or clinical minimum
Synthetic loss of annotated pixels does not measure disease extent
