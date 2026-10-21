# Treinamento em textura polar e controle clássico de fase

## Hipótese e critério

O encoder anterior conserva a melhor TAR entre os métodos testados até esta etapa, mas permanece abaixo do critério registrado de pelo menos 90% de Rank-1 e TAR no original, com limiar calibrado na validação para FMR empírica de até 1%. Esta rodada muda a representação e treina um novo encoder no domínio local, em vez de prolongar os ajustes anteriores ou aplicar diretamente outro checkpoint público. O modelo atual não é substituído automaticamente.

São usadas 183 pessoas de treino, com 7.716 imagens antes das falhas geométricas, e as 16 pessoas de validação elegíveis entre sessões, com 962 imagens e 482 consultas de 32 olhos. A validação já foi usada no desenvolvimento anterior; não é confirmação independente. Não se extrai novo reconhecimento de teste ou de base clínica.

## Representação e treinamento

A U-Net retreinada fica congelada. A previsão em RGB 320 × 240 é redimensionada ao original por vizinho mais próximo. Um recorte com margem de 50% é convertido a cinza, recebe CLAHE com clip 2 e grade 8 × 8 e é normalizado para 64 × 512 por aproximação elíptica da máscara prevista. A pupila é estimada pelo maior orifício interno; na ausência de orifício válido, usa-se aproximação concêntrica no centro da caixa da máscara, com raio de um oitavo da menor dimensão dessa caixa. Essa regra não recupera anatomia oculta nem é referência clínica.

Pixels fora da máscara amostrada recebem cinza 127. Os três canais de entrada repetem a textura em cinza. O encoder é ResNet18 inicializado em ImageNet, com projeção para 256 dimensões e cabeça angular treinável. A entrada mantém a proporção 64 × 512; não é comprimida para 128 × 128.

O treino usa deslocamento horizontal circular de até 32 colunas, brilho/contraste de até 15%, normalização ImageNet, AdamW com taxa 0,0003 e decaimento 0,0001, batch 64, clipping 5, margem angular 0,3 e escala 30. São até 30 épocas com cosseno e paciência oito, semente 45. Máscaras vazias ou geometria inutilizável são excluídas só do treino; as consultas de validação permanecem como falhas. A seleção maximiza TAR, com desempate por Rank-1, em cadastro top-3 com todas as imagens da sessão 1. Cada época recalibra o limiar no mesmo alvo de FMR.

## Controle clássico de fase

Para verificar se o gargalo está na representação aprendida, foi registrado um controle Log-Gabor sem treinamento sobre as mesmas faixas de validação. É uma implementação local, não uma reprodução oficial do OSIRIS. Usa filtro angular unilateral com comprimento de onda 18 pixels, sigma 0,5 e dois bits de fase, Hamming mascarado e busca de ±16 colunas. A formulação do filtro foi consultada na [documentação técnica de Peter Kovesi](https://www.peterkovesi.com/matlabfns/PhaseCongruency/Docs/convexpl.html).

A máscara é reconstruída conservadoramente dos pixels diferentes do sentinela 127; pixels genuínos que também valem 127 são descartados. Isso é uma limitação adicional do controle, explicitamente registrada. Há erosão radial/angular de 3 × 5 e rejeição de amplitude abaixo de 0,000001. A distância é normalizada pelo suporte de bits, com sobreposição mínima de 10% da tela de código. Esse percentual é um filtro de qualidade da comparação, não um mínimo anatômico de área de íris. Avaliam-se foto única, máximo e média top-3, preservando as 482 consultas.

## Pesquisa complementar e risco de sobreposição

Foi localizado o [VIS-IrisFormer](https://github.com/naveengv7/Vis-IrisFormer), cujo README descreve treinamento em UBIRIS.v2. A [página oficial UBIPr](https://iris.di.ubi.pt/ubipr.html) informa que UBIPr deriva de UBIRIS.v2. Portanto, há risco concreto de sobreposição de identidades ou imagens: um checkpoint desses não pode ser apresentado como confirmação independente no nosso UBIPr sem auditoria. Não foi usado para inflar os resultados. O repositório permanece como referência de arquitetura e domínio, não como ganho confirmado.

## Reprodução e situação

- Treino: `executar.ps1 treinar_encoder_polar.py`; piloto separado com `--smoke`.
- Controle de fase: `executar.ps1 validar_loggabor_polar.py`, somente após o término da preparação de `val_valid.npy`.
- Resultados: `outputs/encoder_polar_2026-10-20` e `outputs/loggabor_polar_val_2026-10-20`.
- `CONCLUIDO.json` é o marcador de término; histórico ou protocolo isolados não indicam conclusão.

Os protocolos computacionais são registrados antes da extração/treino e incluem hashes. Qualquer ganho continua exploratório até uma avaliação independente com configuração e limiar congelados. A nova curva de área só deve ser interpretada como mínimo aprovado se o critério original for atingido e confirmado; não se presume que o treinamento garanta alcançar esse alvo.

## Controles complementares registrados

Após o encerramento da seleção do encoder polar, dois controles de correspondência espacial reutilizam seus pesos congelados até a camada 3: resposta ao fundo uniforme 127 subtraída, canais normalizados por local e protótipo espacial médio por olho. Compara-se similaridade média sem deslocamento e com deslocamento angular de até duas colunas de característica. Não há deslocamento radial nem novo treino. O protocolo fica em `outputs/espacial_polar_val_2026-10-20`.

Também foi definida uma única fusão de pesos iguais entre o encoder RGB anterior e o novo polar: cada escore é padronizado pela média e desvio dos impostores válidos da própria validação; faz-se média com pesos fixos 0,5 e 0,5 e transformação logística. Não há busca de pesos nem utilização do teste. Exigem-se ambas as extrações e comparações válidas, preservando falhas no denominador. Os parâmetros de normalização e o limiar são ajustados nessa validação, por isso o resultado é de desenvolvimento. O protocolo separado é registrado antes de calcular a fusão, em `outputs/fusao_polar_rgb_val_2026-10-20`.

Esses controles investigam complementaridade e alinhamento; não alteram o critério de aceitação e não constituem confirmação independente. O aluno confirmou explicitamente: **UBIPr como base principal e uma única foto de consulta**. O cadastro pode conter várias fotos do mesmo olho, conforme o protocolo existente; não há fusão entre fotos de consulta.

## Próximo controle: preservar resolução interna

O controle `treinar_encoder_polar.py --dense` substitui apenas o MaxPool2d inicial por identidade, preservando quatro vezes mais posições espaciais nas camadas seguintes. Reinicia do mesmo ImageNet ResNet18, com o mesmo seed 45, dados, pré-processamento e margem angular. O lote passa de 64 para 32 para caber na GPU; isso também altera a dinâmica de otimização, portanto o ensaio não isola exclusivamente a arquitetura. Limite de 30 épocas, paciência 8 e seleção por TAR na validação, desempate por Rank-1. Reutiliza o cache polar após conferir hashes das entradas e dos módulos de pré-processamento. A consulta permanece individual e as falhas ficam no denominador. Resultados em pasta própria, sem sobrescrever pesos anteriores; nenhum teste ou curva de oclusão será executado automaticamente.

Após o controle de duas vias, foi registrado outro candidato com três componentes de pesos fixos de um terço: RGB, polar e descritor espacial sem deslocamento angular. O protocolo foi escrito antes do cálculo dessa fusão e registra hashes dos três arquivos de escores. As mesmas regras de padronização por impostores, falhas e calibração são mantidas. O candidato é de desenvolvimento após observar outros resultados; não constitui comparação independente nem busca exaustiva de pesos.
