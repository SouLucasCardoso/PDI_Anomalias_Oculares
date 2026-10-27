# Forma elíptica da pupila — 23/10/2026

## Conclusão

Foi treinada e avaliada uma saída elíptica para o localizador auxiliar. A mudança não trouxe ganho global de Rank-1 nas imagens limpas. A estratégia principal, com calibração congelada, permaneceu acima do limite de falsos reconhecimentos. A análise secundária recalibrada passou os três critérios limpos, mas com TAR menor que o reconhecedor de referência e sem aprovação sob oclusão de 10%. Nenhuma variante foi promovida; não houve nova inferência no teste ou alteração das fronteiras de área já documentadas.

## Comparação controlada

O experimento alterou somente a forma do contorno interno nos casos que utilizavam a alternativa geométrica de pupila. O centro e o raio equivalente em área do localizador circular de 22/10 foram congelados. Também foram preservados a segmentação, o contorno externo, os contornos internos ordinários, as entradas RGB, os pesos dos reconhecedores e os pesos da fusão.

A forma é representada por dois valores: `d*cos(2θ)` e `d*sin(2θ)`, com `d = 0,5*log(eixo maior/eixo menor)`. A decodificação mantém centro e área equivalente, estima dois eixos e orientação, e evita a descontinuidade de orientação em 180 graus. Uma camada linear com 8.194 parâmetros aprende esses valores a partir das características congeladas do localizador anterior. A elipse só é usada quando seus 512 pontos de borda amostrados ficam dentro do contorno externo e há suporte polar; caso contrário, retorna-se à saída circular aprendida. Isso não constitui garantia de contenção contínua ou anatomia correta.

O ajuste usou os mesmos 6.282 exemplos de 167 participantes e o monitor interno os mesmos 879 exemplos de 16 outros participantes, todos no treino original. Os alvos são elipses ajustadas aos buracos da anotação da íris, não anotações anatômicas independentes da pupila. O monitor já havia sido usado para selecionar o localizador circular; o segmentador também já havia visto esses participantes. Logo, não é uma confirmação independente.

O protocolo foi registrado antes do treino, e o protocolo de identificação antes de sua execução. Foram treinadas sete épocas, com seleção da época 4. A perda interna de forma foi 0,0045347284 contra 0,0089657586 da saída isotrópica inicial. Essa perda usa parâmetros de forma e **não pode ser comparada numericamente à perda de centro/raio do experimento circular**. O treino da forma não usou aumento de dados; as características congeladas foram calculadas sobre as entradas já preservadas. Não houve escolha por resultados de identificação ou por oclusão.

## Resultados na validação

Todas as 482 consultas foram mantidas, inclusive falhas de extração. Cada consulta consiste em uma foto original, com lado do olho informado e 16 candidatos do mesmo lado. Cada condição contém 482 comparações genuínas e 7.230 impostoras. As falhas continuaram em quatro na limpa, quatro na superior e sete na inferior.

| Estratégia | Condição | Rank-1 (%) | TAR (%) | FMR (%) |
|---|---|---:|---:|---:|
| Referência congelada | Limpa | 90,0415 | 90,6639 | 0,9820 |
| Círculo aprendido, calibração fixa | Limpa | 90,0415 | 90,2490 | 1,0235 |
| Elipse, calibração fixa — principal | Limpa | 90,0415 | 90,0415 | **1,0235** |
| Elipse, recalibração limpa — secundária | Limpa | 90,0415 | 90,0415 | 0,9820 |
| Referência congelada | Superior 10% | 80,7054 | 78,0083 | 1,3001 |
| Círculo aprendido, calibração fixa | Superior 10% | 80,4979 | 78,8382 | 1,3140 |
| Elipse, calibração fixa | Superior 10% | 81,1203 | 78,8382 | 1,3001 |
| Elipse, recalibração limpa | Superior 10% | 81,1203 | 78,8382 | 1,2863 |
| Referência congelada | Inferior 10% | 59,9585 | 57,8838 | 2,4066 |
| Círculo aprendido, calibração fixa | Inferior 10% | 60,9959 | 57,2614 | 2,3790 |
| Elipse, calibração fixa | Inferior 10% | 60,9959 | 57,2614 | 2,3513 |
| Elipse, recalibração limpa | Inferior 10% | 60,9959 | 57,2614 | 2,3375 |

Os critérios são simultaneamente Rank-1 ≥ 90%, TAR ≥ 90% e FMR empírico ≤ 1%. A elipse com calibração fixa teve 434 acertos de identificação, 434 genuínos aceitos e 74 impostores aceitos na condição limpa, falhando no FMR. A recalibração somente na condição limpa reduziu os impostores aceitos para 71, com os mesmos 434 acertos e 434 genuínos aceitos, passando estritamente os critérios limpos. A referência já tinha 434 acertos e 437 genuínos aceitos, com os mesmos 71 impostores aceitos. Assim, passar a calibração secundária não representa uma melhora sobre a referência.

O limiar principal permaneceu 0,8581747485460748. O secundário foi 0,8586236616028832, definido somente na validação limpa e usado sem mudança nas duas oclusões. Não houve busca de pesos ou escolha por desempenho com oclusão. As quatro estratégias foram previstas antes da avaliação.

## Efeito isolado da forma e incerteza

Com calibração fixa, a elipse perdeu um acerto e recuperou outro na condição limpa, em relação ao círculo aprendido. Na oclusão superior, recuperou três sem perder acertos; na inferior, perdeu dois e recuperou dois. Em relação à referência congelada, os ganhos de Rank-1 foram 0,00 ponto percentual na limpa, 0,41 na superior e 1,04 na inferior. Os respectivos IC95% foram −0,63 a 0,62; −0,83 a 2,07; e −0,63 a 2,90 pontos percentuais, todos incluindo zero.

Os intervalos usam 5.000 reamostragens pareadas por participante, com cadastro e limiar fixos; são pontuais e sem correção pela seleção de modelos. A validação foi examinada repetidamente. Esses resultados não demonstram ganho populacional de reconhecimento nem tolerância a anomalias clínicas.

Das 68 imagens limpas tratadas pela alternativa circular aprendida, 65 tiveram saída não circular; nas condições superior e inferior foram 160/167 e 197/210. Essas contagens incluem cadastro e consulta. O restante conservou a saída circular conforme as guardas previstas. Os centros foram idênticos aos circulares em todos os casos, e a diferença relativa máxima de área equivalente foi inferior a 4 × 10⁻¹⁶. As consultas tratadas continuaram em 39, 138 e 181, respectivamente; não houve remoção de imagens.

## Verificação e preservação

A recarga do modelo reproduziu a perda interna. As doze combinações de estratégia e condição tiveram escores de fusão reproduzidos com diferença máxima zero. O controle circular reproduziu exatamente o resultado de 22/10; os CSV reproduziram os NPZ, e foram conferidos hashes dos reconhecedores, calibração, limiar, disponibilidade e preservação geométrica. A suíte completa passou em **94 testes**.

- [Treino, protocolo e histórico](outputs/forma_pupila_2026-10-23/CONCLUIDO.json).
- [Avaliação e parâmetros](outputs/forma_pupila_val_2026-10-23/CONCLUIDO.json).
- [Recarga, controles e intervalos](outputs/forma_pupila_val_2026-10-23/VERIFICACAO_RELOAD.json).
- [Escores da elipse com calibração fixa, condição limpa](outputs/forma_pupila_val_2026-10-23/scores_ellipse_fixed_clean.csv).
- [Manifesto do pacote recuperável](backups/forma_pupila_2026-10-23/MANIFESTO.json).

A execução gravou em pasta temporária, sem depender de exceções do Defender. Os relatórios, protocolos, histórico, modelo JSON e tabelas foram preservados no projeto pelo mecanismo de edição; a cópia textual normaliza quebras de linha. O pacote de recuperação conserva os bytes originais do modelo, componentes e escores, incluindo fontes e auditoria, em partes Base64 ignoradas pelo Git. Ele exclui imagens de entrada, dataset bruto e pesos congelados já preservados anteriormente. A cópia legível do modelo JSON também fica fora do Git. Não houve alteração de configuração de segurança, e o upload na nuvem não foi confirmado.

Foi testada a restauração a partir das 36 partes preservadas no projeto. O pacote de 2.325.219 bytes recuperou 55 arquivos, todos com SHA-256 conferido, além da comparação das 22 cópias textuais legíveis com suas origens. SHA-256 do ZIP: `62133f7701e8c879c4ca05c53fe057d72c2469b21cd1c8e59a6741233db8736a`. O [registro da restauração](backups/forma_pupila_2026-10-23/VERIFICACAO_PRESERVACAO.json) confirma a recuperação; não confirma sincronização na nuvem.

## Resultado de referência e continuidade

O teste anteriormente examinado permanece em 91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR. As menores áreas nominais aprovadas na grade explorada permanecem em 100% para oclusão superior e 99% para inferior. Nenhuma dessas medidas é um mínimo anatômico ou clínico universal.

A comparação isolou o efeito da forma e não justificou promover a elipse. Antes de outro retreino, a decisão metodológica é avaliar a qualidade das referências geométricas e a compatibilidade dos descritores congelados com a nova normalização. Treinar mais a mesma aproximação não tem ganho garantido; a série de resultados deve ser documentada como desenvolvimento, preservando a distinção entre hipótese, calibração e confirmação.
