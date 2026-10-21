# Desenvolvimento: cadastro multicaptura e recorte automático

## Hipótese e escopo

A primeira fotografia em ordem de nome pode ser um cadastro fraco. Esta rodada verifica o efeito de múltiplas capturas e o efeito da máscara automática antes de iniciar outro treinamento. Somente a validação UBIPr é usada; não são produzidos novos escores de teste ou oclusão. Os pesos do encoder de identidade e da U-Net permanecem congelados.

O registro computacional anterior à extração está em `outputs/cadastro_multicaptura_val_v2_2026-10-20/protocolo.json`, com hashes dos pesos, código e dependências. A rodada tem 482 consultas de 16 pessoas e 32 olhos, com 480 imagens de cadastro da sessão 1 e consultas da sessão 2. Todas as identidades e consultas permanecem no protocolo.

## Comparações predefinidas

O encoder em 128 pixels é avaliado com duas máscaras: referência da base e previsão automática da U-Net. O recorte mantém margem de 25%, exterior preto e normalização ImageNet, como no treinamento. A previsão automática é produzida em 320 × 240 e redimensionada para a imagem original por vizinho mais próximo; não é corrigida com a referência.

Para cada tipo de máscara, são avaliados:

1. Primeira captura da sessão 1 em ordem lexicográfica por olho, mesmo que seja falha.
2. Maior similaridade entre as capturas de cadastro disponíveis.
3. Média das três maiores similaridades válidas, ou das disponíveis se houver menos de três.
4. Similaridade com o centróide normalizado dos vetores válidos do olho.

O HDBIF usa o recorte de referência com margem de 50%, normalização polar e filtros da rodada anterior. Compara primeira captura, maior similaridade e média das três melhores. Não há centróide HDBIF, pois seus códigos e máscaras binários não são os vetores neurais. A combinação gera onze variantes de desenvolvimento, sem equivalência a onze testes independentes.

## Calibração, falhas e controles

Cada variante recebe seu próprio limiar para FMR empírica de até 1% na validação. Reutilizar o limiar de uma foto para muitas fotos poderia favorecer artificialmente o acerto sem controlar falsas correspondências. As taxas de FMR efetivas, TAR, Rank-1 e falhas são registradas para todas as variantes.

Uma máscara vazia, cadastro indisponível ou comparação sem sobreposição não é removida silenciosamente. A sentinela de falha é -2; similaridades cosseno negativas continuam sendo comparações válidas. Falhas de consulta rejeitam, e um olho sem cadastro válido permanece com escore -2. Capturas válidas de um mesmo olho podem compor o cadastro múltiplo, sem usar as consultas para escolhê-las.

O comparador HDBIF em lote foi testado contra o cálculo escalar FFT, com máscaras e rotações, e contra ausência de sobreposição. Há testes para manter cossenos negativos válidos e impedir que a agregação aceite cadastros completamente inválidos. A tentativa inicial de execução foi interrompida durante a preparação para corrigir o tratamento desses cossenos; a versão válida é `v2`, em pasta separada.

## Limites de interpretação e sequência

Essas pessoas de validação já foram usadas no desenvolvimento e na seleção do checkpoint. Os resultados podem orientar a implementação, mas não confirmam generalização independente. Selecionar a melhor entre onze variantes também pode otimizar a estimativa de validação; não transformar essa escolha em resultado final de teste.

O recorte de referência funciona como controle assistido. O controle automático mede a operação com a U-Net, mas o encoder foi treinado originalmente com referências, portanto existe mudança de distribuição. Um resultado baixo no automático pode indicar necessidade de treinamento com máscaras previstas ou de correção geométrica, e não apenas falta de épocas.

Depois desta rodada, a decisão deve considerar o ganho de cadastro, a perda causada pela máscara automática e a qualidade visual da normalização. Um mínimo só poderá ser calculado após o desempenho original cumprir o critério e ser confirmado por avaliação independente.

Execução: `executar.ps1 validar_cadastro_multicaptura.py`. A conclusão é indicada exclusivamente por `CONCLUIDO.json`; a existência de resultados parciais não significa experimento finalizado.
