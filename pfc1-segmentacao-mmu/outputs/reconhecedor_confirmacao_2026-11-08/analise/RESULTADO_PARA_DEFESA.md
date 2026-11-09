# Resultado para a defesa — melhoria do reconhecedor

O contorno contínuo foi aplicado somente aos descritores polares; os quatro descritores RGB mantiveram a entrada anterior. A escolha ocorreu na validação, antes da nova inferência. O ajuste supervisionado de cinco épocas não passou pela regra registrada e manteve a época zero.

| Perda | Posição | Versão | Rank-1 | TAR | FMR | Correto e aceito |
|---:|---|---|---:|---:|---:|---:|
| 0% | original | baseline | 91.15% | 92.39% | 0.864% | 89.51% |
| 0% | original | candidate | 91.15% | 92.80% | 0.837% | 89.92% |
| 1% | oclusao_superior | baseline | 89.92% | 92.18% | 0.878% | 88.48% |
| 1% | oclusao_superior | candidate | 91.15% | 92.59% | 0.796% | 89.71% |
| 1% | oclusao_inferior | baseline | 90.95% | 91.15% | 0.892% | 88.89% |
| 1% | oclusao_inferior | candidate | 90.53% | 91.36% | 0.933% | 88.89% |
| 5% | oclusao_superior | baseline | 87.86% | 88.89% | 1.303% | 85.60% |
| 5% | oclusao_superior | candidate | 87.04% | 89.09% | 1.139% | 85.39% |
| 5% | oclusao_inferior | baseline | 74.07% | 77.78% | 1.879% | 71.40% |
| 5% | oclusao_inferior | candidate | 75.10% | 77.57% | 1.866% | 71.60% |
| 10% | oclusao_superior | baseline | 82.30% | 84.57% | 1.674% | 80.25% |
| 10% | oclusao_superior | candidate | 83.13% | 84.98% | 1.564% | 80.45% |
| 10% | oclusao_inferior | baseline | 58.23% | 60.91% | 2.565% | 55.56% |
| 10% | oclusao_inferior | candidate | 59.47% | 59.88% | 2.565% | 55.14% |
| 20% | oclusao_superior | baseline | 69.96% | 72.63% | 2.154% | 67.90% |
| 20% | oclusao_superior | candidate | 69.55% | 72.02% | 2.085% | 67.28% |
| 20% | oclusao_inferior | baseline | 40.74% | 40.33% | 3.224% | 37.24% |
| 20% | oclusao_inferior | candidate | 40.95% | 41.15% | 3.278% | 38.07% |
| 30% | oclusao_superior | baseline | 69.96% | 69.96% | 2.099% | 66.46% |
| 30% | oclusao_superior | candidate | 68.93% | 70.58% | 2.222% | 67.08% |
| 30% | oclusao_inferior | baseline | 33.54% | 32.30% | 3.471% | 29.63% |
| 30% | oclusao_inferior | candidate | 32.92% | 32.10% | 3.635% | 29.22% |
| 31% | oclusao_superior | baseline | 69.34% | 70.99% | 2.016% | 66.26% |
| 31% | oclusao_superior | candidate | 70.37% | 71.19% | 2.044% | 67.49% |
| 31% | oclusao_inferior | baseline | 32.51% | 29.42% | 3.525% | 27.57% |
| 31% | oclusao_inferior | candidate | 30.25% | 30.45% | 3.690% | 27.57% |

## Alcance do resultado

Regra completa de comparação aprovada: **não**. Essa regra exigia preservar o controle limpo, melhorar a média conjunta e não aumentar a FMR em nenhuma condição. Melhoras pontuais não equivalem à superioridade geral.

Critérios marginais por ponto: Rank-1≥90%,TAR≥90%,FMR≤1%. Na grade registrada:
- baseline/oclusao_superior: menor suporte nominal no prefixo aprovado = 100%; perdas aprovadas no prefixo = [0].
- baseline/oclusao_inferior: menor suporte nominal no prefixo aprovado = 99%; perdas aprovadas no prefixo = [0, 1].
- candidate/oclusao_superior: menor suporte nominal no prefixo aprovado = 99%; perdas aprovadas no prefixo = [0, 1].
- candidate/oclusao_inferior: menor suporte nominal no prefixo aprovado = 99%; perdas aprovadas no prefixo = [0, 1].

O percentual é condicionado à grade, reconhecedor, limiar, galeria e suporte originalmente anotado. O critério conjunto correto-e-aceito≥90% é diferente e está auditado separadamente. As486consultas incluem6referências de área vazia, mantidas no denominador primário; a coorte fixa de480casos com área definida também foi recontada, sem selecionar acertos. Nenhum desses percentuais é mínimo universal, medida de doença ou conformidade ISO.

A coluna de ganho pareado e os intervalos descritivos por pessoa estão em AUDITORIA_FINAL.json. Há seleção na validação e exposição prévia ao teste; não se trata de confirmação independente. Nenhum checkpoint do aplicativo ou resultado anterior foi substituído.
