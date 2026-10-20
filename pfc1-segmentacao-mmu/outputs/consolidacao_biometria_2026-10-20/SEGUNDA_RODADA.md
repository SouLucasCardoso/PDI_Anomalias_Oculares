# Segunda rodada exploratória concluída

O encoder ResNet18 com margem angular foi treinado em 183 pessoas e 366 classes de olho. O treinamento terminou na época 23; o checkpoint foi selecionado na época 15, somente pela validação. O teste UBIPr já havia sido examinado na rodada DINOv3; esta comparação é exploratória.

| Medida no original | Estimativa | IC 95% condicional por pessoa |
|---|---:|---:|
| RANK1 | 67.90% | 61.04% a 74.80% |
| TAR | 55.14% | 40.36% a 68.75% |
| FMR | 0.96% | 0.46% a 1.49% |

Foram concluídas as 19 condições. O mínimo global segue **não determinado** pelo critério registrado de 90% de Rank-1 e TAR. A configuração treinada e a referência DINOv3 diferem em arquitetura, treinamento e resolução; o resultado não isola causalmente apenas a margem angular.

## Diagnóstico por consulta

234 das 486 consultas foram identificadas corretamente e com escore genuíno acima do limiar no original. Com 90% da área preservada, mantiveram o sucesso 117 dessas 234 sob oclusão superior (50%) e 115 sob oclusão inferior (49,15%). As demais consultas originalmente não identificadas continuam exportadas como mínimo indefinido.

Os valores por consulta indicam a menor fração **testada** que passa em todos os níveis maiores. Um resultado 100% significa que nenhum nível com oclusão testado satisfaz a regra; não prova que uma perda entre 1% e 9% seja inviável. A mediana interpolada 95% presente no JSON estatístico não é um nível efetivamente testado. Usar a tabela por níveis e os histogramas, sem anunciá-la como mínimo validado.

## Nuclear Cataract

A preparação foi interrompida após revisão de oito exemplos de calibração e antes de qualquer escore de reconhecimento. Várias máscaras eram fragmentos sem recorte confiável da íris. Os dados foram preservados; os protocolos e códigos registrados permanecem arquivados. A ausência de avaliação não permite afirmar falha biométrica de toda a base, apenas inadequação do pipeline atual para prosseguir.

Os resultados não estabelecem causalidade de doença nem um mínimo universal. As figuras e os dados auxiliares estão nesta pasta e em `tolerancia_condicional_exploratoria_2026-10-20`.
