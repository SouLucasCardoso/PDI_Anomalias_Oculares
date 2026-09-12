# Relatório de avanço — treinamento e comparação no UBIPr

| Identificação | Informação |
|---|---|
| Projeto | Influência da segmentação da íris no desempenho de redes neurais convolucionais para a classificação de alterações oculares |
| Disciplina | Projeto Final de Curso I — PFC I |
| Curso | Engenharia de Computação |
| Instituição | UniSatc |
| Acadêmico | Lucas Cardoso Rodrigues |
| Orientador | Rodrigo Ramos Silva |
| Data | 11 de setembro de 2026 |
| Etapa | Validação externa da segmentação com o UBIPr e comparação U-Net × SAM 2.1 |

## 1. Síntese do avanço

Nesta etapa, a avaliação foi ampliada do conjunto MMU para o **UBIPr Single
Eyes Segmented Version**, uma base substancialmente maior e com anotações
semânticas. A cópia oficial foi obtida, auditada e organizada sem alterar os
arquivos originais. Foram encontrados 11.018 pares válidos de imagem e máscara,
pertencentes a 261 pessoas.

Foi implementada uma nova pipeline para treinar uma Small U-Net com quatro
classes: fundo/pupila, íris, esclera e sobrancelha. O modelo foi treinado por 30
épocas com separação por pessoa. Em seguida, o SAM 2.1 Hiera Tiny foi avaliado
em regime zero-shot na mesma partição de teste. Uma rotina independente reuniu
as previsões dos dois métodos e recalculou métricas por imagem sob exatamente o
mesmo protocolo.

O principal resultado foi um Dice médio de **0,9171** para a U-Net treinada no
UBIPr e **0,7026** para o SAM 2.1 zero-shot nas 1.642 imagens de teste com íris
anotada. Também foi produzida uma prancha visual com casos difíceis, medianos,
bons e de maior divergência entre os modelos.

## 2. Obtenção e auditoria do UBIPr

O arquivo oficial `ubipr1.tar` foi obtido do portal do SOCIA Lab/Universidade da
Beira Interior. A auditoria registrou:

| Característica | Resultado |
|---|---:|
| Pares de imagem e máscara | 11.018 |
| Pessoas | 261 |
| Sessões | 2 |
| Lados | Esquerdo e direito |
| Pixels de íris | 103.218.384 |
| SHA-256 do arquivo | `b71a593dc03e04808a6ff11a1e12698cbc9151deb04575dcf8e648dabaf3de34` |

Os valores nativos das máscaras foram decodificados da seguinte forma:

| Valor | Classe usada |
|---:|---|
| 0 | Fundo ou pupila |
| 85 | Íris |
| 170 | Esclera |
| 255 | Sobrancelha |

A pupila não possui classe própria: ela usa o mesmo valor zero do fundo. Essa
limitação impede medir diretamente o preenchimento pupilar no UBIPr e motivou
uma solicitação de esclarecimento aos responsáveis pela base.

## 3. Protocolo experimental

A divisão foi realizada por pessoa com semente 42, impedindo que imagens do
mesmo indivíduo aparecessem em treinamento e teste:

| Partição | Pessoas | Imagens | Uso |
|---|---:|---:|---|
| Treinamento | 183 | 7.716 | Ajuste da Small U-Net |
| Validação | 39 | 1.652 | Seleção do checkpoint e calibração do SAM |
| Teste | 39 | 1.650 | Avaliação final congelada |

### 3.1 Small U-Net

A rede foi treinada durante 30 épocas com entrada de 320 × 240 pixels, 8 canais
iniciais, lote 32 e semente 42. O melhor checkpoint foi obtido na época 25. A
saída é multiclasse, embora a comparação principal use apenas a classe íris.

### 3.2 SAM 2.1 Hiera Tiny

O checkpoint `facebook/sam2.1-hiera-tiny`, revisão
`de431c4043854a71d8101e17995dfe596bf101a5`, foi executado na GPU em regime
zero-shot, sem fine-tuning. A geometria do prompt foi estimada com 200 imagens
de validação distribuídas entre pessoas. Entre as variantes avaliadas, a caixa
automática foi selecionada sem consultar o conjunto de teste.

### 3.3 Comparação comum

As métricas foram recalculadas por uma rotina única, usando as mesmas imagens,
referências, redimensionamento e definição de íris. O teste contém oito máscaras
sem pixels de íris; elas foram analisadas separadamente para que o Dice médio
principal não fosse distorcido por referências vazias.

## 4. Resultados quantitativos

### 4.1 Segmentação multiclasse da Small U-Net

No melhor checkpoint, a avaliação agregada do conjunto de teste produziu Dice
global de íris igual a **0,9332**. Por classe:

| Classe | Dice |
|---|---:|
| Íris | **0,9332** |
| Esclera | 0,8539 |
| Sobrancelha | 0,8942 |
| Média das classes de primeiro plano | **0,8938** |

### 4.2 Comparação da classe íris por imagem

A tabela seguinte usa média macro nas 1.642 imagens cuja referência de íris não
é vazia:

| Método | Dice | IoU | Aproveitamento | Pureza |
|---|---:|---:|---:|---:|
| Small U-Net treinada no UBIPr | **0,9171** | **0,8676** | **92,10%** | **92,24%** |
| SAM 2.1 Tiny zero-shot | 0,7026 | 0,6278 | 77,22% | 65,33% |

A U-Net superou o SAM em 0,2145 no Dice e 0,2398 na IoU. Também preservou
14,88 pontos percentuais a mais da íris e apresentou pureza 26,91 pontos
percentuais maior.

Nas oito referências vazias, a U-Net produziu falsos positivos em quatro
imagens, enquanto o SAM produziu falsos positivos em todas as oito. Esses casos
não foram incluídos artificialmente como acertos ou erros máximos na média de
Dice; foram relatados à parte.

## 5. Análise qualitativa

A prancha visual contém cinco colunas: imagem original, referência manual,
previsão da U-Net, previsão do SAM e recortes lado a lado. As cores usadas são
verde para a referência, azul para a U-Net e vermelho para o SAM.

Os exemplos foram selecionados deterministicamente para representar o pior
resultado conjunto, o pior caso do SAM, a maior vantagem da U-Net, um caso
mediano e o melhor resultado conjunto. Isso evita apresentar somente exemplos
favoráveis.

A inspeção mostrou que:

- a U-Net acompanha de forma consistente a região da íris na maioria dos casos;
- o SAM pode obter resultado próximo da U-Net quando a geometria ocular é
  regular;
- nos casos difíceis, o SAM pode deslocar a máscara para sobrancelha, pele ou
  armação dos óculos;
- existem falhas comuns aos dois modelos quando a anotação de íris é vazia ou
  muito pequena.

## 6. Interpretação

O experimento demonstra que, para esta base e este protocolo, o treinamento
supervisionado específico para o domínio ocular foi mais eficaz que a aplicação
direta de um foundation model geral. Isso não significa que CNNs sejam, em
geral, superiores a tecnologias mais recentes. A comparação mede duas
condições diferentes: U-Net treinada no UBIPr contra SAM usado sem fine-tuning.

O SAM continua relevante como alternativa para adaptação ao domínio, geração
assistida de rótulos ou experimentos futuros com fine-tuning. Entretanto, o
resultado atual não justifica substituir a U-Net treinada como segmentador-base
do projeto.

## 7. Solicitações externas preparadas

Foi criado o documento `EMAILS_SOLICITACAO_DATASETS.md`, contendo mensagens para
solicitar bases e acessos ainda indisponíveis e para esclarecer os rótulos e as
condições de uso do UBIPr. Entre as questões encaminhadas estão a representação
da pupila e a permissão para publicar pesos treinados, máscaras previstas e
métricas agregadas sem redistribuir as imagens originais.

Enquanto as respostas não chegam, o UBIPr permite avançar no desenvolvimento e
na validação técnica da segmentação. Ainda é necessária uma base clínica com
rótulos de alterações oculares para executar a etapa final de classificação.

## 8. Artefatos produzidos

| Artefato | Finalidade |
|---|---|
| `treinar_segmentacao_ubipr.py` | Auditoria, divisão por pessoa, treinamento e avaliação multiclasse |
| `avaliar_sam2_ubipr.py` | Calibração e avaliação do SAM 2.1 no UBIPr |
| `comparar_modelos_ubipr.py` | Comparação comum entre U-Net e SAM por imagem |
| `gerar_amostras_visuais_ubipr.py` | Geração reproduzível da prancha qualitativa |
| `outputs/cnn/ubipr_multiclasse_30ep_batch32/` | Checkpoint, histórico e métricas da U-Net |
| `outputs/modelos_modernos/sam2_1_hiera_tiny_ubipr/` | Métricas de validação e teste do SAM |
| `outputs/comparacao_ubipr.json` | Comparação quantitativa consolidada |
| `outputs/amostras_visuais_ubipr.png` | Prancha com previsões e recortes reais do teste |
| `outputs/amostras_visuais_ubipr.json` | Identificação e Dice dos exemplos visuais |
| `EMAILS_SOLICITACAO_DATASETS.md` | Modelos de solicitação de dados, acessos e esclarecimentos |

A suíte automatizada totaliza 16 testes, todos aprovados. Ela verifica a
decodificação dos rótulos, a separação sem vazamento de pessoas, a seleção do
SAM sem máscaras vazias, métricas, perdas e utilitários das pipelines anteriores.

## 9. Limitações

1. A pupila não é uma classe separada no UBIPr, impossibilitando medir
   diretamente sua preservação como abertura interna.
2. O UBIPr é uma base de segmentação ocular, não uma base de diagnóstico de
   alterações oculares.
3. A U-Net foi treinada no domínio avaliado; o SAM foi usado sem fine-tuning.
4. As métricas não provam que o recorte melhora a classificação clínica futura.
5. O desvio-padrão do SAM é elevado, indicando comportamento instável entre
   imagens e condições de captura.
6. Pesos ou produtos derivados não devem ser publicados antes da confirmação
   das condições de uso da base.

## 10. Próximas etapas recomendadas

1. Aguardar as respostas sobre bases clínicas, acessos e condições de uso.
2. Congelar a Small U-Net atual como baseline de segmentação do UBIPr.
3. Gerar uma análise por pessoa e por condição visual, incluindo óculos,
   oclusão, pose e iluminação.
4. Avaliar fine-tuning do SAM somente como experimento adicional, mantendo o
   teste isolado.
5. Obter uma base clínica rotulada para medir classificação com imagem inteira,
   recorte da U-Net e, se pertinente, outros segmentadores.
6. Investigar uma base que separe explicitamente íris e pupila para avaliar a
   preservação real da textura anular.

## 11. Conclusão

O avanço de hoje estabeleceu um baseline sólido e reproduzível em uma base de
grande porte. A Small U-Net alcançou Dice médio por imagem de 0,9171 e superou o
SAM 2.1 zero-shot em todos os indicadores principais da comparação comum. A
análise visual confirmou maior estabilidade da rede treinada e revelou falhas
do SAM em objetos próximos ao olho.

O resultado permite continuar o desenvolvimento da etapa de segmentação sem
depender imediatamente das respostas externas. A dependência que permanece é a
obtenção de dados clínicos e das autorizações necessárias para realizar e
divulgar a etapa de classificação de alterações oculares.

## 12. Evidências

- auditoria do UBIPr: `pfc1-segmentacao-mmu/outputs/cnn/ubipr_multiclasse_30ep_batch32/auditoria.json`;
- histórico de treinamento: `pfc1-segmentacao-mmu/outputs/cnn/ubipr_multiclasse_30ep_batch32/historico.csv`;
- comparação quantitativa: `pfc1-segmentacao-mmu/outputs/comparacao_ubipr.json`;
- amostras visuais: `pfc1-segmentacao-mmu/outputs/amostras_visuais_ubipr.png`;
- metadados das amostras: `pfc1-segmentacao-mmu/outputs/amostras_visuais_ubipr.json`;
- documentação de execução: `pfc1-segmentacao-mmu/README.md`;
- solicitações externas: `pfc1-segmentacao-mmu/EMAILS_SOLICITACAO_DATASETS.md`.
