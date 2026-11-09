# Relatório de avanço — 9 de novembro de 2026

**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Dia:** segunda-feira  
**Escopo:** fechamento do artigo, conferência da entrega e organização da atualização no GitHub. Não foi iniciado novo treinamento.

## Fechamento dos resultados

Foram conferidas as conclusões das execuções encerradas em 08/11: 63 condições da referência e 63 do candidato, abrangendo todos os inteiros de 1% a 31%, nas duas posições, além do controle. A auditoria independente confirmou contagens, hashes e preservação de todas as 486 consultas por condição.

O relatório final distingue o ganho limpo do candidato — evento correto e aceito de 89,51% para 90,12%, com FMR de 0,864% para 0,823% — da reprovação geral, pois a FMR aumentou em 31 condições. A validação limpa do candidato teve evento conjunto de 88,59%; o teste limpo acima de 90% não foi apresentado como prontidão clínica. Nenhum motor do aplicativo ou modelo de referência foi substituído.

## Artigo no modelo UniSatc

A versão final incorporou a curva completa de oclusão e as três composições clínicas com apresentação subpixel. O texto mantém resultados históricos identificados, falhas de localização, créditos das imagens e limitações do denominador de área. A máscara binária não foi alterada pela suavização visual.

| Item conferido | Resultado |
|---|---:|
| Páginas de conteúdo | 30 |
| Páginas de referências | 4 |
| Início físico das referências | 31 |
| Referências bibliográficas | 31 |
| Tabelas nativas | 12 |
| Figuras | 5 |
| Condições científicas recontadas e reproduzidas | 63 |

O Word e o PDF interno de conferência coincidiram em 34 páginas. As dez páginas alteradas foram inspecionadas em resolução original; as demais 24 herdaram a revisão anterior somente após igualdade byte a byte dos PNGs. O modelo institucional e suas partes preservadas foram conferidos, com cadeia de revisão e hashes arquivados.

DOCX final SHA-256: `24c0a0bef2f77f65f7af5f5b5a3478a25b62eea1e0308690acb7686005bf515e`.

Uma checagem adicional confirmou os dez hashes de entrada do fechamento, a sincronização entre o corpo consolidado e o texto em produção e 41 links locais. O DOCX, as fotografias e os intermediários visuais de revisão permanecem locais; o Git recebe código, texto do artigo, documentação e evidências selecionadas.

## Documentação e publicação

- Complementação do relatório de 05/11 com a correção do cadastro de olhos e a preparação inicial do artigo.
- Criação do relatório retrospectivo de 08/11 e deste relatório de fechamento, sem inventar atividades para 06 e 07/11, dias sem evidência de alteração nos registros examinados.
- Atualização dos índices semanais, do README principal e da entrada do README técnico, destacando os resultados mais recentes e a diferença em relação ao teste histórico.
- Revisão do conjunto de publicação: código de pesquisa, correção do cadastro móvel, relatórios, protocolos, resultados agregados e auditorias. Pesos, caches, fotografias e cadastro privado continuam locais.

Os relatórios são registros por dia de atividade; os commits da publicação usam a data real de envio. O clone continua dependendo de dados, checkpoints e demais recursos locais para repetir a inferência e as auditorias numéricas completas.

## Verificações da atualização

Passaram os sete testes HTTP do aplicativo e as cinco verificações do formulário com DOM e transporte simulados. Cobrem isolamento, revisão antes do cadastro, nomes distintos, seleção explícita de registro, preservação das fotos ao renomear e prevenção de envio duplicado. Uma execução inicial teve interrupção transitória da conexão local no Windows; o teste isolado e a execução completa seguinte passaram. Não foi atribuída acurácia biométrica a esses testes funcionais.

## Registros técnicos

- [Fechamento consolidado](../pfc1-segmentacao-mmu/RESULTADO_GRADE_DENSA_2026-11-08.md).
- [Marcador final e hashes](../pfc1-segmentacao-mmu/outputs/FECHAMENTO_GRADE_DENSA_2026-11-08.json).
- [Verificação final do artigo](../pfc1-segmentacao-mmu/artigo/verificacao_2026-11-08/VERIFICACAO_FINAL.json).
- [Artigo em texto](../pfc1-segmentacao-mmu/artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md).
- [Código do verificador do documento](../pfc1-segmentacao-mmu/artigo/verificar_entrega_2026_11_08.py).
- [README e uso do demonstrador](../reconhecedor-iris/README.md).
