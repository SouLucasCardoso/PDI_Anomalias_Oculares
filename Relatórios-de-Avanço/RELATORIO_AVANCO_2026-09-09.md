# Relatório de avanço — avaliação de segmentadores modernos e aproveitamento da íris

| Identificação | Informação |
|---|---|
| Projeto | Influência da segmentação da íris no desempenho de redes neurais convolucionais para a classificação de alterações oculares |
| Disciplina | Projeto Final de Curso I — PFC I |
| Curso | Engenharia de Computação |
| Instituição | UniSatc |
| Acadêmico | Lucas Cardoso Rodrigues |
| Orientador | Rodrigo Ramos Silva |
| Data | 9 de setembro de 2026 |
| Etapa | Avaliação de tecnologias modernas e reformulação das métricas de segmentação |

## 1. Síntese do avanço

Nesta etapa, o experimento deixou de se limitar à comparação direta entre duas
pipelines e passou a medir a porcentagem de aproveitamento da região da íris.
Essa mudança responde à orientação de avaliar não apenas se a máscara se
aproxima da referência, mas quanto da textura iridiana é preservado e quanto do
recorte é contaminado por pupila, esclera, pálpebras, cílios e fundo.

Os resultados anteriores da rede Small U-Net foram preservados e reorganizados
em uma pasta exclusiva para CNN. Em seguida, foram implementados e executados
dois benchmarks adicionais: o SAM 2.1 Hiera Tiny, da Meta, em regime zero-shot,
e o segmentador semântico público OpenIRIS. Os três métodos foram avaliados na
mesma partição do MMU, mantendo a separação por pessoa já estabelecida.

Os testes mostram que os modelos modernos reduzem a inclusão da pupila e
aumentam a pureza do recorte, mas preservam uma porcentagem menor da íris. Não
foi encontrada uma solução superior em todos os indicadores. O resultado
reforça a necessidade de adaptar o SAM ao domínio ocular, em vez de utilizar
diretamente um modelo geral sem ajuste.

## 2. Mudança no foco da avaliação

O Dice e a IoU continuam sendo necessários para avaliar a concordância espacial
com a máscara de referência. Entretanto, isoladamente, eles não descrevem se o
recorte é adequado para estudar a textura da íris. Uma máscara aproximadamente
circular pode alcançar sobreposição razoável e ainda preencher a pupila.

Foram incorporados os seguintes indicadores:

| Indicador | Definição | Interpretação desejada |
|---|---|---|
| Aproveitamento | Pixels da íris corretamente preservados / pixels da íris real | Maior é melhor |
| Pureza | Pixels corretos da íris / todos os pixels previstos | Maior é melhor |
| Contaminação | Pixels externos à íris / todos os pixels previstos | Menor é melhor |
| Perda de íris | Pixels da íris não preservados / pixels da íris real | Menor é melhor |
| Preenchimento da pupila | Fração da abertura pupilar incluída na previsão | Menor é melhor |

No código, aproveitamento corresponde à revocação da máscara e é apresentado em
porcentagem. Para selecionar prompts e limiares sem favorecer discos sólidos,
foi criado o índice auxiliar:

\[
I_{útil} = Dice \times (1 - preenchimento\ da\ pupila)
\]

Esse índice não é uma métrica padronizada e não substitui Dice, IoU, pureza ou
aproveitamento. Ele foi usado somente como critério experimental de seleção na
validação para penalizar máscaras que apagam a abertura pupilar.

## 3. Organização dos experimentos

Os arquivos foram separados da seguinte forma:

```text
pfc1-segmentacao-mmu/outputs/
├── cnn/
│   ├── baseline/
│   ├── baseline_30ep/
│   ├── minha_reproducao_30ep/
│   ├── pareamento_corrigido_50ep/
│   └── teste_local_5ep/
└── modelos_modernos/
    ├── sam2_1_hiera_tiny/
    └── openiris/
```

Pesos, datasets, manifestos com caminhos locais, exemplos biométricos e recortes
individuais permanecem ignorados pelo Git. Métricas agregadas, tabelas por
imagem, código e relatórios podem ser versionados.

## 4. Protocolo experimental

Foi reutilizada a divisão sem compartilhamento de pessoas definida com semente
42:

| Partição | Pessoas | Imagens | Uso |
|---|---:|---:|---|
| Treinamento da CNN | 32 | 320 | Ajuste do baseline supervisionado |
| Validação | 6 | 60 | Calibração geométrica e seleção de prompt/limiar |
| Teste | 7 | 70 | Avaliação final |

O conjunto de teste não foi usado para escolher a variante de prompt, o limiar
ou a composição da máscara. Todos os resultados principais a seguir usam as
mesmas 70 imagens e máscaras corrigidas da avaliação anterior.

### 4.1 SAM 2.1 Hiera Tiny

Foi utilizado o checkpoint público `facebook/sam2.1-hiera-tiny`, fixado na
revisão `de431c4043854a71d8101e17995dfe596bf101a5`. O modelo de imagem carregado
possui 31.440.721 parâmetros e foi executado na GPU NVIDIA GeForce RTX 3050 de
6 GB por meio do PyTorch e da biblioteca Transformers.

Foram avaliadas três variantes de prompt:

1. caixa automática ao redor da região estimada da íris;
2. caixa automática com um ponto negativo no centro pupilar;
3. caixa, quatro pontos positivos no anel e um ponto negativo na pupila.

A geometria automática foi calibrada exclusivamente com as 60 imagens de
validação. A variante selecionada foi a caixa com ponto negativo na pupila.

Também foi executado um protocolo assistido no qual a caixa delimitadora vem da
máscara real. Esse resultado funciona como limite superior da segmentação
condicionada por prompt e não representa uma pipeline autônoma.

### 4.2 OpenIRIS

Foi avaliado o modelo público `Worldcoin/iris-semantic-segmentation`, revisão
`e6c8fbb8e2e7e024a58818530a6e3ae5c005f47a`, em formato ONNX. O modelo produz
mapas independentes para globo ocular, íris, pupila e cílios.

Na validação, foram comparados os limiares 0,3, 0,5 e 0,7 e três composições:

1. máscara da íris sem subtração;
2. íris menos pupila;
3. íris menos pupila e cílios.

Pelo índice útil, foi selecionada a terceira composição, com limiar 0,3. A
inferência foi realizada em CPU com ONNX Runtime.

## 5. Resultados quantitativos

| Método | Dice | IoU | Aproveitamento | Pureza | Contaminação | Pupila preenchida | Índice útil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Small U-Net | **0,5247** | 0,3739 | **63,72%** | 45,33% | 54,67% | 60,66% | 0,2064 |
| SAM 2.1 automático, zero-shot | 0,5141 | **0,3764** | 55,33% | 48,61% | 51,39% | 47,20% | 0,2715 |
| OpenIRIS pré-treinado | 0,4944 | 0,3575 | 49,79% | **49,83%** | **50,17%** | **36,25%** | **0,3152** |

Entre as soluções autônomas, a Small U-Net preservou a maior quantidade de íris
e obteve o maior Dice. O SAM 2.1 teve Dice 0,0106 menor e aproveitamento 8,40
pontos percentuais menor, mas aumentou a pureza em 3,28 pontos e reduziu o
preenchimento da pupila em 13,46 pontos percentuais.

O OpenIRIS apresentou a maior pureza e a menor inclusão pupilar. Em relação à
CNN, porém, o Dice diminuiu 0,0303 e o aproveitamento caiu 13,93 pontos
percentuais. Isso significa que o modelo produz um recorte mais conservador e
mais limpo, mas descarta uma parcela maior da textura iridiana.

### 5.1 Resultado assistido do SAM 2.1

| Método assistido | Dice | IoU | Aproveitamento | Pureza | Contaminação | Pupila preenchida |
|---|---:|---:|---:|---:|---:|---:|
| SAM 2.1 com caixa da máscara real | 0,6123 | 0,4598 | 63,62% | 59,68% | 40,32% | 53,09% |

O ganho obtido com uma caixa precisa mostra que a qualidade do prompt é um dos
principais gargalos. Entretanto, como a caixa foi derivada da anotação da imagem
avaliada, esses números não podem ser comparados como resultado autônomo. Eles
indicam potencial para combinar um localizador ocular treinado com o SAM ou para
realizar fine-tuning específico para íris.

## 6. Análise qualitativa

A inspeção dos recortes confirma três comportamentos:

- a Small U-Net tende a capturar uma área maior, mas inclui pupila e regiões
  externas à íris com frequência;
- o SAM 2.1 reconhece bem o disco ocular em vários casos, porém sua saída depende
  fortemente da posição da caixa e do ponto negativo;
- o OpenIRIS delimita a pupila de forma mais consistente e permite remover
  cílios, mas em olhos parcialmente ocluídos pode eliminar trechos válidos da
  íris.

Os piores casos continuam concentrados em mudanças de pose, oclusões, reflexos e
referências geometricamente suspeitas. Os melhores casos do SAM e do OpenIRIS
produzem anéis visualmente adequados, com Dice próximo ou superior a 0,90 em
imagens individuais, mas o comportamento ainda não é uniforme entre pessoas.

## 7. Grau de satisfação

O avanço é **satisfatório como investigação de tecnologias modernas**. Foram
implementados dois modelos públicos, executados na mesma divisão experimental e
avaliados por imagem com métricas compatíveis. O experimento demonstra que um
foundation model pode ser executado no hardware disponível e que prompts
negativos ajudam a preservar a pupila.

O resultado é **parcialmente satisfatório para o novo objetivo de
aproveitamento**. A análise deixou de premiar somente a sobreposição global e
passou a revelar o compromisso entre quantidade preservada e pureza. Contudo,
reduzir a inclusão pupilar causou perda relevante da área da íris.

O resultado ainda é **insuficiente como segmentação final do PFC**. Nenhum
método autônomo combina alto aproveitamento, alta pureza e baixo vazamento
pupilar. Além disso, ainda não foi realizada validação em imagens clínicas com
alterações oculares.

## 8. Limitações metodológicas

1. O SAM 2.1 foi avaliado sem fine-tuning específico para imagens oculares.
2. O OpenIRIS declara o MMU entre as bases usadas em seu treinamento. Não é
   possível garantir que as 70 imagens locais de teste sejam inéditas para o
   modelo; seu resultado é uma verificação técnica, não uma estimativa
   independente de generalização.
3. O MMU não contém rótulos de doenças ou alterações oculares.
4. O conjunto de teste possui somente sete pessoas, mantendo alta incerteza
   entre indivíduos.
5. O índice útil proposto é auxiliar e ainda precisa ser validado ou substituído
   por um critério fundamentado em qualidade biométrica.
6. As máscaras disponíveis não separam explicitamente todas as fontes de
   oclusão e reflexo.
7. Os resultados não demonstram ainda que maior área útil melhora a futura
   classificação de alterações oculares.

## 9. Artefatos e verificações produzidos

| Artefato | Finalidade |
|---|---|
| `avaliar_sam2_mmu.py` | Calibração de prompts e avaliação reproduzível do SAM 2.1 |
| `avaliar_openiris_mmu.py` | Inferência multiclasse e avaliação do OpenIRIS |
| `metricas_validacao_por_imagem.csv` | Seleção auditável sem consulta ao teste |
| `metricas_teste_por_imagem.csv` | Dice, IoU e percentuais para cada imagem |
| `metricas.json` | Configuração, revisão dos modelos e resultados agregados |
| `RELATORIO_COMPARATIVO_GERAL.md` | Comparação consolidada dos métodos |
| `recortes_teste/` | Máscaras e recortes locais não enviados ao Git |

Foram gerados 280 artefatos individuais para os dois protocolos do SAM e 140
para o OpenIRIS. A suíte automatizada totaliza 11 testes, todos aprovados. Os
testes verificam pareamento, identificação da abertura pupilar, perdas da CNN,
métricas de aproveitamento, construção dos prompts, pré-processamento ONNX e
composição das máscaras multiclasse.

## 10. Próximas etapas recomendadas

1. Adquirir MOBIUS ou UBIPr para obter máscaras multiclasse com indivíduos não
   presentes no treinamento do OpenIRIS.
2. Implementar fine-tuning do SAM 2.1 Tiny com encoder congelado, adapters ou
   LoRA, respeitando o limite de 6 GB da GPU.
3. Avaliar o Iris-SAM como modelo diretamente especializado no formato anular.
4. Separar explicitamente íris, pupila, esclera, pálpebras, cílios e reflexos na
   representação das máscaras.
5. Definir um indicador de área visível útil normalizado pela área teórica do
   anel iridiano e fundamentado na literatura de qualidade biométrica.
6. Realizar validação externa em outra base e apresentar intervalos de confiança
   por pessoa.
7. Alinhar título, objetivo e pergunta de pesquisa com a mudança de comparação
   de pipelines para análise de aproveitamento da íris.
8. Após congelar o segmentador, verificar se o aproveitamento se relaciona com o
   desempenho do classificador de alterações oculares.

## 11. Conclusão

O avanço demonstrou que adotar uma tecnologia mais nova não garante, por si só,
uma segmentação mais adequada da íris. O SAM 2.1 zero-shot e o OpenIRIS reduziram
a inclusão da pupila, mas sacrificaram parte da área iridiana. A Small U-Net
continua sendo o método que mais preserva a região anotada, enquanto os modelos
adicionais fornecem recortes mais conservadores e evidenciam caminhos para
melhoria.

A principal contribuição desta etapa é a criação de uma avaliação mais adequada
ao novo foco do PFC: quantidade de textura preservada, pureza do recorte e
controle da contaminação. O próximo passo tecnicamente mais promissor é adaptar
o SAM ao domínio ocular usando dados multiclasse e validar o modelo em uma base
externa sem sobreposição de indivíduos.

## 12. Evidências

- CNN reorganizada: `pfc1-segmentacao-mmu/outputs/cnn/`;
- SAM 2.1: `pfc1-segmentacao-mmu/outputs/modelos_modernos/sam2_1_hiera_tiny/`;
- OpenIRIS: `pfc1-segmentacao-mmu/outputs/modelos_modernos/openiris/`;
- relatório comparativo: `pfc1-segmentacao-mmu/outputs/modelos_modernos/openiris/RELATORIO_COMPARATIVO_GERAL.md`;
- documentação de execução: `pfc1-segmentacao-mmu/README.md`.

## Referências principais

- RAVI, Nikhila et al. *SAM 2: Segment Anything in Images and Videos*. 2024.
  Disponível em: <https://arxiv.org/abs/2408.00714>. Acesso em: 9 set. 2026.
- META AI. *Segment Anything Model 2*. Repositório oficial. Disponível em:
  <https://github.com/facebookresearch/sam2>. Acesso em: 9 set. 2026.
- FARMANIFARD, Parisa; ROSS, Arun. *Iris-SAM: Iris Segmentation Using a
  Foundation Model*. 2024. Disponível em: <https://arxiv.org/abs/2402.06497>.
  Acesso em: 9 set. 2026.
- WORLDCOIN FOUNDATION. *Iris Semantic Segmentation Model Card*. Disponível em:
  <https://github.com/worldcoin/open-iris/blob/main/SEMSEG_MODEL_CARD.md>.
  Acesso em: 9 set. 2026.
- INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. *ISO/IEC 29794-6:2015 —
  Biometric sample quality — Part 6: Iris image data*. Disponível em:
  <https://www.iso.org/standard/54066.html>. Acesso em: 9 set. 2026.
