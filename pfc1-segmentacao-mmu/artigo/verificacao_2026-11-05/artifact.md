# Contrato do artigo no modelo UniSatc

Referência retida: `C:/Users/lucaz/OneDrive/Documentos/SATC/0 - Disciplinas/SEMESTRE 8/PFC I/Modelo_artigo_Computacao_e_software_2026_2-6a8d952b18e6b.docx`.
SHA-256: `e8d9f33821f15443b4c27d3289a4d65cc110385dcbdca790a3766030257ac2eb`. Original inalterado.

O contrato anterior da mesma referência foi distilado em `../verificacao_2026-10-27/artifact.md`. Nesta revisão, as 11 páginas do modelo foram novamente renderizadas pelo Word e inspecionadas. Evidência visual: `%TEMP%/pfc-artigo-unisatc-20261105/template-render/`. O runtime gerenciado foi resolvido pelo manifesto `C:/Users/lucaz/.cache/codex-runtimes/codex-primary-runtime/runtime.json`: Python em `dependencies/python/python.exe`, Node em `dependencies/node/bin/node.exe` e Poppler em `dependencies/native/poppler/Library/bin`. Não há LibreOffice empacotado nesse runtime; a exportação utiliza uma instância invisível própria do Word, seguida do renderer empacotado da habilidade documents.

## Sistema de página e estilos

Uma seção em A4 retrato, 21,0009 × 29,7004 cm. Margens superior/esquerda 3,0004 cm e inferior/direita 2,0002 cm. Numeração PAGE no alto à direita e logotipo institucional conforme as relações originais. Preservar `sectPr`, cabeçalhos, rodapés, tema, fontes e numeração.

Texto corrente conforme as instruções visíveis do modelo: Arial 12, justificado, espaço 1,5, primeira linha com recuo de 2 cm. A declaração interna do estilo `1Texto` herda Times New Roman; os parágrafos instrucionais do modelo usam Arial por formatação direta. A revisão mantém o mesmo mecanismo de formatação direta Arial, sem reescrever o arquivo de estilos.

Title centralizado, negrito, em maiúsculas. Autores no estilo Assinaturas à direita, com notas reais 1 e 2. Resumo em parágrafo único com entrelinha simples e palavras-chave no estilo próprio. Fonte das notas 10. Seções primárias em negrito e maiúsculas, secundárias em maiúsculas sem negrito, terciárias em negrito com capitalização de frase; todas com os estilos e a numeração originais.

Tabelas editáveis em Arial 10, com largura deliberada total de 16 cm. Bordas horizontais e ausência de grade vertical reproduzem os exemplos institucionais, em lugar do padrão genérico da habilidade. Linhas não partidas e cabeçalhos repetidos. Figuras com título sequencial acima, corpo legível e crédito abaixo em Arial 10; legendas centralizadas em Arial 12.

Referências em ordem alfabética, fonte Arial 12, alinhamento à esquerda, entrelinha simples e separação por dois espaços simples. Título não numerado. URLs ativas. Os exemplos de referências, agradecimentos e lista de símbolos do manual são conteúdo instrucional removível.

## Conteúdo e alterações autorizadas

O usuário solicitou atualização do artigo com **30 páginas de conteúdo, excluídas as referências**, e imagens dos melhores recortes disponíveis em controles normais e casos com alterações. Essa exigência específica de contagem prevalece sobre o intervalo geral mencionado no modelo. O fluxo final será contínuo, com a seção Referências iniciando na página física 31, sem páginas vazias para completar a contagem.

Corpo: resumo, introdução, materiais e métodos, resultados e discussão, considerações finais. Atualizar os resultados de novembro, a revisão bibliográfica e a demonstração móvel sem alterar métricas históricas ou afirmar mínimo universal. Imagens documentais selecionadas, com diagnóstico/rótulo da base e máscara prevista identificados; manter exemplos de falha e não atribuir desempenho médio à seleção visual.

## Mapa de slots e preservação

`word/document.xml`, seus relacionamentos e Content Types: substituir o corpo instrucional e adicionar imagens/tabelas/citações; preservar a seção e os estilos. `word/footnotes.xml`: atualizar as duas notas dos autores previamente informados. `word/settings.xml`: habilitar atualização de campos. `docProps/core.xml`: atualizar título, autores e assunto.

Todos os demais componentes originais são preservados byte a byte. A saída declara e verifica esse inventário em `verificacao_pacote.json`. Novas imagens são identificadas pelas relações próprias. Não há controles de conteúdo ricos a preencher; não modificar logotipos ou exemplos do manual para simular resultados. Os marcadores internos `PFC_PAGINA_*` são localizadores de blocos, não texto visível nem garantia de paginação; a contagem é obtida da renderização do Word.

## Portas de verificação

Conferir hash do modelo antes e depois, inventário de partes preservadas, seção/margens, autores/notas, cinco figuras e doze tabelas. Renderizar para PNG, inspecionar todas as páginas finais e verificar os limites das tabelas/figuras, caracteres e numeração. Medir pelo Word e pelo PDF que as referências começam na página 31. Registrar a contagem total e as páginas de referência separadamente. Entregar o DOCX atualizado; PNGs/PDF de QA são intermediários.
