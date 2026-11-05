# Delimitação para encerrar os ensaios e redigir o artigo

Pode-se encerrar a coleta atual como investigação exploratória, com resultados negativos ou insuficientes em relação ao objetivo prescrito. Isso não equivale a declarar comprovado um mínimo universal, validar o uso clínico nem considerar o manuscrito já finalizado.

## O que os registros atuais permitem afirmar

Na rodada residual SAM3.1 de 05/11/2026, o treinamento terminou após 14 épocas, com seleção da época 8. O Dice médio de segmentação foi 88,65% na condição limpa, 86,65% em zoom, 87,63% em obliquidade e 88,40% com óculos sintéticos. A meta de engenharia registrada não foi atingida.

Na avaliação de identidade limpa dessa rodada, entre 482 consultas de validação, ocorreram 431 identificações Rank-1 corretas (89,42%), 432 aceitações genuínas (89,63%) e 421 sucessos conjuntos (87,34%), com 67 falsas correspondências entre 7.230 comparações impostoras (0,927%). Os critérios de prontidão não foram satisfeitos. O arquivo `outputs/sam31_residual_2026-11-05/identidade/CONCLUIDO.json` registra fronteira vazia, ausência de mínimo atribuído, reutilização de validação e ausência de efeito clínico estabelecido. Esses números pertencem a esta rodada; não substituem nem podem ser misturados sem delimitação aos resultados históricos de outros protocolos ou conjuntos.

A revisão bibliográfica reunida nesta pasta distingue o requisito de qualidade de área utilizável ≥70% da ISO/IEC 29794-6:2015 de uma garantia universal de identificação. A fração de suporte visível anotado retida nos nossos experimentos não equivale automaticamente à fração anatômica do anel da íris usada pela norma. A literatura de reconhecimento parcial e patologias contém evidências relevantes, mas populações, sensores, algoritmos, denominadores e definições de êxito diferentes.

## Conclusão defensável

“Nas condições e protocolos avaliados, não foi possível estabelecer uma fração mínima universal de íris visível que assegure identificação sob o controle de falsas correspondências adotado. Os resultados mostram a dependência do desempenho da segmentação, da geometria, da distribuição da oclusão e do domínio de aquisição. O requisito normativo de qualidade não foi interpretado como garantia biométrica. A quantificação do efeito de patologias permanece dependente de dados clínicos anotados e avaliação específica.”

É possível apresentar o método, os experimentos, as falhas e as limitações como contribuição. Para afirmar um limiar específico de um sistema, ainda seria necessário um protocolo delimitado, calibração e confirmação independentes, intervalos de incerteza e definição explícita de denominador, sensor, população e critério de falsas correspondências. Para efeito de patologias, são necessários dados e revisão clínica apropriados.

## Protótipo móvel como demonstração separada

O demonstrador do S23 reutiliza pesos existentes sem mudar os registros experimentais. Abre cadastro próprio, captura nova, segmenta e ordena candidatos; não transfere acurácia ou limiar da base acadêmica para o telefone. Um resultado favorável ao vivo não estabelece o mínimo de área nem efeito clínico. Sua avaliação, se incluída no artigo, deve ser identificada como demonstração exploratória separada, com os resultados efetivamente observados no aparelho.

Referências e detalhes: [pesquisa bibliográfica](RELATORIO_PESQUISA.md), [matriz comentada](REFERENCIAS_COMENTADAS.md), [guia do protótipo](../../APP_CELULAR.md).
