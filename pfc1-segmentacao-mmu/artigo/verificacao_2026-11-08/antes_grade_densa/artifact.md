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

## Fechamento da entrega em 08/11/2026

- Entrega: ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx, conferido no Word e no PDF de QA: 30 páginas de conteúdo e 4 de referências; referências começam na página física 31.
- 31 referências, 12 tabelas nativas e 5 figuras. Os recortes clínicos são fotografias reais do SLP-VLD, com rótulos, créditos, licença e proveniência; não são referências anatômicas validadas.
- Todas as 34 páginas finais foram inspecionadas em resolução original. Páginas já inspecionadas foram reaproveitadas apenas quando os PNGs finais tinham o mesmo SHA-256. Evidência por página em VERIFICACAO_FINAL.json.
- Curva completa de 13 condições: original e perdas de 1%, 5%, 10%, 20%, 30%, 31%, superior e inferior. 486 consultas por condição; 480 com referência de área definida. Contagens e decisões foram reproduzidas pelo avaliador histórico congelado.
- A tentativa de fusão aprendida não superou o controle fora das dobras de validação; os pesos históricos foram mantidos. Não se anuncia uma melhoria inexistente nem um mínimo universal ou clínico.
- Comparação pareada de 30% e 31%: perdas de Rank-1 de 0,62 e 1,03 pontos; os dois intervalos descritivos incluem zero. A conclusão preserva a diferença entre fração anotada e área utilizável normativa.
- Modelo institucional, estilos, margens, tema, cabeçalhos e demais partes opacas preservados. Links das referências ativos; tabela principal e tabela residual mantidas inteiras. Conferir verificacao_pacote.json e PAGINACAO_WORD.json.
- O renderizador usa o pacote documents 26.1105.12137 e uma instância do Word local em modo invisível, sem salvar a cópia de entrada. Não fecha documentos do usuário. O pacote anterior do renderer foi substituído no ambiente entre 05/11 e 08/11.
- PDF e PNGs de renderização permanecem temporários como QA; a entrega do artigo é o DOCX. A versão anterior foi preservada em historico/ARTIGO_AREA_IRIS_ANTES_ATUALIZACAO_2026-11-08.md.

## Refino de recortes em 08/11/2026

Versão final v12 em %TEMP%/pfc-artigo-unisatc-20261105/versao12, 34 páginas, referências a partir da31. Fonte e três figuras atualizadas; nenhuma alteração nas fontes/modelos do ensaio congelado. Inspeção original1414x2000: páginas16,17,24,27 emv12; páginas25,26,28,29,30 emv11 com PNGs idênticos av12. Demais25páginas idênticas av10, revisão original preservada em antes_refino/VERIFICACAO_FINAL.json. A legenda do caso vazio foi centralizada após detectar corte de texto emv11. A avaliação pareada de78imagens distingue melhoria conservadora da margem contínua e refino SAM inferior; nenhuma melhoria de identidade atribuída às novas figuras.

## Fechamento da incerteza em 08/11/2026

Versão final v16 em %TEMP%/pfc-artigo-unisatc-20261105/versao16. Word e PDF de QA confirmaram 34 páginas, sendo 30 de conteúdo e 4 de referências. Apenas a página 18 mudou em relação à v15; foi inspecionada na resolução original de 1414 × 2000. As demais 33 páginas têm PNGs byte a byte idênticos aos da versão já revisada. A cadeia de conferência está em REVISAO_VISUAL.json e VERIFICACAO_FINAL.json; a QA da v15 foi preservada em antes_incerteza/.

O texto explicita os intervalos descritivos de 95% do controle da rodada atual: Rank-1 de 84,79% a 95,83%, TAR de 86,25% a 96,75%, FMR de 0,514% a 1,278%. As estimativas pontuais aprovadas não foram convertidas em garantia populacional. As contagens, os modelos, o limiar, as cinco figuras e as doze tabelas permaneceram iguais. O guia auxiliar está em outputs/defesa_consolidada_final_2026-11-08/GUIA_DEFESA.md, com os três critérios marginais, o sucesso conjunto e a interpretação da incerteza separados.
