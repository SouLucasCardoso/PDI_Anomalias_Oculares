# Referência de área para o experimento UBIPr

Esta caracterização descreve as anotações existentes. **Ainda não determina o mínimo necessário para identificação.**

São 482 consultas, 16 pessoas e 32 olhos, com lado informado. Referências vazias mantidas: 10.

Os pixels são contados na resolução original da anotação. A fração é relativa à íris visível anotada em cada fotografia, sem reconstruir a parte escondida ou a íris anatômica inteira.

| Área nominal preservada | Pixels preservados: mínimo | Mediana | Máximo |
|---:|---:|---:|---:|
| 100% | 31 | 7054 | 28952 |
| 99% | 31 | 6983.5 | 28662 |
| 98% | 30 | 6913 | 28373 |
| 95% | 29 | 6701 | 27504 |
| 90% | 28 | 6348.5 | 26057 |
| 80% | 25 | 5643 | 23162 |
| 70% | 22 | 4938 | 20266 |
| 60% | 19 | 4232.5 | 17371 |
| 50% | 15 | 3527 | 14476 |
| 40% | 12 | 2821.5 | 11581 |
| 30% | 9 | 2116 | 8686 |
| 20% | 6 | 1411 | 5790 |
| 10% | 3 | 705.5 | 2895 |

Cada nível usa o mesmo número de pixels em oclusão superior e inferior; a posição desses pixels muda. Isso pode produzir efeitos diferentes no reconhecimento.

A seleção de pixels usa arredondamento inteiro, conforme o protocolo. A planilha CSV conserva todas as consultas, quantidades e frações efetivas, inclusive referências vazias.

As 482 contagens de referência e o arredondamento em perda de 10% foram reproduzidos nas duas orientações contra as evidências da rodada anterior, sem nova inferência.

O mesmo percentual pode preservar quantidades diferentes de pixels entre fotografias. Estes números não medem resolução óptica, gravidade de doença ou reconhecimento com o novo SAM3.

[Acompanhar o treino e o resultado biométrico](../analise_area/RELATORIO_ATUAL.md).