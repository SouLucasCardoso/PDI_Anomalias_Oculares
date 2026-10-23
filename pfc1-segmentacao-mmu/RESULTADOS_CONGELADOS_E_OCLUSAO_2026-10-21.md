# Resultados da configuração congelada e da oclusão — 21/10/2026

## Resultado principal sem oclusão adicional

A reprodução integrada da validação manteve 434 identificações corretas e 437 aceitações genuínas em 482 consultas, sem mudar nenhuma decisão e com diferença máxima de 9,99×10⁻¹⁶ nos escores. No teste UBIPr, a configuração congelada atingiu **91,36% de Rank-1 (444/486), 92,39% de TAR (449/486) e 0,88% de FMR (64/7.290)**. A taxa conjunta de identificação correta e aceitação foi 89,71% (436/486), distinta das duas métricas anteriores.

Uma foto original por consulta, lado do olho corretamente informado, 16 candidatos do mesmo lado, cadastro original da sessão 1 e consultas da sessão 2. Todos os 486 casos permaneceram na avaliação, incluindo duas falhas de extração. O limiar foi 0,8581747485460748 e os parâmetros de normalização vieram exclusivamente da validação; nenhum foi recalibrado para o teste ou para as oclusões.

O teste já havia sido examinado por estratégias anteriores: não é um teste cego novo. A população de pré-treinamento dos pesos públicos ArcIris permanece desconhecida; sobreposição não pode ser excluída. Os IC95% descritivos por pessoa foram 85,42–95,68% para Rank-1, 86,46–96,67% para TAR e 0,52–1,28% para FMR. Eles não corrigem seleção de estratégias ou possível sobreposição externa.

## Condições de oclusão avaliadas

A anotação da base foi usada somente para definir quais pixels receberiam cinza 128, sem modificar o exterior. A segmentação U-Net e a geometria polar foram recalculadas sobre a foto alterada; a anotação não foi fornecida ao extrator. O resultado mede o processamento completo, incluindo instabilidade de recorte e normalização; não isola a informação da textura.

| Condição | Área nominal preservada | Rank-1 | TAR | FMR | Critério |
|---|---:|---:|---:|---:|---|
| Original |100%|91,36%|92,39%|0,88%|Aprovado|
| Superior: perda de 1% |99%|89,92%|92,39%|0,88%|Reprovado|
| Inferior: perda de 1% |99%|90,95%|91,36%|0,93%|Aprovado|
| Inferior: perda de 2% |98%|87,45%|87,86%|1,23%|Reprovado|
| Superior: perda de 10% |90%|82,30%|84,98%|1,69%|Reprovado|
| Inferior: perda de 10% |90%|58,23%|60,29%|2,61%|Reprovado|

## Fronteira observada na grade de 1 ponto percentual

- **Oclusão superior:** apenas 100% da área nominal original passou. Com 99% preservados, foram 437 identificações corretas; faltou uma para o mínimo de 438 em 486 consultas.
- **Oclusão inferior:** 99% preservados passaram; 98% reprovaram.
- **Critério comum às duas orientações:** somente a condição original, sem perda adicional, passou em todas as condições exigidas da grade. Isso não prova que todos os pixels sejam indispensáveis, nem define mínimo anatômico ou clínico.

A busca grossa começou com 10% de perda por orientação e foi refinada exploratoriamente em passos de 1%. Cada orientação parou na primeira reprovação: qualquer fração menor já não satisfaria a regra de aprovação em todas as áreas maiores. Portanto, não se trata de curva completa de 19 condições nem de garantia de monotonicidade do desempenho. Não foram escolhidos pesos ou limiares para recuperar aprovações.

## Área indefinida e análise de sensibilidade

Há 480 consultas com anotação de íris não vazia e seis com referência vazia. As seis foram mantidas inalteradas nas condições de oclusão e no denominador principal; para elas não há fração de área definida. Na perda nominal de 1%, o arredondamento para pixels correspondeu a perdas individuais de 0,84% a 1,69%, com média de 1,0016%. Os valores de 99% e 100% são níveis nominais de uma grade, não medidas exatas de anatomia.

Na análise posterior de sensibilidade restrita às 480 referências definidas, a oclusão superior de 1% apresentou 90,83% de Rank-1 e 93,13% de TAR, com 0,85% de FMR. Essa análise secundária mostra a influência do denominador e não substitui os 486 casos nem altera a fronteira principal para obter aprovação. A oclusão inferior de 1% passou também nessa análise; a de 2% continuou reprovada.

## Verificação e evidências

Foram aprovados 57 testes automatizados. A auditoria recalculou as decisões, conferiu a contagem exata de pixels da intervenção e verificou igualdade de todas as entradas de cadastro e das seis consultas sem referência entre as condições. Pesos e parâmetros permaneceram congelados.

![Recortes reais sob oclusão](outputs/diagnostico_oclusao_congelada_2026-10-21/recortes_sob_oclusao.png)

Os exemplos são as primeiras consultas de quatro pessoas do teste, sem seleção por desempenho. As diferenças visuais e o diagnóstico pareado dos componentes não permitem atribuir causalmente a queda apenas à textura ou apenas à segmentação.

- [Teste original](outputs/confirmacao_congelada_test_2026-10-21/CONCLUIDO.json).
- [Fronteira em passos de 1%](outputs/refinamento_oclusao_congelada_2026-10-21/CONCLUIDO.json).
- [Auditoria e análise de sensibilidade](outputs/auditoria_oclusao_congelada_2026-10-21/AUDITORIA.json).
- [Protocolo de avaliação](PROTOCOLO_CONFIRMACAO_CONGELADA_2026-10-21.md).

O resultado confirma o desempenho pontual do candidato sem oclusão nesta avaliação e revela baixa margem de tolerância no processamento completo. Melhorias futuras devem separar robustez da segmentação e da normalização da robustez do reconhecedor, com desenvolvimento em treino/validação e sem ajustar parâmetros para corrigir estes resultados de teste.
