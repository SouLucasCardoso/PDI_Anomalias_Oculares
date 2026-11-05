# Proposta de texto para incorporar após revisão

Este arquivo é uma proposta bibliográfica. Não substitui o manuscrito em produção, seus resultados ou protocolos. As chaves abaixo estão em [referencias.bib](referencias.bib).

## Contextualização sugerida

A quantidade de informação de íris necessária para reconhecimento depende da captura, da região disponível e do processo de comparação. Requisitos normativos de qualidade de amostra não devem ser interpretados como garantias universais de identificação. A ISO/IEC 29794-6:2015 inclui um limiar de área utilizável, enquanto a avaliação de desempenho exige um protocolo e medidas de erro próprios [iso29794_6_2015; iso19795_1_2021]. Estudos de íris parcial e estabilidade de códigos também mostram que regiões distintas não fornecem necessariamente a mesma informação discriminante [du2005; hollingsworth2009bits; daugman2007].

A influência de alterações oculares já foi investigada em estudos clínicos e computacionais. As conclusões variam com diagnóstico, procedimento, equipamento e condição de aquisição [aslam2009; dhir2010; seyeddain2014; trokielewicz2017; nigam2019]. A presença desse corpo de evidência afasta uma justificativa de ausência de estudos sobre patologias. A lacuna que este trabalho pretende examinar deve ser delimitada por suas condições experimentais, sem transformar uma curva de oclusão em estimativa causal de comprometimento por doença.

## Objetivo delimitado sugerido

Este trabalho objetiva estimar a menor fração do suporte de íris visível originalmente anotado que mantém critérios pré-especificados de desempenho biométrico sob oclusões controladas, preservando falhas no denominador. Como extensão exploratória, examina limitações de transferência do processamento para olhos com alterações oculares. O resultado é condicionado ao sistema, ao conjunto de imagens, à galeria, ao limiar e às intervenções avaliadas.

## Distinção de medidas para a seção de método

Define-se a fração preservada como a razão entre os pixels de referência mantidos após a intervenção e os pixels de íris visível anotados na imagem original. Ela não equivale automaticamente à fração desobstruída de um anel de íris estimado, nem à área em comum entre duas imagens. Os percentuais das curvas devem ser identificados pelo denominador usado. Referências vazias não recebem uma fração de área, embora seus casos permaneçam na avaliação operacional.

## Discussão sugerida

O desempenho da segmentação deve ser interpretado junto com o resultado do reconhecimento. A relação não é monotônica para todas as combinações de base, algoritmo e parametrização [hofbauer2016; hofbauer2019]. Melhorias em métricas de máscara não demonstram, isoladamente, redução do erro biométrico. A literatura recente de área visível fornece um antecedente direto para contextualizar a análise [pessaud2026]; a contribuição deste estudo precisa ser explicitada em relação a esse trabalho, respeitando diferenças de medida e protocolo.

## Alegações a evitar

- “Abaixo de 70% é impossível identificar uma pessoa.”
- “70% de qualquer parte da íris garantem identificação.”
- “Remover 30% sinteticamente demonstra o efeito de uma patologia que afeta 30% da íris.”
- “Não existem estudos sobre reconhecimento de íris em olhos doentes.”
- “Um aumento de Dice comprova o percentual mínimo necessário para reconhecer alguém.”
- “O resultado em uma galeria pequena estabelece um limite biológico aplicável à população.”

## Conferências editoriais antes da incorporação

Usar o ano do fascículo quando houver diferença em relação à data online: Dhir et al. 2010; Seyeddain et al. 2014; Trokielewicz et al. 2017. A postagem arXiv em 2018 deste último não é seu ano de publicação no periódico. A referência de Pessaud et al. 2026 reúne a versão publicada e o preprint relacionado de 2025, sem duplicá-los como evidências independentes. Os percentuais do artigo de Kumar et al. 2025 precisam ser tratados com ressalva devido às inconsistências do próprio relato.
