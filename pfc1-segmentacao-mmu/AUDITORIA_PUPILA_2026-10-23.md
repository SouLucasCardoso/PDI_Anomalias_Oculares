# Auditoria dos alvos da pupila — 23/10/2026

## Conclusão

O localizador treinado ontem continua mais próximo dos alvos aproximados que a alternativa concêntrica mesmo quando os buracos do canal de máscara são preenchidos. A auditoria não encontrou cruzamento dos contornos internos de referência com o externo ajustado nos 879 exemplos examinados. Entretanto, esses contornos internos não são circulares: a mediana da razão eixo menor/eixo maior foi 0,7618. Isso justifica investigar uma representação elíptica, sem demonstrar que ela melhorará a identificação.

## Desenho e limites

Foram usadas todas as 879 imagens dos 16 participantes do monitor interno do treino original. Esse conjunto já serviu para escolher a época do localizador; portanto, a análise é descritiva, não uma confirmação independente. O segmentador também já havia visto essas pessoas no seu próprio treinamento. Não houve novo ajuste de parâmetros, seleção de limiares, execução de identificação na validação ou inferência no teste.

A intervenção preencheu buracos somente no canal de máscara predita de 64 × 64 pixels, mantendo RGB e alvos idênticos. Ela alterou 860 máscaras; as outras 19 já não tinham buracos nessa resolução. Essa topologia reduzida não equivale à classificação de fallback na imagem nativa. Preencher um canal auxiliar não simula oclusão física do olho.

Os alvos continuam sendo círculos equivalentes em área derivados de buracos na anotação da íris. Não são anotações anatômicas independentes da pupila. A comparação com elipses descreve esses buracos e não valida sua fidelidade anatômica.

## Medidas

| Entrada ou método | Perda ponderada contra o alvo aproximado | Erro médio de centro normalizado na ROI | Erro médio absoluto de raio normalizado |
|---|---:|---:|---:|
| Localizador, máscara original | 0,0001663508 | 0,015939 | 0,007978 |
| Localizador, buracos preenchidos | 0,0001723508 | 0,016367 | 0,008045 |
| Aproximação concêntrica | 0,0008265907 | 0,051288 | 0,018502 |

A remoção dos buracos aumentou a perda em aproximadamente 3,61%. O deslocamento médio do centro entre as duas entradas foi 0,004389 em coordenadas normalizadas da ROI. Essas medidas não são porcentagens de identificação nem erro anatômico em pixels; centro e raio têm convenções de normalização diferentes, documentadas no código.

A razão eixo menor/eixo maior dos alvos elípticos teve média 0,7410 e mediana 0,7618. Todos os 512 pontos amostrados na borda de cada elipse interna e de cada círculo equivalente ficaram dentro da elipse externa ajustada: zero exemplos com ponto fora, em ambas as representações. Trata-se de uma verificação discreta de geometria de referência, não uma prova de contenção contínua nem uma avaliação das previsões nativas do localizador.

O menor erro geométrico já observado ontem não levou à aprovação biométrica: com a calibração fixa, a validação limpa teve Rank-1 de 90,0415%, TAR de 90,2490% e FMR de 1,0235%. A recalibração limpa teve TAR de 89,8340%. A auditoria de hoje não altera essa decisão.

## Próxima hipótese

A comparação seguinte deverá representar centro, dois eixos e orientação, preservando a máscara e a elipse externa, com controles explícitos de contenção. Ela precisará separar ganho de representação do ganho de treinamento. Ainda não foi treinado um modelo elíptico. O diagnóstico atual não autoriza afirmar que a forma circular explica os erros de identificação.

O reconhecedor de referência e seus 91,36% de Rank-1 no teste anteriormente examinado permanecem inalterados. As fronteiras nominais já aprovadas na grade continuam em 100% para oclusão superior e 99% para inferior, sem interpretação de mínimo clínico universal.

## Rastreabilidade e armazenamento

- [Protocolo anterior à execução](outputs/auditoria_alvos_pupila_2026-10-23/protocolo.json).
- [Resumo completo](outputs/auditoria_alvos_pupila_2026-10-23/CONCLUIDO.json).
- [Medidas por imagem](outputs/auditoria_alvos_pupila_2026-10-23/por_imagem.csv).
- [Médias por participante](outputs/auditoria_alvos_pupila_2026-10-23/por_pessoa.json).
- [Código](auditar_alvos_pupila.py) e [testes geométricos](test_auditoria_alvos_pupila.py).

A gravação direta pelo Python no OneDrive falhou com WinError 2 ao criar a pasta, tanto no sandbox quanto na execução escalada. A análise terminou em uma pasta temporária e seus cinco arquivos textuais foram preservados no projeto pelo mecanismo de edição disponível. A causa atual e o upload na nuvem não foram verificados. Nenhuma configuração de segurança foi alterada.

Na nova tentativa autorizada pelo usuário em 23/10, PowerShell e Python conseguiram gravar e ler arquivos diretamente no projeto. Os cinco artefatos da auditoria foram regravados com os bytes originais e conferidos por SHA-256. O registro está em [VERIFICACAO.json](outputs/verificacao_gravacao_2026-10-23/VERIFICACAO.json). Isso confirma a gravação local na pasta do OneDrive, sem confirmar o upload na nuvem. Nenhuma configuração do Defender foi alterada pelo agente.
