# Consolidação do artigo em 23 de outubro de 2026

Foi preparada uma versão completa para revisão do orientador, com 18 páginas no modelo institucional da UniSATC, cinco tabelas, duas figuras e nove referências. O texto substitui o histórico acumulado como manuscrito ativo. A versão anterior foi preservada em `historico/ARTIGO_AREA_IRIS_ANTES_CONSOLIDACAO_2026-10-23.md`.

## Conteúdo consolidado

O artigo apresenta pergunta de pesquisa, objetivos, materiais, métodos, resultados, discussão e considerações finais. Foram incluídos curso e e-mails informados pelo autor. Rodrigo Ramos Silva foi identificado como professor, sem atribuir titulação não confirmada.

As oito condições do teste foram reunidas numa tabela. O desempenho original é 444/486 identificações corretas, ou 91,36%; os mínimos nominais aprovados na grade irregular são 99,5% para oclusão superior e 99% para inferior. O texto não anuncia mínimo comum abaixo de 100%, pois a perda inferior de 0,5% não foi medida. A incerteza por participante, a reutilização do teste e a diferença entre oclusão digital e anomalia clínica aparecem na interpretação dos resultados.

As figuras mostram o processamento completo e as estimativas das três métricas com intervalos de 95%. Não foram executados novos treinos ou inferências para produzir o artigo.

## Conferência realizada

O arquivo foi renderizado pelo Word instalado e pelo renderizador empacotado de documentos. Todas as 18 páginas da última versão foram inspecionadas visualmente. Foram corrigidos os indicadores das notas dos autores, a largura da tabela inicial e os textos do fluxograma. O cabeçalho, logotipo, estilos, numeração e geometria de página do modelo foram preservados; 18 componentes do pacote original permaneceram idênticos em bytes. A última versão possui SHA256 `225b2b47eb14b22bb93e2da6bdbffbd8d19410136bb852d3621ecd54bd4901f0`.

## Arquivo Word e preservação

O Word pronto para abrir está em `%TEMP%\pfc-artigo-restaurado-20261023\ARTIGO_AREA_IRIS_CONSOLIDADO_2026-10-23.docx`. A gravação direta do binário na pasta protegida não foi possível. Não foram alteradas configurações do Defender nem adicionadas exceções.

Uma cópia restaurável do documento, das figuras, do manuscrito e dos roteiros foi preservada dentro do projeto em `backups/artigo_consolidado_2026-10-23`, em 13 partes textuais. A restauração dos nove arquivos foi executada e todos os hashes foram conferidos. O pacote ZIP reconstruído tem 609.617 bytes e SHA256 `0f450d345bdc733be9162ad9e879233e5f9da2c1f76a615b1fe12efdd1acbbbf`. O envio efetivo ao OneDrive não foi verificado. As partes `.b64` seguem a política existente de exclusão do Git; os textos e o registro de integridade podem ser versionados.

Para restaurar novamente, a partir da pasta do projeto:

```powershell
.\executar.ps1 artigo\preservar_artigo.py
```

Para manter também o `.docx` diretamente na pasta sincronizada, abrir a cópia restaurada no Word e usar **Salvar como** na pasta `artigo`. Isso utiliza o fluxo normal de edição do usuário, sem liberar executáveis no Defender.

## Próximo passo

Revisão científica e editorial pelo autor e pelo orientador, principalmente título, interpretação da fronteira, seleção dos resultados negativos e referências. O arquivo é uma versão completa para revisão, ainda sem aprovação do orientador. Não houve commit nem envio ao GitHub nesta etapa.
