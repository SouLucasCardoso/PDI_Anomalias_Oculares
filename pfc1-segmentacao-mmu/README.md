# PFC I — prova de conceito de segmentação da íris

Este pacote treina uma U-Net pequena para segmentar a região visível da íris nas
imagens do **MMU Iris Database**, usando 450 máscaras manuais disponibilizadas
em um repositório público associado ao trabalho de Ganeeva e Myasnikov (2022).
É uma validação inicial da etapa de segmentação; **não é ainda o
experimento clínico final**, pois o MMU não possui rótulos de olhos saudáveis e
afetados por doenças.

## O que o experimento já demonstra

- aquisição e pareamento automático de 450 imagens e 450 máscaras;
- correção da diferença de numeração entre as cópias dos dois conjuntos;
- divisão por pessoa: 32 para treino, 6 para validação e 7 para teste;
- treinamento de uma U-Net com perda `BCE + Dice`;
- avaliação por Dice e IoU;
- geração de curvas, exemplos visuais, manifesto da divisão e pesos do modelo.

## Como executar

Requer Python 3.10 ou superior. Em uma pasta vazia, crie um ambiente virtual e
instale as dependências:

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python treinar_segmentacao_mmu.py --epochs 20
```

O programa baixa os dados públicos automaticamente. Para uma execução muito
rápida antes da reunião:

```bash
python treinar_segmentacao_mmu.py --epochs 5 --base-channels 8
```

Com GPU NVIDIA e uma instalação do PyTorch compatível com CUDA, o dispositivo é
detectado automaticamente. Os resultados ficam em `outputs/baseline/`.

## Arquivos gerados

- `metricas.json`: Dice, IoU, perda e configuração da execução;
- `historico.csv`: métricas de cada época;
- `curvas_treinamento.png`: evolução de perda e Dice;
- `exemplos_teste.png`: imagem, máscara real, probabilidade e máscara prevista;
- `manifesto.json`: sujeitos e arquivos de cada partição;
- `melhor_modelo.pt`: pesos da melhor época de validação.

## Cuidados metodológicos

1. Não apresentar este resultado como detecção de alterações oculares. Ele mede
   apenas a capacidade de segmentar a íris em um conjunto biométrico saudável.
2. Não misturar imagens da mesma pessoa entre treino e teste. O script já evita
   esse vazamento.
3. O repositório das máscaras é público e foi atualizado em 2022, mas não contém
   uma licença explícita; a cópia das imagens no Kaggle informa licença
   `Unknown`. Antes de incorporar os resultados à publicação final, deve-se
   solicitar autorização aos responsáveis ou trocar por uma base com licença
   clara.
4. A etapa final ainda depende de uma base clínica com rótulos de condição
   ocular, como a Warsaw-BioBase-Disease-Iris, para comparar classificação com e
   sem segmentação.

## Fontes dos dados

- Imagens: https://www.kaggle.com/datasets/naureenmohammad/mmu-iris-dataset
- Máscaras: https://github.com/jkozlova/Masks-for-MMU-Iris-dataset
- Artigo associado às máscaras: https://doi.org/10.1007/978-3-031-16500-9_15
