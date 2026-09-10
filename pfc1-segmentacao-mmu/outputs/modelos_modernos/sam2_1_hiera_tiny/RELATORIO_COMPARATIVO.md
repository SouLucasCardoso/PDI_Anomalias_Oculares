# Benchmark inicial: CNN e SAM 2.1 Hiera Tiny

## Resultado no teste MMU

| Método | Dice | IoU | Aproveitamento | Pureza | Contaminação | Pupila preenchida | Índice útil |
|---|---:|---:|---:|---:|---:|---:|---:|
| CNN Small U-Net | 0.5247 | 0.3739 | 63.72% | 45.33% | 54.67% | 60.66% | 0.2064 |
| SAM 2.1 automático | 0.5141 | 0.3764 | 55.33% | 48.61% | 51.39% | 47.20% | 0.2715 |
| SAM 2.1 caixa real (assistido) | 0.6123 | 0.4598 | 63.62% | 59.68% | 40.32% | 53.09% | 0.2872 |

Aproveitamento é a revocação da máscara: porcentagem da íris de referência preservada. Deve ser interpretado junto com pureza e contaminação.
O índice útil é `Dice × (1 − preenchimento da pupila)` e serve apenas para selecionar, na validação, máscaras que preservam a abertura pupilar.

## Protocolo

- `automatic`: centro estimado exclusivamente pela imagem e geometria global calibrada na validação; é o resultado utilizável como pipeline.
- `oracle_bbox`: caixa delimitadora obtida da máscara real; é um limite superior assistido e não constitui segmentação autônoma.
- A variante de prompt foi escolhida pelo índice útil de validação. O conjunto de teste não foi usado para calibrar geometria ou escolher prompt.
- Para cada prompt, a máscara foi escolhida pela qualidade prevista pelo próprio SAM.

## Interpretação

O SAM 2.1 é um modelo de segmentação geral e foi avaliado sem fine-tuning em íris. Dice e aproveitamento precisam ser interpretados junto do preenchimento da pupila: encontrar o disco ocular não garante preservar o anel útil. O próximo experimento deve ajustar o modelo ao domínio ou usar um segmentador multiclasse.

Referências: [SAM 2 oficial](https://github.com/facebookresearch/sam2) e [checkpoint oficial](https://huggingface.co/facebook/sam2.1-hiera-tiny).
