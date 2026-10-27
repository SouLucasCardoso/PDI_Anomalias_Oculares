# Piloto de comparação regional da textura polar

## Hipótese e protocolo

Em vez de adaptar novamente o descritor global, foi testada uma comparação entre regiões correspondentes dos mapas do encoder polar original. A hipótese era reduzir o efeito de regiões alteradas sem conhecer a identidade ou receber uma máscara de oclusão de referência. O protocolo foi registrado antes dos escores. O piloto ficou restrito ao TREINO: 167 pessoas de ajuste para estatísticas de normalização e 16 pessoas do monitor reutilizado, com 480 consultas, 16 olhos candidatos do mesmo lado e uma foto por consulta. Os encoders já viram esses participantes; não há avaliação independente de generalização.

O cache FP32 até layer3 tem mapas de 256 canais por 4 posições radiais e 32 angulares. Foram estimadas média e variância de cada canal exclusivamente nas 4.955 fotos S1 limpas elegíveis das pessoas de ajuste. Após padronização, cada grupo de quatro colunas angulares foi agregado, resultando em 32 descritores locais de 256 dimensões, normalizados por L2. O cadastro é a média dos descritores locais das fotos S1 válidas de cada olho do monitor, renormalizada por região e sempre limpa.

O candidato primário compara regiões correspondentes por cosseno e calcula a média das 24 maiores concordâncias entre as 32 regiões de cada par consulta/cadastro. O controle usa todas as 32 concordâncias. Não há busca de deslocamento, percentual, pesos ou limiar nas oclusões. Descartar oito descritores **não equivale a remover 25% dos pixels da íris**: os mapas têm campos receptivos amplos e sobrepostos. As regiões descartadas também podem variar conforme o candidato, o que pode favorecer impostores; a FMR permanece no critério.

Cada método recebe um limiar somente na condição limpa do monitor para FMR empírica de até 1%, aplicado sem alteração às duas oclusões de 10%. A anotação só definiu a intervenção sintética na preparação anterior do cache; não participa da extração ou escolha de regiões no comparador. O cadastro S1 fica limpo e não há foto limpa da consulta usada no escore. Falhas permanecem no denominador. Não foram treinados novos pesos CNN.

## Resultado no monitor de treino

| Método | Condição | Rank-1 | TAR | FMR |
|---|---|---:|---:|---:|
| Polar global original | Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 0,9861% |
| Regional, retém 24 — primário | Limpa | 371/480 (77,29%) | 209/480 (43,54%) | 0,9861% |
| Regional, todas 32 — controle | Limpa | 365/480 (76,04%) | 207/480 (43,13%) | 0,9861% |
| Polar global original | Superior 10% | 396/480 (82,50%) | 372/480 (77,50%) | 1,5694% |
| Regional, retém 24 — primário | Superior 10% | 261/480 (54,38%) | 66/480 (13,75%) | 0,0694% |
| Regional, todas 32 — controle | Superior 10% | 251/480 (52,29%) | 59/480 (12,29%) | 0,0972% |
| Polar global original | Inferior 10% | 291/480 (60,63%) | 268/480 (55,83%) | 1,6528% |
| Regional, retém 24 — primário | Inferior 10% | 231/480 (48,13%) | 36/480 (7,50%) | 0,0972% |
| Regional, todas 32 — controle | Inferior 10% | 223/480 (46,46%) | 37/480 (7,71%) | 0,1111% |

O primário não preservou o controle limpo e foi barrado antes da validação. O limiar regional foi 0,6211485688885054; o do controle local foi 0,5642381487414242. A baixa FMR ocluída veio acompanhada de rejeição de muitas consultas genuínas; não constitui sucesso. Houve uma falha limpa/superior e duas inferiores, como no cache original.

Retirar as oito menores concordâncias trouxe pequeno ganho de Rank-1 frente ao controle local em todas as condições, mas ambos ficaram muito abaixo do descritor global. O controle limpo fraco impede atribuir a perda apenas à oclusão. Este resultado não condena comparação parcial em geral: testa somente descritores intermediários congelados, essa normalização, pooling e cadastro por protótipo. Não separa causalmente a contribuição desses fatores. A rede foi treinada para seu descritor global, não para que cada região isolada seja um reconhecedor.

## Decisão

Encerrar esta formulação sem varrer percentuais, sem recalibrar sobre o monitor ocluído e sem usar validação/teste para salvá-la. Qualquer próximo comparador local precisará primeiro demonstrar discriminação limpa nas pessoas de treino, com descritores adequados à comparação parcial, antes de avaliar tolerância à oclusão. O monitor reutilizado e os resultados anteriores não serão apresentados como confirmação cega. A referência principal de 444/486 (91,36%) e a fronteira de área anterior permanecem inalteradas; não houve novo mínimo aprovado.

## Auditoria e recuperação

Passaram três testes: descarte fixo das oito menores concordâncias, mapas nulos finitos e invariância dos escores à permutação dos candidatos. A auditoria reconstruiu exatamente a padronização somente com S1 do ajuste, os protótipos de cadastro, os seis conjuntos de escores, métricas e limiares limpos, além da decisão de bloqueio. A correspondência das consultas, os lados, hashes e a separação de pessoas foram verificados.

A execução original salvou resultados completos, mas terminou com erro de impressão: `flush=True` estava passado a `json.dumps`. A correção posterior alterou apenas a impressão final, sem repetir a inferência ou mudar os escores. O código originalmente registrado permanece em `source.py`; a auditoria confirma essa diferença exata e o hash do código executado. A mensagem de erro não foi tratada como falha do método ou apagada do histórico.

Foram preservados 19 arquivos em 26 partes base64, ZIP de 1.232.507 bytes, incluindo protótipos, normalização, escores e código. O cache original de 1,59 GB é reutilizado por hash e não foi duplicado. O pacote foi restaurado, com hashes e auditoria compacta de decisões conferidos. Isso não comprova sincronização do OneDrive.

Durante a recuperação, uma política de Controle de Aplicativo do Windows bloqueou o carregamento de `torch/lib/shm.dll`. A execução e a primeira auditoria completa já haviam terminado. As rotinas de preservação e auditoria foram desacopladas do PyTorch; a segunda auditoria completa e a recuperação compacta passaram usando apenas NumPy e a biblioteca padrão. Não foram criadas exceções de segurança. O bloqueio continua relevante para futuras execuções de redes; não foi afirmado que o PyTorch voltou a carregar.

```powershell
.\executar.ps1 preservar_comparacao_regional.py
.\executar.ps1 auditar_comparacao_regional.py --root "$env:TEMP/pfc-regional-restaurado-20261023"
# Reprodução completa dos escores requer o cache original:
.\executar.ps1 auditar_comparacao_regional.py --root "$env:TEMP/pfc-regional-restaurado-20261023" --cache-root "$env:TEMP/pfc-tcc-resultados"
```
