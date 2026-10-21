# Comparação de reconhecedor específico e normalização polar

## Objetivo e fontes

Após duas adaptações do encoder não melhorarem a TAR, foi avaliado o TripletIris disponibilizado pelo [CVRL/University of Notre Dame](https://github.com/CVRL/OpenSourceIrisRecognition). Este é um modelo público específico de reconhecimento de íris; não deve ser confundido com a rodada local que apenas acrescentou perda triplet ao ResNet18.

As fontes foram fixadas na revisão `4a535e4a9a0728e4428c25f743f6d59098ae397f` e verificadas por tamanho, hash Git de cada blob e SHA-256. Foram baixados os dois pesos da pasta pública indicada no README dos autores: ConvNeXt-tiny com saída de 2.048 dimensões e regressor de círculos `resnet18-1543-0.047488-maskIoU-0.934494.pth`. Os hashes locais foram registrados. Este regressor corresponde ao nome previsto na configuração TripletIris, ao contrário do substituto 027 usado anteriormente no HDBIF; não foram alterados os resultados históricos.

Reprodução dos downloads: `executar.ps1 preparar_reconhecedores_polares.py TripletIris --download-weights`. Fontes e pesos ficam em `data/modelos/cvrl_tripletiris`, fora do Git.

## Validação original

Somente a validação UBIPr foi usada: 16 pessoas, 32 olhos, 480 imagens da sessão 1 no cadastro e 482 consultas da sessão 2. Nenhum peso foi treinado nesta rodada. Não foi estabelecida independência entre as populações de pré-treinamento dos autores e esses dados, e esse conjunto já foi examinado no desenvolvimento anterior.

Três entradas foram registradas antes da extração: imagem inteira com conversão de proporção do código dos autores; localização pela máscara de referência; localização pela máscara automática U-Net. Os recortes usam caixa com margem de 50% e conversão proporcional para 640 × 480. O canal vermelho segue o demonstrador oficial. As máscaras localizam o recorte, mas não removem pixels da faixa polar; portanto, reflexos, pálpebras e contexto incluído pelos limites podem participar do embedding.

A extração segue o código oficial: normalização polar de 64 × 512, z-normalização individual, clipping de -4 a 4, três canais repetidos e ConvNeXt-tiny. Usa-se a distância euclidiana entre vetores sem normalização L2 adicional. A transformação monotônica `1/(1+distância)` permite usar a infraestrutura de similaridades; no piloto, foi conferida contra os 16 pares do comparador original, com erro máximo inferior a 0,000000000001.

Foram avaliados foto única, maior similaridade e média das três melhores similaridades por olho. Essas regras de cadastro são extensões locais, não uma reprodução de uma taxa publicada pelos autores. O limiar é calibrado separadamente em cada configuração para FMR empírica de até 1% na própria validação. Todas as identidades e consultas permanecem no denominador. Máscaras de localização vazias, círculos inválidos ou textura constante/não finita são falhas explícitas.

## Nova hipótese geométrica

A inspeção do piloto mostrou limites circulares que incluem regiões externas à íris visível. Foi registrada outra rodada, em pasta separada, antes de executar sua extração completa. A aproximação elíptica ajusta o maior contorno externo da máscara e estima a pupila pelo maior orifício interno geometricamente válido. Quando esse orifício não está disponível, mantém a pupila do regressor público como fallback. Os controles de validade dos círculos anteriores continuam aplicados.

As duas bordas geram pontos por ângulo global, interpolados radialmente para uma faixa de 64 × 512, com amostragem bilinear OpenCV. A textura não é multiplicada pela máscara. O encaixe acompanha a região segmentada visível: não recupera a borda anatômica escondida pela pálpebra nem constitui referência clínica. O amostrador também difere do código circular oficial, de modo que não se isola um único efeito geométrico.

São comparadas referência assistida e máscara automática, nas mesmas três regras de cadastro. Os testes cobrem ângulos globais, anel sintético, recuperação do orifício pupilar, fallback e rejeição de máscara vazia. O piloto é apenas verificação técnica; suas quatro consultas não são estimativas finais.

## Artefatos e limites

- `outputs/tripletiris_validacao_2026-10-20`: nove controles de desenvolvimento.
- `outputs/tripletiris_elipse_validacao_2026-10-20`: seis controles geométricos de desenvolvimento.
- Pastas com `piloto`: compatibilidade e inspeção, separadas dos resultados científicos.
- `CONCLUIDO.json`: marcador de conclusão de cada execução; protocolos parciais não indicam término.

As taxas destas rodadas não confirmam generalização independente. Comparar os reconhecedores envolve pesos, dados prévios de treino, canal de imagem, normalização e representação diferentes. O mínimo de área não pode ser anunciado por localizar ou normalizar melhor o olho: o desempenho original e o critério registrados ainda precisam ser satisfeitos e confirmados. Não há novo ensaio de oclusão nesta etapa.
