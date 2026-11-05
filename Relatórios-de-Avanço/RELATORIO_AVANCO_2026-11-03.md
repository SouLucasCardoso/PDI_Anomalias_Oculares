# Relatório de avanço — 3 de novembro de 2026

**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Dia:** terça-feira  
**Registro retrospectivo:** elaborado em 05/11/2026 a partir dos protocolos, fontes e resultados preservados. Resultados encerrados posteriormente são identificados como tal.

## Objetivo do dia

Melhorar a transferência da segmentação para variações de captura e preparar uma avaliação de reconhecimento que preserve o objetivo científico: estimar a menor fração observada de íris visível sob controle de falsas correspondências, sem confundir Dice com identificação.

## Desenvolvimento realizado

- Preparação de um ambiente separado para a revisão oficial recente da família SAM 3, respeitando a compatibilidade Windows/CUDA/GPU e preservando a proveniência das rodadas anteriores.
- Verificação do código SAM 3 `f1647e8d0c1d280991f4d1b7d974c2704537fe66` e do checkpoint SAM3.1 na revisão `daa63191845a41281374e725f4c9e51c7a824460`. O checkpoint base possui SHA-256 `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`.
- Ensaios de prompts em casos clínicos fixos, comparando texto e caixas automáticas. As falhas visuais foram mantidas; o SAM textual não foi promovido a reconhecedor ou medidor anatômico.
- Implementação do extrator visual SAM3.1 congelado e do decodificador supervisionado RGB+SAM, com variações sintéticas de escala, obliquidade e óculos. A rodada foi registrada às 19h05, horário de Brasília, com seleção baseada em segmentação.
- Preparação do editor de revisão humana de máscaras clínicas. O usuário assumiu a primeira revisão; isso não equivale a validação por especialista.
- Implementação do fluxo persistente de treino, avaliação de identidade, critérios de prontidão, relatórios de acompanhamento e sensibilidade ao denominador de área. Revisão clínica e avaliação UBIPr permaneceram separadas.
- Verificação de compatibilidade em CPU dos nove componentes de identidade entre os ambientes: entradas e saídas coincidiram exatamente nas duas fotos utilizadas. Essa checagem não demonstra equivalência completa em GPU nem nova acurácia.

## Evidências e decisões

A rodada diversa anterior foi examinada como motivação para o SAM3.1. Embora melhorasse algumas condições de captura, seu candidato não sustentou os critérios de reconhecimento limpo e não substituiu a referência. Os protocolos exigem manter falhas no denominador e não atribuir novo mínimo quando o candidato já reprova sem perda artificial de área.

As versões registradas no novo ambiente incluem PyTorch 2.14.1+cu130, torchvision 0.29.1+cu130 e NumPy 1.26.4. A preferência por versões recentes foi condicionada à compatibilidade concreta; não se atualizou uma rodada ativa no meio da execução.

O treinamento SAM3.1 iniciado neste dia terminou em **04/11**, com 20 épocas e seleção da época 15. Os resultados finais pertencem ao relatório do dia seguinte, não constituem uma entrega concluída em 03/11.

## Limitações e continuidade

Óculos e vistas oblíquas são transformações sintéticas, não populações clínicas. Não foi estabelecido percentual anatômico mínimo nem efeito causal de anomalias. O próximo passo foi concluir o treinamento, auditar a seleção e medir identificação com os reconhecedores e limiar congelados.

## Registros técnicos

- [Tecnologias e compatibilidade](../pfc1-segmentacao-mmu/TECNOLOGIAS_ATUAIS_2026-11-03.md).
- [Preparação para anomalias e critérios](../pfc1-segmentacao-mmu/PRONTIDAO_ANOMALIAS_2026-11-03.md).
- [Protocolo do treino iniciado](../pfc1-segmentacao-mmu/outputs/sam31_iris_adaptacao_2026-11-03/protocolo.json).
- [Extrator visual e decodificador](../pfc1-segmentacao-mmu/segmentador_sam3_iris.py).
- [Editor de referências](../pfc1-segmentacao-mmu/revisar_mascaras_clinicas.py).

Os arquivos de acompanhamento vinculados podem ter recebido atualizações posteriores. A data da rodada identifica sua abertura, não a conclusão de todas as etapas.
