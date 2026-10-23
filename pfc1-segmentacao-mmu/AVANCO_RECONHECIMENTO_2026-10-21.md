# Relatório de avanço — melhoria do reconhecimento e meta de desenvolvimento

**Data:** 21 de outubro de 2026  
**Projeto — foco atual:** Influência da área preservada da íris no reconhecimento de identidade sob oclusões controladas e alterações oculares  
**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Entrega prevista do artigo:** 9 de novembro de 2026

## 1. Objetivo e situação da etapa

Foi atingido o critério de desenvolvimento de Rank-1 ≥90% e TAR ≥90%, com FMR ≤1%. O candidato foi congelado após reconstrução exata dos escores; ainda não há confirmação independente nem percentual mínimo de área.

## 2. Base e condições do experimento

UBIPr principal, uma foto original por consulta, lado do olho informado corretamente na captura, cadastro com múltiplas fotos da sessão 1 e consulta na sessão 2. São 482 consultas de 16 pessoas e 32 olhos físicos; cada consulta compara 16 olhos do mesmo lado. As quatro falhas de extração permanecem no denominador. O cenário anterior de 32 candidatos foi preservado.

## 3. Resultados sem oclusão artificial adicional

| Estratégia | Rank-1 | TAR | FMR |
|---|---:|---:|---:|
| Fusão5 com lado informado |87,34%|86,72%|0,98%|
| Fusão6, incluindo ResNet50 nativo224 |87,55%|86,93%|0,98%|
| Fusão7, incluindo Transformer polar |88,80%|88,80%|0,98%|
| Fusão8 com ArcIris e contraste local |89,42%|90,66%|0,98%|
| Fusão8 com ArcIris e canal vermelho |89,63%|90,04%|0,98%|
| **Candidato congelado: duas entradas ArcIris da mesma foto** |**90,04%**|**90,66%**|**0,98%**|

O candidato tem 434 identificações corretas e 437 aceitações genuínas em 482 consultas. São 71 aceitações impostoras em 7.230 comparações admissíveis (482×15). O limiar congelado é 0,8581747485460748. Rank-1 e TAR são medidas separadas: 426 consultas foram simultaneamente identificadas corretamente e aceitas (88,38%). Portanto, não foi atingido 90% no critério conjunto, caso esse seja exigido futuramente.

## 4. Trabalho realizado e modelos avaliados

Foram treinados ResNet50 com amostragem entre sessões, ConvNeXt com contraste, ResNet50 com recortes224 diretamente dos originais e Transformer polar derivado das seis primeiras camadas DINOv3. O modelo nativo224 selecionou época 11 de 21; o Transformer selecionou época 16 de 24 e seu checkpoint recarregado reproduziu exatamente os escores salvos. Foram preservados controles de classificadores de cadastro, adaptação usando somente sessão 1, qualidade de cadastro, protótipos por escala, alinhamento angular, variações de iluminação e fusão de probabilidades. Esses controles não substituíram automaticamente o melhor candidato. Uma execução de adaptação interrompida por tipo de rótulo foi corrigida e repetida em outra pasta; a interrupção técnica não foi tratada como resultado científico.

ArcIris foi avaliado com pesos públicos e código fixado do CVRL. Usamos nossa geometria automática da íris, não o pipeline IREX integral. A população do pré-treinamento não está documentada nos arquivos publicados; sobreposição de identidades não pode ser excluída. O resultado com esse componente é exploratório. As entradas vermelho e contraste são processamentos determinísticos da mesma foto, sem gerar textura ou acrescentar fotos de consulta.

A fusão congelada mantém sete componentes com peso 1/8 cada e ArcIris com peso 1/8, dividindo este último igualmente entre suas duas entradas. Os parâmetros de padronização e o limiar foram salvos. Nenhum peso foi escolhido por busca numérica. A validação, contudo, foi reutilizada para muitas estratégias: há viés de seleção e os percentuais não são confirmação independente.

## 5. Verificação, limitações e percentual mínimo de área

Os 52 testes automatizados passaram. A reconstrução dos escores do candidato foi exata e conferiu todos os 482 rótulos, falhas, acertos e aceitações; modelos e resultados foram preservados com conferência SHA-256.

O mínimo anatômico ou clínico de íris continua **não determinado**. A avaliação posterior da seção 8 apresenta a fronteira experimental na grade nominal de área. O resultado atual usa a íris disponível na foto original, sem nova oclusão artificial; isso não significa100% da anatomia visível. O próximo passo é implementar a avaliação completa com estes pesos, transformações, parâmetros e limiar congelados, registrar a exposição anterior do conjunto de teste e então avaliar as curvas de oclusão sem recalibrar o limiar em cada fração.

## 6. Estado atual dos recortes

A prancha apresenta quatro fotos reais da sessão 2 de validação, de pessoas distintas, escolhidas pela ordem do manifesto entre as entradas válidas, sem consultar acertos ou escores de reconhecimento. Cada linha mostra a foto original, a máscara inferida pela U-Net em verde, os recortes RGB de 128 × 128 e 224 × 224 pixels e as faixas polares de contraste local e canal vermelho. Os recortes são calculados diretamente dos originais e ampliados apenas para a exibição.

O exterior previsto como não pertencente à íris é removido dos recortes RGB; o suporte excluído da faixa polar recebe cinza. Reflexos, contornos imperfeitos e oclusões naturais permanecem: não foi gerada nem reconstruída textura ausente. A prancha documenta o processamento, sem demonstrar reconhecimento correto dessas amostras.

![Amostras reais dos recortes e faixas polares](../Relatórios-de-Avanço/AMOSTRAS_RECORTES_IRIS_2026-10-21.png)

O JSON ao lado da imagem registra nomes dos arquivos, índices no manifesto, geometria e hashes dos originais e do checkpoint de segmentação.

## 7. Evidências e rastreabilidade

- [Congelamento e auditoria](outputs/candidato_congelado_2026-10-21/CONGELADO.json).
- [Resultado final de desenvolvimento](outputs/arciris_duas_vistas_2026-10-21/CONCLUIDO.json).
- [Treinamento Transformer](outputs/transformer_polar_2026-10-21/CONCLUIDO.json).
- Fonte do reconhecedor externo: https://github.com/CVRL/OpenSourceIrisRecognition (revisão 4a535e4a9a0728e4428c25f743f6d59098ae397f).


## 8. Avaliação posterior com configuração congelada e oclusão

A execução integrada reproduziu a validação sem alterar nenhuma decisão (diferença máxima de 9,99×10⁻¹⁶). No teste, mantendo o limiar 0,8581747485460748, foram obtidos **91,36% de Rank-1 (444/486), 92,39% de TAR (449/486) e 0,88% de FMR (64/7.290)**. A taxa conjunta foi 89,71% (436/486). Todas as 486 consultas foram mantidas, incluindo duas falhas de extração.

| Condição | Área nominal preservada | Rank-1 | TAR | FMR |
|---|---:|---:|---:|---:|
| Original |100%|91,36%|92,39%|0,88%|
| Oclusão superior de 1% |99%|89,92%|92,39%|0,88%|
| Oclusão inferior de 1% |99%|90,95%|91,36%|0,93%|
| Oclusão inferior de 2% |98%|87,45%|87,86%|1,23%|
| Oclusão superior de 10% |90%|82,30%|84,98%|1,69%|
| Oclusão inferior de 10% |90%|58,23%|60,29%|2,61%|

**Fronteira na grade nominal de 1 ponto percentual:** 99% preservados foram aprovados na oclusão inferior; na superior, somente a condição original sem perda adicional passou. Na oclusão superior de 1%, faltou uma identificação correta para atingir90%. Não é demonstração de que todos os pixels sejam indispensáveis.

A anotação definiu apenas a intervenção cinza nos pixels da íris; a segmentação e a geometria foram recalculadas sobre a imagem alterada. O cadastro original permaneceu exatamente igual e o limiar não foi recalibrado. A busca parou na primeira reprovação por orientação, conforme regra registrada; não é uma curva completa de 19 condições.

Das486 consultas, 480 possuem referência de área definida; as seis referências vazias permaneceram inalteradas e no denominador principal. Em análise secundária restrita às 480 referências definidas, 1% de oclusão superior passou (Rank-1 de 90,83%, TAR de 93,13% e FMR de 0,85%). Isso demonstra sensibilidade ao denominador, sem justificar excluir consultas ou alterar a fronteira principal. A perda nominal de 1% variou de 0,84% a 1,69% por imagem devido ao arredondamento para pixels.

Foram aprovados57 testes. A auditoria conferiu decisões, limiar, contagens de pixels e igualdade das entradas do cadastro e das seis consultas sem referência. O teste já havia sido examinado por modelos anteriores; a população de pré-treinamento externo permanece desconhecida. Os intervalos descritivos por pessoa de 95% no original foram 85,42–95,68% para Rank-1 e 86,46–96,67% para TAR, sem corrigir seleção de estratégias. As fronteiras são estimativas do processamento completo e não mínimos anatômicos, universais ou clínicos.

[Resultados consolidados, auditorias e recortes sob oclusão](RESULTADOS_CONGELADOS_E_OCLUSAO_2026-10-21.md).


## 9. Diagnóstico de geometria e ajuste da segmentação

O controle com máscara, caixa e elipses da foto original recuperou Rank-1 sob 10% de oclusão no teste: 82,30%→89,71% na superior e 58,23%→84,77% na inferior. Como usa a versão não ocluída da mesma foto, é diagnóstico posterior, não uma solução operacional de foto única ou novo mínimo de área. As 486 consultas e o limiar foram preservados.

Foi treinada uma U-Net ajustada com oclusões sintéticas apenas em treino/validação, por seis épocas, selecionando a terceira pelo equilíbrio de Dice limpo e ocluído. Na validação de segmentação com 1.652 imagens, o Dice de íris passou de 85,07% para 92,19% na condição superior e de 77,65% para 91,48% na inferior; nas imagens limpas, variou de 91,52% para 91,42%.

Na validação de reconhecimento com 482 consultas e mesmo limiar, o novo segmentador melhorou o Rank-1 inferior de 59,96% para 81,95%, mas reduziu o limpo de 90,04% para 88,59% e o superior de 80,71% para 76,97%. A fusão fixa dos dois pré-processamentos também não passou no critério limpo (Rank-1 de 89,00%, TAR de 90,46%, FMR de 1,09%). Não houve busca de pesos para obter aprovação.

O resultado demonstra que melhorar Dice não garante melhorar o reconhecimento. Nenhuma dessas variantes substituiu o candidato congelado nem recebeu avaliação nova no teste. Os próximos ajustes devem adaptar o reconhecedor às entradas segmentadas e às oclusões usando treino/validação. Código, novo checkpoint, escores, protocolos e amostras foram preservados;63 testes passaram.

[Resultados completos e comparação visual das novas máscaras](DIAGNOSTICO_E_SEGMENTACAO_ROBUSTA_2026-10-21.md).


## 10. Adaptação do reconhecedor com oclusões

Foram executadas duas estratégias exclusivamente em treino/validação: ajuste por gradiente com professor limpo e correção residual linear com o extrator congelado. No primeiro caso, as três épocas treinadas violaram a trava de desempenho limpo e a seleção permaneceu na época 0. No segundo, houve ganho parcial de Rank-1, mas não melhora conjunta de TAR e Rank-1 nem aprovação de uma nova fusão.

A configuração híbrida residual obteve 89,83% de Rank-1 e 90,25% de TAR na validação limpa, com FMR de 0,98%:433/482 identificações corretas, uma a menos que o mínimo de 434. Sob 10% de oclusão inferior, o híbrido chegou a 64,32% de Rank-1 e 61,41% de TAR, contra 59,96% e 57,88% do controle; a condição superior piorou. Nenhum candidato foi promovido e o teste não foi inferido nesta rodada. O modelo anterior e sua fronteira de área ficam preservados.

A correção residual foi recarregada e reproduziu os escores das três condições com diferença máxima 0. Foram aprovados67 testes. O próximo desenvolvimento deve priorizar comparação local das regiões válidas, sem ajustar parâmetros com os resultados do teste.

[Relatório completo das adaptações e controles](ADAPTACAO_IDENTIDADE_OCLUSAO_2026-10-21.md).


## 11. Diagnóstico de erros e aprendizagem da fusão

A auditoria da validação identificou 37 dos 48 erros limpos com pelo menos um componente correto, sem implicar que esses casos sejam recuperáveis automaticamente. A ponderação por textura local e a fusão aparada não melhoraram o conjunto de critérios. Em seguida, foi treinada uma fusão regularizada de oito grupos de reconhecedores congelados, usando 26.512 episódios de 16 candidatos do mesmo lado, com 4.442 imagens de 74 participantes exclusivamente do treino. As condições limpa, superior 10% e inferior 10% contribuíram igualmente, com 300 passos fixos, sem escolher pesos ou épocas na validação.

Nas 482 consultas de validação, o aprendizado obteve 84,65% de Rank-1 e 81,54% de TAR limpos, contra 90,04% e 90,66% do candidato congelado. Na oclusão inferior 10%, elevou o Rank-1 de 59,96% para 65,35%, mas a TAR ficou em 58,71% e a FMR em 1,41%; a condição superior também regrediu. O controle uniforme da mesma nova normalização apresentou 89,42% de Rank-1 limpo. Portanto, a nova fusão não foi promovida, não houve inferência nova no teste nem alteração do percentual mínimo nominal anteriormente relatado.

A redução da perda no treino não se generalizou às pessoas distintas da validação, já reutilizada no desenvolvimento. O próximo desenho deve produzir escores para aprender fusão com pessoas fora do ajuste dos encoders, o que exige novo treinamento dos modelos-base ou validação cruzada por pessoa. A causa da regressão não foi isolada. A reprodução dos escores foi exata, os cadastros e hashes dos encoders permaneceram iguais e 79 testes passaram. Modelo e escores de validação foram preservados em pacote textual local, restaurado e verificado, sem imagens ou pesos-base. [Protocolo, resultados e recuperação](FUSAO_REGULARIZADA_2026-10-21.md).


## 12. Retreinamento com pessoas separadas entre etapas

Foi concluído um piloto com três reconhecedores novos, ResNet18, ResNet50 e ConvNeXt, inicializados exclusivamente com pesos oficiais do ImageNet. Dentro das 183 pessoas do treino original, 147 foram usadas no ajuste, 16 na seleção dos checkpoints e 20 exclusivamente na aprendizagem posterior da fusão. As 20 pessoas não atualizaram nem selecionaram os encoders. O segmentador permaneceu congelado e já havia visto esses grupos internos; portanto, a separação não representa desconhecimento das pessoas por todo o pipeline.

Os modelos treinaram 15, 23 e 21 épocas, selecionando as épocas 7, 15 e 13. A fusão usou 7.136 episódios das 602 consultas das 20 pessoas, com condições limpa e oclusões superiores/inferiores de 10%. Somente após fixar todos os pesos foram extraídos os componentes das 482 consultas de validação. A fusão aprendida obteve Rank-1 de 79,25%, 71,37% e 61,00%, contra 78,84%, 69,71% e 58,51% da média simples dos mesmos três modelos. A TAR limpa caiu de 73,65% para 71,99%; nenhuma condição passou no conjunto de critérios. O ganho limpo de Rank-1 foi de 0,41 ponto percentual, com IC95% descritivo de -1,87 a 2,50. Não houve promoção, nova inferência de teste ou mudança na fronteira nominal de área.

A arquitetura e a quantidade de pessoas de ajuste diferem do candidato de oito grupos; a comparação não isola o efeito causal da separação. Foram aprovados 82 testes, e a reextração após recarga dos três checkpoints reproduziu os nove conjuntos de escores com diferença zero. Os grupos de pessoas, a seleção interna e os contadores de treinamento foram auditados. Os 40 arquivos do experimento, incluindo checkpoints, foram preservados em ZIP de 238 MB fora do OneDrive, com CRC, hash do ZIP e hashes de todos os membros conferidos. [Resultados completos, auditoria e backup](FUSAO_PESSOAS_SEPARADAS_2026-10-21.md).
