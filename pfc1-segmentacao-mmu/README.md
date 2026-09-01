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
  --output-dir outputs/pareamento_corrigido_50ep
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

## Arquivos gerados

- `metricas.json`: configuração, auditoria do pareamento e métricas agregadas;
- `metricas_por_imagem.csv` e `resumo_detalhado.json`: dispersão, piores casos,
  resultados por pessoa e análise secundária de qualidade;
- `historico.csv` e `curvas_treinamento.png`: evolução por época;
- `exemplos_teste.png`: referência, probabilidade, previsão e recorte aplicado;
- `manifesto.json`: correspondências e partições por pessoa;
- `melhor_modelo.pt`: estado escolhido exclusivamente pela validação.

## Datasets e próximos experimentos

O levantamento com a estratégia de aquisição está em
[DATASETS_RECOMENDADOS.md](DATASETS_RECOMENDADOS.md). As prioridades são:

1. MOBIUS e UBIPr para treinar um segmentador em RGB com máscaras mais completas;
2. Warsaw-BioBase-Disease-Iris para a comparação clínica com e sem recorte;
3. o segmentador aberto da Notre Dame como baseline externo congelado.

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
