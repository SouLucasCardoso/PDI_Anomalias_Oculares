# Relatório de avanço — retreinamento, recortes e reconhecimento sob perda de área da íris

**Data:** 20 de outubro de 2026  
**Projeto — foco atual:** Influência da área preservada da íris no reconhecimento de identidade sob oclusões controladas e alterações oculares  
**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Entrega prevista do artigo:** 9 de novembro de 2026

## 1. Objetivo e situação da etapa

O trabalho desta etapa reconstruiu o ambiente e os experimentos após a perda dos testes anteriores, utilizando bases públicas. Conforme o redirecionamento acordado com a orientação, a pergunta principal passou a ser quanto da região visível da íris pode ser perdido mantendo o reconhecimento de identidade. O título acima descreve o foco atual, ainda sujeito à consolidação na versão final do artigo.

Foram concluídos o retreinamento da segmentação, o treinamento de um extrator de identidade, duas rodadas de curvas de oclusão e uma avaliação biométrica em base clínica pública. Foram produzidos recortes reais, tabelas, figuras e texto do artigo. **O resultado atual é uma medida de desempenho e sensibilidade à perda de área; o percentual mínimo de área suficiente ainda não foi validado.**

## 2. Preparação e protocolo executado

O ambiente local foi preparado para execução com GPU, com dependências registradas e acessos aos modelos verificados. Os códigos, protocolos, pesos treinados e resultados compactos foram preservados em backups com verificação de integridade. Dezoito testes automatizados de métricas, máscaras, limiares e regras de área foram aprovados.

A base principal UBIPr possui 11.018 pares de imagem e máscara, de 261 pessoas. A divisão de segmentação manteve pessoas distintas: 7.716 imagens de treino, 1.652 de validação e 1.650 de teste. No protocolo de reconhecimento entre sessões, a amostra elegível de teste contém **486 consultas, 16 pessoas e 32 identidades oculares**, com pessoa e lado do olho formando a identidade. A galeria permanece fixa e usa capturas da sessão 1; as consultas são da sessão 2.

Foram avaliadas **19 condições por rodada**: original e oclusões superiores e inferiores de 10% a 90%, em passos de dez pontos. Apenas os pixels da íris anotada foram substituídos por cinza; o contexto externo não foi diretamente alterado. Seis consultas com referência vazia foram mantidas como falhas, sem exclusão do denominador.

## 3. Retreinamento da segmentação e estado dos recortes

A U-Net multiclasse foi retreinada durante 30 épocas. O checkpoint selecionado pela validação foi o da época 26. No teste, foram obtidos:

| Medida de segmentação | Resultado |
|---|---:|
| Dice da íris | **0,9342** |
| Dice médio das classes de primeiro plano | **0,8944** |
| Dice da esclera | 0,8538 |
| Dice da sobrancelha | 0,8952 |

Dice é uma medida de sobreposição de máscaras; **0,9342 não significa 93,42% de pessoas reconhecidas**. Os resultados de segmentação e de identidade são tarefas distintas.

A prancha abaixo apresenta quatro exemplos reais da validação: imagem original, máscara inferida em verde, recorte automático da U-Net, recorte com referência da base e oclusões simuladas. Os exemplos foram escolhidos pela ordem do manifesto, com pessoas distintas e referência não vazia, sem seleção por desempenho.

![Estado atual das máscaras e dos recortes de íris](EXEMPLOS_REAIS_RECORTES_IRIS_2026-10-20.png)

O recorte automático conserva a região prevista e remove o exterior com preenchimento preto. A rodada do novo extrator de identidade utilizou **máscaras de referência**, recorte com margem de 25% e entrada de 128 × 128 pixels. Portanto, os números desse extrator ainda não representam uma avaliação completa de reconhecimento com segmentação automática. Permanecem diferenças de contorno, reflexos e casos com óculos nos exemplos.

## 4. Reconhecimento sem oclusão artificial adicional

Foi treinado um extrator ResNet18 com margem angular em **183 pessoas e 366 classes de olho**. O treinamento terminou na época 23 por parada antecipada, com o checkpoint da época 15 selecionado na validação. O limiar de similaridade foi fixado em **0,402684** a partir da validação original, visando FMR empírica de até 1%, e foi mantido nas condições de teste.

| Entrada / extrator | Rank-1 | TAR | FMR observada |
|---|---:|---:|---:|
| DINOv3, recorte de referência | 13,37% | 7,00% | 1,47% |
| DINOv3, imagem inteira, com contexto periocular | 46,50% | 25,51% | 0,87% |
| **Extrator treinado, recorte de referência** | **67,90%** | **55,14%** | **0,96%** |

No extrator treinado, **330/486 consultas** tiveram o olho correto como primeiro candidato (Rank-1) e **268/486 comparações genuínas** foram aceitas no limiar (TAR). A interseção foi **234/486 = 48,15%**, isto é, identificação correta e aceitação simultâneas. Esses critérios têm numeradores diferentes e não são intercambiáveis.

Os intervalos de 95%, por reamostragem de pessoas e condicionais à galeria e ao modelo fixos, foram **61,04%–74,80% para Rank-1**, **40,36%–68,75% para TAR** e **0,46%–1,49% para FMR**. A FMR pontual ficou abaixo de 1%, mas o intervalo não sustenta garantia populacional de permanecer abaixo desse valor.

A diferença em relação ao DINOv3 com referência foi de **54,53 pontos percentuais em Rank-1** e **48,15 pontos em TAR**. Como também mudaram arquitetura, treinamento e resolução, o ganho não pode ser atribuído isoladamente à margem angular. O teste UBIPr já havia sido examinado na rodada inicial; a nova avaliação está registrada como **seguimento exploratório**, não como teste independente inédito.

## 5. Percentuais obtidos com oclusão

Os resultados a seguir usam todas as **486 consultas** e o mesmo limiar original. Rank-1 mede identificação correta do primeiro candidato; TAR mede aceitação genuína; FMR mede falsas correspondências entre olhos diferentes. “Área preservada” é a fração alvo da **região visível anotada**, não da superfície anatômica total da íris. “Sem oclusão” significa sem oclusão artificial adicional e não ausência de oclusões naturais.

| Oclusão adicional | Área preservada | Rank-1 superior | TAR superior | FMR superior | Rank-1 inferior | TAR inferior | FMR inferior |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0% | 100% | 67,90% | 55,14% | 0,96% | 67,90% | 55,14% | 0,96% |
| 10% | 90% | 56,38% | 29,84% | 0,59% | 54,53% | 30,45% | 0,72% |
| 20% | 80% | 45,27% | 16,67% | 0,42% | 40,53% | 19,14% | 0,72% |
| 30% | 70% | 34,16% | 11,32% | 0,23% | 25,51% | 12,55% | 0,55% |
| 40% | 60% | 29,42% | 6,79% | 0,10% | 19,75% | 5,76% | 0,26% |
| 50% | 50% | 25,31% | 2,47% | 0,05% | 14,81% | 1,85% | 0,07% |
| 60% | 40% | 16,67% | 0,00% | 0,00% | 12,35% | 0,21% | 0,02% |
| 70% | 30% | 9,67% | 0,00% | 0,00% | 6,17% | 0,00% | 0,00% |
| 80% | 20% | 4,73% | 0,00% | 0,00% | 5,76% | 0,00% | 0,01% |
| 90% | 10% | 3,29% | 0,00% | 0,00% | 3,91% | 0,00% | 0,00% |

Assim, com **10% de oclusão**, a identificação correta atual é **56,38% na direção superior e 54,53% na inferior**. A aceitação genuína cai para **29,84% e 30,45%**, respectivamente. No original, os valores são **67,90% de identificação e 55,14% de aceitação genuína**. Esses são os percentuais observados; não constituem aprovação pelo critério global de 90%.

Com maior oclusão, a FMR também pode cair porque os escores diminuem, mas isso ocorre junto à rejeição de mais comparações genuínas. FMR baixa isoladamente não demonstra reconhecimento satisfatório. Por exemplo, a partir de 60% de oclusão superior a TAR foi zero, embora o Rank-1 ainda fosse superior a zero.

Uma análise secundária considerou somente as **234 consultas identificadas e aceitas no original**. Com 10% de oclusão superior, **117/234 = 50,00%** mantiveram esse sucesso; com oclusão inferior, **115/234 = 49,15%**. Essa retenção condicional não é a taxa global de todas as 486 consultas e não substitui a tabela acima.

## 6. Distância até a determinação de um percentual mínimo

O critério operacional registrado exige **Rank-1 e TAR de pelo menos 90%**, no limiar definido pela validação original, com aprovação também em todos os níveis maiores de área preservada. O alvo de FMR de 1% é usado na calibração e sua taxa efetiva é reportada no teste. Não foi reduzido o critério de sucesso após observar os resultados.

| Condição | Rank-1 atual | Falta para 90% | TAR atual | Falta para 90% |
|---|---:|---:|---:|---:|
| Original: 100% da região anotada | 67,90% | **22,10 pp** | 55,14% | **34,86 pp** |
| 90% preservados, oclusão superior | 56,38% | **33,62 pp** | 29,84% | **60,16 pp** |
| 90% preservados, oclusão inferior | 54,53% | **35,47 pp** | 30,45% | **59,55 pp** |

Com 486 consultas, uma taxa de pelo menos 90% exige **438 acertos/aceitações** em cada métrica. No original, faltariam **108 identificações corretas** em Rank-1 e **170 aceitações genuínas** em TAR, mantendo o denominador. São distâncias aritméticas ao critério, não uma previsão de melhoria nem de quantidade de treinamento necessária. Os sucessos das duas métricas não precisam ser as mesmas consultas.

**Situação objetiva: nenhum dos 19 cenários atingiu simultaneamente os 90% exigidos. Nem 100% da área anotada passou; logo, não existe ainda uma fração mínima global aprovada neste pipeline.** Tampouco foi demonstrado um intervalo estreito em torno desse mínimo. Não há fundamento para declarar o projeto “X% concluído” ou prometer que mais algumas épocas resolverão a diferença.

Para estabelecer esse mínimo ainda é necessário:

1. Obter desempenho suficiente no original, com ajustes escolhidos no treino/validação e confirmação em avaliação independente. Reutilizar o teste atual para desenvolver melhorias não cria nova evidência independente.
2. Avaliar o reconhecimento com o recorte automático, além do controle com referência, para medir a perda introduzida pela segmentação no fluxo completo.
3. Repetir a curva com o reconhecedor adequado, mantendo limiar e galeria fixos, falhas no denominador e análise de incerteza. Só após existir uma região aprovada e outra reprovada faz sentido refinar a grade perto da transição; a grade atual de 10% não resolve diferenças de 1% a 9%.
4. Distinguir um limite operacional do sistema e da base de um limite anatômico ou clínico. Uma conclusão sobre doenças requer controle de aquisição e comparação clínica própria.

O caminho restante é principalmente **melhorar e validar o reconhecedor**, e não apenas executar mais níveis de oclusão. Se o critério não for atingido no prazo, a contribuição sustentada pelos dados é a caracterização das perdas e limitações do pipeline, com o mínimo global declarado não determinado.

## 7. Avaliação clínica e qualidade das bases públicas

O HDBIF foi avaliado no SLP-VLD com configuração e limiar congelados na validação. O teste incluiu **319 consultas de 107 pessoas**, com **176 olhos na galeria**. Foram obtidos **15,99% de Rank-1**, **50,78% de TAR** e **2,45% de FMR**. Dez imagens falharam e três cadastros ficaram indisponíveis; os casos não foram removidos após a análise dos escores.

A inspeção identificou capturas oblíquas, reflexos, dilatação variável e segmentação imprecisa. A diferença de tamanho de galeria entre validação e teste também afeta a interpretação. Esses resultados não isolam o efeito de doença, nem podem ser comparados diretamente aos do UBIPr como se apenas a condição clínica variasse.

A Nuclear Cataract foi auditada e teve protocolo preparado, mas a inspeção inicial mostrou recortes fragmentados e iluminação em fenda inadequados ao pipeline adotado. A execução foi interrompida **antes de gerar escores biométricos**. Não há taxa de reconhecimento dessa base nesta etapa. As oclusões artificiais do UBIPr são perturbações controladas, sem equivalência clínica demonstrada com uma doença específica.

## 8. Entregas e pendências

Foram entregues os códigos de preparação, treinamento e avaliação; os protocolos e registros de execução; as duas rodadas de 19 condições; as métricas e análises de incerteza; os checkpoints preservados; e a prancha de exemplos reais de máscaras e recortes. O texto ativo do artigo contém resumo, fundamentação, métodos, resultados, discussão, conclusões e referências de trabalho.

Permanecem a revisão científica da interpretação, a normalização das referências e a diagramação no modelo institucional para 9 de novembro. A eventual nova rodada precisa de hipótese específica e avaliação independente viável no prazo; ela não está registrada como experimento já concluído.

### Arquivos de referência

- [Tabela original de todas as condições do extrator treinado](../pfc1-segmentacao-mmu/outputs/area_encoder_ubipr_2026-10-20/resumo.csv).
- [Protocolo e limiar do experimento](../pfc1-segmentacao-mmu/outputs/area_encoder_ubipr_2026-10-20/protocolo.json).
- [Síntese e intervalos da segunda rodada](../pfc1-segmentacao-mmu/outputs/consolidacao_biometria_2026-10-20/SEGUNDA_RODADA.md).
- [Exemplos reais de máscaras, recortes e oclusões](EXEMPLOS_REAIS_RECORTES_IRIS_2026-10-20.png).
- [Artigo em produção](../pfc1-segmentacao-mmu/artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md).

## 9. Atualizações posteriores: desenvolvimento do reconhecedor no mesmo dia

Após os experimentos de teste descritos acima, foram realizadas novas rodadas **somente na validação**, com 482 consultas de 16 pessoas e 32 olhos. Esses números não substituem as 486 consultas de teste das seções anteriores nem constituem confirmação independente.

O cadastro múltiplo com máscaras automáticas melhorou o encoder RGB. Duas adaptações de treinamento não superaram a TAR inicial e mantiveram os parâmetros anteriores. O TripletIris público e a aproximação elíptica foram avaliados, sem justificar a substituição do encoder. Foi então treinado um novo encoder em textura polar própria, com 28 épocas e seleção na época 20; suas representações complementaram as do encoder RGB.

| Candidato de desenvolvimento na validação | Rank-1 | TAR | FMR |
|---|---:|---:|---:|
| RGB automático top-3, linha de base pareada | 66,80% | 59,34% | 0,99% |
| Novo encoder polar top-3 | 58,71% | 49,59% | 0,99% |
| Fusão RGB + polar, pesos iguais | 76,35% | 67,63% | 0,99% |
| Fusão RGB + polar + espacial, pesos iguais | **79,88%** | **68,05%** | **0,99%** |

O ganho da fusão de três vias em relação à linha de base foi de 13,07 pp em Rank-1 e 8,71 pp em TAR. Os pesos são fixos, mas a padronização por impostores e os limiares foram calculados na própria validação. Houve várias hipóteses de desenvolvimento no mesmo conjunto, portanto esses ganhos precisam de confirmação independente.

O critério de 90% nas duas métricas permanece inalterado. Na fusão de três vias, faltam **10,12 pp de Rank-1 e 21,95 pp de TAR**. Em 482 consultas, há 385 identificações corretas e 328 aceitações genuínas; o alvo de pelo menos 90% exige 434 em cada medida. Ainda não existe mínimo global de área aprovado e nenhuma nova curva de oclusão foi calculada para esses candidatos.

Os **37 testes automatizados passaram**. O checkpoint polar, fontes, escores, históricos e backups foram preservados. O aluno confirmou o **UBIPr como base principal e uma única foto de consulta por identificação**. Várias fotos de cadastro continuam permitidas conforme o protocolo; não há agregação de fotos de consulta.

[Relatório da rodada polar, fusões, intervalos e exemplos reais](../pfc1-segmentacao-mmu/outputs/fusao_espacial_val_2026-10-20/RELATORIO_AVANCO_POLAR_FUSAO.md).

## 10. Continuação: controles de resolução interna e métrica

Foi concluído novo treino polar sem o max-pooling inicial: 29 épocas, seleção na 21. A arquitetura mantém mais posições espaciais e utiliza lote 32 por memória; essa mudança simultânea impede isolar o efeito da arquitetura. O encoder isolado obteve 61,62% de Rank-1 e 46,68% de TAR. O modelo recarregado reproduziu exatamente os escores salvos.

| Controle adicional, mesmas 482 consultas de validação | Rank-1 | TAR | FMR |
|---|---:|---:|---:|
| Fusão anterior, referência mantida | 79,88% | 68,05% | 0,99% |
| Fusão fixa com o novo encoder denso | 78,84% | 68,26% | 0,99% |
| Fusão após transformação linear ajustada só no treino | 78,22% | 65,98% | 0,99% |

A fusão densa perdeu cinco identificações corretas e acrescentou uma aceitação genuína. Os intervalos pareados das duas diferenças incluem zero; não há ganho consistente demonstrado. A transformação linear também não superou a referência. Os resultados negativos foram mantidos, sem substituir os pesos anteriores. Os **39 testes passaram**, e novos pesos, escores e protocolos foram copiados para o projeto com hashes conferidos.

O mínimo de área continua **não determinado**, tanto sem oclusão artificial adicional quanto sob oclusões, pelo critério registrado. A referência mantida está a 10,12 pp de Rank-1 e 21,95 pp de TAR dos 90%. A nova fusão tem TAR pontualmente maior, mas Rank-1 menor: não se combinam métricas de configurações diferentes para declarar aprovação. Nenhum novo teste independente ou ensaio de oclusão foi executado nesta continuação.

[Relatório detalhado da continuação](../pfc1-segmentacao-mmu/outputs/fusao_densa_val_2026-10-20/RELATORIO_CONTINUACAO.md).
