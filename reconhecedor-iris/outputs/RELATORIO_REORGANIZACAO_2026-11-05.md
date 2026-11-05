# Reorganização e compatibilidade — 05/11/2026

O reconhecedor passou para uma pasta própria, mantendo os atalhos usados anteriormente. O servidor permanece no loopback, com encaminhamento USB da porta 8787. O S23 foi detectado como autorizado e a ponte foi restabelecida, sem publicar seu número de série.

Foram preservados o banco de cadastro, as capturas, os descritores e os testes locais. O núcleo de inferência original não foi alterado; a nova pasta o importa por uma ponte. O identificador do motor continua `9f2eeac6c8420b5a1131677991438a8eaf14a73ec28ba54e858d3751e7bf01ce`.

Na comparação com a verificação anterior, os **27 arrays** de três fotografias e nove componentes foram exatamente iguais. A proveniência e a lista de candidatos/escores também coincidiram exatamente. Os testes automatizados passaram: **46 de ciência e operação + 4 do aplicativo**, incluindo recuperação de uma análise salva após perder o estado em memória. Esses testes não estimam acurácia do celular.

O código, os guias e os relatórios são publicáveis. Cadastros, fotos, máscaras, descritores, chaves ADB, executáveis baixados, ambientes e pesos continuam locais. Os logs de inicialização antigos que estavam com handles abertos foram deixados no diretório privado anterior; não contêm o cadastro ativo e não são versionados. Nenhum dado pessoal foi descartado para reorganizar o projeto.

Verificação estruturada: [VERIFICACAO_REORGANIZACAO_2026-11-05.json](VERIFICACAO_REORGANIZACAO_2026-11-05.json). Uso e preparação: [README](../README.md).
