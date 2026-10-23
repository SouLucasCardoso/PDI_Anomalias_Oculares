# Bloqueio de gravacao na pasta sincronizada

## Atualizacao: gravacao restabelecida

Apos o usuario informar que autorizou Node, PowerShell, Git e Codex Sandbox no Defender, os novos testes de gravacao por PowerShell e Python funcionaram. O arquivo temporario do teste foi removido. Nao foi necessario executar o script de alteracao de permissoes preparado abaixo.

Os tres ZIPs foram copiados para `pfc1-segmentacao-mmu/backups` e os SHA256 conferidos com os originais: `pf_1021T204326.zip`, `fusao_regularizada_2026-10-21.zip` e `fusao_pessoas_separadas_2026-10-21.zip`, totalizando 337.022.654 bytes. As origens fora do OneDrive foram mantidas como copia adicional. Registro em `backups/VERIFICACAO_COPIA_ONEDRIVE.json`.

Isso confirma a gravacao e a integridade LOCAL na pasta sincronizada. O upload na nuvem ainda nao foi confirmado por esta verificacao; conferir o estado do OneDrive ou os arquivos na versao web. O restante deste documento preserva o diagnostico e a proposta anteriores a correcao.

Diagnostico confirmado em 21/10/2026 pelos eventos1123 do log Microsoft-Windows-Windows Defender/Operational. O Acesso Controlado a Pastas bloqueou PowerShell, Git e componentes do Codex ao modificar o projeto em OneDrive/Documentos. O log inclui bloqueios do Git sobre `.git` e dos gravadores sobre `backups` e `outputs`. O OneDrive estava em execucao. Isso demonstra bloqueio local de gravacao, nao falha comprovada de sincronizacao ou perda de arquivos.

As permissoes NTFS consultadas incluem controle total para o proprietario e permissao de modificacao para o grupo do sandbox; ha tambem uma regra de negacao de exclusao de subpastas/arquivos. Essa regra nao foi alterada. A evidencia direta para as falhas investigadas e o evento de bloqueio do Defender. Nao foram alteradas configuracoes de seguranca.

Uma tentativa de copia pelo mecanismo Shell.Application do Explorador nao concluiu e foi interrompida; nao foi considerada bem-sucedida. Os tres ZIPs continuam preservados em `C:/Users/lucaz/pfc-tcc-backups`.

## Correcao preparada, aguardando autorizacao

`corrigir_gravacao_onedrive.ps1` mostra o plano por padrao, sem alterar configuracoes. A aplicacao exige `-AplicarPermissoes` e PowerShell como administrador. A lista e limitada a:

- `C:/Users/lucaz/pfc-tcc-venv/Scripts/python.exe`
- `.runtime/python312/python.exe` dentro deste repositorio
- `C:/Program Files/Git/ucrt64/bin/git.exe`

Autorizar esses executaveis permite que eles gravem nas pastas protegidas do Windows; o alcance nao e limitado somente ao projeto. O script nao desliga o Defender, nao muda a lista de pastas protegidas, nao adiciona exclusoes de varredura e nao autoriza PowerShell, Node ou componentes do Codex. A configuracao anterior e a lista de adicoes planejadas sao salvas fora do OneDrive antes da alteracao.

Depois de confirmar as permissoes, o script inicia um novo processo Python para copiar os tres ZIPs para `pfc1-segmentacao-mmu/backups`, mantendo as origens. Os SHA256 das origens e destinos sao verificados; arquivos existentes com conteudo diferente nao sao sobrescritos. A copia so sera marcada como concluida depois da verificacao. Ela ainda NAO foi executada com sucesso.

Executado ate agora: plano sem alteracoes, validacao da existencia dos executaveis e verificacao de sintaxe. O upload na nuvem deve ser confirmado separadamente pelo estado do OneDrive ou pela versao web. Estar dentro da pasta sincronizada nao e, por si so, prova de upload concluido.

Referencia oficial: https://support.microsoft.com/en-gb/windows/security/threat-malware-protection/virus-and-threat-protection-in-the-windows-security-app
