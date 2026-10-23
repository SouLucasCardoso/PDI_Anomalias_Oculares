# Localização aprendida da pupila — 22/10/2026

## Resultado e decisão

Foi treinado um localizador auxiliar para substituir somente a aproximação concêntrica utilizada quando a máscara não contém um contorno interno plausível. A hipótese não melhorou os critérios globais de reconhecimento. Nenhuma variante substitui o candidato congelado. Não houve nova inferência no teste nem nova estimativa de área mínima.

## Protocolo e treinamento

O localizador recebe RGB e máscara predita em uma região de 64 × 64 pixels e estima centro e raio de um círculo. A supervisão é uma aproximação obtida de buracos fechados na anotação da íris, não uma anotação anatômica independente da pupila. Portanto, diminuir essa perda não demonstra maior precisão anatômica.

Foram separados 167 participantes para ajuste e 16 para monitoramento interno, exclusivamente dentro das 7.716 imagens do treino original. A preparação produziu 6.282 exemplos de ajuste e 879 de monitoramento; 555 imagens não forneceram alvo utilizável. Essas exclusões dizem respeito somente à supervisão do localizador. Nenhuma consulta de reconhecimento foi excluída. O segmentador congelado já havia visto os participantes desse monitoramento durante seu próprio treinamento.

O treino terminou após 12 épocas, com seleção da época 8 pela menor perda interna. A perda Smooth L1 ponderada normalizada foi 0,0001663508, contra 0,0008265906 da aproximação concêntrica. A escala é de parâmetros geométricos normalizados, não de pixels nem de identificação. Checkpoint SHA-256: `e8cdccd0b76797682e8516cf3a8cffe7f2c360307a9db34f101262a60bd63f6a`.

Na validação, foram mantidas as 482 consultas, inclusive falhas, uma foto por consulta, lado informado e 16 candidatos do mesmo lado. Foram alteradas somente as texturas polares nos casos de aproximação concêntrica. As entradas RGB e os pesos dos reconhecedores permaneceram idênticos. Houve alteração em 39 consultas limpas, 138 com oclusão superior de 10% e 181 com inferior de 10%, além de 29 fotos de cadastro. A anotação de referência não foi usada para localizar a pupila na inferência; nas consultas com oclusão, serviu apenas para definir a intervenção artificial já prevista.

## Resultados completos da validação

Critérios simultâneos: Rank-1 ≥ 90%, TAR ≥ 90% e FMR empírico ≤ 1%. Cada condição contém 482 comparações genuínas e 7.230 impostoras. TAR não é a mesma medida que Rank-1.

| Estratégia | Condição | Rank-1 (%) | TAR (%) | FMR (%) |
|---|---|---:|---:|---:|
| Original | Limpa | 90,0415 | 90,6639 | 0,9820 |
| Nova pupila, calibração fixa | Limpa | 90,0415 | 90,2490 | **1,0235** |
| Nova pupila, recalibração limpa | Limpa | 90,0415 | **89,8340** | 0,9820 |
| Original | Superior 10% | 80,7054 | 78,0083 | 1,3001 |
| Nova pupila, calibração fixa | Superior 10% | 80,4979 | 78,8382 | 1,3140 |
| Nova pupila, recalibração limpa | Superior 10% | 80,7054 | 78,4232 | 1,2725 |
| Original | Inferior 10% | 59,9585 | 57,8838 | 2,4066 |
| Nova pupila, calibração fixa | Inferior 10% | 60,9959 | 57,2614 | 2,3790 |
| Nova pupila, recalibração limpa | Inferior 10% | 61,2033 | 57,2614 | 2,2960 |

A estratégia principal conservou estatísticas e limiar originais (0,8581747485460748). A análise secundária recalibrou somente na validação limpa, mantendo os pesos da fusão, com limiar 0,8595612597898948. Nenhuma delas foi escolhida por resultados com oclusão. A principal teve 74 falsos reconhecimentos, acima dos 71 originais; a secundária aceitou 433 genuínos, abaixo dos 437 originais.

Na condição limpa, ambas mantiveram 434 acertos de identificação: perderam um acerto e recuperaram outro. Na oclusão inferior, o ganho de Rank-1 foi de 1,04 ponto percentual com calibração fixa (IC95% −0,42 a 2,71) e 1,24 com recalibração (−0,41 a 3,11). Os intervalos incluem zero. Foram usadas 5.000 reamostragens por participante, com cadastro e limiar fixos, intervalos pontuais e sem correção pela seleção de modelos. Esta validação já foi examinada repetidamente; não é confirmação independente.

## Verificações e arquivos

A recarga do checkpoint reproduziu exatamente a perda interna; a reprodução das nove combinações de estratégia e condição apresentou diferença máxima de escore igual a zero. Foram conferidos hashes, separação de participantes, rótulos, disponibilidade e controles de entradas inalteradas. As falhas de extração continuaram em 4/4/7 para limpa/superior/inferior.

- [Treinamento e protocolo](outputs/localizador_pupila_2026-10-22/CONCLUIDO.json).
- [Resultados, parâmetros e mudanças](outputs/pupila_aprendida_val_2026-10-22/CONCLUIDO.json).
- [Auditoria de reprodução e intervalos](outputs/pupila_aprendida_val_2026-10-22/VERIFICACAO_RELOAD.json).
- [Fotos reais e comparação de texturas](outputs/pupila_aprendida_val_2026-10-22/qa_pupila_comparacao.png).

A imagem usa as primeiras quatro pessoas distintas por ordem de arquivo entre as consultas limpas alteradas, sem seleção por melhora. Não há geração ou restauração de textura. A figura biométrica fica fora do Git, seguindo as regras existentes, mas permanece na pasta local do OneDrive.

## Estado do estudo

O resultado anterior de teste continua em 91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR, nas condições já documentadas. As menores áreas nominais aprovadas na grade explorada continuam em 100% para oclusão superior e 99% para inferior; não representam um mínimo anatômico ou clínico universal. A nova localização não justificou mudar esses limites. Antes de outro retreino, é necessário revisar a validade dos alvos aproximados e a coerência entre contornos interno e externo: melhorar a perda de um alvo aproximado não garantiu melhorar a identificação.
