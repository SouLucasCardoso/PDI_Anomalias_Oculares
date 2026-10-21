# Adaptação do encoder às máscaras automáticas

## Motivação e separação dos dados

O encoder existente foi treinado com recortes das máscaras de referência. A avaliação anterior mostrou que a distribuição das máscaras automáticas e a forma de cadastro afetam o reconhecimento. Esta rodada adapta o treinamento ao mesmo fluxo de segmentação utilizado na inferência: U-Net congelada e encoder em 128 pixels, com cadastro top-3.

Somente as 183 pessoas de treino participam da atualização dos pesos de identidade. As 16 pessoas elegíveis da validação orientam parada e checkpoint; não são um teste independente. O teste UBIPr anterior e os dados clínicos não recebem nova inferência nesta rodada. A U-Net mantém seus pesos anteriores, sem ajuste nas consultas.

## Configuração registrada

- Inicialização: melhor checkpoint anterior do encoder e sua cabeça angular, com a ordem original das 366 classes de olho.
- Máscara: previsão U-Net em RGB 320 × 240, valores entre 0 e 1, inferência FP32 em lotes de 32; classe da íris redimensionada ao original por vizinho mais próximo. Nenhuma máscara de referência corrige o recorte.
- Entrada: exterior preto, caixa com margem de 25%, interpolação bilinear para 128 × 128, normalização ImageNet.
- Treino: rotação aleatória de até 10 graus e brilho/contraste de até 15%; sem oclusão artificial nesta rodada, para primeiro avaliar o desempenho original.
- AdamW: encoder 0,00003; cabeça angular 0,0001; decaimento 0,0001; margem 0,3 radianos e escala 30; clipping 5; batch 64; semente 43.
- Até 20 épocas, com cosseno de taxa de aprendizado e paciência de seis épocas sem melhora. Workers zero e AMP BF16 no encoder; cabeça e perda em FP32.
- Validação: todas as capturas de cadastro da sessão 1, média das três melhores similaridades válidas por olho, consultas da sessão 2. Limiar recalibrado a cada checkpoint para FMR empírica de até 1% na validação.
- Seleção: maior TAR, desempate por Rank-1. O checkpoint inicial é avaliado como época zero e também pode vencer. Isso evita obrigar a adoção de um ajuste pior pelo critério principal, mas não garante que toda métrica isolada melhore.
- Máscaras vazias são excluídas apenas do treino; todas as consultas e identidades da validação permanecem no denominador, com falhas contadas como rejeições.

O protocolo computacional com hashes é escrito antes da preparação dos recortes em `outputs/identidade_automatica_2026-10-20/protocolo.json`. Os arquivos antigos não são sobrescritos. Um piloto separado `--smoke` verifica extração, atualização dos pesos, validação e gravação; suas estimativas não entram no artigo.

## Critérios de interpretação

O resultado será comparado à época zero da mesma execução, com os mesmos recortes, consultas e cadastro. A inferência segmentada em lote pode produzir pequenas diferenças numéricas em relação à extração anterior de uma imagem por vez; qualquer diferença de linha de base deve ser registrada, sem confundi-la com ganho de treinamento.

Mesmo que haja ganho, ele é de desenvolvimento em validação já utilizada repetidamente. A escolha do melhor checkpoint maximiza a estimativa nesse conjunto; intervalos condicionais não corrigem esse viés. Não será anunciada confirmação independente nem percentual mínimo a partir dessa escolha. Antes de estimar um mínimo, o reconhecimento original precisa atingir o critério estabelecido e ser confirmado em avaliação independente, com limiar congelado.

Execução: `executar.ps1 treinar_identidade_automatica.py`. A existência de `CONCLUIDO.json` indica término; arquivos `historico.csv` parciais não indicam conclusão. Pesos, escores da época zero e da melhor época, auditoria e histórico são preservados.

## Resultado da adaptação simples e rodada seguinte

A adaptação simples terminou após seis épocas sem superar a época zero: 66,80% de Rank-1, 59,34% de TAR e 0,99% de FMR. Foram excluídas 71 previsões vazias somente no treino, mantendo 7.645 imagens; na validação, as quatro consultas com falha permaneceram. Os pesos anteriores foram mantidos pelo critério de seleção.

Foi então registrado um experimento separado em `outputs/identidade_metrica_automatica_2026-10-20/protocolo.json`, antes de executar o novo treinamento. Ele reutiliza os mesmos recortes e o checkpoint original, acrescentando perda triplet batch-hard de distância cosseno (margem 0,2 e peso 0,5) à classificação angular. Lotes são compostos por 16 identidades oculares distintas e quatro capturas por identidade, em cinco rodadas embaralhadas por época. Há reposição só quando faltam quatro capturas válidas de uma classe. A taxa do encoder é 0,00001 e da cabeça 0,00005, com até 20 épocas, paciência seis, semente 44 e os mesmos critérios de seleção e validação. Não se trata de nova evidência independente. A conclusão dessa rodada exige seu próprio `CONCLUIDO.json`.
