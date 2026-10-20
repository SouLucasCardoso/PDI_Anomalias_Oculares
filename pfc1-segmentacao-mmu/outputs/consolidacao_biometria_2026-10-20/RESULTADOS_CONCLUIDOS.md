# Resultados concluídos — rodada inicial

Todos os números abaixo são novos experimentos. Os pilotos técnicos não entram nas estimativas finais. A segunda rodada de treinamento de identidade é separada.

## Segmentação UBIPr

Treinamento: 30 épocas; checkpoint escolhido na época 26, apenas pela validação. Dice de teste da íris: **0,9342**; Dice médio de primeiro plano: **0,8944**.

## Reconhecimento DINOv3 sem oclusão

486 consultas de 16 pessoas, galeria de 32 olhos. Limiar por ramo calibrado na validação.

| Entrada | Rank-1 | TAR | FMR de teste |
|---|---:|---:|---:|
| Imagem inteira | 46.50% | 25.51% | 0.87% |
| Íris: referência | 13.37% | 7.00% | 1.47% |
| Íris: U-Net | 18.52% | 9.67% | 1.57% |

Foram concluídas 19 condições e 57 combinações de condição e entrada. **Mínimo não determinado** em todos os ramos pelo critério registrado, porque a condição original não alcança Rank-1 e TAR de 90%. Isso não demonstra que a íris seja inutilizável para outros reconhecedores.

Os níveis descrevem a fração alvo da máscara anotada, apenas quando ela existe. Seis consultas têm referência de íris vazia; a média da cobertura em todas as consultas inclui esses zeros. Esse detalhe não deve ser interpretado como oclusão clínica medida.

## Reconhecimento HDBIF no teste clínico

319 consultas, 107 pessoas e galeria de 176 olhos. Reconhecedor e limiar congelados na validação.

Rank-1: **15.99%**; TAR: **50.78%**; FMR: **2.45%**.

IC 95% condicional por pessoa: Rank-1 11,01–21,45%; TAR 43,00–58,95%; FMR 1,95–3,02%.

A galeria clínica de teste é maior que a de validação (176 contra 60 olhos). Não atribuir a diferença de Rank-1 exclusivamente a doença ou a sobreajuste. A FMR pairwise também mudou de distribuição e excedeu o alvo da validação.

Diagnóstico descritivo posterior: Rank-1 correto e genuíno acima do limiar simultaneamente em 15.36% das consultas. TAR isolada não mede identificação correta entre todos os candidatos.

Há 10 imagens com falha, três cadastros com falha e 2.582 comparações indisponíveis. Foram mantidos no protocolo e nos denominadores. Não houve ajustes no teste. As análises posteriores de qualidade não autorizam seleção retrospectiva de casos.

## Artefatos

`curvas_area_preservada.png` e `.svg`: figura das curvas completas; `diagnostico_pos_hoc_teste.json`: diagnóstico exploratório de identificação e candidatos errados. Os relatórios originais permanecem nas pastas de cada execução.
