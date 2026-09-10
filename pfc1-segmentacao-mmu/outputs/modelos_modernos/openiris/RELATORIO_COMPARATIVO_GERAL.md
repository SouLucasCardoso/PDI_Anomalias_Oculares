# Comparação de segmentação no MMU

| Método | Dice | IoU | Aproveitamento | Pureza | Contaminação | Pupila preenchida | Índice útil |
|---|---:|---:|---:|---:|---:|---:|---:|
| CNN Small U-Net | 0.5247 | 0.3739 | 63.72% | 45.33% | 54.67% | 60.66% | 0.2064 |
| SAM 2.1 automático (zero-shot) | 0.5141 | 0.3764 | 55.33% | 48.61% | 51.39% | 47.20% | 0.2715 |
| OpenIRIS pré-treinado | 0.4944 | 0.3575 | 49.79% | 49.83% | 50.17% | 36.25% | 0.3152 |

## Advertência metodológica

O model card do OpenIRIS declara o MMU entre as bases usadas no treinamento. Não é possível garantir que as 70 imagens locais de teste sejam inéditas para o modelo. Portanto, o resultado OpenIRIS nesta base é uma verificação técnica e não deve ser apresentado como estimativa independente de generalização.

O SAM 2.1 automático foi executado zero-shot. O prompt que preserva melhor a abertura pupilar perde Dice e aproveitamento em relação à CNN, mas melhora pureza, contaminação e preenchimento da pupila. Não há superioridade absoluta.

Aproveitamento corresponde à revocação da máscara. Ele deve sempre ser apresentado junto de pureza, contaminação e preenchimento da pupila.
O índice útil é `Dice × (1 − preenchimento da pupila)` e foi usado somente para selecionar limiar e composição na validação.

Fontes: [SAM 2](https://github.com/facebookresearch/sam2) e [OpenIRIS model card](https://github.com/worldcoin/open-iris/blob/main/SEMSEG_MODEL_CARD.md).
