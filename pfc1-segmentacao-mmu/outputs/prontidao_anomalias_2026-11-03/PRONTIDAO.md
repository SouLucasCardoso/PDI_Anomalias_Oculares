# Prontidão para o piloto com anomalias

**Metas de engenharia propostas para este projeto. Não são um padrão clínico validado.**

Primeiras revisões de olhos normais: **2/30**, de 2 pessoas.

| Verificação | Meta | Situação |
|---|---|---|
| Validação de segmentação | Dice macro ≥90% nas quatro condições,1.652 imagens cada | Pendente ou não atingida |
| Controles clínicos normais | 30 referências humanas; Dice≥90%; sem falhas graves; vazamento na pupila≤2% | Pendente ou não atingida |
| Identificação do mesmo candidato | Rank1/TAR/acerto aceito≥90%,FMR≤1% | Pendente ou não atingida |

**Piloto de segmentação com anomalias: ainda não liberado pelos critérios**.

A primeira revisão do usuário deve ser distinguida de validação anatômica por especialista. As seis imagens com diagnóstico envolvendo íris pertencem a cinco pessoas e permitem um piloto exploratório, sem conclusão populacional ou causal sobre identificação. Óculos e poses sintéticos não comprovam cobertura de óculos e poses clínicas reais.

[Abrir o editor local de revisão](http://127.0.0.1:8766/). Os rascunhos não entram como referências.

O percentual mínimo de área exige a avaliação biométrica e a curva de oclusão do mesmo candidato. Não é atribuído por aparência, Dice ou número de épocas.