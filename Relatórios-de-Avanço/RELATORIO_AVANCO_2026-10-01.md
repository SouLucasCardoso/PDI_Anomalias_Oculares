# Relatório de avanço — perda de reconhecimento no UBIPr e alternativas à Warsaw

**Data:** 1º de outubro de 2026  
**Projeto:** Influência da segmentação da íris no desempenho de redes neurais convolucionais para a classificação de alterações oculares  
**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva

## 1. Objetivo e situação da etapa

Diante da indisponibilidade da Warsaw-BioBase-Disease-Iris, foi realizado um levantamento de alternativas para iniciar estudos com olhos clinicamente alterados e definir como quantificar a interferência dessas condições no reconhecimento biométrico.

O trabalho começou com pesquisa bibliográfica e definição de protocolo e avançou, nesta atualização, para a execução completa de um ensaio de reconhecimento no UBIPr. Foram medidas alterações de qualidade nas imagens originais e perdas sob perturbações controladas. Não houve novo treinamento nem aquisição de base clínica. Agora há medidas próprias de perda de reconhecimento sob alterações visuais, embora ainda não haja uma estimativa clínica por doença.

Há uma distinção de escopo a explicitar na redação: o título atual aborda classificação de alterações oculares, enquanto a pergunta desta etapa trata de reconhecimento de identidade sob alterações. São tarefas relacionadas, mas distintas. O título e o objetivo formal não foram alterados; o enquadramento da avaliação biométrica como objetivo complementar ou principal deverá ser alinhado na orientação.

### Resultado para apresentação ao orientador

Foi executado um teste completo com **486 consultas, 32 identidades oculares e 16 pessoas de teste**, além de validação com outras 16 pessoas. Foram avaliadas **13 condições em três entradas**, totalizando **39 combinações e 18.954 decisões de identificação**. A galeria usa 474 imagens de outra sessão. Não foi utilizado limite de desenvolvimento ou uma subamostra para acelerar a execução.

A linha de base do reconhecimento **com recorte da U-Net** foi de **20,16% de Rank-1**. Os níveis mais intensos predefinidos produziram:

| Alteração na íris anotada | Rank-1 após alteração | Perda absoluta | IC 95% da perda |
|---|---:|---:|---|
| Oclusão superior de 60% da área | 4,73% | 15,43 pp | 10,62 a 20,33 pp |
| Oclusão inferior de 60% da área | 3,29% | 16,87 pp | 11,88 a 21,54 pp |
| Desfoque com sigma de 5% da largura | 6,58% | 13,58 pp | 6,46 a 19,79 pp |
| Mistura com cinza em 75% (redução de contraste) | 3,70% | 16,46 pp | 11,25 a 21,60 pp |

Na imagem inteira, a linha de base foi **46,50%**. A oclusão superior de 60% reduziu o Rank-1 para **38,27%**, queda de **8,23 pp**, com IC 95% de **3,09 a 12,96 pp**. O contexto periocular preservado é uma possível explicação para a menor sensibilidade; isso não comprova robustez da textura da íris isolada.

Nas **imagens originais**, o reconhecimento com recorte da U-Net foi de **4,95%** no grupo de baixa nitidez e **28,97%** no de alta nitidez. Para controlar diferenças entre identidades, uma análise adicional comparou capturas do **mesmo olho**, exigindo ao menos duas consultas em cada extremo: em 23 olhos de 12 pessoas, a diferença média alta − baixa nitidez foi **19,44 pp**, IC 95% **13,73 a 26,03 pp**. É uma associação com qualidade de captura, ainda sujeita a outros fatores, não uma estimativa causal de doença.

**Material para apresentar:** [HTML com gráficos e exemplos](../pfc1-segmentacao-mmu/outputs/robustez_reconhecimento_2026-10-01/APRESENTACAO_RESULTADOS.html). **Detalhamento:** [relatório experimental completo](../pfc1-segmentacao-mmu/outputs/robustez_reconhecimento_2026-10-01/RELATORIO_RESULTADOS.md) e [tabela de todas as condições](../pfc1-segmentacao-mmu/outputs/robustez_reconhecimento_2026-10-01/resumo.csv).

![Perda de identificação e intervalos](../pfc1-segmentacao-mmu/outputs/robustez_reconhecimento_2026-10-01/perda_rank1_ic95.png)

### Controles do ensaio executado

- Pessoa + lado do olho como identidade, com pessoas distintas entre treino, validação e teste. A galeria anterior agrupava lados por pessoa; por isso os 74,28% antigos não são diretamente comparáveis ao Rank-1 ocular atual.
- DINOv3 ViT-L/16 e U-Net congelados. Mesmas consultas e galeria em todas as condições; máscara manual fixa como controle e U-Net executada novamente após cada alteração.
- Perturbações restritas à íris anotada; nenhum pixel periocular é alterado diretamente. Oclusão por cinza 128 em 20/40/60%; desfoque em 1/3/5% da largura; mistura com cinza em 25/50/75%. Não são simulações validadas de doenças.
- Limiar de verificação definido apenas na validação original, com FAR empírica ≤ 1%. O relatório registra FAR efetiva no teste, TAR, EER e falhas. Na imagem inteira, a oclusão superior de 60% também reduziu a TAR de 25,51% para 2,67% no limiar fixo.
- ICs pontuais por 5.000 reamostragens de pessoas, com galeria fixa. Não foi feita correção simultânea por múltiplas condições.
- Seis consultas com referência manual vazia permanecem no resultado operacional. Uma análise complementar usa as mesmas 480 consultas com referência válida em todas as condições, sem remover falhas induzidas pela perturbação.
- Auditoria sem duplicatas exatas por SHA-256; não equivale a auditoria de quase-duplicatas. Cinco testes automatizados foram aprovados. Escores, decisões individuais, hashes, versões e condições foram preservados para reprodução.

O UBIPr foi escolhido para esta execução por oferecer as máscaras e duas sessões necessárias à comparação pareada. O MMU não foi misturado ao resultado: exigiria um protocolo próprio de galeria/consulta e controle das diferenças de aquisição. Os recortes ainda têm desempenho inicial baixo com o extrator genérico; as perdas demonstram limitações deste pipeline e não um limite universal da biometria de íris.

## 2. O que os dados disponíveis permitem testar

| Material disponível no projeto | Avaliação viável | Limitação para a pergunta clínica |
|---|---|---|
| MMU e máscaras usadas na prova de conceito | Segmentação e preparação de um protocolo biométrico com identidade ocular auditada | A cópia utilizada não fornece rótulos clínicos que sustentem comparação por doença. Ausência de rótulo não comprova saúde ocular. |
| UBIPr segmentado | Segmentação multiclasse e reconhecimento de identidade entre sessões | Não há rótulos clínicos disponíveis no projeto; não é possível separar doença, gravidade e controles clínicos. |
| UBIPr com faixas pretas artificiais, ensaio de 24/09 | Sensibilidade do segmentador à perturbação definida | A faixa não reproduz uma doença; altera também contexto e distribuição visual. Esse ensaio antigo não mede perda de identificação; o novo ensaio pareado descrito acima mede. |
| Checkpoints U-Net, SAM e DINOv3 | Inferência e comparação de métodos nas tarefas apropriadas | Modelos disponíveis não substituem uma base com condição clínica, identidade e capturas repetidas. |

Os problemas anteriores de pareamento das máscaras do MMU e os casos inconsistentes/vazios do UBIPr reforçam a necessidade de auditar as anotações antes de interpretar falhas como efeitos anatômicos. A situação das cópias locais e dos resultados é documentada no README e no relatório de 24/09; não foi feita nova auditoria imagem a imagem nesta etapa.

## 3. Resultados anteriores e limites de interpretação

O relatório de 24/09 registra 11.018 pares no UBIPr e divisão por pessoa: 7.716 imagens de treino, 1.652 de validação e 1.650 de teste. A U-Net obteve Dice médio por imagem de 0,9171 no teste. Isso descreve concordância de máscaras, não probabilidade de reconhecer uma pessoa.

As métricas de reconhecimento abaixo foram conferidas em `pfc1-segmentacao-mmu/outputs/modelos_modernos/dinov3_vitl16_ubipr/metricas.json`. O teste utilizou 16 pessoas elegíveis entre sessões e 486 consultas, com galeria na sessão 1 e consultas na sessão 2.

| Entrada do DINOv3 | Top-1 | EER |
|---|---:|---:|
| Imagem inteira | 74,28% | 14,41% |
| Recorte com referência manual | 26,54% | 41,36% |
| Recorte com máscara U-Net | 33,33% | 38,72% |

O melhor resultado com imagem inteira é compatível com uso de informação periocular. A queda com recorte manual mostra que a representação atual não pode ser apresentada como um reconhecedor validado exclusivamente para a textura da íris. Também não demonstra que segmentar seja prejudicial em qualquer sistema: recorte, contexto, normalização e adequação do extrator precisam ser controlados.

O código anterior, `avaliar_dinov3_ubipr.py`, agrega a galeria por `sample.subject`. O novo ensaio em `avaliar_robustez_reconhecimento.py` usa pessoa + lado e mantém a separação das partições por pessoa. Os resultados históricos acima são preservados como referência do protocolo antigo.

Os limiares de FAR foram selecionados na validação. A nomenclatura TAR @ FAR-alvo não garante que a FAR observada no teste tenha exatamente o valor nominal. O novo ensaio já salva essa taxa efetiva e intervalos de confiança para as perdas. As 486 consultas não representam 486 indivíduos independentes; as 16 pessoas (32 olhos no protocolo novo) limitam a generalização.

Na oclusão artificial, o relatório anterior registra queda de aprovação da segmentação de 96,22% sem perturbação para 58,25% no primeiro nível, cuja cobertura real média foi 1,92%. Esse achado é específico de faixas pretas e do critério Dice visível ≥ 0,70. Não significa que 1,92% de alteração natural impeça identificação, nem estabelece um limiar clínico de comprometimento da íris.

## 4. Evidência acadêmica e alternativas

Nigam et al. (2019) relatam desempenho de autenticação de 93,42% no pré/pré-operatório e 74,69% no pré/pós-operatório, diferença de 18,73 pontos percentuais. É evidência de alteração do desempenho associada ao cenário cirúrgico naquele estudo; não uma medida própria, uma taxa de Rank-1 ou um efeito universal da catarata. [Artigo](https://doi.org/10.1038/s41598-019-47222-4).

Os trabalhos de Trokielewicz, Czajka e Maciejewicz apontam obstruções, distorções e falhas de segmentação como fatores relevantes para o reconhecimento em olhos afetados. Essa evidência fundamenta a necessidade de avaliar tanto a máscara quanto a decisão biométrica. Parte dessas publicações compartilha dados e resultados, de modo que não deve ser contada como múltiplas replicações independentes. [Estudo de 2016](https://doi.org/10.1016/j.imavis.2016.08.001).

| Alternativa | Adequação e pendência |
|---|---|
| CMPD | Prioridade proposta para o pipeline RGB/periocular. Possui imagens pré/pós-cirurgia, mas exige acordo institucional e senha. A comparação envolve também variação de sessão e captura. |
| IIITD CaSD | Relevante para íris com sensores dedicados e cirurgia de catarata. Acesso imediato não confirmado; exige avaliar mudança de domínio em relação ao UBIPr. |
| CatScreen | Amostra pública anunciada para triagem de catarata. Ainda é necessário verificar IDs, lado, sessões, repetições e termos antes de avaliar reconhecimento. |
| SLID e dados de ceratite associados ao SDCTrans | Candidatos para imagens de alterações reais e segmentação clínica. Arquivos e elegibilidade biométrica não auditados. |

Fontes e estado de consulta estão detalhados em [REFERENCIAS_ANOMALIAS_OCULARES.md](../pfc1-segmentacao-mmu/REFERENCIAS_ANOMALIAS_OCULARES.md). Nenhuma alternativa foi baixada ou utilizada nesta etapa.

## 5. Por que ainda não podemos medir o efeito de uma doença

Para medir reconhecimento, precisamos conhecer a identidade e dispor de capturas distintas do mesmo olho; uma coleção com apenas uma imagem por olho não permite avaliar comparações genuínas independentes. Para atribuir diferenças a condições clínicas, precisamos também de rótulos confiáveis, controles de aquisição e comparações adequadas entre condições.

Comparar olhos do UBIPr com olhos doentes de outro equipamento confundiria patologia com iluminação, resolução, sensor e população. Comparar pré/pós-cirurgia responde à mudança nesse cenário, sem isolar automaticamente doença, intervenção e alterações pós-operatórias. Retinografias não são substitutas diretas de fotografias externas para este pipeline.

Transformações artificiais podem quantificar sensibilidade à perda de informação, mas não devem receber nomes de doenças sem validação de sua correspondência clínica. Da mesma forma, falhas de segmentação precisam ser contadas e analisadas; excluí-las silenciosamente pode superestimar o reconhecimento.

## 6. Protocolo e próximos passos

1. Auditar a identidade ocular e montar manifesto com pessoa, lado, sessão, condição, dispositivo e origem dos rótulos.
2. Priorizar o acesso à CMPD/CaSD e inspecionar a elegibilidade das amostras clínicas públicas. Ainda não foram enviados pedidos nesta etapa.
3. Fixar modelo e limiares em treino/validação, mantendo pessoas distintas no teste. Não usar a mesma imagem ou sua transformação como captura independente da galeria.
4. Adotar queda de Rank-1 em pontos percentuais como medida principal de identificação. Complementar com EER, TAR/FNMR, FAR efetiva e falhas de cadastro/extração, distinguindo identificação de verificação.
5. Manter indivíduos e galeria comparáveis entre cenários. Calcular incerteza por reamostragem de pessoas, preservando a dependência entre olhos e capturas.
6. Separar reconhecimento periocular de reconhecimento da íris; para este último, incluir normalização e um reconhecedor validado no domínio.
7. A curva de reconhecimento sob perturbações controladas no UBIPr foi executada nesta atualização, explicitamente como robustez sintética. O próximo passo é usar esse protocolo como referência ao preparar a avaliação clínica, preservando uma validação independente na nova base.

O desenho detalhado está em [PROTOCOLO_ANOMALIAS_BIOMETRIA.md](../pfc1-segmentacao-mmu/PROTOCOLO_ANOMALIAS_BIOMETRIA.md).

## 7. Entregas e conclusão da etapa

Foram produzidos o protocolo experimental, o registro comentado da pesquisa e o ensaio completo de robustez, acompanhado de relatório, HTML local, seis figuras, CSVs, escores e caches retomáveis. As referências anteriores e os resultados históricos foram preservados; o artigo PDF não foi alterado.

Os dados atuais permitiram demonstrar e quantificar perda de reconhecimento sob alterações visuais, além de associação com a qualidade das capturas originais. Ainda não sustentam uma conclusão quantitativa própria sobre patologias específicas. A pendência clínica é obter imagens com identidade ocular, capturas repetidas e condições de comparação adequadas; essa pendência não impediu o avanço experimental apresentado hoje.
