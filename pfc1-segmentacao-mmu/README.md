
> Atualização posterior de 21/10: teste com configuração congelada =91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR. A busca de área em passos nominais de 1% foi concluída:99% aprovados na oclusão inferior; na superior, apenas a condição original passou. Consulte [os resultados e limitações](RESULTADOS_CONGELADOS_E_OCLUSAO_2026-10-21.md).



## Atualização de desenvolvimento — 21/10/2026

O candidato congelado atingiu **Rank-1 de 90,04% e TAR de 90,66%, com FMR de 0,98%**, na validação UBIPr de 482 consultas, com uma foto original e lado do olho informado (16 candidatos). São 434 identificações corretas e 437 aceitações genuínas; o resultado conjunto de identificação correta e aceitação é88,38%. A validação foi reutilizada para seleção de estratégias e o componente externo ArcIris tem população de pré-treinamento desconhecida: estes números são exploratórios, sem confirmação independente. O mínimo de área permanece não determinado, com e sem oclusão. Consulte [o relatório atualizado](AVANCO_RECONHECIMENTO_2026-10-21.md) e `outputs/candidato_congelado_2026-10-21/CONGELADO.json`.

# PFC I — prova de conceito de segmentação da íris

> **Continuação concluída:** o encoder polar com mais resolução terminou 29
> épocas (seleção na 21). Sua fusão obteve 78,84% de Rank-1 e 68,26% de TAR;
> a transformação linear ficou em 78,22% e 65,98%. Nenhuma melhorou ambas
> as métricas da fusão anterior, mantida como referência. UBIPr principal,
> uma foto por consulta e 39 testes aprovados. [Relatório da continuação](outputs/fusao_densa_val_2026-10-20/RELATORIO_CONTINUACAO.md).

> **Treino polar e fusões concluídos em 20/10:** o novo encoder polar terminou
> 28 épocas (seleção na 20). Uma fusão fixa RGB/polar/espacial atingiu Rank-1
> de 79,88%, TAR de 68,05% e FMR de 0,99% nas 482 consultas de validação.
> É um candidato de desenvolvimento, sem confirmação independente ou mínimo
> aprovado. Os 37 testes passaram. [Relatório e distância até o critério](outputs/fusao_espacial_val_2026-10-20/RELATORIO_AVANCO_POLAR_FUSAO.md).

> **Reconhecedor polar avaliado em 20/10:** fontes e pesos oficiais TripletIris
> foram instalados, e 15 variantes de normalização/cadastro terminaram na
> validação. Nenhuma superou o encoder atual; ele permanece preservado. A
> aproximação elíptica não melhorou a identificação nessa configuração. Os
> 32 testes passaram. [Relatório e imagens reais](outputs/tripletiris_elipse_validacao_2026-10-20/RELATORIO_RECONHECEDOR_POLAR.md).

> **Duas adaptações de treinamento concluídas em 20/10:** ajuste em máscaras
> automáticas e ajuste angular com triplet balanceado executaram seis épocas
> cada, sem superar a TAR da época zero. O critério preservou os parâmetros
> anteriores: 66,80% de Rank-1, 59,34% de TAR e 0,99% de FMR nesta execução de
> validação. Não há novo modelo adotado, teste independente ou mínimo aprovado.
> [Relatório dos treinamentos](outputs/identidade_metrica_automatica_2026-10-20/RELATORIO_TREINAMENTOS.md).

> **Cadastro multicaptura e fluxo automático, validação concluída:** em 482
> consultas, a máscara automática da U-Net com média das três melhores
> correspondências atingiu Rank-1 de 67,01%, TAR de 59,34% e FMR de 0,99%.
> São estimativas de desenvolvimento, não novo teste ou mínimo aprovado.
> O HDBIF máximo multicaptura piorou; um controle posterior de suporte polar foi
> registrado separadamente. [Resultados e exemplos reais](outputs/cadastro_multicaptura_val_v2_2026-10-20/RELATORIO_CADASTRO.md)
> e [controle exploratório de qualidade](outputs/suporte_polar_val_2026-10-20/RELATORIO_SUPORTE.md).

> **Melhoria do reconhecedor, validação concluída em 20/10:** o recorte antes da
> normalização HDBIF elevou Rank-1 de 28,84% para 42,12% em 482 consultas de
> validação com uma captura de cadastro por olho. Ampliar a entrada do encoder
> congelado de 128 para 256 pixels piorou o controle. Essas taxas são de
> desenvolvimento e não substituem o teste anterior com galeria por centróide.
> [Protocolo](MELHORIA_RECONHECEDOR_2026-10-20.md) e
> [relatório completo](outputs/melhoria_normalizacao_val_gpu_2026-10-20/RELATORIO_MELHORIA.md).

> **Estado atual em 20/10/2026:** o objetivo ativo é investigar área preservada
> e identidade ocular. Duas rodadas UBIPr e o teste clínico HDBIF foram concluídos.
> O novo encoder obteve Rank-1 de 67,90% no benchmark exploratório; o mínimo
> global não foi determinado pelo critério registrado. O texto ativo está em
> [artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md](artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md).
> Os planos de classificação e indicações de tarefas em execução abaixo são
> históricos. Consulte [INSTALACAO_LOCAL.md](INSTALACAO_LOCAL.md) para o estado atual.

> **Instalação neste computador, 20/10/2026:** consulte
> [INSTALACAO_LOCAL.md](INSTALACAO_LOCAL.md) para os dados recuperados, ambiente
> com CUDA, comandos de execução e pendências de acesso. As métricas abaixo
> são resultados históricos; os checkpoints originais não estão nesta cópia.
>
> **Produção para 09/11:** base clínica pública SLP-VLD v3 adquirida e auditada,
> protocolo em `outputs/clinico_slpvld_2026-10-20/`, retreinamento UBIPr em
> andamento. Consulte [pesquisa de bases](PESQUISA_BASES_PUBLICAS_2026-10-20.md),
> [plano de produção](PLANO_ARTIGO_2026-11-09.md) e
> [rascunho do artigo](artigo/ARTIGO_EM_PRODUCAO.md). Para consultar o progresso,
> execute `executar.ps1 status_producao.py`.

Este pacote treina uma U-Net pequena para recortar a região visível da íris no
**MMU Iris Database**. Ele valida a etapa de segmentação, mas ainda não constitui
o experimento clínico do PFC, pois o MMU não contém rótulos de alterações
oculares.

## Situação atual

Uma auditoria visual revelou que os cinco arquivos de imagem e máscara de cada
pessoa/lado não usam a mesma ordem interna. O pareamento antigo por índice podia
associar uma imagem à máscara de outra posição do olhar. O pipeline agora:

- associa as pastas de pessoas pela ordem numérica correta;
- estima os centros da íris e resolve a atribuição de menor custo entre as cinco
  imagens e máscaras de cada lado;
- registra índice original, índice da máscara e distância de pareamento;
- alerta para sujeitos com anotações geometricamente suspeitas;
- separa 32 pessoas para treino, 6 para validação e 7 para teste;
- escolhe época e limiar apenas na validação;
- mede Dice, IoU, precisão, revocação, razão de área e preenchimento da pupila;
- salva exemplos ordenados dos piores aos melhores casos e o recorte aplicado.

Foram reordenados 350 dos 450 pares. Os testes automatizados cobrem o pareamento
sintético, a identificação do interior pupilar e a nova função de perda.

## Resultado reproduzido

A configuração escolhida na validação foi U-Net com 8 canais iniciais, entrada
160 × 120, `BCE + Dice`, aumento leve e limiar 0,46.

| Indicador | Resultado |
|---|---:|
| Dice de validação | 0,6549 |
| Dice de teste, 70 imagens | 0,5247 |
| IoU de teste | 0,3739 |
| Precisão / revocação | 0,4533 / 0,6372 |
| Razão área prevista / área real | 1,436 |
| Fração média da pupila preenchida | 0,607 |
| Imagens com Dice ≥ 0,70 | 12 de 70 |

O sujeito 10 apresenta distância média de pareamento acima do limite de auditoria
e referências visualmente incompatíveis em parte das imagens. Uma análise de
sensibilidade, claramente secundária, obtém Dice 0,5547 nas 60 imagens restantes.
O resultado oficial continua sendo 0,5247 nas 70 imagens.

**Avaliação:** satisfatório como prova de conceito e como pipeline auditável;
apenas moderado como segmentador; insuficiente como resultado final ou clínico.
O recorte preserva a abertura pupilar com mais frequência e reduz a área
excedente, mas ainda falha em oclusões, reflexos e mudanças entre pessoas.

## Benchmark com modelos modernos

Os resultados da CNN foram separados em `outputs/cnn/`. Dois modelos públicos
também foram avaliados na mesma partição de 60 imagens de validação e 70 de
teste. A configuração foi escolhida somente na validação pelo índice auxiliar
`Dice × (1 - preenchimento da pupila)`.

| Método | Dice | IoU | Aproveitamento | Pureza | Pupila preenchida | Índice útil |
|---|---:|---:|---:|---:|---:|---:|
| Small U-Net | 0,5247 | 0,3739 | 63,72% | 45,33% | 60,66% | 0,2064 |
| SAM 2.1 Tiny automático, zero-shot | 0,5141 | 0,3764 | 55,33% | 48,61% | 47,20% | 0,2715 |
| OpenIRIS pré-treinado | 0,4944 | 0,3575 | 49,79% | 49,83% | 36,25% | 0,3152 |

O SAM 2.1 e o OpenIRIS preservaram melhor a abertura pupilar, mas perderam área
de íris e Dice. Portanto, nenhum deles substitui a CNN de forma inequívoca neste
teste. O resultado sugere ajustar o SAM ao domínio da íris em vez de usar apenas
o modelo zero-shot.

O OpenIRIS declara o MMU entre as bases usadas no próprio treinamento. Como não
é possível excluir sobreposição com estas imagens, seu resultado é apenas uma
verificação técnica, não uma estimativa independente de generalização. O
relatório completo está em
`outputs/modelos_modernos/openiris/RELATORIO_COMPARATIVO_GERAL.md`.

## Como executar

Requer Python 3.10 ou superior:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python treinar_segmentacao_mmu.py `
  --data-dir data `
  --epochs 50 `
  --base-channels 8 `
  --batch-size 16 `
  --height 120 `
  --width 160 `
  --loss bce_dice `
  --augmentation light `
  --patience 15 `
  --seed 42 `
  --output-dir outputs/cnn/pareamento_corrigido_50ep
```

O programa baixa os arquivos quando eles ainda não existem. Use `--no-download`
para exigir uma cópia local. Durante comparação de configurações, use `--no-test`
para preservar o conjunto de teste:

```powershell
python treinar_segmentacao_mmu.py --epochs 30 --no-test --output-dir outputs/candidato
```

Os testes são executados com:

```powershell
python -m unittest discover -p "test_*.py" -v
```

Para reproduzir os benchmarks modernos, os modelos são baixados para o cache
local na primeira execução:

```powershell
$env:HF_HOME = (Join-Path (Get-Location) "data/modelos/huggingface")
python avaliar_sam2_mmu.py
python avaliar_openiris_mmu.py
```

O SAM 2.1 testa um prompt automático e uma caixa obtida da máscara real. O
resultado com caixa real é identificado como assistido e não deve ser usado
como desempenho de um pipeline autônomo.

## Arquivos gerados

- `metricas.json`: configuração, auditoria do pareamento e métricas agregadas;
- `metricas_por_imagem.csv` e `resumo_detalhado.json`: dispersão, piores casos,
  resultados por pessoa e análise secundária de qualidade;
- `historico.csv` e `curvas_treinamento.png`: evolução por época;
- `exemplos_teste.png`: referência, probabilidade, previsão e recorte aplicado;
- `manifesto.json`: correspondências e partições por pessoa;
- `melhor_modelo.pt`: estado escolhido exclusivamente pela validação.
- `outputs/cnn/`: treinamentos e recortes produzidos pela Small U-Net;
- `outputs/modelos_modernos/sam2_1_hiera_tiny/`: métricas e recortes do SAM;
- `outputs/modelos_modernos/openiris/`: métricas e recortes do OpenIRIS.

## Datasets e próximos experimentos

O levantamento com a estratégia de aquisição está em
[DATASETS_RECOMENDADOS.md](DATASETS_RECOMENDADOS.md). As prioridades são:

1. MOBIUS e UBIPr para treinar um segmentador em RGB com máscaras mais completas;
2. Warsaw-BioBase-Disease-Iris para a comparação clínica com e sem recorte;
3. o segmentador aberto da Notre Dame como baseline externo congelado.

### UBIPr multiclasse

O UBIPr *Single Eyes Segmented Version* pode ser auditado e treinado pelo script
`treinar_segmentacao_ubipr.py`. As imagens RGB (`.jpg`) e máscaras (`.png`) são
pareadas pelo nome, e a divisão é feita pelo identificador de pessoa `C`.

```powershell
python treinar_segmentacao_ubipr.py --audit-only
python treinar_segmentacao_ubipr.py --epochs 30 --batch-size 8
```

A máscara possui quatro níveis: `0=fundo ou pupila`, `85=íris`, `170=esclera` e
`255=sobrancelha`. Como fundo e pupila compartilham o valor zero, o UBIPr não
permite aprender a pupila como classe independente. Dados e pesos permanecem
fora do Git; somente auditoria, manifesto e métricas agregadas são produzidos.

O treinamento completo em 320 × 240, com batch 32, 8 canais iniciais e semente
42, selecionou a época 25 exclusivamente pela validação. No teste independente
de 1.650 imagens, os resultados foram:

| Classe | Dice de teste |
|---|---:|
| Fundo ou pupila | 0,9884 |
| Íris | **0,9332** |
| Esclera | 0,8540 |
| Sobrancelha | 0,8942 |
| Média das classes de primeiro plano | **0,8938** |

Essas métricas avaliam somente segmentação no UBIPr e não permitem concluir
nada sobre classificação ou diagnóstico de alterações oculares.

### Comparação UBIPr: U-Net treinada × SAM 2.1 zero-shot

O SAM 2.1 Hiera Tiny foi avaliado no mesmo teste de 1.650 imagens. A geometria
do prompt foi calibrada em 200 imagens de validação distribuídas entre pessoas,
e a variante `box` foi escolhida sem consultar o teste. Para tornar os métodos
comparáveis, a métrica principal abaixo é a média por imagem nas 1.642 amostras
de teste que possuem referência de íris não vazia:

| Método | Dice | IoU | Aproveitamento | Pureza |
|---|---:|---:|---:|---:|
| Small U-Net treinada no UBIPr | **0,9171** | **0,8676** | **92,10%** | **92,24%** |
| SAM 2.1 Tiny zero-shot | 0,7026 | 0,6278 | 77,22% | 65,33% |

O teste contém ainda oito imagens sem pixels de íris anotados. A U-Net produziu
falsos positivos em quatro delas, enquanto o SAM produziu falsos positivos nas
oito. A comparação demonstra maior adaptação da U-Net ao UBIPr, mas não prova
superioridade geral da arquitetura: o SAM foi usado sem fine-tuning.

### Amostras visuais do teste

A prancha `outputs/amostras_visuais_ubipr.png` mostra imagens reais da partição
de teste, a referência manual, as previsões da U-Net e do SAM e os respectivos
recortes. Verde indica referência, azul indica U-Net e vermelho indica SAM. Os
casos são selecionados deterministicamente para incluir resultado ruim, caso
mediano, resultado bom e grande divergência entre os modelos; portanto, não são
apenas exemplos favoráveis.

Para regenerar a prancha e o arquivo JSON com a identificação e o Dice de cada
amostra:

```powershell
python gerar_amostras_visuais_ubipr.py
```

Arquivos produzidos:

- `outputs/amostras_visuais_ubipr.png`: comparação visual em cinco colunas;
- `outputs/amostras_visuais_ubipr.json`: categoria, pessoa, sessão, imagem e
  Dice de cada modelo para cada exemplo selecionado.

### Limite sob oclusão controlada

O script `avaliar_oclusao_ubipr.py` mede a robustez da U-Net congelada quando
faixas opacas entram pelas margens superior e inferior da imagem. O percentual
é calculado sobre os pixels de íris anotados, e a referência de avaliação é a
parte que permanece visível. O critério foi declarado antes da leitura do
resultado: Dice da região visível maior ou igual a 0,70 em pelo menos 95% dos
casos-direções.

No teste completo (1.642 imagens com íris), o baseline sem oclusão atingiu esse
critério em 96,22% dos casos. A menor perturbação testada, alvo de 1% e cobertura
real média de 1,92% devido à discretização em linhas, reduziu a taxa para
58,25%. Assim, **nenhuma oclusão adicional testada preservou o critério**; o
limite operacional conservador ficou em 0%. Esse valor não deve ser apresentado
como limite fisiológico ou de reconhecimento: a faixa preta também remove
contexto externo à íris e é uma perturbação fora da distribuição natural.

```powershell
python avaliar_oclusao_ubipr.py
python avaliar_oclusao_ubipr.py --levels 0,1,2,3,4,5,6,7,8,9,10 `
  --output-dir outputs/robustez_oclusao_ubipr_fino
```

Os resultados completos estão em `outputs/robustez_oclusao_ubipr/` (passos de
10%) e `outputs/robustez_oclusao_ubipr_fino/` (passos de 1% até 10%). O próximo
ensaio deve medir reconhecimento por identidade com embeddings; segmentação
sozinha não permite afirmar quanto de íris é suficiente para “leitura”.

### DINOv3 e SAM 3

O backbone solicitado `facebook/dinov3-vitl16-pretrain-lvd1689m` foi verificado
com Transformers 5.17, mas o repositório oficial é restrito e retornou HTTP 401
sem autenticação e aceite da licença. O DINOv3 é um extrator de características,
não um segmentador pronto: o uso proposto é comparar embeddings/identidades sob
oclusão ou treinar uma cabeça de segmentação. O ViT-L/16 tem cerca de 300 milhões
de parâmetros; nesta GPU de 6 GB, a opção realista é inferência congelada com
lote pequeno, e não fine-tuning completo.

O SAM 3/3.1 é o sucessor apropriado para uma nova comparação de segmentação,
mas deve usar o mesmo manifesto por pessoa, calibrar prompts somente na
validação e manter o teste congelado. “Embeddings 3” não foi tratado como nome
de um terceiro modelo: no contexto da Meta, a interpretação tecnicamente
coerente é avaliar os embeddings produzidos pelo DINOv3. Essa nomenclatura deve
ser confirmada com o orientador antes de citá-la no texto acadêmico.

O passo a passo de aceite das licenças, criação segura do token e autenticação
está em `ACESSO_MODELOS_META.md`. O ambiente isolado do SAM 3.1 e o script
`avaliar_sam3_1_ubipr.py` já estão preparados. A avaliação produz métricas por
imagem e `amostras_visuais.png`, com original, referência manual, previsão e
recorte real nos casos pior, mediano e melhor.

O SAM 3.1 foi executado em regime zero-shot nas 1.650 imagens do teste, com o
prompt predefinido `iris of the eye` e confiança oficial 0,5. Nas 1.642 imagens
com referência não vazia, obteve Dice 0,8834, IoU 0,8095, aproveitamento 95,90%
e pureza 82,51%. Ele superou claramente o SAM 2.1 Tiny zero-shot (Dice 0,7026),
mas permaneceu abaixo da Small U-Net treinada no UBIPr (Dice 0,9171). Nas oito
referências vazias, o SAM 3.1 produziu previsão positiva em todas.

| Método | Dice | IoU | Aproveitamento | Pureza |
|---|---:|---:|---:|---:|
| Small U-Net treinada | **0,9171** | **0,8676** | 92,10% | **92,24%** |
| SAM 3.1 zero-shot textual | 0,8834 | 0,8095 | **95,90%** | 82,51% |
| SAM 2.1 Tiny zero-shot | 0,7026 | 0,6278 | 77,22% | 65,33% |

O carregador oficial de imagem reportou quatro pesos ausentes em uma camada
convolucional adicional do checkpoint multiplex. A execução usa o detector de
imagem extraído do checkpoint SAM 3.1 e essa mensagem deve constar como
limitação de reprodutibilidade. A prancha visual completa está em
`outputs/modelos_modernos/sam3_1_ubipr/amostras_visuais.png`.

### Reconhecimento com DINOv3 ViT-L/16

O `avaliar_dinov3_ubipr.py` usa o DINOv3 ViT-L/16 oficial como extrator
congelado. Somente pessoas presentes nas duas sessões entram no protocolo:
sessão 1 forma o centroide da galeria e sessão 2 é usada como consulta. Os
limiares para FAR de 1% e 0,1% são escolhidos nas 16 pessoas da validação e
aplicados às 16 pessoas independentes do teste (486 consultas).

| Entrada do DINOv3 | Top-1 | EER | TAR @ FAR 1% |
|---|---:|---:|---:|
| Imagem inteira | **74,28%** | **14,41%** | **47,33%** |
| Recorte pela referência | 26,54% | 41,36% | 7,82% |
| Recorte pela U-Net | 33,33% | 38,72% | 10,29% |

O recorte da íris piorou muito o reconhecimento. Logo, os embeddings genéricos
do DINOv3 estão explorando principalmente características perioculares ou
faciais presentes na imagem inteira; o resultado não demonstra reconhecimento
biométrico robusto pela textura da íris. O recorte da U-Net supera o recorte
ideal neste protocolo, mas ambos permanecem fracos. Isso justifica treinar uma
cabeça específica, fazer adaptação ao domínio ou empregar um reconhecedor de
íris dedicado antes de definir um limite de leitura por oclusão.

O gráfico está em
`outputs/modelos_modernos/dinov3_vitl16_ubipr/comparacao_reconhecimento.png` e
as métricas completas em `metricas.json` no mesmo diretório.

## Cuidados metodológicos

1. O MMU valida somente segmentação; não permite inferência sobre doenças.
2. Métricas calculadas após corrigir referências não são diretamente comparáveis
   às métricas do pareamento antigo.
3. A cópia do MMU no Kaggle informa licença `Unknown`, e o repositório das
   máscaras não declara uma licença explícita. Não redistribuir dados ou pesos
   derivados sem confirmar autorização.
4. Filtros de qualidade e limiares não podem ser escolhidos pelo teste.
5. O segmentador deve ser congelado antes da comparação clínica para impedir
   vazamento entre as duas etapas.

## Fontes do experimento MMU

- Imagens: https://www.kaggle.com/datasets/naureenmohammad/mmu-iris-dataset
- Máscaras: https://github.com/jkozlova/Masks-for-MMU-Iris-dataset
- Artigo associado: https://doi.org/10.1007/978-3-031-16500-9_15


### Desenvolvimento posterior: segmentação sob oclusão

O diagnóstico e o novo ajuste foram concluídos. O novo segmentador melhorou Dice e identificação sob oclusão inferior, mas regrediu em outras condições; não substituiu o candidato aprovado. [Resultados e máscaras reais](DIAGNOSTICO_E_SEGMENTACAO_ROBUSTA_2026-10-21.md).


### Piloto de fusão com pessoas separadas

Foram retreinados três encoders a partir do ImageNet, com 147 pessoas para ajuste, 16 para seleção e 20 para aprendizagem da fusão. O piloto não substituiu o candidato aprovado: obteve 79,25% de Rank-1 limpo na validação, contra 78,84% do controle uniforme de três modelos. A U-Net congelada já havia visto os grupos internos; a separação refere-se aos encoders de identidade. Checkpoints e resultados completos estão preservados em backup local fora do OneDrive. [Resultados, limites e localização do backup](FUSAO_PESSOAS_SEPARADAS_2026-10-21.md).


### Diagnóstico de resolução e geometria — 22/10/2026

Uma análise descritiva das 482 consultas de validação reproduziu exatamente as entradas RGB e polares do candidato congelado. Entre as 198 consultas com Dice de íris de pelo menos 0,95, houve 193 identificações corretas (97,47%). Nos 39 casos em que a geometria da pupila usou o círculo concêntrico alternativo, houve 28 acertos (71,79%); nos 439 casos com contorno interno da máscara, houve 406 (92,48%). A relação entre tamanho nativo da caixa segmentada e identificação limpa não foi monotônica nos intervalos fixados antes da análise. As medidas se referem ao suporte visível segmentado, não ao diâmetro anatômico completo.

Esses subgrupos não alteram o resultado global de 434/482 acertos (90,04%) nem permitem filtrar consultas: o Dice depende de anotação, há confundimento por pessoa e aquisição, e não foi demonstrada causalidade ou aprovação conjunta dos critérios por grupo. As dez referências vazias e quatro falhas de extração foram mantidas. Nenhum modelo, limiar ou resultado de teste foi alterado. Foram aprovados 84 testes. A investigação seguinte deve separar localização da pupila, geometria e descritor, sem prometer recuperação de todos os erros. [Relatório e amostras reais dos recortes](../Relatórios-de-Avanço/RELATORIO_AVANCO_2026-10-22.md).


### Localização aprendida da pupila — 22/10/2026

Um localizador auxiliar foi treinado exclusivamente no treino original, com alvos geométricos aproximados obtidos de buracos nas máscaras. Na validação com 482 consultas, o Rank-1 limpo permaneceu em 90,0415%. A calibração fixa produziu TAR de 90,2490% e FMR de 1,0235%; a recalibração limpa produziu TAR de 89,8340% e FMR de 0,9820%. Nenhuma cumpriu os critérios simultâneos e o candidato anterior foi preservado. O ganho de Rank-1 sob oclusão inferior de 10% teve intervalo por participante incluindo zero. Não houve nova inferência no teste. Alvos aproximados e reutilização da validação limitam as conclusões. A suíte completa passou em 87 testes. Ver [protocolo, resultados e imagem](PUPILA_APRENDIDA_2026-10-22.md).

### Forma elíptica da pupila — 23/10/2026

Foi isolado o efeito da forma com uma camada de 8.194 parâmetros, mantendo centro e raio equivalente do localizador circular congelados. O treino usou 6.282 exemplos e selecionou a época 4 por perda em 879 exemplos internos. Na validação com todas as 482 consultas, a elipse com calibração fixa manteve Rank-1 de 90,0415%, com TAR de 90,0415% e FMR de 1,0235%. A recalibração somente limpa atingiu os mesmos Rank-1 e TAR, com FMR de 0,9820%, passando os critérios limpos, mas sem superar a referência, cujo TAR era 90,6639%. Sob oclusão superior/inferior de 10%, o Rank-1 foi 81,1203%/60,9959%, sem aprovação dos critérios completos. Nenhuma variante foi promovida e não houve nova inferência no teste. Alvos aproximados e reutilização da validação limitam a conclusão. A reprodução dos escores foi exata e a suíte completa passou em 94 testes. Ver [protocolo, controles e resultados](FORMA_PUPILA_2026-10-23.md).

### Transporte de descritores — piloto interno de 23/10/2026

Uma regressão residual fixa, ajustada em 200 descritores de fotos alteradas das pessoas de ajuste, não passou o controle nas 55 fotos alteradas do monitor. A similaridade média com o descritor original melhorou no ajuste (0,6842 para 0,8506), mas piorou no monitor (0,7401 para 0,6613), e o TAR interno caiu. O encoder permaneceu congelado; nenhuma avaliação desta adaptação foi feita na validação principal ou no teste. O monitor pertence ao treino original e já foi visto pelo encoder, portanto seus resultados não são confirmação independente. A referência e as fronteiras de área foram preservadas. A regressão e os escores foram reproduzidos e a suíte completa passou em 97 testes. Ver [protocolo e resultado do piloto](TRANSPORTE_DESCRITOR_2026-10-23.md).

### Fronteira de área e fechamento — 23/10/2026

Uma análise com 5.000 reamostragens pareadas por participante reaproveitou as seis condições existentes, sem novo treino, inferência ou calibração. Com perda nominal de 10%, a diferença de Rank-1 entre superior e inferior foi 24,07 pontos percentuais (IC95% pareado 10,83–36,25), evidenciando a influência da região no processamento completo. A condição inferior com perda de 1% passou os critérios em 50,46% das reamostras; essa frequência descreve estabilidade amostral, não probabilidade populacional de sucesso. Os mínimos pontuais da grade continuam em 100% superior e 99% inferior, sem interpretação de mínimo clínico universal.

A análise foi reproduzida por uma segunda implementação usando 96 linhas de contagens por participante/condição, com diferença máxima de intervalo de 2,23 × 10⁻¹⁶ p.p.; cinco testes direcionados passaram. Não houve nova execução da suíte completa nesta etapa. Foram descritas somente as perdas em pixels de duas condições candidatas, 0,5% superior e 1,5% inferior; elas ainda não foram avaliadas no reconhecedor. O plano limita o refinamento a uma rodada com esses dois pontos e reserva o restante do prazo para fechar o artigo até 09/11. Ver [incerteza, resultados e plano de fechamento](INCERTEZA_AREA_2026-10-23.md).

### Rodada fracionária concluída — fronteira atual de 23/10/2026

Foram executados exatamente os dois novos pontos previstos, com modelo e limiar congelados e todas as 486 consultas mantidas. A perda superior de 0,5% passou: 443 acertos (Rank-1 91,1523%), TAR de 92,3868% e FMR de 0,8916%. A perda inferior de 1,5% reprovou: 433 acertos (89,0947%), TAR de 88,8889% e FMR de 1,0151%. Portanto, o menor aproveitamento nominal aprovado na grade irregular estudada é agora **99,5% na superior e 99% na inferior**. Isso refina o limite observado, sem alterar o reconhecedor ou estabelecer mínimo anatômico/clínico.

Não foi avaliada perda inferior de 0,5%; assim, 99,5% não foi aprovado em ambas as orientações. Entre os níveis coincidentes, o prefixo comum continua em 100%. Na condição superior de 0,5%, uma referência definida arredondou para zero pixels selecionados; as seis referências vazias continuaram inalteradas. Os IC95% descritivos de Rank-1 foram 85,00–95,63% e 81,07–94,72% nas duas novas condições, respectivamente.

A auditoria reproduziu a fusão com diferença zero e conferiu intervenções, entradas inalteradas e hashes do pipeline original. Cinco testes direcionados passaram. O pacote de recuperação foi restaurado em 37 arquivos com hashes conferidos; os escores foram reproduzidos a partir dos componentes restaurados. A rodada experimental limitada foi encerrada, priorizando agora método, tabelas e discussão do artigo. Ver [fronteira consolidada e limites](FRONTEIRA_REFINADA_2026-10-23.md).

### Artigo consolidado para revisão — 23/10/2026

O [manuscrito ativo](artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md) foi reorganizado como artigo completo, com resultados atuais, método, discussão e limitações. Foi preparado um Word de 18 páginas no modelo UniSATC, com cinco tabelas e duas figuras, e todas as páginas foram conferidas visualmente. Os dados de curso e e-mail dos autores foram incluídos; a versão anterior foi arquivada. O documento e as figuras possuem cópia restaurável com hashes conferidos dentro do projeto, sem alterar o Defender. Ver [revisão, localização do Word e recuperação](artigo/REVISAO_ARTIGO_2026-10-23.md). A revisão do orientador permanece pendente.

### Retomada da robustez após solicitação do autor — 23/10/2026

Foram concluídos dois pilotos somente na validação: média de três vistas da mesma foto para segmentar e consenso fixo 50/50 entre a extração original e a nova. O consenso elevou o Rank-1 limpo de 434/482 (90,04%) para 437/482 (90,66%), mas reduziu o TAR de 90,66% para 89,63% e não resolveu a robustez sob oclusão. Nenhum candidato passou o critério registrado; a referência e os resultados de teste permanecem preservados. Quatro testes direcionados passaram, os escores e decisões foram auditados e 55 arquivos foram restaurados com hashes conferidos. Ver [resultados completos e direção seguinte](RETOMADA_ROBUSTEZ_2026-10-23.md).

### Correção aprendida do contorno externo — 23/10/2026

Foram treinadas duas formulações somente no treino original. A primeira falhou na preservação geométrica limpa; a segunda, ensinada pela geometria limpa das fotos de treino, reduziu o erro geométrico superior/inferior em 13,59%/22,93% no monitor, com aumento limpo de 2,87% dentro do limite registrado. Na validação biométrica, o Rank-1 inferior passou de 59,96% para 63,49%, mas o limpo caiu para 89,21% e o superior para 78,84%. O candidato não cumpriu os critérios e não substituiu a referência. Nove testes direcionados passaram; as seleções e os escores foram auditados, e 60 arquivos foram restaurados com hashes conferidos. Ver [método, tabelas e alcance](CONTORNO_EXTERNO_2026-10-23.md).

### Adaptação polar com cadastro fixo — 23/10/2026

O adaptador residual melhorou o Rank-1 do descritor polar no monitor interno de 64,58% para 76,46% na perda superior de 10% e de 45,21% para 63,96% na inferior. A última época permaneceu abaixo da referência limpa original e foi rejeitada; nenhuma época foi elegível. Não houve inferência na validação ou no teste. Treze testes passaram; as cinco épocas foram reproduzidas com perdas idênticas, e 40 arquivos foram restaurados com hashes conferidos. Ver [método, resultados e recuperação](ADAPTACAO_POLAR_2026-10-23.md).


### Complemento geométrico com ramo original preservado — 23/10/2026

O piloto fixo 75% original/25% corrigido preservou 479/480 acertos limpos do descritor polar no monitor interno. Na perda inferior de 10%, o Rank-1 passou de 60,63% para 61,67%, mas o TAR caiu; na superior, ambos pioraram. A FMR permaneceu acima de 1% nas duas oclusões. O candidato foi rejeitado antes da validação, sem nova inferência no teste. Seis testes direcionados passaram e a auditoria reproduziu exatamente a combinação e as decisões. Ver [resultados e recuperação](COMPLEMENTO_GEOMETRICO_2026-10-23.md).


### Estudo do segmentador compartilhado pelo orientador — 23/10/2026

A aplicação externa foi examinada e sua lógica botânica não será integrada. A ideia reaproveitável de SAM guiado foi testada no nosso projeto, sem instalar o aplicativo: 32 fotos de treino em três condições, com prompts automáticos da U-Net. O Dice limpo caiu de 95,15% para 91,45%, apesar de ganho localizado inferior; o piloto reprovou o critério registrado. Dois testes passaram e máscaras, métricas e prompts foram auditados e preservados. Não houve avaliação de identidade nem uso de validação/teste. Ver [viabilidade, resultados e decisão](ESTUDO_SEGMENTADOR_ORIENTADOR_2026-10-23.md).


### Adaptação à oclusão com normalização original — 23/10/2026

Foram preparadas as 7.716 fotos do treino original em três condições e treinado um adaptador residual por 12 épocas, com encoders congelados. Nas 480 consultas do monitor interno, o Rank-1 limpo permaneceu em 479/480 (99,79%), e o superior/inferior com perda de 10% passou de 82,50%/60,63% para 84,38%/68,33%. O TAR melhorou nas duas oclusões, mas a FMR permaneceu em 1,5139%/1,4861%, reprovando o avanço antes da validação. Cinco testes passaram; escores e seleção foram auditados, e 28 arquivos foram restaurados com hashes conferidos. Ver [método, resultados e limites](ADAPTACAO_POLAR_ORIGINAL_2026-10-23.md).


### Perda de identidade no adaptador polar — 23/10/2026

A nova perda com protótipos limpos S1 das pessoas de ajuste foi treinada por 12 épocas, reutilizando as características existentes. O monitor manteve 479/480 acertos limpos; o Rank-1 com perda superior/inferior de 10% foi 84,79%/68,54%, com FMR de 1,6111%/1,5000%. Houve dois e um acertos adicionais frente à rodada anterior, mas a FMR piorou ligeiramente e o candidato continuou barrado antes da validação. Oito testes passaram, protótipos e escores foram auditados, e 35 arquivos foram restaurados com hashes conferidos. Ver [método, correção técnica e resultados](ADAPTACAO_IDENTIDADE_POLAR_2026-10-23.md).


### Cadastro múltiplo e negativos difíceis — 23/10/2026

A perda passou a usar a média das três melhores fotos de cadastro por olho e o impostor mais semelhante do mesmo lado. O treino concluiu 12 épocas, com a época 11 selecionada. No monitor interno, preservou 479/480 acertos limpos; os Rank-1 superior/inferior com perda de 10% foram 84,17%/68,33%. As FMR caíram de 1,6111%/1,5000% na rodada anterior para 1,4861%/1,2917%, com pequena perda de identificação. O candidato continuou barrado antes da validação. Onze testes passaram; 33 arquivos foram restaurados com hashes conferidos. Ver [método, resultados e limites](ADAPTACAO_TOP3_POLAR_2026-10-23.md).


### Penalização absoluta de escores impostores — 23/10/2026

Foi testada uma referência fixa de similaridade calculada somente nas pessoas do ajuste, mantendo o limiar de avaliação limpo. O treino parou na época 8 e selecionou a época 4. No monitor interno, as FMR superior/inferior caíram de 1,4861%/1,2917% para 1,4167%/1,2778%, com Rank-1 de 83,54%/66,67% e perda de acertos/TAR frente ao piloto top3. O limpo permaneceu em 99,79%. O candidato continuou barrado antes da validação. O diagnóstico mostrou erros distribuídos entre dezenas de consultas. Quatorze testes passaram, e 38 arquivos foram restaurados com hashes conferidos. Ver [referência, resultados e diagnóstico](ADAPTACAO_FMR_POLAR_2026-10-23.md).


### Correções espaciais no último bloco do encoder — 23/10/2026

Foi concluído um piloto de oito épocas com 145.408 parâmetros de correção treináveis nas convoluções de layer4, mantendo kernels originais, prefixo, projeção e BatchNorm congelados. A época 6 preservou 479/480 acertos limpos no monitor interno e elevou o TAR superior/inferior, frente ao encoder sem adaptação, para 80,63%/60,21%. Os Rank-1 foram 83,13%/68,13%, com FMR de 1,5833%/1,3056%; o candidato continuou barrado antes da validação. Doze testes passaram; 33 arquivos foram restaurados com hashes conferidos. O cache FP32 de 1,59 GB pode ser reaproveitado. Ver [escopo do piloto, resultados e recuperação](ENCODER_ESPACIAL_2026-10-23.md).

### Retomada, calibração e transferência — 24/10/2026

Foi concluído e auditado um piloto de diversidade nativa de oclusões no ajuste: 3.222 simulações de 1% a 20% e cinco tons, com oito épocas e avaliação fixa de 10%. Preservou 99,79% limpos no monitor, mas não superou o controle direto: Rank-1 de 82,92%/65,63% e FMR de 1,4028%/1,2917%. Não avançou à validação. Pesos, escores e protocolos foram preservados e recuperados por hashes. Ver [hipótese, comparação e limites](DIVERSIDADE_OCLUSAO_2026-10-24.md).

A gravação no projeto voltou a funcionar após a liberação do Defender pelo usuário. O pacote pendente de 104 arquivos foi preservado em quatro partes e recuperado com hashes. O relatório de 24/10 registra as rodadas anteriores com calibração separada, coorte, fusão completa e normalização de fundo.

Uma nova calibração global, estimada somente nas condições simuladas internas, controlou a FMR do monitor em 0,0417%/0,0972%/0,2222% no limpo/superior/inferior de 10%. Não atingiu a meta conjunta: o TAR inferior foi 76,25%. Com todos os parâmetros de treino congelados, a validação limpa obteve Rank-1 de 90,46%, TAR de 64,32% e FMR de 0,2075%, reprovando a porta limpa. A troca isolada do polar mantendo exatamente os parâmetros do sistema principal também reprovou: Rank-1 de 89,83%, TAR de 90,25% e FMR de 1,0235%. Não foram abertas oclusões ou teste desses candidatos. Nenhuma variante substituiu a referência ou estabeleceu novo mínimo.

As três rodadas foram auditadas e preservadas em um pacote de 65 arquivos, com recuperação por hashes. Ver [relatório e limites](../Relatórios-de-Avanço/RELATORIO_AVANCO_2026-10-24.md), `restaurar_pendencias_2026-10-24.py` e `preservar_rodadas_2026-10-24.py`. Gravação local não comprova envio à nuvem.

### Ajuste dos kernels do último bloco — 23/10/2026

Foi concluído um piloto de oito épocas ajustando os cinco kernels originais de layer4, com 8.388.608 pesos treináveis e prefixo, projeção e BatchNorm congelados. A época 8 preservou 479/480 acertos limpos e elevou o Rank-1 superior/inferior sob perda de 10% de 82,50%/60,63% para 84,79%/71,25% no monitor de treino. A FMR de 1,6389%/1,3472% barrou o avanço à validação. O teste direcionado e a auditoria dos descritores/escores passaram. Ambos os checkpoints foram recuperados com hashes exatos de um pacote de 43 partes, sem quantização. Ver [método, ganhos, limites e recuperação](AJUSTE_BLOCO_POLAR_2026-10-23.md).

### Ponderação aprendida de regiões — 23/10/2026

O PyTorch voltou a carregar após a liberação dos arquivos pelo usuário, e teste CUDA, treinamento e auditoria executaram com sucesso. O novo pooling de atenção usa 16.449 parâmetros, com inicialização equivalente à média global e encoder/projeção congelados. A época 8 preservou 479/480 acertos limpos e obteve Rank-1 de 83,75%/61,46% sob perda superior/inferior de 10%, com FMR de 1,7083%/1,8056%; não avançou à validação. Dois testes passaram e a auditoria reproduziu os escores no cache. Foram preservados 28 arquivos em 12 partes, sem duplicar os mapas. Ver [método, limites e recuperação](ATENCAO_POLAR_2026-10-23.md).

### Comparação regional da textura — 23/10/2026

Foi executado um piloto registrado usando 32 descritores locais dos mapas polares congelados, com padronização em 4.955 fotos S1 das pessoas de ajuste. O primário retém as 24 maiores concordâncias de cada par, sem referência ou identidade para escolher regiões; o controle compara todas as 32. No monitor de treino, o primário obteve Rank-1 de 77,29% limpo e 54,38%/48,13% nas perdas superior/inferior de 10%, abaixo do polar global. O critério limpo falhou e o piloto não avançou à validação. Três testes passaram; a reconstrução do cache reproduziu escores, protótipos e decisões. Nenhuma nova fronteira foi aprovada. Ver [resultado, limites e recuperação](COMPARACAO_REGIONAL_2026-10-23.md).

### Diagnóstico dos limites de comparação — 23/10/2026

Os escores de quatro componentes polares foram reanalisados nas 480 consultas do monitor de treino, sem novas imagens ou treinamento. Mesmo o melhor limiar privilegiado por condição, usado somente como diagnóstico, limita o TAR espacial a 78,13%/58,13% sob perda superior/inferior de 10%, com FMR de até 1%. A seleção privilegiada entre as decisões top3/espacial também permanece abaixo de 90%; isso não é um limite para fusão de escores. Dois testes passaram. A próxima hipótese deve atuar na comparação da textura disponível, sem repetir ajustes globais ou recalibrar sobre o monitor ocluído. Ver [números, alcance e reprodução](DIAGNOSTICO_COMPARACAO_2026-10-23.md).

### Avaliação do Iris-SAM — 23/10/2026

O checkpoint público foi baixado e executado com adaptador próprio, sem alterar o repositório externo ou o ambiente principal. Em 32 pessoas da validação e 96 casos pareados, a U-Net atual obteve Dice limpo de 84,40%, contra 78,80% do Iris-SAM guiado por caixa automática da U-Net. Com perda superior/inferior de 10%, os Dice da área visível foram 81,29%/78,67% e 80,29%/77,49%, respectivamente. O candidato não passou ao critério registrado e não substituiu o segmentador. O modo sem prompt falhou, e caixas da anotação foram separadas como diagnóstico privilegiado. Três testes passaram; máscaras, caixas, métricas e bootstrap foram auditados e recuperados por hashes em um pacote de 22 arquivos, incluindo figura de casos fixos. Nenhuma nova identificação ou estimativa de área mínima foi realizada. Ver [estudo, resultados e recuperação da figura](IRIS_SAM_ESTUDO_2026-10-23.md).
