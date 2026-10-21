# Reconhecedor polar e aproximação elíptica — 20/10/2026

## 1. Trabalho concluído

Foram baixados e verificados 12 arquivos de fontes oficiais do CVRL TripletIris e dois pesos públicos, somando aproximadamente 162,5 MB. Foi instalado um novo reconhecedor polar ConvNeXt-tiny de 2.048 dimensões, com o regressor de círculos 1543 previsto pelos autores. Não foi alterado o ambiente de dependências nem retreinado esse reconhecedor.

O piloto verificou o pipeline e a comparação euclidiana contra o código original em 16 pares, com erro máximo de similaridade de aproximadamente 1,4 × 10⁻¹⁶. Depois foram executadas nove variantes completas com limites circulares e seis com aproximação elíptica. Cada variante inclui 482 consultas de 16 pessoas e 32 olhos, com até 480 capturas de cadastro da sessão 1. Nenhum novo escore de teste ou oclusão foi produzido.

## 2. Todos os resultados de validação

| Variante | Rank-1 | TAR | FMR | Falhas de consulta |
|---|---:|---:|---:|---:|
| full_author_first | 26,76% | 11,41% | 1,00% | 0 |
| full_author_max | 37,55% | 12,45% | 1,00% | 0 |
| full_author_top3 | 41,49% | 11,62% | 1,00% | 0 |
| roi_reference_first | 25,93% | 13,90% | 0,94% | 10 |
| roi_reference_max | 30,50% | 10,79% | 0,98% | 10 |
| roi_reference_top3 | 37,55% | 12,66% | 0,98% | 10 |
| roi_automatic_first | 29,88% | 13,69% | 0,99% | 4 |
| roi_automatic_max | 31,74% | 11,00% | 0,99% | 4 |
| roi_automatic_top3 | 38,59% | 12,86% | 0,99% | 4 |
| roi_reference_ellipse_first | 14,52% | 5,19% | 0,94% | 10 |
| roi_reference_ellipse_max | 24,27% | 7,68% | 0,98% | 10 |
| roi_reference_ellipse_top3 | 27,39% | 8,09% | 0,98% | 10 |
| roi_automatic_ellipse_first | 17,84% | 8,09% | 0,99% | 4 |
| roi_automatic_ellipse_max | 21,37% | 6,64% | 0,99% | 4 |
| roi_automatic_ellipse_top3 | 28,42% | 9,54% | 0,99% | 4 |

As regras first, max e top3 representam foto única, maior similaridade e média das três melhores similaridades. Cada variante tem limiar recalibrado para FMR empírica de até 1% na própria validação. Full_author segue o canal vermelho e a conversão de imagem do demonstrador; ROI localiza o recorte pela referência ou U-Net. As máscaras não removem a textura externa da faixa polar.

## 3. Decisão e interpretação

O maior Rank-1 TripletIris foi **41,49%**, com **11,62% de TAR**, na imagem inteira com cadastro top-3. A maior TAR entre as variantes foi **13,90%**, com **25,93% de Rank-1**, no recorte de referência com uma foto. Não combinar esses máximos de variantes diferentes como se fossem um único resultado.

No recorte automático top-3, o TripletIris circular obteve **38,59% de Rank-1 e 12,86% de TAR**. Com a aproximação elíptica, obteve **28,42% e 9,54%**. A hipótese geométrica não melhorou o reconhecimento nesta configuração. Os intervalos pareados dessas diferenças estão registrados separadamente.

O encoder anterior com máscaras automáticas top-3 havia obtido 67,01% de Rank-1 e 59,34% de TAR no controle multicaptura. Seu modelo continua preservado. O novo reconhecedor e a aproximação elíptica **não foram adotados como substitutos**. Isso é uma comparação de sistemas completos: modelo, pré-treinamento, canal, normalização e amostragem mudam, portanto não se isola uma única causa. Não se pode concluir que todo reconhecedor específico de íris ou toda normalização polar seja inferior.

A inspeção visual mostrou melhor acompanhamento do contorno segmentado em alguns exemplos com elipses, mas esses contornos incluem os limites da região visível, e não necessariamente as bordas anatômicas ocultas. Há fallback para pupila regredida quando a máscara não tem um orifício interno válido. O amostrador elíptico também difere do código circular oficial. Melhor aparência de um recorte não substitui a avaliação de identidade.

Não foi estabelecida independência entre as populações de pré-treinamento dos pesos públicos e o UBIPr. A validação já foi usada repetidamente no desenvolvimento local. As estimativas orientam investigação; não confirmam generalização independente nem estabelecem causa clínica.

## 4. Área mínima e direção técnica

Nenhuma variante atingiu simultaneamente 90% de Rank-1 e TAR. O mínimo global segue **não determinado**. A normalização ou o encaixe da máscara não fornecem, isoladamente, um percentual anatômico suficiente. Não foi recalculada a curva de oclusão com um reconhecedor ainda abaixo do critério original.

Esta rodada não sustenta substituir o encoder nem prolongar uma busca por variantes na mesma validação como se cada escolha fosse confirmação nova. Um próximo experimento precisa de hipótese de domínio e representação própria, como treinamento em uma faixa polar adequada às capturas visíveis, com protocolo e avaliação independente definidos antes da confirmação. A coleta de mais níveis de oclusão, por si só, não resolve o desempenho original.

## 5. Verificação e artefatos

Os 32 testes automatizados passaram. Os três novos testes geométricos verificam ângulos, anel sintético com pupila, fallback e máscara vazia. Fontes, pesos, protocolos, escores e imagens foram preservados. Exemplos visuais são os dois primeiros cadastros de cada variante, sem seleção por escore; não equivalem a auditoria manual completa de todas as capturas.

- [Protocolo e reprodução](../../PROTOCOLO_RECONHECEDOR_POLAR_2026-10-20.md).
- [Resultados circulares](../tripletiris_validacao_2026-10-20/CONCLUIDO.json).
- [Resultados elípticos](CONCLUIDO.json).
- [Tabela completa](resumo_completo.csv).
- [Comparações pareadas e auditoria geométrica](comparacoes_pareadas.json).

![Limites aproximados e faixas polares — exemplos reais](qa_polar_tripletiris.png)

Fonte do modelo: [CVRL OpenSourceIrisRecognition](https://github.com/CVRL/OpenSourceIrisRecognition), revisão fixada no protocolo.
