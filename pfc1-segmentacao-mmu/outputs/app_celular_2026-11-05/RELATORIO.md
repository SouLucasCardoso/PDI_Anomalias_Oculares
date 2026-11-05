# Protótipo móvel — estado da entrega

## Implementado

Aplicativo web local para o S23, cadastro independente por pessoa e lado do olho, captura pela câmera nativa/galeria, recorte na resolução original, inferência SAM3.1 residual, nove componentes de identidade, visualização da máscara/faixa polar, ordenação experimental, registro posterior dos testes, descarte e exclusão. Sem nuvem de processamento, limiar de identificação para telefone ou probabilidade inventada.

Modo principal de apresentação: USB-C, servidor no loopback `127.0.0.1:8787`, `adb reverse` apenas dessa porta, Platform-Tools 37.0.1 estável baixado do catálogo oficial e verificado. O download e `adb version` foram concluídos. A ponte ADB usa porta local 5038. Não foram instalados drivers nem alteradas configurações do Android.

## Verificado

- Quatro testes automatizados de fronteira: acesso sem autenticação, Host/Origin, proibição de servir o repositório, fotos inválidas, limite de tentativas de pareamento, exigência de revisão, lados/versões separados, repetição exata da foto e exclusão restrita aos dados do app. Motor simulado nesses testes HTTP.
- Inferência **real na GPU**, offline, em três fotos VAL já existentes: duas sessões da pessoa 49 e cadastro da pessoa 79. Todos os nove descritores finitos produzidos; uma consulta colocou a pessoa 49 em primeiro entre dois candidatos. Não é estimativa de acurácia nem teste do S23. Metadados e escores integrais: `verificacao_real/VERIFICACAO.json`.
- Uma tentativa inicial em `C117_S1_I10_L.jpg` foi recusada por máscara vazia. Nenhum sucesso de reconhecimento foi atribuído a essa imagem. O smoke de três fotos foi refeito com sujeitos que têm ambas as sessões, sem usar máscaras de referência para extração; esse conjunto é apenas verificação funcional.
- Sintaxe JavaScript válida, elementos referenciados presentes e IDs HTML únicos.
- Servidor ativo: página, JS, CSS, status, pareamento e QR retornaram HTTP 200; galeria sem autenticação retornou 401. Cadastro real do celular vazio no momento da verificação. `HTTP_ATIVO.json` registra os checks.

## Pendências concretas

- **Teste físico no S23:** ainda não realizado. Na consulta inicial, o ADB não enumerou nenhum aparelho. O usuário está preparando cabo e autorização USB; o aplicativo não deve ser descrito como já validado no celular.
- **Inspeção visual automatizada:** bloqueada por indisponibilidade do host de Browser/Computer Use e do pipe nativo. Não houve screenshot ou aprovação visual automatizada da interface.
- **Alternativa Wi-Fi/hotspot:** iniciador com descoberta dinâmica de IPv4 preparado; nenhuma regra de firewall aplicada. A revisão automática rejeitou a criação persistente da regra TCP 8787 porque faltava aprovação explícita do usuário para a alteração de segurança. USB é a alternativa preparada que preserva o isolamento de rede.

## Limites científicos

Os padrões do benchmark não são transferidos como limiar/precisão do celular. O protótipo usa pesos selecionados na validação histórica em leitura; não é uma nova confirmação independente. A faixa polar emprega geometria automática aproximada. A seleção de candidatos não confirma identidade, não mede área anatômica e não demonstra efeito de patologias.

Uso: [APP_CELULAR.md](../../APP_CELULAR.md). Delimitação do artigo: [ENCERRAMENTO_EXPERIMENTAL.md](../../artigo/revisao_bibliografica_2026-11-05/ENCERRAMENTO_EXPERIMENTAL.md).
