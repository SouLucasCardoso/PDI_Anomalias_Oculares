# PFC I — prova de conceito de segmentação da íris

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
