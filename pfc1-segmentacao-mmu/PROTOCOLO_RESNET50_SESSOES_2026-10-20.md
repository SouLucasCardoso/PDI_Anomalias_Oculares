# Reconhecedor maior e variabilidade entre capturas

**Condição adicional autorizada pelo aluno:** a captura pode exigir informar se o olho é esquerdo ou direito. Avaliar separadamente a galeria de 16 olhos do mesmo lado para cada consulta, preservando as 482 consultas e o olho genuíno original. O ensaio anterior de 32 candidatos continua registrado. Recalibrar FMR usando apenas as 15 comparações impostoras admissíveis por consulta; não contar candidatos removidos como rejeições para reduzir artificialmente a taxa. O lado deve ser fornecido corretamente, não se presume que o modelo o detecte. Aplicar inicialmente à fusão ResNet50 e depois à fusão ConvNeXt já previstas, com e sem a normalização por consulta definida. Resultados continuam de desenvolvimento e o mínimo de área exige avaliação posterior.

Além de restringir os escores da fusão já calculada, um controle registrado antes do cálculo recalibra a média/desvio dos componentes usando somente os impostores do mesmo lado, antes da fusão de pesos iguais. Executar quatro componentes sem ConvNeXt e cinco com ConvNeXt quando seu treino terminar; versões com e sem a normalização por consulta já definida. Não há busca de pesos ou parâmetros. A FMR continua usando apenas as 15 comparações impostoras admissíveis por consulta.

O aluno confirmou UBIPr como base principal, uma única foto por consulta e alvo de pelo menos 90% em Rank-1 e TAR. Mantém-se o limiar calibrado para FMR empírica de até 1%. Não se troca a base, agrega fotos de consulta ou remove imagens difíceis para alcançar esse número. Todas as saídas são de desenvolvimento na validação repetidamente examinada; alcançar 90% nela não seria confirmação independente nem, sozinho, mínimo de área aprovado.

## ResNet50 com GeM e sessões balanceadas

Novo treinamento a partir dos pesos oficiais Torchvision ResNet50 ImageNet1K_V2, SHA-256 `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`. Fonte: [documentação oficial](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet50.html). O uso de entradas 128x128 e novo treinamento constitui adaptação própria; as métricas ImageNet da documentação não representam desempenho biométrico.

Backbone ResNet50, pooling GeM com expoente fixo 3, projeção 2048→256, BatchNorm e normalização L2. Reutiliza os recortes automáticos RGB128 com hashes conferidos; máscaras manuais não corrigem as entradas. Lotes de 16 olhos e quatro capturas por olho; quando disponíveis, duas de cada sessão. Quatro rodadas por época. Perda angular mais 0,2 de contraste supervisionado com temperatura 0,1. Margem angular sobe de 0 a 0,3 nas primeiras sete épocas; escala 30. AdamW, backbone 1e-4, projeção e cabeça 5e-4, regularização 1e-4, cosine40, gradiente limitado a 5, seed46. Até 40 épocas, paciência10 após época10. Seleção por TAR, desempate por Rank-1, na mesma validação já usada em desenvolvimento.

Todos os olhos e consultas elegíveis da validação são mantidos. Somente extrações vazias de treino são excluídas do aprendizado. Cadastro top-3 de todas as fotos elegíveis da sessão 1, consultas individuais da sessão 2. Novo diretório, sem sobrescrever modelos anteriores.

## Controle de normalização por consulta

Antes dos resultados, foi definido um único controle sobre a fusão anterior de três componentes: inverter a transformação logística, padronizar os escores pela média e desvio entre os olhos cadastrados para aquela consulta e reaplicar logística. Não usa a identidade da consulta nessa transformação e não combina consultas diferentes. A ordenação das identidades deve ser preservada. Não há busca de temperatura ou de pesos. O limiar usa os rótulos de validação apenas para calibração habitual de FMR. O controle pode alterar TAR, mas não melhorar Rank-1 quando a extração continua válida.

## Fusões posteriores fixadas

Após o término do ResNet50, definir apenas a fusão de quatro componentes com pesos iguais: RGB anterior, polar anterior, espacial anterior e novo ResNet50. Mesma padronização por impostores e logística das fusões anteriores. Também aplicar a essa fusão a única normalização por consulta descrita acima. Sem buscar pesos ou excluir consultas. São candidatos de desenvolvimento, não resultados confirmatórios.

## Multivista da mesma foto, pesos anteriores congelados

Outro controle registrado antes de calcular seus resultados: extrair três vistas do mesmo recorte RGB (rotações −10°, 0°, +10°) e cinco da mesma faixa polar (deslocamentos circulares −32, −16, 0, +16, +32 colunas). Fazer média dos vetores normalizados e renormalizar por foto original. Aplicar tanto ao cadastro quanto à consulta, com pesos anteriores congelados. Não reúne fotografias diferentes de consulta nem seleciona a melhor vista pelo rótulo. Avaliar os dois encoders isolados, uma fusão de pesos iguais com o espacial anterior e a normalização por consulta já definida. Não há busca dos ângulos ou deslocamentos na validação.

## Correspondência local por captura de cadastro

Controle registrado antes da inferência: usar a camada2 do encoder polar anterior, com 128x8x64 posições/canais, subtrair resposta ao cinza127 e normalizar canais por posição. Comparar cada consulta individual com todas as capturas válidas do cadastro, buscar deslocamento angular fixo de −2 a +2 colunas e agregar média top-3 por olho. Não há busca radial ou seleção de consultas. Avaliar o controle isolado e sua fusão fixa de pesos iguais com os encoders RGB e polar anteriores, com e sem a normalização por consulta já definida. O ensaio muda simultaneamente camada e agregação de cadastro; não é ablação isolada de um desses componentes.

## Normalização por olho cadastrado

Antes do cálculo, definiu-se um controle de viés por identidade cadastrada: nos encoders RGB e polar anteriores congelados, cada olho recebe média e desvio de escores top-3 de todas as imagens válidas de outros olhos do próprio cadastro. Comparações genuínas não entram nesse ajuste, nem as consultas. Usa-se desvio mínimo numérico 1e-6; se não houver coorte suficiente, o ensaio acusa erro, sem excluir o olho. Avaliar os encoders com e sem essa normalização para controle pareado, a fusão RGB/polar normalizados + espacial anterior com pesos iguais e sua versão com a normalização por consulta já definida. Sem buscar regularização ou pesos. A adaptação usa o cadastro conhecido; a calibração de limiar e padronização da fusão continuam na validação, sem confirmação independente.

## Classificador aprendido no cadastro

Controle registrado antes de seus resultados: concatenar vetores congelados RGB anterior, polar anterior e ResNet50 novo, normalizar L2 e ajustar classificador ridge com alpha fixo1 somente nas capturas válidas da sessão1. Centrar entradas e alvos one-hot, resolver na forma dual. Todas as consultas da sessão2 ficam fora do ajuste. Comparar com protótipos médios normalizados das mesmas representações; avaliar ridge com e sem a normalização por consulta já definida. Não há busca de alpha na validação. Este é um classificador adaptado aos olhos cadastrados, distinto de um extrator global congelado com simples comparação de templates. Continua exigindo apenas uma foto por consulta e mantendo todas as falhas na avaliação.

Após a autorização de lado informado, registrar dois classificadores separados por lado usando os mesmos vetores, treinados só no cadastro: ridge linear alpha1 e ridge de kernel RBF alpha0,01, gamma definido como inverso da mediana das distâncias quadráticas de impostores do cadastro. Não ajustar gamma ou alpha nas consultas. Avaliar com e sem a normalização por consulta já definida, usando15 impostores admissíveis por consulta. Nenhuma consulta é usada para ajustar os classificadores.

## Novo treinamento ConvNeXt com contraste local

Após a rodada ResNet50, foi definido outro treinamento a partir de pesos oficiais ImageNet, usando ConvNeXt-tiny, média global e LayerNorm originais, projeção 768→256 com BatchNorm e L2. Reutilizar recortes automáticos RGB128, aplicar CLAHE ao canal L em LAB (clip2, grade8x8) e restaurar o exterior exatamente preto dos recortes originais. Não é super-resolução nem geração de textura, e o suporte inferido do preto não é uma nova máscara anatômica de referência. A transformação é aplicada tanto no treino como na inferência. O modelo e o pré-processamento mudam juntos, portanto não é ablação isolada. Mesmo esquema de sessões, perdas e otimizador do ResNet50, seed47, até40 épocas e paciência10. Pesos SHA-256 `983f1562536e84ff750a1576fb08e54de751dbf2e17c0d8a4a13704341fdcd3d`, [fonte oficial](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.convnext_tiny.html).

Depois do treino, uma única fusão adicional de cinco componentes com pesos iguais: RGB, polar, espacial, ResNet50 e ConvNeXt. Avaliar com e sem a normalização por consulta previamente definida. Sem buscar pesos ou configurações de contraste na validação; manter todos os resultados negativos.

## Controle de representação antes da projeção

Registrar antes dos resultados um controle dos vetores completos dos backbones treinados: ResNet50 com 2048 componentes e ConvNeXt com 768, antes da projeção256. Estimar o centro apenas nos vetores válidos das fotos de cadastro da sessão1, subtrair de todas as fotos e normalizar L2. Não usar consultas para estimar o centro. Manter top-3 por olho. Avaliar no cenário autorizado de lado informado, isoladamente e por fusão igualitária com RGB/polar/espacial anteriores: quatro componentes com ResNet50 amplo e cinco com ResNet50 amplo + ConvNeXt amplo, sempre com e sem a normalização por consulta já definida. Não buscar dimensões ou pesos. O centro e o tipo de vetor mudam juntos; não se atribui qualquer ganho exclusivamente à dimensão.

## Treinamento com recortes nativos em 224 — continuação em 21/10

Novo ResNet50 ImageNet, mesmo esquema de treino/sessões/perdas/seed46, entrada224 diretamente recortada dos arquivos originais com U-Net congelada. Não ampliar o cache128 como substituto dos originais. Máscara prevista em320x240, redimensionada à foto original, bbox com margem25%, exterior preto e redução/interpolação direta para224. Conferir que a validade de todas as imagens coincide com o controle128, sem excluir novas consultas. Até40 épocas e paciência10, lote64. A seleção agora acompanha a condição operacional autorizada: TAR entre os16 olhos do mesmo lado e15 impostores por consulta, desempate por Rank-1; métricas da galeria32 preservadas como controle. Mudam entrada e condição de seleção, portanto não é ablação isolada da resolução. Não há super-resolução ou geração de textura.

Após o término, uma fusão adicional fixa de seis componentes — RGB anterior, polar, espacial, ResNet50-128, ConvNeXt-128 e ResNet50-224 — com pesos iguais, padronização somente por impostores do mesmo lado e a normalização por consulta já definida. Avaliar com e sem essa normalização, sem buscar pesos ou remover consultas.

## Tokens locais intermediários DINOv3

Controle distinto do CLS global anteriormente avaliado: usar somente as primeiras6 de24 camadas do ViT-L DINOv3 já instalado, sem o LayerNorm final treinado para a saída da última camada; remover CLS e quatro tokens de registro. Não se trata da saída final oficial. Entrada polar64x512 e128 patches, sem forçar quadrado224; subtrair a resposta ao cinza127, normalizar canais por patch e comparar posições alinhadas com deslocamentos angulares −2..2, top-3 das capturas de cadastro. Fonte da família e conceito de características densas: [repositório oficial](https://github.com/facebookresearch/dinov3). A escolha da camada6 e do pré-processamento é hipótese própria registrada antes dos resultados, sem busca de camadas na validação. População de pré-treinamento web não auditada individualmente; não se presume independência de identidades.

Avaliar o controle isolado com lado informado e uma fusão fixa substituindo o espacial CNN por esse descritor local, mantendo RGB/polar/ResNet50/ConvNeXt e pesos iguais; versão com e sem a normalização por consulta já definida. Não agregar consultas, não filtrar imagens, calibrar somente nos15 impostores admissíveis por consulta. Memória reduzida removendo as18 camadas não utilizadas antes de mover o modelo para a GPU.

## Adaptação supervisionada do reconhecedor ao cadastro

Registrar antes dos resultados uma adaptação de12 épocas fixas do ResNet50-128 global ao cadastro operacional: usar apenas478 fotos válidas da sessão1, três vistas fotométricas/geometria fixas (−8°/gamma0,75;0°/1;+8°/1,33), nenhuma consulta da sessão2. Congelar as três primeiras etapas residuais e todas as estatísticas BatchNorm; ajustar apenas layer4 (lr1e-5), projeção (1e-4) e nova cabeça angular32 olhos (1e-3). AdamW1e-4, margem0,15, escala20, perda angular+0,2 de contraste supervisionado+0,1 de retenção cosseno ao professor original, seed48. Cache das características congeladas com CUDA/BF16 e ajuste em CPU/FP32 para não disputar a memória do treino224. Não avaliar consultas entre épocas nem selecionar checkpoint por elas; usar somente a época12.

Avaliar top-3 de templates e cosseno à cabeça aprendida, sempre sem inserir o rótulo genuíno na inferência. Uma fusão fixa de cinco componentes substitui o ResNet50 global pelo adaptado, mantendo RGB/polar/espacial/ConvNeXt, com e sem normalização por consulta. Lado informado,16 candidatos,15 impostores, todas as482 consultas. O reconhecedor passa a depender do cadastro: para nova galeria, reiniciar do checkpoint global e repetir a adaptação fixa usando só aquela galeria. Não reutilizar o modelo adaptado às identidades de validação como se fosse modelo global confirmado em outras pessoas. O resultado permanece de desenvolvimento.

## Média aritmética de probabilidades

Alternativa de combinação registrada antes dos resultados: para cada modelo, padronizar escores pelos impostores do mesmo lado e aplicar softmax de temperatura fixa1 entre os16 olhos candidatos daquela única consulta. Fazer média aritmética dessas probabilidades com pesos iguais. Isso difere de fazer média dos escores padronizados; componentes pouco discriminativos tendem a distribuir o voto. Não treinar pesos ou temperatura nas consultas. Avaliar cinco componentes atuais e seis incluindo o nativo224 quando concluído, com e sem a normalização por consulta já definida. Manter as482 consultas,15 impostores admissíveis e FMR calibrada até1% para cada configuração.

## Transformer polar treinado por identidade

Depois dos controles congelados, registrar novo treino das primeiras6 camadas ViT-L DINOv3 já instalado, com parâmetros FP32 e forward BF16, nas pessoas de treino UBIPr apenas. Não usar o CLS como vetor da íris: retirar CLS+4 registros, normalizar/projetar cada um dos128 patches1024→64 e preservar posições ao achatar8192→256, Dropout0,2, BatchNorm e L2. A normalização final original DINOv3 é substituída por identidade; a nova normalização de tokens é treinável. Trata-se de arquitetura própria, não da saída final oficial. Pré-treinamento web sem auditoria individual de identidades, explicitamente limitado.

Mesmo cache polar automático64x512, roll angular±32 e brilho/contraste15% apenas no treino. Lotes16 olhos×4 capturas,4rodadas por época, sessões balanceadas. AdamW backbone2e-5, novos tokens/projeção2e-4, cabeça5e-4, wd1e-4, cosine30, clip5, seed49; margem angular cresce de0 a0,3 em sete épocas, escala30, CE+0,2 de contraste supervisionado. Até30 épocas, paciência8, seleção por TAR entre16 candidatos do lado informado, FMR até1% entre15impostores, desempateRank-1. Guardar escores32 como controle. Nenhuma inferência de teste ou oclusão.

Após o treino, comparar isoladamente e uma única fusão adicional de sete componentes com pesos iguais, acrescentando esse Transformer à fusão de seis atual; versões com e sem a normalização por consulta já definida. Sem buscar pesos, camadas ou temperatura na validação.

## Seleção de referências por qualidade

Controle registrado antes dos resultados: selecionar três fotos válidas do cadastro de cada olho por indicador próprio de nitidez, calculado somente nas imagens S1. Usar variância do Laplaciano da imagem cinza dividida pela variância de intensidade+1, excluindo exterior preto, pixels saturados≥245 e escuros<5, com erosão3x3 da região útil; multiplicar por largura nativa/(largura nativa+128), estimada pela máscara automática já auditada. Não é medida ISO nem área anatômica. Escolher as três maiores notas por olho, desempate pelo nome; não remover olhos ou consultas. Nenhuma consulta participa da seleção ou ajuste do indicador.

Comparar com controle de todas as fotos de cadastro, usando exatamente a mesma extração congelada de quatro CNNs (RGB/polar/ResNet50/ConvNeXt), mantendo espacial anterior e pesos de um quinto. Versões com e sem a normalização por consulta já definida,16 candidatos do lado informado,15 impostores, todas482 consultas. O controle com a mesma extração evita atribuir pequenas diferenças de execução/batch à seleção de referências.

## Grupos de escala no cadastro

Após o controle de qualidade, registrar outra agregação sem nova extração: ordenar as referências válidas de cada olho pela largura nativa prevista da íris e dividir em três grupos de tamanhos próximos, preservando todas as referências válidas. A largura é apenas proxy de escala, não distância física controlada. Usar, por CNN, o maior dos três escores médios por grupo, mantendo espacial anterior e a fusão de cinco componentes de pesos iguais. Versões com e sem normalização por consulta; mesmo lado informado,15impostores,482consultas. Nenhuma consulta determina os grupos ou exclui referências. Não buscar número de grupos ou pesos.

## Alinhamento angular do Transformer congelado

Após o treino, registrar um controle angular específico para a projeção espacial do Transformer: cadastro na orientação original, mesma foto de consulta em deslocamentos circulares fixos −32,−16,0,+16,+32 colunas (faixa já usada no treino e no controle multivista anterior). Para cada candidato, agregar top-3 das referências em cada vista e usar o maior escore entre as cinco vistas. Nenhum rótulo de consulta seleciona a vista. Comparar com orientação0 usando exatamente a mesma extração; avaliar ambos isolados e por fusão com os seis componentes anteriores, pesos de um sétimo, com e sem a normalização por consulta já definida. Lado informado,15impostores,482consultas, limiar recalibrado para FMR até1% considerando também os impostores com a busca angular. Não são cinco fotos distintas nem busca de parâmetros na validação.

## Alinhamento fotométrico em uma consulta

Controle registrado antes dos resultados: nos quatro encoders RGB congelados (RGB anterior, ResNet50-128, ConvNeXt e ResNet50-224), manter o cadastro sem variação gamma e gerar da mesma consulta três vistas gamma0,75/1/1,33 após o pré-processamento fixo, antes da normalização ImageNet. Esses valores já foram usados na adaptação do cadastro. Agregar top-3 por olho para cada vista e usar o maior escore entre as três, sem consultar o rótulo genuíno. O controle gamma1 usa exatamente a mesma extração e lote16, para separar pequenas diferenças de execução do alinhamento. Manter polar, espacial e Transformer originais, fusão de sete componentes com pesos iguais, com e sem normalização por consulta. Nenhuma busca de gamma, pesos ou exclusão de consultas. Recalibrar FMR considerando que todos os15impostores admissíveis recebem a mesma maximização. Não são várias fotos de consulta, nem restauração generativa.
