# Relatório de avanço — 23/10/2026

**Estado consolidado após o refinamento:** menor área nominal aprovada na grade estudada de **99,5% na orientação superior e 99% na inferior**. Entre os níveis avaliados nas duas orientações, o prefixo comum continua em 100%; não foi testada perda inferior de 0,5%. O reconhecedor e seu resultado original de 91,36% foram preservados. Os detalhes e a cronologia das etapas anteriores seguem abaixo.

**Acadêmico:** Lucas Cardoso Rodrigues

**Orientador:** Rodrigo Ramos Silva

## Atividades realizadas

Foi auditado o localizador de pupila desenvolvido em 22/10, com foco na dependência do contorno interno da máscara e na aproximação circular dos alvos. Foram analisadas todas as 879 imagens de 16 participantes do monitor interno, pertencentes ao treino original. Não houve novo treinamento, execução de identificação na validação ou avaliação no teste.

## Resultados

O preenchimento dos buracos do canal de máscara alterou 860 das 879 entradas, preservando todas as imagens RGB. A perda geométrica aproximada passou de 0,0001663508 para 0,0001723508, aumento de 3,61%, ainda abaixo da aproximação concêntrica (0,0008265907). O erro médio de centro foi 0,015939 com máscara original, 0,016367 com máscara preenchida e 0,051288 para a alternativa concêntrica, em coordenadas normalizadas da região de entrada. Essas medidas não são taxas de identificação.

A mediana da razão entre os eixos menor e maior dos contornos internos de referência foi 0,7618. Isso mostra que os alvos aproximados frequentemente não são circulares. Nenhum dos 879 pares apresentou ponto interno fora da elipse externa nos 512 ângulos amostrados, tanto para a elipse interna quanto para seu círculo equivalente em área. Essa checagem é limitada à geometria de referência amostrada; não prova correção anatômica nem contenção das previsões.

## Estado do reconhecimento e área mínima

O modelo auxiliar de ontem continua sem aprovação nos critérios simultâneos. Sua calibração fixa manteve Rank-1 de 90,0415%, mas apresentou FMR de 1,0235%, superior ao limite de 1%. A alternativa recalibrada ficou com TAR de 89,8340%, abaixo de 90%.

O reconhecedor de referência permanece com 91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR no teste anteriormente examinado, nas condições já documentadas: uma consulta, lado informado e 16 candidatos do mesmo lado. As menores áreas nominais aprovadas na grade explorada continuam em 100% para oclusão superior e 99% para inferior. Não foi estabelecido um percentual mínimo anatômico ou clínico universal. A auditoria de hoje não mudou esses resultados.

## Limitações e continuidade

O monitor já foi usado para selecionar a época do localizador e não constitui confirmação independente. Os alvos são derivados de buracos na anotação da íris; não são marcações anatômicas independentes da pupila. A próxima hipótese é uma representação elíptica com controles de contenção, cuja contribuição deverá ser isolada antes de qualquer promoção. Não há evidência de ganho biométrico dessa hipótese neste momento.

O Python voltou a falhar ao gravar diretamente no OneDrive, inclusive fora do sandbox. A análise terminou em pasta temporária e os resultados textuais foram preservados no projeto pelo mecanismo de edição disponível. O upload na nuvem não foi confirmado. Nenhuma configuração de segurança foi alterada.

Após a nova liberação informada pelo usuário em 23/10, a gravação e a leitura pelo PowerShell e pelo Python foram testadas novamente e funcionaram. Os cinco arquivos da auditoria foram regravados diretamente na pasta do projeto no OneDrive, com identidade de bytes confirmada por SHA-256 em relação aos originais temporários. O registro está em `pfc1-segmentacao-mmu/outputs/verificacao_gravacao_2026-10-23/VERIFICACAO.json`. A sincronização na nuvem continua sem confirmação; nenhuma configuração do Defender foi alterada pelo agente.

Protocolo, tabela detalhada, resultados por imagem e por pessoa estão no [relatório da auditoria](../pfc1-segmentacao-mmu/AUDITORIA_PUPILA_2026-10-23.md).

## Verificação

Passaram nove testes direcionados de geometria, normalização e localizador, incluindo contenção de elipses rotacionadas e o caso em que o centro está dentro mas a borda ultrapassa o contorno externo. A cópia dos cinco artefatos textuais foi comparada à origem temporária; hashes do código, 879 linhas, 16 participantes, 860 intervenções e todas as estatísticas-resumo foram conferidos. A suíte anterior de 87 testes não foi executada novamente nesta etapa; os nove testes são a verificação direcionada de hoje.

## Continuação: representação elíptica treinada

Após a auditoria, foi treinada uma saída elíptica com 8.194 parâmetros, preservando o centro, o raio equivalente e as características do localizador circular de ontem. Foram usados 6.282 exemplos no ajuste e 879 no monitor interno. O treino terminou após sete épocas, selecionando a época 4. A perda interna de forma foi 0,0045347284, contra 0,0089657586 da forma circular inicial. Essa perda tem objetivo diferente da perda circular anterior e não pode ser comparada numericamente a ela. Os alvos continuam sendo aproximações derivadas de buracos nas máscaras, sem validação anatômica independente.

A avaliação conservou todas as 482 consultas e incluiu controles da referência congelada e do círculo aprendido. Com calibração fixa, a elipse teve 90,0415% de Rank-1, 90,0415% de TAR e 1,0235% de FMR nas imagens limpas: o FMR falhou. A recalibração somente na condição limpa produziu os mesmos Rank-1 e TAR, com 0,9820% de FMR, passando os critérios limpos. Isso não supera a referência, que já tinha o mesmo Rank-1 e FMR, com TAR maior (90,6639%). Não houve promoção.

Na oclusão superior de 10%, o Rank-1 elíptico foi 81,1203%; na inferior, 60,9959%. Os ganhos sobre a referência foram 0,41 e 1,04 ponto percentual, com intervalos por participante incluindo zero. Nenhuma condição com oclusão de 10% passou os critérios completos. O teste anterior e os limites nominais de área continuam inalterados.

Foi reproduzida exatamente a fusão das doze combinações de estratégia e condição. O controle circular coincidiu com o de ontem, os centros foram preservados, e a diferença relativa máxima de área equivalente ficou abaixo de 4 × 10⁻¹⁶. A suíte completa foi agora executada e passou em **94 testes**, incluindo os testes geométricos novos.

Com a decisão do usuário de retirar as exceções do Defender, a execução passou a usar uma pasta temporária e a preservação no projeto pelo mecanismo de edição disponível, sem solicitar exceções ou alterar a segurança. Um pacote textual recuperável preserva os bytes originais do modelo, componentes, escores, protocolos e fontes; imagens de entrada e pesos antigos não foram duplicados. A sincronização na nuvem não foi verificada. O [relatório da forma elíptica](../pfc1-segmentacao-mmu/FORMA_PUPILA_2026-10-23.md) contém as tabelas completas e o manifesto de recuperação.

A restauração do pacote foi executada a partir das 36 partes locais: 55 arquivos recuperados, todos com hashes SHA-256 conferidos. Também foram comparadas à origem as 22 cópias textuais legíveis. O pacote preserva os bytes originais, enquanto as cópias legíveis normalizam quebras de linha. Isso permite continuar sem exceções amplas para os interpretadores.

## Continuação: compatibilidade do descritor com a nova geometria

Foi avaliada uma regressão residual para aproximar os descritores polares da nova geometria dos descritores originais da mesma foto. O encoder permaneceu congelado. Das 259 imagens de treino com alternativa geométrica concêntrica, 255 tiveram recortes alterados: 200 das pessoas de ajuste e 55 das pessoas do monitor. O transporte foi ajustado somente nas 200 primeiras, com regularização fixa e sem busca de parâmetros.

A similaridade média com o descritor original melhorou de 0,684239 para 0,850565 no ajuste, mas piorou de 0,740051 para 0,661303 no monitor, indicando sobreajuste deste piloto. No monitor completo, com 480 consultas e uma falha mantida, o transporte teve Rank-1 de 479/480 e TAR de 477/480, contra 479/480 em ambas as medidas na geometria original. A barreira previamente definida falhou: não houve avaliação desta adaptação na validação principal nem no teste.

Os resultados internos próximos de 99% são de um componente polar, em pessoas já vistas pelo encoder original; não são um novo resultado de generalização e não substituem os 91,36% anteriores. O reconhecedor de referência e as fronteiras nominais de área permanecem inalterados.

Foram reproduzidos regressão, limiares, escores e decisões com diferença máxima zero. Uma evidência compacta preserva os descritores de todas as fotos alteradas e de todas as do monitor, em 1.160 registros distintos. A suíte completa passou em **97 testes**. O [relatório do transporte de descritores](../pfc1-segmentacao-mmu/TRANSPORTE_DESCRITOR_2026-10-23.md) documenta o protocolo, a rejeição e a reprodução. A execução e a preservação continuaram sem alterações no Defender.

O pacote deste piloto foi restaurado a partir de 31 partes: 17 arquivos com hashes conferidos. A evidência compacta restaurada permitiu refazer a regressão e reproduzir todos os escores e a rejeição, sem o cache completo de embeddings. As sete cópias textuais também foram conferidas. O upload no OneDrive não foi verificado.

### Fronteira de área e fechamento — 23/10/2026

Uma análise com 5.000 reamostragens pareadas por participante reaproveitou as seis condições existentes, sem novo treino, inferência ou calibração. Com perda nominal de 10%, a diferença de Rank-1 entre superior e inferior foi 24,07 pontos percentuais (IC95% pareado 10,83–36,25), evidenciando a influência da região no processamento completo. A condição inferior com perda de 1% passou os critérios em 50,46% das reamostras; essa frequência descreve estabilidade amostral, não probabilidade populacional de sucesso. Os mínimos pontuais da grade continuam em 100% superior e 99% inferior, sem interpretação de mínimo clínico universal.

A análise foi reproduzida por uma segunda implementação usando 96 linhas de contagens por participante/condição, com diferença máxima de intervalo de 2,23 × 10⁻¹⁶ p.p.; cinco testes direcionados passaram. Não houve nova execução da suíte completa nesta etapa. Foram descritas somente as perdas em pixels de duas condições candidatas, 0,5% superior e 1,5% inferior; elas ainda não foram avaliadas no reconhecedor. O plano limita o refinamento a uma rodada com esses dois pontos e reserva o restante do prazo para fechar o artigo até 09/11. Ver [incerteza, resultados e plano de fechamento](../pfc1-segmentacao-mmu/INCERTEZA_AREA_2026-10-23.md).

### Rodada fracionária concluída — fronteira atual de 23/10/2026

Foram executados exatamente os dois novos pontos previstos, com modelo e limiar congelados e todas as 486 consultas mantidas. A perda superior de 0,5% passou: 443 acertos (Rank-1 91,1523%), TAR de 92,3868% e FMR de 0,8916%. A perda inferior de 1,5% reprovou: 433 acertos (89,0947%), TAR de 88,8889% e FMR de 1,0151%. Portanto, o menor aproveitamento nominal aprovado na grade irregular estudada é agora **99,5% na superior e 99% na inferior**. Isso refina o limite observado, sem alterar o reconhecedor ou estabelecer mínimo anatômico/clínico.

Não foi avaliada perda inferior de 0,5%; assim, 99,5% não foi aprovado em ambas as orientações. Entre os níveis coincidentes, o prefixo comum continua em 100%. Na condição superior de 0,5%, uma referência definida arredondou para zero pixels selecionados; as seis referências vazias continuaram inalteradas. Os IC95% descritivos de Rank-1 foram 85,00–95,63% e 81,07–94,72% nas duas novas condições, respectivamente.

A auditoria reproduziu a fusão com diferença zero e conferiu intervenções, entradas inalteradas e hashes do pipeline original. Cinco testes direcionados passaram. O pacote de recuperação foi restaurado em 37 arquivos com hashes conferidos; os escores foram reproduzidos a partir dos componentes restaurados. A rodada experimental limitada foi encerrada, priorizando agora método, tabelas e discussão do artigo. Ver [fronteira consolidada e limites](../pfc1-segmentacao-mmu/FRONTEIRA_REFINADA_2026-10-23.md).

### Consolidação do artigo no modelo institucional

Foi preparada uma versão completa para revisão do orientador, com **18 páginas, cinco tabelas, duas figuras e nove referências**, utilizando o modelo de artigo disponível na pasta do PFC I. O manuscrito ativo foi reorganizado em introdução, materiais e métodos, resultados e discussão e considerações finais, substituindo o acúmulo cronológico de experimentos. A versão anterior foi arquivada. Foram incluídos Engenharia de Computação e os e-mails dos autores informados pelo aluno; não foi atribuída titulação não confirmada ao orientador.

As tabelas reúnem as oito condições avaliadas e mantêm os mínimos observados de 99,5% superior e 99% inferior, com as ressalvas sobre grade irregular, incerteza e ausência de comprovação de um mínimo comum abaixo de 100%. O fluxograma distingue a referência usada na intervenção da segmentação automática; a segunda figura apresenta os intervalos de 95% das métricas. Nenhum novo experimento biométrico foi executado para essa consolidação.

Todas as 18 páginas da última versão foram renderizadas e inspecionadas. A gravação direta do Word na pasta protegida permaneceu indisponível; o arquivo foi disponibilizado em pasta temporária, e uma cópia restaurável foi preservada no projeto sem alterar o Defender. Os nove arquivos restaurados tiveram seus hashes conferidos. O upload no OneDrive não foi verificado. A revisão pelo orientador e a aprovação da versão final permanecem pendentes. Ver [conferência, localização e recuperação do artigo](../pfc1-segmentacao-mmu/artigo/REVISAO_ARTIGO_2026-10-23.md).

### Retomada das melhorias de reconhecimento

Após a solicitação do aluno de continuar melhorando o reconhecedor, foram implementados e executados dois pilotos somente na validação: segmentação com média de probabilidades de três vistas da mesma fotografia e consenso fixo 50/50 dessa extração com a referência. As vistas não correspondem a capturas adicionais. Os pesos de identidade foram mantidos; cada novo candidato recebeu calibração apenas na condição limpa, aplicada sem alteração às oclusões superior e inferior de 10%. Todas as 482 consultas permaneceram na avaliação.

A segmentação multivista apresentou Rank-1/TAR limpos de 89,83%/89,42%. O consenso atingiu 437/482 identificações corretas (90,66%), contra 434/482 (90,04%) da referência de validação, mas seu TAR foi 432/482 (89,63%), abaixo da meta de 90%. Nas perdas superior e inferior de 10%, o Rank-1 do consenso foi 79,46% e 60,58%, com FMR de 1,3140% e 2,3513%. Assim, **nenhum dos candidatos cumpriu os critérios de melhoria**. O aumento isolado de Rank-1 limpo não foi apresentado como meta global alcançada.

Quatro testes direcionados passaram. A auditoria reproduziu exatamente fusões, consenso, decisões, limiares e reprovação dos critérios; o cadastro foi conferido entre condições. Os componentes, escores e registros foram preservados em 43 partes, restaurando 55 arquivos com hashes conferidos. Não houve nova inferência no teste ou substituição da referência. Os 91,36% do teste e os mínimos nominais anteriores permanecem associados ao reconhecedor original. Ver [tabelas, limitações e próximos ajustes](../pfc1-segmentacao-mmu/RETOMADA_ROBUSTEZ_2026-10-23.md).

### Treinamento do contorno externo e avaliação do reconhecimento

Foi implementado um corretor da elipse externa em coordenadas da fotografia inteira, utilizando características da U-Net congelada. Das 7.716 fotos de treino, 6.623 de 167 pessoas foram elegíveis para ajuste e 951 de 16 pessoas distintas para monitoramento; 142 foram excluídas somente do treino geométrico por falta de contorno utilizável. As consultas biométricas não foram filtradas. O monitor é reutilizado e já foi visto pela U-Net, portanto não constitui confirmação independente.

A primeira formulação, supervisionada pela elipse da anotação, falhou no limite de preservação geométrica limpa e não foi avaliada biometricamente. A segunda utilizou a elipse limpa predita como professora somente durante o treino, reaproveitando as características já preparadas. Foi selecionada a época 12, com redução do erro geométrico superior/inferior de 13,59%/22,93% e aumento limpo de 2,87%, dentro do limite registrado de 5%. Essas porcentagens descrevem erro geométrico auxiliar, não acerto de identificação.

Nas 482 consultas de validação, o Rank-1 com perda inferior de 10% aumentou de **59,96% para 63,49%**, com 17 identificações corretas adicionais; o TAR passou de 57,88% para 61,62%, e a FMR caiu de 2,4066% para 2,0747%. Porém, o Rank-1 limpo caiu de 90,04% para 89,21%, e o superior, de 80,71% para 78,84%. **O candidato não foi aprovado nem substituiu o reconhecedor original.** Os controles conservaram máscaras, recortes RGB/nativos, elipse interna e pesos de identidade; as falhas e todas as consultas permaneceram nas métricas.

Nove testes direcionados passaram. A auditoria reproduziu a seleção geométrica, os escores e as decisões; os dados do cadastro foram conferidos entre condições. Dois checkpoints e seus registros foram preservados em 88 partes, restaurando 60 arquivos com hashes conferidos. A partir da recuperação, foram reproduzidos os controles geométricos e as fusões, sem recalcular os caches de características ou imagens. Não houve inferência no teste, novo mínimo de área ou reexportação do Word. Ver [detalhamento e recuperação dos artefatos](../pfc1-segmentacao-mmu/CONTORNO_EXTERNO_2026-10-23.md).

### Adaptação do descritor polar à geometria corrigida

Foi treinado um adaptador residual com os encoders congelados, utilizando 6.665 fotos de 167 pessoas para ajuste e um monitor de 480 consultas de 16 pessoas distintas. O monitor é reutilizado e já foi visto pelos encoders, portanto seus resultados não constituem avaliação independente. O cadastro permaneceu limpo; uma montagem inicial incorreta do cadastro foi invalidada, corrigida e coberta por teste de regressão antes de qualquer inferência na validação.

Na última época treinada, o descritor polar isolado passou de **310/480 (64,58%) para 367/480 (76,46%)** em Rank-1 na perda superior de 10%, e de **217/480 (45,21%) para 307/480 (63,96%)** na inferior. Os TAR foram 69,38% e 47,29%, respectivamente. O Rank-1/TAR limpos dessa época foram 476/480 e 477/480, abaixo dos 479/480 de ambos os indicadores do descritor original. Assim, **nenhuma época foi elegível e o adaptador foi rejeitado**, sem inferência de identidade na validação ou no teste. Esses números são de um único componente no monitor de treino, não da fusão principal.

Passaram 13 testes direcionados. A auditoria reproduziu os escores e a decisão; as cinco épocas foram repetidas com diferença zero nas perdas. Foram preservados os pesos selecionados da época zero e os da última época rejeitada, com identificação explícita. O pacote de 40 arquivos em 24 partes foi restaurado, com hashes, escores e decisões conferidos. Os caches foram registrados por hash e não recalculados na recuperação compacta. A referência do teste continua em **91,36% sem oclusão**, e não há novo mínimo de área aceito nesta rodada. Ver [relatório técnico completo](../pfc1-segmentacao-mmu/ADAPTACAO_POLAR_2026-10-23.md).


### Combinação do descritor original com a geometria corrigida

Foi concluído um piloto com contribuição fixa de 75% do descritor polar original e 25% do corrigido, registrada antes da execução, sem varredura de pesos e sem usar o adaptador rejeitado. A avaliação ficou restrita às 480 consultas de 16 pessoas do monitor de treino reutilizado; esses resultados não constituem confirmação independente. Cada consulta usa uma foto e lado informado, com cadastro limpo fixo.

A combinação preservou **479/480 (99,79%)** tanto em Rank-1 como em TAR limpos desse componente. Na perda superior de 10%, o Rank-1 caiu de 396/480 (82,50%) para 394/480 (82,08%) e o TAR de 77,50% para 77,29%. Na inferior, o Rank-1 subiu de 291/480 (60,63%) para 296/480 (61,67%), mas o TAR caiu de 55,83% para 54,58%. A FMR da combinação foi 1,5000% e 1,3750%, respectivamente, acima do limite de 1%. **O critério de avanço foi reprovado**, sem inferência na validação ou no teste e sem novo mínimo de área.

Passaram seis testes direcionados. A auditoria reproduziu exatamente a combinação dos descritores, os escores e as decisões. Foram preservados 21 arquivos em oito partes, com recuperação e hashes conferidos; o cache de características foi excluído do pacote e registrado por hash. A referência principal segue em 91,36% no teste sem oclusão. Ver [relatório técnico](../pfc1-segmentacao-mmu/COMPLEMENTO_GEOMETRICO_2026-10-23.md).


### Viabilidade do segmentador compartilhado pelo orientador

Foram examinados código, dependências e configuração do `segmentadorduffatto-main`. A separação de mudas por âncoras, excesso de verde, competição geodésica e medição de caules não corresponde diretamente à segmentação de íris. Não foram encontrados pesos treinados para íris. A aplicação não foi instalada nem integrada.

A ideia genérica de orientar o SAM por pontos e caixas foi testada isoladamente no nosso projeto, com o SAM2.1 Tiny já disponível e prompts gerados automaticamente pela U-Net, sem referência manual na inferência. O protocolo foi registrado antes do teste em 32 fotos do treino original (16 pessoas, ambos os olhos) e três condições, totalizando 96 casos pareados. Não houve inferência biométrica ou uso de validação/teste; o monitor é reutilizado e não independente.

O Dice limpo caiu de **95,15% para 91,45%**. Com perda superior/inferior de 10%, o Dice da referência completa passou de 89,74%/84,73% para 88,39%/87,38%; considerando apenas a área visível, passou de 91,70%/89,07% para 92,65%/90,75%. Apesar do ganho localizado inferior, **o critério foi reprovado**. Esses números medem segmentação, não identificação nem um mínimo de área reconhecível.

Passaram dois testes direcionados, e a auditoria reproduziu prompts e todos os 192 registros de métricas. Onze arquivos em quatro partes foram preservados e restaurados com hashes conferidos. A aplicação botânica fica fora do caminho principal; a prioridade retorna à tolerância do descritor à oclusão mantendo a normalização original. A referência principal segue em 91,36% no teste limpo, sem novo mínimo de área. Ver [estudo técnico](../pfc1-segmentacao-mmu/ESTUDO_SEGMENTADOR_ORIENTADOR_2026-10-23.md).


### Adaptação à oclusão mantendo a normalização original

Foi concluído um novo treinamento, sem corretor geométrico nem SAM: a U-Net e o encoder polar permaneceram congelados, e um adaptador residual foi ajustado por 12 épocas. As 7.716 fotos de treino foram preparadas nas condições limpa e oclusão nativa superior/inferior de 10%. O ajuste utilizou 6.665 fotos válidas de 167 pessoas; 91 foram excluídas somente do ajuste. O monitor preservou todas as 480 consultas de 16 pessoas, com cadastro limpo, lado informado e falhas contabilizadas. Esse monitor é reutilizado e já foi visto pelos encoders; não é uma confirmação independente.

A época 12 preservou **479/480 (99,79%)** em Rank-1 e TAR limpos do componente polar. Na perda superior de 10%, o Rank-1 passou de **396/480 (82,50%) para 405/480 (84,38%)**, e o TAR de 77,50% para 79,17%. Na inferior, o Rank-1 passou de **291/480 (60,63%) para 328/480 (68,33%)**, e o TAR de 55,83% para 60,00%. Foram nove e 37 identificações corretas adicionais, respectivamente. Entretanto, as FMR de **1,5139% e 1,4861%** permaneceram acima do limite de 1%; **o candidato foi barrado antes da validação**.

Passaram cinco testes direcionados. A extração limpa reproduziu os descritores do professor com diferença máxima zero; a auditoria reproduziu o adaptador, os escores e a seleção. Os pesos e registros foram preservados em 24 partes, restaurando 28 arquivos com hashes conferidos. O cache foi registrado por hash e não recalculado na recuperação compacta. Não houve inferência na validação ou no teste, substituição da fusão principal ou novo mínimo de área: os 91,36% do teste original permanecem. A próxima hipótese é investigar uma perda que também separe identidades para reduzir as aceitações impostoras; isso ainda não foi executado. Ver [relatório técnico](../pfc1-segmentacao-mmu/ADAPTACAO_POLAR_ORIGINAL_2026-10-23.md).


### Treinamento com separação supervisionada de identidades

Foi concluída uma nova rodada de 12 épocas, com normalização original e encoders congelados, reutilizando as características da rodada anterior. O adaptador iniciou do zero e recebeu uma perda adicional de identidade contra 334 protótipos congelados, construídos com 4.955 fotos limpas de cadastro das pessoas do ajuste. A nova perda foi aplicada somente às 1.729 consultas S2 elegíveis do ajuste, com negativos do mesmo lado. Não houve uso de pessoas do monitor nos protótipos ou gradientes.

O monitor interno reutilizado manteve **479/480 (99,79%)** em Rank-1 e TAR limpos. Na oclusão superior de 10%, o Rank-1 foi **407/480 (84,79%)**, contra 405/480 da adaptação anterior; na inferior, **329/480 (68,54%)**, contra 328/480. Os TAR foram 79,17%/60,42%. Porém, as FMR passaram de 1,5139%/1,4861% para **1,6111%/1,5000%**. Assim, a perda de identidade **não resolveu as aceitações impostoras**, e o candidato foi barrado antes da validação. Os números são de um componente no monitor do treino, não de uma confirmação independente ou do teste principal.

Uma incompatibilidade de rótulos int32/int64 interrompeu a primeira execução antes de qualquer atualização de pesos; ela foi corrigida com conversão explícita, teste de regressão e reinício registrado em pasta v2. Passaram oito testes direcionados. A auditoria reproduziu os protótipos, a seleção da época 12 e os escores; 35 arquivos em 31 partes foram preservados e restaurados com hashes conferidos. Não houve nova inferência de imagens, validação ou teste, nem novo mínimo de área. A referência de 91,36% no teste limpo permanece. Ver [detalhamento técnico](../pfc1-segmentacao-mmu/ADAPTACAO_IDENTIDADE_POLAR_2026-10-23.md).


### Treinamento com cadastro múltiplo e negativos difíceis

Foi concluído um piloto de 12 épocas que aproxima a perda do comparador real: usa a média das três melhores similaridades com fotos S1 por olho e uma margem contra o impostor mais semelhante do mesmo lado. O cadastro de ajuste contém 4.955 fotos de 334 olhos das 167 pessoas de ajuste; a perda de comparação atua somente nas 1.729 consultas S2 elegíveis. Os descritores de cadastro são atualizados no início de cada época e mantidos sem gradiente durante ela, como aproximação computacional registrada. As características de imagens foram reaproveitadas, sem nova inferência das redes.

A época 11 foi selecionada no monitor interno de 480 consultas, que é reutilizado e não constitui confirmação independente. Preservou **479/480 (99,79%)** em Rank-1 e TAR limpos. Na perda superior/inferior de 10%, os Rank-1 foram **404/480 (84,17%) e 328/480 (68,33%)**, com TAR de 78,54%/59,79%. Frente à perda com protótipos médios, as FMR caíram de 1,6111%/1,5000% para **1,4861%/1,2917%**: 107 e 93 aceitações impostoras em 7.200 comparações por condição. Isso representa 35 e 21 aceitações acima do máximo de 72 correspondente a 1%. Houve perda de três identificações superiores e uma inferior frente à rodada anterior; não há ganho uniforme.

O candidato foi barrado antes da validação por exceder a FMR permitida, mantendo os limiares calibrados somente na condição limpa. Passaram 11 testes direcionados, incluindo equivalência da agregação com o comparador real, padding, cossenos negativos e negativos do mesmo lado. A auditoria reproduziu escores e seleção; 33 arquivos em 25 partes foram preservados e restaurados com hashes conferidos. Não houve inferência na validação ou no teste, substituição da fusão principal ou novo mínimo de área. A referência principal segue em 91,36% no teste limpo. Ver [detalhamento e direção seguinte](../pfc1-segmentacao-mmu/ADAPTACAO_TOP3_POLAR_2026-10-23.md).


### Penalização direta de escores impostores

Foi concluído um novo piloto com referência fixa calculada antes do ajuste, somente nas 167 pessoas de treino: 287.512 comparações impostoras limpas utilizáveis definiram a referência 0,27272370457649237. Esse valor é parâmetro da perda, não o limiar de avaliação. A referência não utilizou fotos ou rótulos do monitor, validação ou teste. A perda acrescentou penalização para os dois olhos impostores de maior escore por consulta, com proteção para o escore genuíno. As características existentes foram reutilizadas, sem nova inferência das redes de imagens.

A execução parou na época 8, após quatro épocas sem melhora da seleção; a época 4 foi selecionada. No monitor reutilizado de 480 consultas, preservou **479/480 (99,79%)** em Rank-1 e TAR limpos. Com perda superior/inferior de 10%, o Rank-1 foi **401/480 (83,54%) e 320/480 (66,67%)**, com TAR de 78,33%/59,17%. As FMR passaram de 1,4861%/1,2917% no piloto top3 para **1,4167%/1,2778%**. A redução de cinco e uma aceitações impostoras veio com perda de três e oito identificações corretas, respectivamente. O critério continua reprovado, e a validação foi encerrada sem inferência.

O diagnóstico dos escores existentes encontrou falsas aceitações em 93 consultas superiores e 83 inferiores; 73 e 65 consultas respondem por 80% dessas aceitações. Os erros não estão concentrados em poucos casos extremos. Isso não justifica excluir consultas e não demonstra uma causa clínica. Passaram 14 testes direcionados; a auditoria reproduziu a referência de ajuste, a seleção e os escores. Foram preservados 38 arquivos em 54 partes, restaurados com hashes e decisões conferidos. Não houve avaliação na validação/teste, troca da fusão principal ou novo mínimo de área; a referência principal permanece em 91,36% no teste limpo. Ver [detalhamento e limites](../pfc1-segmentacao-mmu/ADAPTACAO_FMR_POLAR_2026-10-23.md).


### Correções treináveis no último bloco do encoder polar

Foi executado um piloto de oito épocas com correções espaciais de rank 8 nas quatro convoluções de layer4, totalizando 145.408 parâmetros treináveis. Os kernels originais, prefixo até layer3, projeção e todos os parâmetros e estatísticas de BatchNorm permaneceram congelados, com hashes conferidos antes e depois. Esse piloto não equivale à liberação completa dos pesos do último bloco.

O cache FP32 reuniu 12.160 mapas de características: 7.716 fotos limpas e duas oclusões de 10% das 2.222 consultas S2. O cadastro S1 ficou sempre limpo. A preparação levou cerca de 169 segundos e reproduziu os descritores limpos anteriores com diferença máxima zero. O cache de 1,59 GB permite novos estudos sem repetir a parte congelada da rede. Foram mantidas as 6.665 fotos de ajuste e as 480 consultas do monitor, com falhas contabilizadas; esse monitor é reutilizado e já foi visto pelos encoders, portanto não é uma confirmação independente.

A época 6 foi selecionada. Preservou **479/480 (99,79%)** em Rank-1 e TAR limpos do componente polar. Com perda superior/inferior de 10%, o Rank-1 foi **399/480 (83,13%) e 327/480 (68,13%)**, com TAR de **80,63%/60,21%**, contra 77,50%/55,83% do encoder sem adaptação. A FMR ficou em **1,5833%/1,3056%**, com 114 e 94 aceitações impostoras em 7.200 comparações por condição. O candidato não passou ao limite de 1% e foi barrado antes da validação. Há ganho de TAR, mas não superioridade conjunta sobre os pilotos anteriores.

Passaram 12 testes direcionados. A auditoria reproduziu os escores, cossenos e seleção, conferiu a origem dos cadastros e a reconstrução das correções sobre o checkpoint original. Foram preservados 33 arquivos em 32 partes, restaurados com hashes, decisões e escopo dos parâmetros conferidos. O cache foi excluído do pacote e registrado por hash. Não houve inferência na validação ou no teste, troca da fusão principal ou novo mínimo de área: os 91,36% do teste principal permanecem. Ver [método e limites](../pfc1-segmentacao-mmu/ENCODER_ESPACIAL_2026-10-23.md).

### Ajuste completo dos kernels convolucionais do último bloco polar

Foi testado o ajuste dos cinco kernels originais de layer4, incluindo downsample, com 8.388.608 pesos treináveis. Prefixo, projeção e parâmetros/estatísticas BatchNorm permaneceram congelados. O piloto parte do encoder original e não utiliza pesos rejeitados. O protocolo foi registrado antes do treino: semente 63, AdamW 1e-5, lote de 16 fotos, oito épocas, alinhamento ao descritor limpo e perda top3 contra impostores do mesmo lado. Foram reutilizados os mapas anteriores, com 6.665 fotos de ajuste de 167 pessoas e cadastro S1 sempre limpo.

A época 8 foi selecionada. No monitor reutilizado de treino, preservou **479/480 (99,79%)** acertos e aceitações limpos. Com oclusão superior/inferior de 10%, o Rank-1 subiu de **82,50%/60,63%** para **407/480 (84,79%) e 342/480 (71,25%)**; são 11 e 51 acertos adicionais. O TAR passou de 77,50%/55,83% para **81,67%/61,88%**. A FMR ficou em **1,6389%/1,3472%**, com 118 e 97 falsas aceitações em 7.200 comparações, acima das 72 permitidas. O candidato foi barrado antes da validação. Faltam 25 e 90 acertos para Rank-1 de 90% nesse monitor; os ganhos não demonstram generalização independente.

O teste direcionado passou. A auditoria refez descritores selecionados/finais no cache e reproduziu exatamente escores, cossenos, seleção e bloqueio. O treino conferiu a invariância dos pesos/buffers congelados. Foram preservados 28 arquivos em um ZIP de 31.591.947 bytes, distribuído em 43 partes. Um delta binário reversível evita duplicar os tensores dos checkpoints selecionado/final; a recuperação confere os bytes e SHA-256 exatos de ambos. As duas partes que divergiram na cópia inicial foram corrigidas, e restauração/auditoria compacta passaram. Não houve quantização, nova exceção de segurança ou confirmação de upload ao OneDrive.

O PyTorch/GPU funcionaram nesta rodada; a gravação direta via Python na pasta OneDrive ainda falhou, e os resultados foram preservados pelo mecanismo de edição a partir de TEMP. O reconhecedor principal, seus 91,36% no teste e a fronteira de área não foram alterados. Não houve treino ou inferência na validação/teste. Ver [protocolo, resultados e recuperação](../pfc1-segmentacao-mmu/AJUSTE_BLOCO_POLAR_2026-10-23.md).

### Retomada do PyTorch e ponderação aprendida de regiões

Após o usuário permitir os arquivos bloqueados, sem adicionar exceções, o PyTorch carregou e uma operação FP32 na RTX 3050 passou. Foram concluídos treinamento e auditoria na mesma sessão, sem alterar configurações de segurança. O novo piloto mantém encoder, projeção e BatchNorm congelados e aprende somente 16.449 parâmetros para ponderar as 32 posições do mapa final. A inicialização uniforme reproduz o reconhecedor global; metade do peso permanece uniforme, evitando descarte completo de regiões. A atenção usa apenas características da imagem observada, sem anotação ou identidade como entrada.

O protocolo foi registrado antes do treino. O cache anterior foi reutilizado, com 6.665 fotos de ajuste de 167 pessoas e cadastro S1 sempre limpo. O monitor reutilizado tem 480 consultas de 16 pessoas e não é confirmação independente. O treino concluiu oito épocas e selecionou a oitava. Preservou 479/480 (99,79%) acertos e aceitações limpas. Sob perda superior/inferior de 10%, o Rank-1 foi 402/480 (83,75%) e 295/480 (61,46%), contra 82,50%/60,63% do polar original. O TAR subiu para 79,58%/59,17%, mas a FMR piorou para 1,7083%/1,8056%, com 123/130 falsas aceitações em 7.200 comparações, acima das 72 permitidas. O candidato foi barrado antes da validação.

Dois testes passaram, incluindo equivalência inicial, piso/soma dos pesos, congelamento e restauração. A auditoria refez os descritores no cache e reproduziu exatamente escores, seleção e bloqueio. Foram preservados 28 arquivos em 12 partes, sem duplicação dos mapas originais. A ponderação evitou a perda limpa do comparador regional anterior, mas não resolveu a robustez ou a FMR; não houve troca do reconhecedor, inferência na validação/teste ou novo mínimo de área. Os 91,36% do teste principal permanecem. Ver [detalhes e recuperação](../pfc1-segmentacao-mmu/ATENCAO_POLAR_2026-10-23.md).

### Piloto de comparação regional sem novo treino CNN

Foi registrado e executado um piloto com os mapas espaciais polares já calculados. A padronização foi estimada exclusivamente em 4.955 fotos S1 das 167 pessoas de ajuste. Cada imagem passou a ter 32 descritores locais; o primário compara regiões correspondentes e retém as 24 maiores concordâncias por par, enquanto o controle usa todas. Não há uso da anotação ou identidade correta para escolher regiões. Os campos receptivos são sobrepostos, portanto o descarte de descritores não equivale a um percentual de pixels da íris.

Nas 480 consultas do monitor reutilizado de treino, o primário obteve Rank-1 de 371/480 (77,29%) limpo, 261/480 (54,38%) na perda superior de 10% e 231/480 (48,13%) na inferior. Os TAR foram 43,54%, 13,75% e 7,50%. O controle local sem descarte teve Rank-1 de 76,04%, 52,29% e 46,46%. Ambos ficaram abaixo do polar global, que tinha 99,79%, 82,50% e 60,63%. A condição limpa falhou; não houve avanço à validação ou teste. A FMR ocluída baixa acompanha rejeição excessiva de genuínos e não caracteriza melhoria.

Três testes passaram. A auditoria refez padronização, protótipos e os seis conjuntos de escores a partir do cache, reproduzindo métricas, limiares e bloqueio. Um erro apenas na impressão final do script ocorreu após a gravação dos resultados e foi corrigido sem repetir os cálculos, preservando o código registrado. O pacote de 19 arquivos em 26 partes conserva os artefatos, sem duplicar o cache de 1,59 GB. Esta formulação foi encerrada; qualquer próximo comparador parcial precisa primeiro preservar discriminação limpa nas pessoas de treino. O teste principal e o mínimo de área permanecem inalterados. Ver [método, auditoria e recuperação](../pfc1-segmentacao-mmu/COMPARACAO_REGIONAL_2026-10-23.md).

### Diagnóstico posterior dos escores do nosso pipeline

Na retomada do desenvolvimento próprio, foram examinados os escores já salvos de quatro componentes polares nas 480 consultas do monitor de treino. Mesmo escolhendo um limiar privilegiado para cada condição, apenas para diagnóstico, o componente espacial alcançaria TAR máximo de 375/480 (78,13%) na perda superior de 10% e 279/480 (58,13%) na inferior, respeitando FMR de até 1%. Faltariam 57 e 153 aceitações para as 432 necessárias à meta de 90%. O Rank-1 não muda com um limiar comum; portanto, somente recalibração escalar não resolve os escores atuais.

Top3 e espacial erram conjuntamente 70 consultas superiores e 133 inferiores. Um seletor privilegiado entre suas decisões alcançaria 85,42%/72,29%; essa análise não limita uma eventual fusão de escores nem avalia tal fusão. Foram reproduzidas as métricas originais, conferidos alinhamento e hashes de 12 arquivos, e passaram dois testes direcionados. Não houve treinamento, novas imagens, validação/teste, promoção de candidato ou alteração do limiar do sistema. A próxima hipótese deve melhorar a comparação da textura disponível com suporte espacial explícito, antes de novos ajustes globais. Ver [diagnóstico e limites](../pfc1-segmentacao-mmu/DIAGNOSTICO_COMPARACAO_2026-10-23.md).

### Avaliação externa do Iris-SAM

A pedido do aluno, foi estudado o repositório público Iris-SAM e seu artigo. O checkpoint de 2,56 GB foi baixado, conferido por SHA-256 e executado em GPU com FP16, usando um adaptador próprio. A cópia externa permaneceu sem modificações. Os exemplos publicados requerem adaptações: há caixas manuais ou extraídas da referência nos testes, arquivos de imagem de exemplo inválidos e pressupostos de rótulos binários incompatíveis com o UBIPr. O modelo é utilizável para pesquisa após adaptação, mas não constitui um pipeline automático pronto.

Foi registrado antes da inferência um piloto de segmentação em 32 pessoas da validação, uma foto por pessoa, com imagem limpa e duas perdas simuladas de 10%: 96 casos pareados, quatro métodos e 384 registros. Nenhuma pessoa pertence ao treino ou teste do manifesto. A validação já foi usada no desenvolvimento e o piloto não é confirmação cega. O modo primário usa somente a caixa prevista pela U-Net, sem receber localização da anotação.

| Método | Dice limpo | Dice visível: perda superior 10% | Dice visível: perda inferior 10% |
|---|---:|---:|---:|
| U-Net atual | 84,40% | 81,29% | 78,67% |
| Iris-SAM com caixa automática da U-Net | 78,80% | 80,29% | 77,49% |
| Iris-SAM sem prompt, diagnóstico | 0,19% | 0,13% | 0,04% |
| Iris-SAM com caixa da anotação, diagnóstico privilegiado | 85,10% | 85,46% | 81,69% |

O candidato automático perdeu 5,61 pontos de Dice limpo, IC95% pareado de −6,69 a −4,60 pp. Nas oclusões, os intervalos da diferença incluíram zero; a amostra não permite afirmar diferença populacional nessas condições. O critério de preservar o limpo e melhorar pelo menos um ponto em cada oclusão falhou. As métricas desta amostra não devem ser confundidas com o Dice do teste completo anterior. A caixa da anotação não está disponível na captura real e não autoriza promover o modo oracle.

A inferência levou cerca de 80 segundos, sem carga dos pesos, incluindo os quatro métodos. O pico CUDA alocado foi de 2,79 GiB. O controle FP32 em duas fotos teve diferença máxima de 0,00537 ponto de Dice frente ao FP16, abaixo do critério material registrado. Três testes do adaptador passaram. Uma auditoria reproduziu exatamente as métricas das máscaras, as caixas e o bootstrap; o pacote de 22 arquivos em 83 partes foi restaurado e auditado novamente. Foi gerada uma imagem com as duas primeiras pessoas sorteadas, nas três condições, com contornos previstos e de referência.

**Decisão:** manter a U-Net atual. O artigo pode sustentar a discussão e hipóteses de ajuste do decoder/Focal Loss, mas o checkpoint disponível não trouxe melhoria no protocolo automático avaliado. Não houve treino, identificação biométrica ou inferência no teste final neste piloto; os 91,36% do reconhecedor e a estimativa de fronteira de área permanecem. Fontes, limites e instruções para recuperar a figura estão no [estudo completo](../pfc1-segmentacao-mmu/IRIS_SAM_ESTUDO_2026-10-23.md).

