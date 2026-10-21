# Continuação: resolução interna do encoder polar

**Concluído:** 29 épocas, seleção na 21. Encoder denso: 61,62% de Rank-1,
46,68% de TAR. Fusão fixa de quatro componentes: 78,84% e 68,26%; fusão com
métricas lineares: 78,22% e 65,98%, todas com FMR 0,99% na validação.
Mantida a fusão anterior como referência, pois nenhuma nova configuração
melhorou ambas as métricas. Mínimo de área não determinado. Os 39 testes
passaram e o checkpoint recarregado reproduziu os escores com erro máximo
zero. [Relatório completo](outputs/fusao_densa_val_2026-10-20/RELATORIO_CONTINUACAO.md).

Condições confirmadas pelo aluno: UBIPr principal, uma foto por consulta. Cadastro com várias imagens permitido. Critério mantido: Rank-1 e TAR de pelo menos 90%, com limiar calibrado na validação para FMR empírica de no máximo 1%; o mínimo de área exige aprovação também em todos os níveis de maior área preservada.

## Ensaio registrado

`treinar_encoder_polar.py --dense` treina novamente a partir de ImageNet, retirando o max-pooling inicial do ResNet18. Preserva mais posições espaciais ao longo da rede sem inventar detalhes na imagem. Mesmo cache polar, máscaras automáticas, seed 45, margem 0,3, AdamW 3e-4, até 30 épocas e paciência 8. Lote 32 em vez de 64 para memória: não é uma ablação que isole exclusivamente a arquitetura. Seleção por TAR e depois Rank-1 na validação já utilizada em desenvolvimento.

Nenhum novo teste de reconhecimento ou oclusão é disparado por esse treinamento. Só `CONCLUIDO.json` indica término.

## Local dos artefatos nesta execução

A criação de novos arquivos por Python/PowerShell no diretório do OneDrive falhou com `FileNotFoundError`, mesmo quando a pasta existente era legível. A causa não foi identificada; não houve alteração de proteção do Windows ou do OneDrive. Edições pelo mecanismo de patch continuaram funcionando. Foi verificado que a API de arquivos Node conseguia copiar para o projeto: as cópias são conferidas por SHA-256.

Para permitir a execução, os novos artefatos foram direcionados inicialmente a `%TEMP%\pfc-tcc-resultados\encoder_polar_denso_2026-10-20`. Após o término, os oito arquivos foram copiados para `outputs/encoder_polar_denso_2026-10-20`; os cinco arquivos da fusão e os oito da métrica linear também foram copiados para as respectivas pastas em `outputs/`. Todas as cópias tiveram SHA-256 conferido. Não dependem mais da pasta temporária. Os experimentos anteriores no projeto permanecem preservados.

Backup verificado da rodada anterior: `backups/pf_1021T021138.zip`, 154 arquivos, 44.693.707 bytes. SHA-256: `44d8a700a7afae717b7892bd2ca16dd7a33a96fa7026c182a8fcbed5698afdc7`. Todos os arquivos internos tiveram o hash conferido, além do CRC do ZIP. Inclui checkpoint polar, escores e fontes; não inclui os datasets ou os caches volumosos de imagens. A cópia temporária também permanece disponível.

## Comparações posteriores definidas antes do resultado

Após o treino, comparar o novo encoder isoladamente e uma fusão fixa de quatro componentes: RGB anterior, polar anterior, descritor espacial anterior e novo polar denso. Pesos iguais de 1/4, mesma padronização por impostores da validação e transformação logística das fusões anteriores. Exigir todos os componentes válidos e manter todas as consultas no denominador. Não procurar pesos na validação. Essa comparação é exploratória e não constitui confirmação independente.

## Controle linear complementar registrado

`validar_metrica_intra_classe.py` mantém os encoders RGB e polar anteriores congelados. Extrai os vetores das imagens de treino, estima a média global e a covariância das diferenças em relação à média de cada olho de treino. Usa regularização fixa de 0,1 em direção à identidade multiplicada pela variância média, aplica a raiz inversa da covariância e normaliza os vetores. Não ajusta esses parâmetros nas pessoas de validação. Define três resultados: RGB transformado, polar transformado e fusão fixa de pesos iguais entre ambos e o descritor espacial anterior. Limiar e padronização de fusão continuam calibrados na validação, portanto a avaliação permanece de desenvolvimento. Não haverá busca de intensidade de regularização nem seleção de consultas pela qualidade.
