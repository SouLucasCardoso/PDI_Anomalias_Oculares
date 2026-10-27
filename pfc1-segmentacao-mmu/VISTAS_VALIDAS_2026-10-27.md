# Correção das perdas de vistas inválidas — 27/10/2026

## Hipótese e controle

O piloto de diversidade de 24/10 gerou dez vistas cuja extração automática não produziu textura útil. Essas vistas receberam textura neutra, mas ainda participavam das perdas de identidade. A correção elimina sua contribuição nas três perdas por vista: alinhamento ao descritor limpo, margem contra impostor e penalização absoluta de escores. A regularização dos kernels permanece global. O denominador fixo de seis por foto preserva os pesos das vistas válidas; não há compensação aumentando seu peso.

Não são removidas fotografias, e falhas de avaliação permanecem nos denominadores. Todas as 6.067 fotos do ajuste continuam no treinamento, com três vistas cada. Há zero vistas limpas inválidas, duas superiores e oito inferiores. Apenas dez das 18.201 vistas têm sua contribuição de identidade zerada; não se presume um grande ganho por corrigir uma fração tão pequena.

O ensaio reutiliza exatamente os 3.222 mapas de intervenção e o plano sorteado do piloto anterior, sem nova segmentação, novo sorteio ou alteração dos pixels. Mantém 151 pessoas para ajuste, 16 para calibração interna e 16 do monitor antigo. Rede, oito épocas, semente 63, AdamW, pesos das perdas, cadastro e regras de seleção/calibração são iguais. Os pesos partem do encoder original. O protocolo foi salvo antes do treinamento; não há busca de hiperparâmetros.

## Verificações do código

Cinco testes direcionados passaram antes da execução: equivalência de valores e gradientes com a formulação anterior quando todas as vistas são válidas; gradiente zero nas inválidas em cada perda; perda e gradiente zero se todas são inválidas; peso inalterado das demais vistas; e ausência das perdas de consulta quando o lote só possui cadastros. A tolerância do teste de equivalência é 1e-12 em precisão dupla.

## Avaliação e interpretação

A época é escolhida pela perda do ajuste entre aquelas que preservam Rank-1/TAR do limpo interno e FMR interna de até 0,5%. O limiar interno limpo selecionado é único para todas as condições. O monitor só é aberto depois de congelar os pesos. Os encoders anteriores já viram essas pessoas e o monitor é reutilizado; esta execução não é confirmação independente.

O piloto não pode substituir a referência principal nem alterar o mínimo de área automaticamente. A barreira exige preservar o limpo, FMR de até 1% em todas as condições e ganho estrito de Rank-1/TAR nas duas oclusões sobre o encoder original. A comparação com o piloto diverso anterior também deve ser reportada. Não há inferência nova de validação ou teste nesta rodada.

## Resultado das oito épocas

A época 8 foi selecionada pela regra registrada. O limiar interno limpo foi 0,2904952963193258. No monitor reutilizado, a comparação direta é:

| Condição | Rank-1 anterior → corrigido | TAR anterior → corrigido | FMR anterior → corrigido |
|---|---:|---:|---:|
| Limpa | 479/480 → 479/480 (99,79%) | 479/480 → 479/480 (99,79%) | 49/7200 → 49/7200 (0,6806%) |
| Superior 10% | 398/480 → 397/480 (82,71%) | 379/480 → 381/480 (79,38%) | 101/7200 → 96/7200 (1,3333%) |
| Inferior 10% | 315/480 → 314/480 (65,42%) | 278/480 → 278/480 (57,92%) | 93/7200 → 91/7200 (1,2639%) |

O código agora trata corretamente as vistas inválidas, mas não houve melhoria conjunta de reconhecimento. A diferença entre candidatos é pequena, exploratória e não constitui evidência estatística de superioridade. Em ambas as oclusões, a FMR continua acima das 72 falsas correspondências permitidas em 7.200 comparações. A regra de avanço falhou; não houve avaliação de validação/teste, troca do reconhecedor ou novo mínimo de área.

A referência anterior continua em 91,36% no teste já examinado; as fronteiras nominais continuam 99,5% superior e 99% inferior. Esta correção não resolve o problema principal de discriminação sob oclusão e não justifica uma busca de limiares ou pesos sobre o monitor. A pequena dimensão do defeito corrigido e a falta de ganho reforçam a necessidade de encerrar os ajustes incrementais desta linha, preservando tempo para análise e artigo.

## Reprodução

Os scripts `treinar_vistas_validas.py`, `auditar_vistas_validas.py` e `preservar_vistas_validas.py` usam a mesma estrutura de recuperação dos pilotos anteriores. O ensaio está em `%TEMP%/pfc-tcc-resultados/vistas_validas_treino_2026-10-27`. Os caches grandes são reutilizados por hash, não duplicados. O pacote de recuperação local é ignorado pelo Git, conforme a política existente para pesos e escores derivados.

A auditoria completa reproduziu exatamente escores, decisões, limiar, seleção de época, separação de pessoas, pixels das intervenções e dez flags inválidas. O pacote contém 42 arquivos em um ZIP de 32.770.356 bytes, preservado em 44 partes. A restauração conferiu os hashes de todos os arquivos e recuperou exatamente os dois checkpoints, sem quantização. Nove cópias JSON/CSV legíveis estão em `outputs/vistas_validas_treino_2026-10-27`. Não foi alterada a segurança do Windows e não foi verificado o upload do OneDrive.
