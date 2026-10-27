# Recorte e reconhecimento em casos oculares reais — 27/10/2026

## Pergunta e seleção

Foram executados testes com alterações reais documentadas no SLP-VLD, separados de exemplos UBIPr sem diagnóstico clínico. Não foi acrescentada oclusão sintética e não houve treinamento ou calibração clínica.

Incluíram-se todas as nove imagens com menção literal a íris/iridodiálise no manifesto SLP-VLD. Elas representam oito olhos codificados. Seis olhos têm uma única captura disponível e permitem apenas análise de recorte. Dois aparecem no manifesto clínico longitudinal previamente preparado: P0114 OS, com duas capturas, e P0803 OD, com quatro. As primeiras capturas de cada olho são cadastro; as demais somam quatro consultas. Os diagnósticos incluem comorbidades e pós-operatório; não há comparação saudável/doente do mesmo olho que permita atribuir causalidade à doença.

O cadastro contém, por lado, o olho alvo e os primeiros 15 outros olhos do manifesto clínico de teste, ordenados por código/arquivo, sem seleção por qualidade ou escore. São 32 fotos de cadastro, quatro consultas e seis casos adicionais de recorte: 42 fotografias processadas. A análise clínica foi previamente exposta por um estudo HDBIF; esta rodada é exploratória, não um teste cego.

O sistema usa os nove componentes, os pesos e o limiar **0,8581747485460748** congelados no UBIPr. Não se substituiu o reconhecedor principal. A mudança de captura e população impede comparar diretamente estes quatro casos com os 91,36% do UBIPr.

## Resultado do sistema original

Nas quatro consultas, houve **0 identificações corretas e 0 aceitações genuínas**; houve **1 falsa correspondência em 60 pares impostores (1,67%)**. Todas permaneceram no denominador.

Uma consulta de P0114 não tinha comparação genuína disponível: a U-Net produziu máscara vazia na foto de cadastro. As três consultas de P0803 tinham cadastro computacionalmente disponível, mas nenhuma foi corretamente identificada/aceita. A inspeção das máscaras mostrou extração de fragmentos muito pequenos, com regiões da íris visível fora da máscara. Sem referência clínica anotada, não se calculou Dice nem percentual de tecido perdido. Um recorte não vazio não comprova extração correta.

Entre as nove fotos com diagnóstico explícito, três tiveram máscara vazia. Nas outras seis, o suporte polar variou de 8,18% a 96,05%. Esses valores descrevem o suporte do algoritmo dentro da sua própria geometria estimada: até uma pequena região segmentada incorretamente pode ter suporte alto. **96,05% não significa que 96,05% da anatomia da íris foi preservada.**

## Controle de escala, registrado após examinar a falha original

Foi testada uma única hipótese posterior: as fotos de lâmpada de fenda mostram o olho muito mais de perto que o domínio UBIPr. Antes da segunda inferência, registrou-se escala fixa de 1/3 para a entrada clínica da U-Net: a foto é redimensionada para 106 × 80 dentro de uma moldura cinza 320 × 240, e a máscara é mapeada de volta à foto original. Os pixels usados no reconhecimento continuam vindo da foto original. Não há geração de textura, anotação usada na extração ou busca de escalas. Pesos, cadastro, consultas e limiar permanecem iguais.

| Execução | Acertos/consultas | Aceitações genuínas | Falsas correspondências | Consultas sem comparação genuína disponível |
|---|---:|---:|---:|---:|
| Original | 0/4 | 0/4 | 1/60 (1,67%) | 1/4 |
| Escala fixa 1/3 | 1/4 | 1/4 | 2/60 (3,33%) | 3/4 |

O caso P0114 com cisto de íris e alterações corneanas passou a ser identificado e aceito: escore genuíno **0,8753819683**, acima do limiar congelado. O cadastro passou de máscara vazia a 146.225 pixels previstos e suporte polar de 73,25%; a consulta passou de 6.055 a 620.862 pixels previstos e suporte de 94,10%. Isso demonstra que o pré-processamento mudou a extração e a decisão nesse caso; não quantifica tecido verdadeiro nem valida um percentual mínimo.

No olho P0803, a máscara do cadastro passou a ficar vazia, indisponibilizando as três comparações genuínas. Assim, o controle não foi uma melhoria geral e não foi promovido. Não houve exclusão dessas consultas ou escolha retrospectiva da melhor escala por olho. A taxa de 25% vem de apenas quatro consultas de dois olhos; não é estimativa confiável de desempenho clínico. Com 60 pares impostores, uma falsa correspondência já representa 1,67%; não é possível comprovar segurança populacional de FMR de 1% nesta amostra.

## Casos medidos e suporte extraído

| Imagem | Papel | Suporte polar original | Suporte polar no controle 1/3 |
|---|---|---:|---:|
| P0114_OS20250327.JPG | Cadastro | Indefinido: máscara vazia | 73,25% |
| P0114_OS20250417.JPG | Consulta | 8,18% | 94,10% |
| P0803_OD20250112.JPG | Cadastro | 63,97% | Indefinido: máscara vazia |
| P0803_OD20250209.JPG | Consulta | 37,73% | 59,00% |
| P0803_OD20250223.JPG | Consulta | 57,17% | 84,56% |
| P0803_OD20250415.JPG | Consulta | 82,37% | 61,90% |

Os JSONs registram também os seis casos sem cadastro, áreas em pixels e a razão máscara/fotografia. Esta última depende do enquadramento e não é a fração preservada da íris. Os percentuais anatômicos permanecem explicitamente indefinidos.

## UBIPr: suporte natural e reconhecimento já medido

Foram reaproveitadas todas as 482 consultas de validação do diagnóstico anterior, com o reconhecedor congelado. Não se executou novo reconhecimento UBIPr nem se afirmou inspecionar as 11.018 fotografias. As ilustrações usam quatro pessoas distintas com menor suporte polar e duas outras pela ordem do manifesto, sem escolher por acerto. As imagens mostram reflexos, óculos, gaze e oclusões naturais; não receberam diagnóstico de doença.

| Suporte da grade polar | Consultas | Identificações corretas | Aceitações genuínas |
|---|---:|---:|---:|
| Menor que 50% | 1 | 1 | 1 |
| 50% a menos de 75% | 4 | 2 | 2 |
| 75% a menos de 90% | 15 | 12 | 12 |
| Pelo menos 90% | 458 | 419 | 422 |
| Indefinido | 4 | 0 | 0 |
| Total | 482 | 434 | 437 |

C317_S2_I12_L.jpg foi identificado e aceito com suporte polar de **47,36%**. É um exemplo real interessante, mas **não prova que 47,36% da área anatômica basta**: suporte polar não mede a mesma quantidade que a fração nominal de oclusão, sua geometria pode estar errada e um único acerto não estabelece uma fronteira global. Esses números não substituem os limites nominais de 99,5% superior e 99% inferior do ensaio sintético.

## Figuras, auditoria e próximos requisitos

As pranchas prontas foram copiadas e conferidas em `outputs/`, dentro da pasta do projeto no OneDrive. As cópias temporárias também permanecem disponíveis. Caminhos relativos a `outputs/`:

- `casos_oculares_reais_2026-10-27/CASOS_CLINICOS_01.png` e `CASOS_CLINICOS_02.png`: original, máscara automática, recorte e faixa polar dos 12 registros clínicos (nove explícitos e três acompanhamentos).
- `casos_oculares_escala3_2026-10-27/CASOS_CLINICOS_01.png` e `CASOS_CLINICOS_02.png`: os mesmos casos no controle de escala.
- `casos_oculares_reais_2026-10-27/UBIPR_SUPORTE_NATURAL_01.png`: seis exemplos UBIPr, sem diagnóstico.

As pranchas completas foram inspecionadas visualmente e permanecem fora do Git. Uma composição documental selecionada, com controles Normal eye da mesma base e dois casos alterados, acompanha o [relatório de avanço](../Relatórios-de-Avanço/RELATORIO_AVANCO_2026-10-27.md), com atribuição e licença. As duas auditorias reproduziram exatamente fusão, decisões, limiar, rótulos de identidade, grupos UBIPr e a contagem de cadastros indisponíveis, e verificaram os hashes das 42 fotos. Passaram um teste de correspondência do olho genuíno e dois de escala/mapeamento de máscara. Não se repetiu toda a suíte do projeto.

Foram preservados 49 arquivos (incluindo pranchas, escores e fontes) em ZIP de 5.503.752 bytes, distribuído em oito partes locais. A restauração conferiu todos os hashes, e ambas as auditorias passaram novamente nos artefatos restaurados. As 14 cópias JSON legíveis estão nas duas pastas correspondentes de `outputs/`. Os caches de pré-processamento e as fotos originais não foram duplicados no pacote; a sincronização do OneDrive não foi verificada.

O estudo mostra a necessidade de **segmentação clínica revisada antes de estimar aproveitamento anatômico**. O próximo passo adequado é delimitar íris visível, pupila, oclusões e incerteza com revisão humana especializada, validar vínculos e captura repetida e só então avaliar identificação em um protocolo registrado. Inferir a área verdadeira a partir de uma máscara que já falhou confundiria erro do segmentador com perda de tecido. A referência principal continua preservada.
