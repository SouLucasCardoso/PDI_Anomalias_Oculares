# Relatório de avanço — 8 de novembro de 2026

**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Dia:** domingo  
**Registro retrospectivo:** elaborado em 09/11/2026 a partir dos protocolos, fontes e resultados preservados. O fechamento do artigo após a meia-noite é descrito no relatório de 09/11.

## Objetivo do dia

Melhorar o recorte e o reconhecimento sob oclusões para o artigo, avaliando todos os percentuais inteiros de 1% a 31%. Manter limiar, pesos e critérios registrados, incluir falhas nas métricas e separar melhoria visual, identificação e interpretação clínica.

## Reconhecimento e hipóteses avaliadas

Foram implementados ensaios de contorno contínuo, aplicação seletiva aos descritores, geometria externa SAM3.1, misturas de escores, ablações, ajuste supervisionado dos encoders RGB e polar e média de rotações polares. Os ajustes supervisionados não produziram época elegível para substituir a referência. O ajuste polar completou seis épocas, com os 108 tensores congelados conferidos na auditoria.

No ensaio anterior com 13 condições, aplicar o contorno contínuo aos descritores polares elevou o Rank-1 sob 1% de perda superior de 89,92% para 91,15%, mas piorou outras condições. Esse candidato não foi adotado como substituto geral. O ganho localizado foi mantido separado do candidato posterior da grade densa.

Uma mistura fixa de 50% do escore polar original e 50% do escore obtido com contorno contínuo e remoção de pequenos componentes foi escolhida na validação, antes da comparação densa. Os outros oito componentes, a fusão, a calibração e o limiar permaneceram fixos.

## Grade inteira de 1% a 31%

A grade reuniu o controle sem perda adicional e cada percentual inteiro de 1% a 31%, nas posições superior e inferior: **63 condições por versão**. Treze condições da referência foram reutilizadas após conferência; cinquenta foram calculadas nesta rodada. A referência e o candidato completaram a execução por volta das **23h03 de 08/11**, antes do corte computacional previsto.

Cada condição manteve 486 consultas, 7.290 comparações impostoras e o cadastro original. A alteração foi aplicada à fotografia antes de repetir segmentação e extração. Seis referências vazias continuaram no denominador, com área indefinida; a análise secundária manteve o mesmo grupo fixo de 480 referências com área definida.

| Condição | Versão | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| Sem perda adicional | Referência | 91,15% | 92,39% | 0,864% | 89,51% |
| Sem perda adicional | Candidato | 91,15% | 93,00% | 0,823% | 90,12% |
| 31% superior | Referência | 69,34% | 70,99% | 2,016% | 66,26% |
| 31% superior | Candidato | 69,34% | 71,40% | 1,975% | 66,87% |
| 31% inferior | Referência | 32,51% | 29,42% | 3,525% | 27,57% |
| 31% inferior | Candidato | 30,86% | 29,01% | 3,608% | 26,95% |

A média do evento correto e aceito nas 63 condições passou de 61,46% para 61,58%. Entretanto, a FMR aumentou em **31 condições**. A regra completa foi reprovada e a referência permaneceu preservada. As repetições das mesmas fotografias em diferentes níveis não representam novas pessoas nem observações independentes adicionais.

## Recorte e SAM3.1

A revisão oficial SAM 3 `f1647e8d0c1d280991f4d1b7d974c2704537fe66`, o checkpoint SAM3.1 na revisão `daa63191845a41281374e725f4c9e51c7a824460` e o SHA-256 do checkpoint `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6` foram conferidos para as novas rodadas. O ambiente foi preservado durante as comparações: Python 3.12.10, PyTorch 2.14.1+cu130, torchvision 0.29.1+cu130, NumPy 1.26.4 e RTX 3050 Laptop de 6 GB.

Em 78 fotografias fixas de validação, o contorno contínuo apresentou Dice médio limpo de 88,46%. Filtragem guiada e combinações de resoluções não superaram o controle nas três situações avaliadas: original, perda superior de 10% e inferior de 10%. A retirada de componentes menores que 0,5% do maior componente alterou o Dice em menos de 0,01 ponto percentual, sem preencher lacunas nem criar pixels.

O ensaio SAM3.1 com até 24 pontos positivos e negativos exteriores alcançou Dice limpo de 84,19%, incluindo retorno à máscara inicial em 40 das 78 fotografias. Esse procedimento híbrido ficou abaixo do controle contínuo e não foi promovido. Seu resultado não foi atribuído exclusivamente ao SAM.

Nos seis exemplos clínicos fixos, a cobertura subpixel suavizou a apresentação da borda preservando RGB e máscaras binárias. Cinco exemplos mantiveram recorte; a falha de localização permaneceu vazia e sinalizada para revisão. Não foi gerada textura nem demonstrado ganho de acurácia anatômica clínica.

## Auditoria, artigo e conclusão do dia

A auditoria independente recontou as decisões das 63 condições por versão, conferiu hashes, fontes congeladas e quantidade de pixels da intervenção. Foram produzidas curvas completas, tabela CSV e intervalos descritivos com 5.000 reamostragens por pessoa, condicionados à galeria fixa. A consolidação inicial do artigo e os guias de defesa foram atualizados; a incorporação final da grade densa e a revisão de paginação terminaram em 09/11.

O resultado sustenta sensibilidade à posição da perda: a mesma fração nominal produziu respostas diferentes. A comparação entre 30% e 31% não demonstrou ruptura universal em 70% de suporte preservado. A fração originalmente anotada não equivale à área anatômica normativa nem à extensão de uma patologia. Validação e teste reutilizados no desenvolvimento limitam a generalização.

## Registros técnicos

- [Resultado consolidado da grade densa](../pfc1-segmentacao-mmu/RESULTADO_GRADE_DENSA_2026-11-08.md), fechado em 09/11.
- [Tabela completa de todos os percentuais](../pfc1-segmentacao-mmu/outputs/grade_densa_analise_2026-11-08/tabela_completa.csv).
- [Auditoria final da grade](../pfc1-segmentacao-mmu/outputs/grade_densa_analise_2026-11-08/AUDITORIA_FINAL.json).
- [Protocolo da referência](../pfc1-segmentacao-mmu/outputs/grade_densa_1a31_2026-11-08/protocolo.json).
- [Protocolo do candidato](../pfc1-segmentacao-mmu/outputs/grade_densa_contorno_misto_2026-11-08/protocolo.json).
- [Resultados da etapa anterior com 13 condições](../pfc1-segmentacao-mmu/RESULTADO_MELHORIA_RECONHECEDOR_2026-11-08.md).
- [Recortes e proveniência](../pfc1-segmentacao-mmu/RECORTES_NATIVOS_2026-11-08.md); fotografias e painéis permanecem locais.
