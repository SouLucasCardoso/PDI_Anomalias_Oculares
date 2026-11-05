# Área mínima de íris, ISO e alterações oculares

Pesquisa consultada em **05/11/2026**. Esta é uma revisão dirigida da literatura, não uma revisão sistemática ou metanálise. Foram organizadas **26 referências**: 19 artigos/conferências, quatro relatórios NIST e três normas. Nem todas representam experimentos independentes. [Bibliografia comentada](REFERENCIAS_COMENTADAS.md), [BibTeX](referencias.bib), [matriz de evidências](MATRIZ_EVIDENCIAS.json), [proposta de redação para o artigo](TRECHOS_PARA_ARTIGO.md).

## O que a pesquisa permite concluir

**Não localizei evidência que justifique um percentual mínimo universal, independente de algoritmo, qualidade de captura, região preservada, população e critério de erro.** Localizei requisitos normativos de qualidade e resultados experimentais condicionados ao sistema. Doenças oculares já foram estudadas; a contribuição do projeto precisa ser delimitada em relação a esses antecedentes.

### 1. De onde vêm os 70%

A referência direta é a **ISO/IEC 29794-6:2015**, cláusula **6.2.1.4**: o indicador `USABLE_IRIS_AREA` tem limiar de 70. Sua medição considera pixels desobstruídos em um anel aproximado entre pupila e limbo. Isso é requisito de qualidade da imagem; não afirma que toda comparação acima dele reconhecerá corretamente alguém. [Catálogo oficial](https://www.iso.org/standard/54066.html), [prévia pública](https://cdn.standards.iteh.ai/samples/54066/5bd98d11a8824ab29d5935edbfe997a9/ISO-IEC-29794-6-2015.pdf).

A edição consultada continua publicada, confirmada em 2021 e sob revisão no catálogo. Há também notas sobre variações pupilares inatas em outros indicadores; portanto, seria impreciso dizer que a norma ignora toda alteração anatômica. Isso não constitui validação de um limiar clínico por diagnóstico. O acesso foi ao catálogo, à prévia e aos trechos públicos, sem aquisição do texto integral pago de 29 páginas. [Conteúdo público da norma, 6.2.4.4 e 6.2.8.4](https://standards.iteh.ai/catalog/standards/iso/1a53ce7d-ac5e-4335-91e1-db50f8842bf7/iso-iec-29794-6-2015).

Minha interpretação, combinando a norma com os estudos: o limiar não impede sucesso de um algoritmo abaixo de 70%, nem garante sucesso acima dele. Outros atributos da imagem, informações comuns ao par e o critério biométrico também entram na decisão. [Daugman, 2007](https://doi.org/10.1109/TSMCB.2007.903540), [NIST IREX II](https://doi.org/10.6028/NIST.IR.7820).

### 2. Os percentuais não têm necessariamente o mesmo denominador

| Medida | Numerador e denominador | Significado |
|---|---|---|
| Área utilizável normativa | Pixels desobstruídos / área do anel estimado | Qualidade geométrica da imagem |
| Fração do nosso experimento | Pixels preservados / suporte visível originalmente anotado | Perda adicional em relação àquela foto |
| Informação comum ao par | Interseção das regiões utilizáveis após alinhamento | Suporte efetivamente comparável |
| VIA do estudo de 2026 | Contagem de pixels da máscara de íris, descontada a pupila | Área absoluta na captura estudada |

As duas primeiras frações e a interseção não são intercambiáveis. O último conceito é explicitamente uma contagem em pixels no estudo de [Pessaud et al., 2026, seção 4.1](https://doi.org/10.3390/app16147227). A distinção de área comum também é relevante para máscaras e escores em [Daugman, 2007](https://doi.org/10.1109/TSMCB.2007.903540).

**Exemplo matemático hipotético, não resultado do projeto:** se uma foto tiver 80% de um anel desobstruído e preservarmos 70% dessa parte, restarão 56% do anel, mantendo o mesmo denominador e geometria. Logo, preservar 70% da nossa anotação não comprova `USABLE_IRIS_AREA=70`. Da mesma forma, duas imagens com 70% visível cada podem ter somente 40% em comum, no caso extremo de regiões complementares em um anel alinhado.

Consequência para o manuscrito: resultados como 99,5% da região previamente visível não podem ser apresentados como confirmação ou refutação do requisito normativo. É preciso conhecer a área de referência usada em cada avaliação. Essa observação é sobre o método e não reinterpreta os resultados de uma rodada ativa.

### 3. Já existem experimentos de íris parcial

[Du et al. (2005)](https://doi.org/10.1109/ICASSP.2005.1415566) compararam regiões diferentes. Seus exemplos de aproximadamente 40% para a parte interna e 65% para a externa se referem a **95% em rank-10**. Nos modelos de anéis, a fração usada é radial, não a fração de área anular. Além disso, a máscara parcial aproveita informação da imagem completa. Esses números não equivalem a 95% de identificação rank-1 com uma foto parcialmente observada em produção.

[Hollingsworth, Bowyer e Flynn (2009)](https://doi.org/10.1109/TPAMI.2008.185) mostram que bits e regiões têm estabilidade desigual. Essa evidência impede tratar toda área da íris como igualmente informativa. Seu resultado sobre faixas médias também recomenda cautela com a ideia de que a parte interna seria sempre a melhor.

### 4. Há um antecedente recente muito próximo

[Pessaud et al. (2026)](https://doi.org/10.3390/app16147227) estudam área visível, dilatação e oclusão com OpenIRIS/NIR. A versão publicada tem 414 participantes e 827 íris; o [preprint de 2025](https://arxiv.org/abs/2510.19884) tinha 555 íris e não deve ser contado separadamente. O grupo publicado não apresentava alterações relevantes de íris ou opacidade corneana que prejudicassem a imagem. Foram corrigidas manualmente 139 segmentações e excluídas 20 imagens. O trabalho sustenta área como sinal de qualidade, não uma porcentagem clínica universal.

Esse estudo reduz a originalidade de uma alegação ampla de que a relação entre área visível e reconhecimento ainda não teria sido investigada. O diferencial do nosso trabalho precisa ser demonstrado no protocolo, nas condições de captura e na análise de falhas, não apenas na escolha do tema.

### 5. Patologias e procedimentos já foram investigados

| Referência | Evidência relevante | Limite da comparação |
|---|---|---|
| [Roizenblatt et al., 2004](https://doi.org/10.1186/1475-925X-3-2) | Investigação após cirurgia de catarata; algumas alterações comprometem o reconhecimento. | Equipamento, técnica e época específicos. |
| [Aslam, Tan e Dhillon, 2009](https://doi.org/10.1098/rsif.2008.0530) | Coorte de 54 pacientes; resiliência em várias condições, com falhas em uveíte anterior. | Não implica o mesmo efeito em todos os diagnósticos. |
| [Dhir et al., 2010](https://doi.org/10.1038/eye.2009.275) | Em 15 participantes, separa dilatação e cirurgia; os efeitos diferem. | Estudo pequeno; resultado favorável não é garantia geral. |
| [Seyeddain et al., 2014](https://doi.org/10.5301/ejo.5000343) | Maioria reconhecida, mas há falhas após cirurgia e após dilatação. | Cadastro novo pode recuperar reconhecimento; não estima área mínima. |
| [Trokielewicz, Czajka e Maciejewicz, 2017](https://doi.org/10.1016/j.imavis.2016.08.001) | 230 olhos, 184 afetados; quatro métodos; destaca erros de segmentação em olhos doentes. | Base relacionada a publicações anteriores dos mesmos autores. |
| [Nigam et al., 2019](https://doi.org/10.1038/s41598-019-47222-4) | Avalia captura e segmentação antes/depois da cirurgia com múltiplos sensores. | Momento pós-operatório e reflexos afetam o resultado. |
| [Frasca e La Torre, 2024](https://doi.org/10.1016/j.eswa.2024.124160) | Adapta a geometria da pupila no coloboma. | O ganho destacado de 32% é em erro de segmentação, não em taxa de identificação. |
| [Kumar et al., 2025](https://doi.org/10.22336/rjo.2025.30) | Cirurgias sem complicação, 100 participantes. | Relato apresenta 95/100 e 99%; melhor tentativa e exclusões exigem cautela. |

A síntese é que **a área não é a única via de comprometimento**. Geometria, textura, reflexos, localização e normalização podem mudar. A mesma fração visível pode gerar desempenhos diferentes. Isso é uma inferência apoiada no conjunto desses estudos, não uma porcentagem de doença deduzida das imagens do nosso projeto.

### 6. Melhor máscara não garante melhor reconhecimento

[Hofbauer et al. (2016)](https://doi.org/10.1049/iet-bmt.2015.0069) mostram que a acurácia da segmentação não prevê de forma confiável o resultado da cadeia inteira. Região parcial consistente pode funcionar, sob normalização adequada. [Hofbauer, Jalilian e Uhl (2019)](https://doi.org/10.1016/j.patrec.2018.12.021) também mostram dependência da base ao integrar máscaras CNN e parametrização.

Assim, SAM3 ou Dice maior pode ajudar, mas não substitui a avaliação dos escores de identidade. Pupila ou limbo mal estimados podem afetar o mapeamento polar apesar de um recorte visualmente bom. Essa é uma implicação metodológica para o próximo protocolo, não uma alteração do experimento congelado.

## Como isso muda a pergunta do artigo

Formulação defensável proposta:

> Estimar a menor fração do suporte de íris visível anotado que mantém os critérios biométricos definidos, nas condições de captura e oclusão avaliadas, e analisar as limitações da transferência para olhos com alterações oculares.

O projeto pode contribuir com análise operacional reproduzível, localização das perdas, falhas de segmentação/normalização e avaliação clínica exploratória. Não deve alegar que descobriu uma constante universal ou que é o primeiro trabalho sobre doenças e reconhecimento de íris. Com uma amostra clínica pequena e sem pares comparáveis do mesmo olho, a extensão clínica continua exploratória.

## Antes de outro refinamento: decisões de método sugeridas

1. Definir separadamente anel de referência, região visível anotada, região utilizável e interseção do par. Registrar área relativa e pixels absolutos, sem inventar referência para pupila ou lesão.
2. Tratar os 70% como referência normativa contextual. Uma eventual análise de conformidade precisa implementar a métrica e os demais requisitos aplicáveis; não basta substituir o denominador da nossa curva.
3. Comparar posição e forma da perda com a mesma quantidade removida. A hipótese de que localização importa é testável; não presumir equivalência entre oclusão cinza e dano ocular.
4. Medir desempenho da cadeia completa, com limiar e critérios pré-especificados, falhas mantidas e intervalos por pessoa/olho. Diferenciar FMR por comparação, FPIR por busca 1:N e rank-1. [ISO/IEC 19795-1](https://www.iso.org/standard/73515.html), [IREX IX](https://doi.org/10.6028/NIST.IR.8207).
5. Na extensão clínica, distinguir mudanças de geometria, obstrução e textura. Preferir pares do mesmo olho e capturas comparáveis; controles normais de pessoas diferentes não isolam o efeito da patologia.
6. Reservar confirmação independente para o protocolo final. A validação já consultada no desenvolvimento deve continuar identificada como tal.

Estas sugestões são para um protocolo futuro. Nenhum peso, limiar, critério ou código de uma rodada ativa foi alterado nesta pesquisa.

## Rastreabilidade e limites desta pesquisa

- Fontes priorizadas: ISO, NIST, editoras científicas, repositórios dos próprios autores e PubMed/PMC para os resumos originais. Blogs e resumos comerciais não foram usados para sustentar um mínimo universal.
- Buscas incluíram `ISO iris 70 usable iris area`, `minimum visible iris area`, `partial iris recognition`, `ocular pathologies iris recognition`, `cataract surgery pupil dilation` e rastreio de referências dos artigos mais relevantes.
- Os níveis de acesso estão descritos em cada ficha. Artigos com somente resumo/trechos acessíveis não foram apresentados como lidos integralmente.
- Os metadados brutos estão em [metadados_doi.json](metadados_doi.json). Foram corrigidos os anos bibliográficos de fascículo versus depósito/online. As versões do mesmo artigo não foram contadas duas vezes.
- Não foi realizada metanálise: populações, algoritmos, qualidade, ranks, denominadores e modos de avaliação não são suficientemente uniformes para combinar percentuais como se fossem a mesma medida.
- PDFs públicos e seus hashes constam em [fontes_acessadas.json](fontes_acessadas.json). O leitor de PDFs foi instalado em pasta isolada; o ambiente SAM3 permaneceu intacto.
