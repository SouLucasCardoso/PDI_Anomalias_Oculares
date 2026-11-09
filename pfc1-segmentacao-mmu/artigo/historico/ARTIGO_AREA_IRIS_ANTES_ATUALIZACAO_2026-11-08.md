# INFLUÊNCIA DA ÁREA PRESERVADA DA ÍRIS NA IDENTIFICAÇÃO OCULAR SOB OCLUSÕES CONTROLADAS

Lucas Cardoso Rodrigues

Rodrigo Ramos Silva

**Resumo:** Este estudo investigou a menor fração nominal da região visível da íris que manteve critérios de identificação ocular sob oclusões digitais superiores e inferiores. Utilizou-se o UBIPr segmentado, com partições por pessoa, extração automática e fusão de representações RGB e polares. A avaliação entre sessões manteve uma fotografia por consulta, lateralidade informada e 16 candidatos do mesmo lado. Modelo, cadastro e limiar permaneceram congelados nas intervenções. Todas as 486 consultas de teste foram mantidas, incluindo falhas e seis referências sem área definida. Exigiram-se Rank-1 e aceitação genuína de pelo menos 90%, com falsa correspondência empírica de até 1%. Sem perda adicional, obtiveram-se 91,36%, 92,39% e 0,88%, respectivamente. Na grade irregular estudada, as menores áreas nominais aprovadas foram 99,5% na orientação superior e 99% na inferior. A perda de 10% produziu diferença de Rank-1 de 24,07 pontos percentuais entre orientações. Pilotos posteriores não superaram conjuntamente os critérios. Em extensão exploratória, nove imagens clínicas com alterações explícitas da íris foram examinadas; dois olhos permitiram quatro consultas. O sistema original não identificou corretamente nenhuma, enquanto um controle de escala recuperou uma consulta e prejudicou outro cadastro. A evidência delimita a tolerância do processamento completo e identifica falhas de transferência de captura, sem estabelecer mínimo anatômico universal ou efeito causal de doenças. A reutilização dos conjuntos e a pequena amostra clínica impedem confirmação independente.

**Palavras-chave:** Biometria da íris. Identificação ocular. Oclusão controlada. Segmentação. Incerteza experimental.

## 1 INTRODUÇÃO

A identificação pela íris depende da obtenção de uma representação discriminativa da região ocular. A presença de pixels na imagem, contudo, não assegura que eles tenham sido corretamente localizados ou que preservem informação suficiente para separar identidades. O problema torna-se particularmente relevante quando parte da região visível está encoberta, apresenta reflexos ou sofre alterações de aparência. Para investigar essa relação, é necessário definir tanto a referência de área quanto o desempenho exigido do sistema.

A literatura de reconhecimento de íris estabelece a importância de localizar e normalizar a região antes da comparação. Daugman (2004) descreve um processamento que relaciona localização, representação da textura e decisão biométrica. Essa organização permite distinguir disponibilidade aparente de tecido, qualidade da representação e evidência para identificação. O presente trabalho adota essa distinção conceitual, sem reproduzir integralmente aquele reconhecedor ou transferir suas taxas de erro para imagens e modelos diferentes.

As condições oculares reais acrescentam dificuldades que ultrapassam a obstrução de uma fração de pixels. Trokielewicz, Czajka e Maciejewicz (2015) analisaram 2.996 imagens de 230 olhos e observaram interferência de obstruções, distorções e erros de segmentação na confiabilidade do reconhecimento. O estudo motiva examinar o processamento completo. Ele não permite converter diretamente a extensão de uma doença em uma porcentagem mínima de íris reconhecível para qualquer base ou algoritmo.

Uma intervenção digital oferece uma maneira delimitada de estudar o problema. Ao substituir uma quantidade conhecida de pixels da região anotada, pode-se comparar o desempenho antes e depois da alteração, preservando as identidades e o cadastro. A manipulação não constitui uma simulação clínica completa, mas permite investigar quanto a remoção de suporte em uma região específica interfere em um sistema previamente definido. Sua interpretação exige explicitar que o resultado depende da imagem, da segmentação, da normalização, do reconhecedor e da população avaliados.

A pergunta de pesquisa foi formulada da seguinte maneira: qual é a menor fração nominal preservada da região de íris definida pelo protocolo que mantém critérios biométricos estabelecidos, sob oclusões superiores e inferiores, em um sistema de identificação ocular entre sessões? O objetivo geral consistiu em estimar esse limite observado e quantificar sua incerteza. Os objetivos específicos compreenderam organizar partições por pessoa e lateralidade, reconstruir a segmentação automática, congelar o reconhecedor, aplicar intervenções de área conhecida, comparar as orientações e examinar a extração e a identificação em um pequeno conjunto clínico complementar.

O UBIPr foi escolhido por disponibilizar imagens da região ocular e uma versão segmentada de olhos individuais. A descrição oficial caracteriza a base como apropriada a estudos perioculares e solicita a citação de Padole e Proença (2012). Neste trabalho, a máscara predita restringe a extração à região classificada como íris. Ainda assim, erros dessa máscara podem introduzir suporte não iridiano ou excluir textura relevante; por isso, o resultado é atribuído ao sistema de identificação ocular assistido por segmentação.

A contribuição pretendida é experimental: apresentar uma fronteira de aprovação reproduzível, com denominadores, falhas e condições de captura explícitos, em vez de propor um número universal de área necessária. Também se examina se a posição da perda altera a resposta do sistema. O estudo possui abordagem quantitativa e utiliza dados públicos, intervenções digitais determinísticas e análise pareada. A discussão considera a aplicação do problema ao estudo de anomalias oculares, mas mantém separadas a evidência obtida com oclusões e as perguntas clínicas que exigiriam dados adicionais.

## 2 PROCEDIMENTOS EXPERIMENTAIS

### 2.1 MATERIAIS

#### 2.1.1 Base de imagens e partições

Utilizou-se a versão Single Eyes Segmented do UBIPr. Conforme a página oficial, sua distribuição é regida pela licença Creative Commons Atribuição Não Comercial Compartilha Igual 4.0, com obrigação de atribuição à base e às suas transformações (Padole; Proença, 2012). A unidade de identidade adotada foi o olho, definido pelo identificador da pessoa e pela lateralidade. Fotografias do olho esquerdo e do direito de uma mesma pessoa não foram tratadas como amostras genuínas entre si.

O manifesto local separou as pessoas entre treino, validação e teste, mantendo os dois olhos de cada participante na mesma partição. A etapa de segmentação considerou todos os pares de imagem e anotação dessas partições. Para o reconhecimento entre sessões, foram elegíveis os olhos com imagens tanto na sessão 1 quanto na sessão 2. Esse requisito de pareamento reduziu a população biométrica em relação à população utilizada para segmentação. A Tab. 1 apresenta os denominadores efetivamente empregados, sem identificá-los como a totalidade de todas as distribuições possíveis da base.

Tabela 1 — Partições e populações efetivamente avaliadas

| Etapa | Pessoas | Imagens | Cadastro S1 | Consultas S2 |
|---|---:|---:|---:|---:|
| Treino do manifesto | 183 | 7.716 | Não se aplica | Não se aplica |
| Validação de segmentação | 39 | 1.652 | Não se aplica | Não se aplica |
| Teste de segmentação | 39 | 1.650 | Não se aplica | Não se aplica |
| Validação biométrica pareada | 16 | 962 | 480 | 482 |
| Teste biométrico pareado | 16 | 960 | 474 | 486 |

Fonte: do autor (2026), a partir do manifesto e dos protocolos preservados.

O cadastro utilizou as capturas elegíveis da sessão 1, e cada consulta correspondeu a uma única captura da sessão 2. Não foram combinadas várias fotografias para formar uma consulta. O protocolo operacional exigiu que o lado do olho fosse informado corretamente; cada consulta competiu com os 16 olhos cadastrados do mesmo lado. Essa restrição mantém 15 comparações impostoras por consulta. Ela integra a definição da tarefa e impede extrapolar os resultados para identificação sem lateralidade informada ou para galerias de tamanho arbitrário.

No teste biométrico, 480 consultas apresentaram máscara de referência de íris não vazia e seis não possuíam área definida. As seis permaneceram na avaliação e foram mantidas inalteradas nas condições de oclusão. Não lhes foi atribuída uma porcentagem anatômica de aproveitamento. As duas falhas de extração da configuração final também foram mantidas no denominador. Assim, o subconjunto usado para calcular a perda efetiva de área não se confunde com o conjunto usado para medir o desempenho operacional.

#### 2.1.2 Recursos computacionais e representações

Os experimentos foram executados localmente em uma GPU NVIDIA RTX 3050 Laptop, com 6 GB de memória, utilizando Python 3.12 e PyTorch. Os roteiros registraram configurações, partições, históricos e hashes de arquivos. O relato explicita partições, seleção de modelos, falhas e limitações de generalização, aspectos recomendados para transparência em estudos de inteligência artificial com imagens médicas (Tejani et al., 2024), sem declarar aderência integral ou validação clínica pelo checklist. As matrizes de escores e os modelos selecionados foram preservados com verificação de integridade. Essas medidas de rastreabilidade permitem relacionar cada tabela ao experimento correspondente e recuperar resultados sem depender de registros informais de execução.

A segmentação empregou uma implementação compacta da família U-Net, com caminhos de contração e expansão, de acordo com o princípio descrito por Ronneberger, Fischer e Brox (2015). O reconhecimento combinou redes residuais, ConvNeXt e uma adaptação polar de DINOv3. As famílias ResNet e ConvNeXt são descritas por He et al. (2016) e Liu et al. (2022). DINOv3 fornece representações visuais pré-treinadas por aprendizagem autossupervisionada (Siméoni et al., 2025). A utilização dessas famílias não implica reproduzir integralmente seus experimentos originais.

A Tab. 2 resume os oito grupos da fusão final. O componente ArcIris provém do repositório público do Computer Vision Research Laboratory da University of Notre Dame, que descreve uma ResNet100 treinada com perda ArcFace para imagens polares (CVRL, 2026). A margem angular foi originalmente proposta no contexto de reconhecimento facial por Deng et al. (2019). Os pesos externos foram usados como fornecidos; não foi comprovada a ausência de sobreposição entre a população de pré-treinamento e a base avaliada.

Tabela 2 — Grupos da fusão congelada

| Grupo | Representação de entrada | Comparação | Peso |
|---|---|---|---:|
| ResNet18 RGB | Recorte automático de 128 × 128 | Vetor global | 1/8 |
| ResNet18 polar | Faixa de 64 × 512 | Vetor global | 1/8 |
| Espacial polar | Mapas intermediários da ResNet18 polar | Correspondência local | 1/8 |
| ResNet50 | Recorte RGB de 128 × 128 | Vetor global | 1/8 |
| ConvNeXt com contraste | Recorte RGB de 128 × 128 | Vetor global | 1/8 |
| ResNet50 nativa | Recorte direto de 224 × 224 | Vetor global | 1/8 |
| Transformer polar | Faixa de 64 × 512 | Vetor global | 1/8 |
| ArcIris em duas vistas | Polar cinza e canal vermelho | Dois vetores globais | 1/8 total |

Fonte: do autor (2026), a partir da configuração congelada. Cada vista ArcIris recebe peso efetivo de 1/16.

#### 2.1.3 Bases complementares e fontes técnicas

A preparação também contemplou o MMU e suas máscaras públicas, como etapa inicial de segmentação, sem diagnósticos por imagem no protocolo (Mohammad, s.d.; Kozlova, s.d.). Para dados clínicos, consultaram-se CatScreen, SLID, Nuclear Cataract e SLP-VLD, mantendo suas modalidades, licenças e identificadores separados (Khurshid et al., 2026; Xu et al., 2026; Cruz-Vega; Morales, 2023; Ignatowicz; Marciniak; Marciniak, 2025; Qian, 2026). A auditoria local encontrou 400 imagens na amostra CatScreen, 2.617 no SLID e 1.320 no Nuclear, das quais 335 tiveram rótulos recuperados da seleção secundária de 2025. As contagens são da cópia adquirida e não substituem as descrições dos depósitos. Nenhuma dessas fontes foi misturada ao UBIPr para fabricar controles saudáveis.

O SLP-VLD v3 contém 2.228 registros de fotografias de lâmpada de fenda e diagnósticos; a auditoria encontrou uma duplicata exata, preservada no inventário e removida das divisões que exigiam deduplicação. Os diagnósticos vieram das planilhas do depósito, não de respostas geradas por modelos de linguagem. A triagem literal de termos relacionados à íris selecionou nove imagens distintas de oito olhos codificados. Seis olhos só possuíam uma captura disponível; dois tinham capturas repetidas elegíveis no manifesto clínico anterior. As imagens e descrições são dados públicos com licença CC BY 4.0 registrada pelos autores (Qian, 2026); não se realizou novo diagnóstico ou exame médico.

Na triagem de ferramentas, foram consultados SAM, SAM 2, SAM 3 e OpenIRIS, além do Iris-SAM para segmentação especializada (Kirillov et al., 2023; Meta AI, s.d.a; Meta AI, s.d.b; Worldcoin, s.d.; Farmanifard; Ross, 2024). Esses recursos não substituíram a U-Net no sistema de referência. Seus testes locais de execução ou viabilidade não equivalem a validação biométrica clínica. Os repositórios foram tratados como fontes de implementação e pesos, e não como garantia de desempenho transferível ao UBIPr ou ao SLP-VLD.

### 2.2 MÉTODOS

#### 2.2.1 Organização do desenvolvimento e congelamento

As identidades de treino foram utilizadas para ajustar os extratores. A validação orientou a seleção de checkpoints e de configurações, incluindo a exigência de lateralidade informada e a composição da fusão. Essa validação foi reutilizada em diversas tentativas e não representa confirmação independente. A configuração final, suas estatísticas de normalização e o limiar foram congelados antes das intervenções aqui analisadas.

O extrator RGB ResNet18 herdou o treinamento de identidade ocular com margem angular em recortes de referência. Uma adaptação para recortes automáticos incluiu a época zero como controle e não substituiu esse ponto inicial. O extrator polar selecionou a época 20; as ResNet50 de 128 e 224 pixels selecionaram as épocas 21 e 11; o ConvNeXt selecionou a época 18; e o transformer polar, a época 16. A seleção ocorreu na validação, por aceitação genuína no alvo empírico de falsa correspondência, com desempate por Rank-1, conforme os registros de cada treinamento.

O transformer utilizado é uma adaptação dos seis primeiros blocos de um ViT-L/16 DINOv3, com projeção dos tokens da faixa polar para um vetor de 256 dimensões. O token de classificação e os quatro tokens de registro não participam da saída espacial. Esse extrator não equivale ao modelo DINOv3 completo. Nos encoders ajustados localmente, o classificador de treinamento representa as classes de treino e não funciona como a lista de identidades do teste; a identificação posterior é feita por comparação com os cadastros disponíveis.

O conjunto de teste já havia sido examinado por estratégias anteriores durante a reconstrução do projeto. Portanto, a avaliação final e seu refinamento são exploratórios. A separação por pessoa evita ajustar os pesos locais com imagens das identidades de teste, mas não elimina o viés decorrente de decisões tomadas após observar resultados anteriores. Nenhum limiar foi recalibrado para obter aprovação de uma condição ocluída.

#### 2.2.2 Segmentação e extração da região

A U-Net recebeu imagens RGB de 320 × 240 pixels, com intensidades divididas por 255. Foram utilizadas oito características de base, quatro classes e uma função de perda que soma entropia cruzada e um termo de Dice para as classes de primeiro plano. As classes corresponderam a fundo ou pupila, íris, esclera e sobrancelha. A pupila não constituiu uma classe independente. O ajuste usou AdamW, taxa de aprendizado de 0,001, decaimento de pesos de 0,0001, lote 32, semente 42 e até 30 épocas, com seleção pelo Dice médio de primeiro plano na validação.

A classe predita como íris foi redimensionada para a resolução nativa por vizinho mais próximo. Nos ramos RGB, os pixels exteriores à máscara receberam zero, e a caixa envolvente foi ampliada por uma margem proporcional de 25%. Os ramos de 128 pixels foram redimensionados a partir desse recorte. O ramo nativo de 224 pixels partiu diretamente da imagem original, sem reconstruir detalhe a partir do cache de 128 pixels ou aplicar super-resolução. Assim, as duas resoluções representam entradas operacionais distintas.

Nos ramos polares, a região envolvente recebeu margem de 50%. O maior contorno externo da máscara foi aproximado por uma elipse. A borda interna foi estimada a partir do maior buraco fechado plausível; quando indisponível, utilizou-se um círculo concêntrico calculado da caixa da máscara, com raio igual a um oitavo de seu menor lado. Esse círculo é uma aproximação geométrica, não uma pupila anotada ou um regressor aprendido. As tentativas posteriores de substituir esse mecanismo não foram incorporadas ao reconhecedor congelado.

Entre as bordas interna e externa foram amostradas 64 posições radiais e 512 angulares, produzindo uma faixa de textura. A vista cinza recebeu equalização adaptativa de histograma com limite de contraste, ou CLAHE, com limite 2 e grade de 8 × 8 regiões. Uma segunda vista utilizou o canal vermelho. As posições fora do suporte predito receberam intensidade neutra 127. O parâmetro geométrico utilizado na normalização é uma aproximação da máscara visível; não constitui medida da superfície anatômica total.

Figura 1 — Fluxo do processamento e separação entre intervenção e reconhecimento

![Fluxo do processamento](figuras/fluxo_experimental.png)

Fonte: do autor (2026). A referência de área atua somente na intervenção digital.

A Fig. 1 destaca a separação entre a anotação usada para selecionar os pixels alterados e a máscara produzida automaticamente para extrair características. Após cada intervenção, o segmentador recebeu a fotografia alterada. Consequentemente, uma perda de suporte pode modificar também o recorte, o contorno interno e a parametrização polar. O experimento mede esse processamento completo; não isola exclusivamente a retirada de informação da textura mantendo a geometria original.

#### 2.2.3 Comparação de identidades e fusão

Para os descritores globais locais, foram calculadas similaridades entre cada consulta e as capturas válidas do cadastro. O escore por olho foi a média das três maiores similaridades disponíveis, com o cadastro original mantido em todas as condições. Essa agregação de cadastro não representa uma consulta composta por várias fotografias. O ramo espacial comparou mapas intermediários de textura com protótipos do cadastro, mantendo a regra registrada antes da avaliação.

Os escores ArcIris utilizaram uma transformação angular da similaridade cosseno. Cada componente foi padronizado pelas estatísticas de comparações impostoras válidas da validação. Os sete grupos compartilhados receberam peso de um oitavo cada, e as duas vistas ArcIris receberam um dezesseis avos cada. Logo, nove matrizes de componentes correspondem a oito grupos de peso igual; não se atribuiu ao ArcIris peso duplo por possuir duas vistas.

Para um escore de componente s, a padronização foi expressa por z = (s − μ)/σ, em que μ e σ são a média e o desvio de impostores da validação. A média ponderada passou por uma transformação logística. Em seguida, os escores disponíveis de cada consulta foram transformados de volta ao domínio logit, padronizados entre seus candidatos e novamente submetidos à logística. Essa normalização usa os escores daquela consulta, sem acessar sua identidade verdadeira. Entretanto, o resultado depende do conjunto de candidatos e de seu tamanho.

O limiar final foi 0,8581747485460748, calibrado no desenvolvimento e preservado no teste. A disponibilidade de uma comparação exigiu os componentes necessários da fusão. Consultas com falha permaneceram como erros na identificação e rejeições na comparação genuína. Comparações indisponíveis foram rejeitadas e permaneceram no denominador previsto. Essa política penaliza falhas em Rank-1 e TAR e deve ser considerada ao interpretar a FMR, pois rejeitar comparações indisponíveis pode reduzi-la.

#### 2.2.4 Intervenções e definição da fronteira

A referência de área foi a máscara anotada da íris na fotografia original. Para uma referência não vazia com N pixels e uma perda nominal p em porcentagem, foram selecionados n = round(N × p/100) pixels. A fração efetivamente preservada foi calculada pela Eq. 1. O arredondamento é aplicado por imagem e pode produzir diferenças entre a porcentagem nominal e a efetiva.

Eq. 1 — A = 100 × (N − n)/N, para N > 0.

Na orientação superior, a ordem de seleção percorreu linhas de cima para baixo; na inferior, de baixo para cima. Empates dentro da linha seguiram a posição horizontal. Os pixels selecionados foram substituídos por cinza de intensidade 128, sem alterar o exterior da referência. A mesma referência original definiu todas as intervenções. Não se utilizou a máscara predita para escolher quantos pixels remover, evitando que a quantidade nominal variasse com a qualidade da segmentação automática.

Para referências vazias, a área não foi definida e a fotografia permaneceu inalterada. O valor nominal de 100% significa ausência de perda adicional em relação à região anotada visível, que pode já excluir partes encobertas pelas pálpebras. Não corresponde necessariamente a toda a íris anatômica. Também não demonstra que cada pixel preservado contenha informação útil ao reconhecedor.

A busca inicial avaliou perda de 10% nas duas orientações e interrompeu a descida de área na primeira falha. O refinamento seguinte considerou perdas inteiras até a primeira reprovação. Por fim, uma rodada limitada previamente a dois pontos acrescentou perda superior de 0,5% e inferior de 1,5%, executando ambas independentemente do resultado da primeira. Os pesos, o cadastro e o limiar permaneceram fixos.

As grades finais de perda foram 0; 0,5; 1; 10% na superior e 0; 1; 1,5; 2; 10% na inferior. A fronteira corresponde à menor área do prefixo em que todas as áreas maiores testadas passaram os critérios. Trata-se de grades irregulares explícitas, sem interpolação ou garantia de monotonicidade entre níveis. Não se avaliou perda inferior de 0,5%; portanto, não se pode anunciar uma fração comum de 99,5% aprovada nas duas orientações.

#### 2.2.5 Métricas e tratamento da incerteza

O Rank-1 foi definido como a proporção de consultas para as quais o olho correto obteve o maior escore. A taxa de aceitação genuína, ou TAR, foi a proporção de consultas cujo escore do olho verdadeiro alcançou o limiar. A taxa de falsa correspondência, ou FMR, foi a proporção de comparações impostoras aceitas. Essas medidas não são equivalentes: um genuíno pode superar o limiar e ainda perder para um candidato errado.

As métricas de teste utilizaram 486 comparações genuínas e 7.290 impostoras. O critério operacional foi definido como Rank-1 e TAR de pelo menos 90%, simultaneamente à FMR de até 1%. Ele expressa uma escolha deste experimento e não uma norma clínica ou um requisito universal de implantação. Também foi registrada a proporção conjunta de consultas identificadas corretamente e aceitas, sem substituí-la por nenhuma das outras métricas.

A incerteza foi estimada por 5.000 reamostragens de participantes com reposição, semente 20261001. Cada sorteio preservou as consultas dos participantes selecionados e foi compartilhado pelas condições comparadas. O cadastro e o limiar permaneceram fixos. Os intervalos de 95% foram calculados pelos percentis das distribuições reamostradas. Para aprovações nos limites de 90% e 1%, foram utilizadas comparações de contagens inteiras, evitando alterações por arredondamento numérico.

As frequências de reamostras que passaram os três critérios descrevem estabilidade amostral; não são probabilidades posteriores de sucesso na população. Os intervalos são pontuais e não corrigem comparações múltiplas ou seleção de modelos. Uma segunda implementação reproduziu a análise agregada das condições anteriores a partir de 96 linhas de contagens por pessoa e condição. Os novos pontos receberam auditoria de componentes, decisões, área efetiva e preservação das entradas que deveriam permanecer inalteradas.

#### 2.2.6 Pilotos posteriores e separação da calibração

Os ajustes posteriores usaram 151 pessoas do treino para gradientes ou estimação de parâmetros, 16 para calibração interna e 16 do monitor antigo para avaliação após congelamento. Os encoders anteriores já haviam visto essas pessoas; a separação desta etapa não transforma o monitor reutilizado em teste independente. No reteste com oclusões diversas, mantiveram-se 6.067 fotografias e 3.222 intervenções superiores/inferiores sorteadas de 1% a 20%, com níveis de cinza fixados antes do treino. Dez vistas com falha de extração tiveram sua contribuição nas perdas de identidade zerada; o peso das demais e os denominadores de avaliação foram preservados. Executaram-se oito épocas, selecionadas pela perda de ajuste com preservação do limpo interno.

O piloto estrutural aprendeu oito regressões regionais ridge, uma por setor angular do mapa polar intermediário, para aproximar o descritor global limpo da mesma foto de ajuste. A regularização de 0,01 e a fusão de 75% global e 25% regional foram fixadas previamente. Compararam-se seis das oito maiores concordâncias por par, com controle usando todos os setores. A comparação por regiões possui precedentes, mas este piloto não reproduz o método de saliência humana estudado em imagens pós-morte por Boyd et al. (2023). Os setores têm campos receptivos sobrepostos e não representam porcentagens isoladas da área física da íris.

Cada método recebeu um único limiar a partir do grupo interno limpo, visando FMR empírica de 0,5%, aplicado sem alteração ao monitor. A barreira de avanço exigiu preservar a condição limpa e melhorar Rank-1 e TAR nas duas oclusões, mantendo FMR de até 1%. Os controles foram reportados sem escolher retrospectivamente o melhor resultado e sem calibrar sobre os casos ocluídos do monitor. Essas rodadas são desenvolvimento complementar e não entram na estimação da fronteira principal.

#### 2.2.7 Estudo complementar de casos clínicos

Dos oito olhos com diagnóstico explícito da íris, dois possuíam capturas repetidas no manifesto clínico previamente preparado: um olho com cisto de íris e alterações corneanas, e um com laceração da íris e acompanhamentos após tratamento. A primeira captura de cada olho foi cadastro e as quatro capturas posteriores foram consultas. Datas e identidade provêm dos códigos distribuídos; não foram confirmadas por prontuário independente. O cadastro de cada lado incluiu o olho alvo e os primeiros 15 outros olhos elegíveis, ordenados por código e nome de arquivo, sem seleção por qualidade ou escore. Ao todo, processaram-se 42 fotografias: 32 de cadastro, quatro consultas e seis casos adicionais sem cadastro elegível.

A fusão principal e o limiar UBIPr foram transportados sem ajuste, mantendo as falhas no denominador. A avaliação clínica anterior já havia exposto esse domínio e as capturas; não se considera esta extensão um teste cego. Após inspecionar as falhas originais, registrou-se um controle posterior de escala: a foto clínica foi reduzida para 106 × 80 pixels dentro de uma entrada 320 × 240 preenchida com cinza 128. A máscara foi mapeada de volta ao original, de onde vieram os pixels do recorte. Não houve reconstrução de textura, treino ou busca entre escalas. O controle alterou somente a apresentação à U-Net e foi executado também sobre os cadastros.

Registraram-se pixels previstos como íris, razão entre máscara e fotografia e fração de suporte da grade polar estimada. Nenhuma dessas medidas foi tratada como porcentagem anatômica preservada. Sem máscara clínica de referência, não se calculou Dice clínico. Duas imagens com rótulo exato Normal eye foram selecionadas por ordem de arquivo e pessoas distintas para ilustração, sem medir seu reconhecimento nessa prancha. A ausência de diagnóstico no UBIPr não foi interpretada como ausência de anomalias.

## 3 RESULTADOS E DISCUSSÃO

### 3.1 SEGMENTAÇÃO E DESEMPENHO ORIGINAL

A segmentação completou 30 épocas, selecionando a época 26 pela validação. O Dice médio de primeiro plano na validação foi 0,8887. No teste completo de segmentação, o Dice da íris foi 0,9342 e o Dice médio das classes de primeiro plano foi 0,8944. Esses valores se referem às 1.650 imagens de teste de segmentação, e não somente às 960 imagens pareadas da avaliação biométrica. A distinção impede associar diretamente o Dice global às taxas de identificação da população entre sessões.

A Tab. 3 apresenta o desempenho original da fusão congelada. A validação biométrica manteve quatro falhas entre 482 consultas; o teste manteve duas entre 486. A diferença entre Rank-1, TAR e sucesso conjunto confirma que aceitar o genuíno não equivale a classificá-lo como primeiro candidato. O resultado de teste passou os critérios pontuais, fornecendo a condição de referência necessária à investigação da área.

Tabela 3 — Desempenho sem oclusão adicional

| Medida | Validação | Teste |
|---|---:|---:|
| Rank-1 | 90,04% (434/482) | 91,36% (444/486) |
| TAR | 90,66% (437/482) | 92,39% (449/486) |
| FMR | 0,9820% (71/7.230) | 0,8779% (64/7.290) |
| Identificação correta e aceitação | 88,38% (426/482) | 89,71% (436/486) |
| Consultas com falha | 4 | 2 |

Fonte: do autor (2026), a partir das matrizes finais preservadas.

O desempenho original fornece uma margem limitada em relação ao alvo de 90%. No teste, a aprovação de Rank-1 exige pelo menos 438 acertos; a condição original apresentou 444. Dessa maneira, alterações de poucas consultas podem mudar a classificação de aprovação sem representar uma transição anatômica abrupta. A interpretação da fronteira deve considerar essa discretização da métrica, além da discretização da área em pixels.

### 3.2 FRONTEIRA OBSERVADA POR ORIENTAÇÃO

A Tab. 4 reúne todas as condições efetivamente avaliadas com o reconhecedor congelado. Com perda superior de 0,5%, obtiveram-se 443 identificações corretas, 449 genuínos aceitos e 65 impostores aceitos. Os três critérios foram atendidos. Com perda superior de 1%, o número de identificações corretas caiu para 437, um abaixo do mínimo inteiro exigido, embora TAR e FMR permanecessem aprovadas.

Tabela 4 — Área nominal preservada e desempenho nas condições avaliadas

| Condição | Área (%) | Rank-1 (%) | TAR (%) | FMR (%) | Aprova |
|---|---:|---:|---:|---:|---|
| Original | 100 | 91,36 | 92,39 | 0,8779 | Sim |
| Superior 0,5% | 99,5 | 91,15 | 92,39 | 0,8916 | Sim |
| Superior 1% | 99 | 89,92 | 92,39 | 0,8779 | Não |
| Inferior 1% | 99 | 90,95 | 91,36 | 0,9328 | Sim |
| Inferior 1,5% | 98,5 | 89,09 | 88,89 | 1,0151 | Não |
| Inferior 2% | 98 | 87,45 | 87,86 | 1,2346 | Não |
| Superior 10% | 90 | 82,30 | 84,98 | 1,6872 | Não |
| Inferior 10% | 90 | 58,23 | 60,29 | 2,6063 | Não |

Fonte: do autor (2026). As áreas são nominais e as grades de perda são irregulares.

Na orientação inferior, a perda de 1% passou os critérios, com 442 identificações corretas e 444 aceitações genuínas. A condição nova de 1,5% apresentou 433 acertos, 432 aceitações genuínas e 74 impostores aceitos, reprovando as três medidas. A FMR correspondente foi 1,0151%; arredondá-la para 1% mudaria indevidamente a decisão. Em 7.290 comparações, o máximo inteiro de impostores aceitos compatível com o limite é 72.

O menor aproveitamento nominal aprovado no prefixo da grade foi, portanto, 99,5% na superior e 99% na inferior. A próxima área testada reprovada foi 99% na superior e 98,5% na inferior. Esses pares delimitam os níveis observados de aprovação e reprovação; não comprovam a posição de uma transição contínua entre eles nem que todos os níveis menores necessariamente falhem.

Entre as frações testadas nas duas orientações, o prefixo comum permaneceu restrito à condição original de 100%. A ausência do ponto inferior de 0,5% impede confirmar 99,5% para as duas regiões, mesmo que 99% tenha passado na inferior. Inferir esse resultado exigiria pressupor uma monotonicidade que não foi estabelecida. A distinção entre limites por orientação e limite comum evita apresentar uma porcentagem global sem apoio na grade efetivamente executada.

### 3.3 INFLUÊNCIA DA REGIÃO E INCERTEZA AMOSTRAL

Com a mesma perda nominal de 10%, o Rank-1 foi 82,30% na superior e 58,23% na inferior. A diferença pareada foi 24,07 pontos percentuais, com IC95% de 10,83 a 36,25. Em relação ao original, as perdas de Rank-1 foram 9,05 pontos na superior e 33,13 na inferior. Seus intervalos pareados foram, respectivamente, 2,50 a 17,68 e 23,13 a 43,62 pontos. Esses resultados indicam que a posição da intervenção importa no processamento avaliado, além de sua quantidade nominal.

Esse comportamento não significa que a região inferior contenha universalmente mais informação biométrica. A substituição de pixels pode alterar o maior contorno, a presença do buraco interno ou a geometria polar. A resposta inclui a informação removida e a instabilidade introduzida nas etapas seguintes. Sem uma intervenção adicional que fixe geometricamente a extração, não se separa a contribuição causal de cada mecanismo; mesmo tal diagnóstico exigiria uma imagem original disponível e não representaria uma melhoria operacional de consulta única.

Figura 2 — Estimativas e intervalos de 95% por condição

![Intervalos das métricas](figuras/intervalos_condicoes.png)

Fonte: do autor (2026). Intervalos pontuais por participante, com cadastro e limiar fixos; pontos não representam uma curva contínua de área.

A Fig. 2 apresenta a incerteza das oito condições, sem interpolar níveis ausentes. Para a condição original, o IC95% de Rank-1 foi 85,19 a 95,73%; para TAR, 86,25 a 96,71%; e para FMR, 0,53 a 1,28%. Logo, passar o critério pontual não equivale a demonstrar que limites populacionais de desempenho foram garantidos. O número de consultas não substitui o número de participantes independentes, pois várias imagens provêm da mesma pessoa.

No ponto superior de 0,5%, os intervalos de Rank-1, TAR e FMR foram 85,00–95,63%, 86,04–96,88% e 0,54–1,26%. Na inferior de 1,5%, foram 81,07–94,72%, 80,66–94,84% e 0,65–1,38%. As duas condições passaram conjuntamente os critérios em 62,00% e 26,32% das reamostras, respectivamente. Essas frequências descrevem sensibilidade à composição da amostra e não autorizam interpretar o mínimo como uma constante clínica conhecida com essas probabilidades.

Na grade inferior anterior de 0, 1 e 2% de perda, 34,58% das reamostras reprovaram já na condição original, ficando sem prefixo aprovado; 15,56% ficaram restritas a 100% preservados; 42,22% chegaram a 99%; e 7,64% chegaram a 98%. A distribuição caracteriza somente aquela grade disponível. Ela foi mantida como análise de estabilidade e não usada para recalibrar o limiar, excluir participantes ou selecionar uma porcentagem favorável.

### 3.4 DISCRETIZAÇÃO DA ÁREA E FALHAS

A Tab. 5 mostra que as perdas nominais não produzem a mesma fração efetiva em todas as referências. Com perda superior nominal de 0,5%, uma das 480 referências definidas recebeu zero pixels selecionados devido ao arredondamento. Esse caso é diferente das seis referências vazias, para as quais não se definiu área. Todos permaneceram nas métricas. A aparente precisão de meio ponto percentual não elimina a discretização da imagem nem a incerteza amostral.

Tabela 5 — Perda efetiva de pixels nos dois pontos adicionados

| Perda nominal (%) | Média efetiva (%) | Mínimo a máximo (%) | Referências definidas com zero pixels |
|---|---:|---|---:|
| Superior 0,5 | 0,4986 | 0 a 0,5455 | 1 |
| Inferior 1,5 | 1,5001 | 1,4545 a 1,6949 | 0 |

Fonte: do autor (2026), em 480 referências não vazias. As seis referências vazias não integram essas médias.

A retenção das referências vazias no denominador operacional influencia a classificação pontual da fronteira. Na análise secundária das 480 referências definidas, a condição superior de 1% apresentou 90,83% de Rank-1, 93,13% de TAR e 0,85% de FMR, enquanto a avaliação principal de 486 consultas reprovou em Rank-1. Esse resultado foi preservado como sensibilidade de denominador, sem substituir a análise principal para recuperar uma aprovação.

As falhas também mostram por que uma taxa de falsa correspondência baixa não pode ser interpretada isoladamente. Quando um extrator não fornece uma comparação utilizável, a rejeição evita uma falsa aceitação, mas impede a aceitação genuína. Relatar apenas comparações bem-sucedidas ocultaria parte desse comportamento. Neste protocolo, a disponibilidade, a aceitação e a posição do candidato correto foram registradas separadamente e mantidas nos resultados.

### 3.5 DESENVOLVIMENTO POSTERIOR E CONTROLES

Foram investigadas alternativas de localização da pupila e de adaptação de descritores após a configuração de referência, sem substituí-la nas curvas apresentadas. Um localizador circular supervisionado por buracos nas anotações reduziu sua perda geométrica interna, mas a validação com calibração fixa apresentou FMR de 1,0235%. A recalibração limpa apresentou TAR de 89,8340%. Nenhuma das duas variantes cumpriu simultaneamente os critérios naquela rodada.

Uma saída elíptica com 8.194 parâmetros foi então ajustada mantendo centro e raio equivalente do localizador circular congelados. Na validação, o Rank-1 permaneceu em 90,0415%. A variante recalibrada apenas na condição limpa teve TAR de 90,0415% e FMR de 0,9820%, passando os critérios limpos, mas sem superar a referência, cujo TAR foi 90,6639%. As condições com oclusão de 10% continuaram abaixo da meta. A redução de erro de um alvo geométrico aproximado não demonstrou, portanto, melhora global de identificação.

Um transporte residual de descritores polares foi ajustado em 200 fotografias alteradas das pessoas de treino e monitorado em outras 55 fotografias alteradas. A similaridade média com o descritor original melhorou de 0,6842 para 0,8506 no ajuste, mas caiu de 0,7401 para 0,6613 no monitor, acompanhada de redução da TAR interna. A barreira de desenvolvimento previamente registrada falhou, e essa adaptação não foi avaliada na validação principal ou no teste.

Essas tentativas documentam resultados negativos e limites de alterações específicas. Seus alvos geométricos não são anotações anatômicas independentes da pupila. Além disso, as pessoas do monitor do transporte já haviam sido vistas pelo encoder original, e as validações geométricas foram reutilizadas. Os resultados internos dessas etapas não devem ser misturados às estimativas de teste ou anunciados como aumento de generalização. A fronteira deste artigo permanece vinculada ao reconhecedor original congelado.

Além dos controles geométricos, o reteste de oito épocas com vistas inválidas corrigidas preservou 479/480 identificações e aceitações no monitor limpo. Sob perda superior/inferior de 10%, o Rank-1 foi 82,71%/65,42%, o TAR foi 79,38%/57,92% e a FMR foi 1,3333%/1,2639%. A correção eliminou um alvo de treinamento inadequado, mas não produziu superioridade conjunta e não recebeu nova avaliação no teste principal.

Na destilação regional, a fusão primária preservou os mesmos acertos limpos e reduziu a FMR ocluída para 0,9167%/0,8472%. O Rank-1 foi 82,71%/61,88%, porém o TAR caiu para 75,63%/51,46%, contra 76,88%/53,96% do componente global original nessa rodada. O controle com todos os setores teve Rank-1 idêntico, impedindo atribuir a redução de FMR exclusivamente ao descarte regional. Portanto, atingir FMR abaixo de 1% em um monitor não resolveu a meta de identificação e aceitação genuína. Nenhum desses pilotos foi promovido.

### 3.6 CASOS CLÍNICOS E TRANSFERÊNCIA DE CAPTURA

A Tab. 6 resume as quatro consultas de dois olhos, com 16 candidatos nominais por lado e o limiar da referência. O sistema original não produziu identificação correta ou aceitação genuína. Uma comparação genuína estava indisponível porque a máscara do cadastro do olho com cisto ficou vazia. No outro olho, o cadastro era computacionalmente disponível, mas as máscaras extraíam fragmentos pequenos. O resultado não mede exclusivamente discriminação da textura e não demonstra efeito causal da condição ocular.

Tabela 6 — Extensão clínica com pesos e limiar congelados

| Processamento | Identificações corretas | Aceitações genuínas | Falsas correspondências | Genuínos indisponíveis |
|---|---:|---:|---:|---:|
| Original | 0/4 | 0/4 | 1/60 (1,67%) | 1/4 |
| Controle de escala 1/3 | 1/4 | 1/4 | 2/60 (3,33%) | 3/4 |

Fonte: do autor (2026), dados SLP-VLD. Controle definido após a falha original; mesmas consultas, cadastros e limiar. As quatro consultas não são quatro pessoas independentes.

O controle de escala recuperou o cadastro do olho com cisto e sua consulta foi identificada e aceita, com escore genuíno de 0,87538, superior ao limiar 0,85817. Entretanto, a máscara de cadastro do olho com laceração tornou-se vazia, indisponibilizando as outras três comparações genuínas. Não se escolheu a melhor escala por olho nem se excluíram falhas para reportar ganho. Uma falsa correspondência já representa 1,67% em 60 pares; a amostra não sustenta uma garantia populacional de FMR de até 1%.

A Fig. 3 apresenta controles com rótulo Normal eye e casos com alterações da íris na mesma base. A U-Net original produz recortes fragmentados também nos exemplos normais. Isso evidencia um confundidor de domínio de captura, sem provar que a escala explique todas as falhas. A melhora visual de alguns recortes não foi convertida em Dice ou percentual anatômico, pois falta anotação independente. O cadastro com laceração ilustra a falha do controle, preservando resultados favoráveis e desfavoráveis.

Figura 3 — Recortes de olhos rotulados como normais e com alterações da íris

![Recortes clínicos](figuras/recortes_clinicos.png)

Fonte: adaptação do autor (2026) de Qian (2026), SLP-VLD v3, CC BY 4.0. De cima para baixo: dois rótulos Normal eye, cisto de íris com comorbidades e laceração da íris. Colunas: fotografia, recorte original e controle de escala 1/3. Não se realizou novo diagnóstico médico.

O estudo de patologias de Trokielewicz, Czajka e Maciejewicz (2015) destaca a importância da segmentação para a confiabilidade do reconhecimento. Os casos presentes são compatíveis com a necessidade de examinar essa etapa, mas não reproduzem a população, a modalidade ou os reconhecedores daquele trabalho. As condições clínicas coexistem com diferenças de dilatação, iluminação, enquadramento, tratamento e qualidade; não se atribui toda discrepância de reconhecimento à doença.

Também se reaproveitaram as 482 consultas UBIPr de validação para descrever suporte polar natural, sem nova inferência de reconhecimento. Houve um acerto e aceitação em uma consulta com suporte de 47,36%; abaixo de 75%, porém, eram apenas cinco consultas, das quais três identificadas. Esses casos não estabelecem um mínimo global: suporte da grade polar, área nominal de intervenção e área anatômica são grandezas distintas. A seleção ilustrativa por suporte não substitui a análise de todas as consultas.

### 3.7 LIMITAÇÕES E RELAÇÃO COM ANOMALIAS OCULARES

A principal limitação estatística é a população de 16 participantes na avaliação biométrica de teste. As 486 consultas permitem observar repetição entre capturas, mas não representam 486 pessoas independentes. A reamostragem por participante considera parte dessa dependência e mantém fixos o cadastro e o limiar. Ela não incorpora novas sessões de cadastramento, diferentes sensores, sementes de treinamento, outras composições de galeria ou erros de anotação.

O teste foi examinado durante o desenvolvimento de estratégias anteriores. As inferências de área e os dois novos pontos de refinamento são, por isso, exploratórios. A separação por pessoa no ajuste local não elimina o efeito de escolhas informadas pela experiência acumulada no mesmo conjunto. Também não foi possível comprovar a independência das identidades do UBIPr em relação a toda a população de pré-treinamento externo do ArcIris e dos modelos de representação visual.

A tarefa é de identificação em conjunto fechado: os olhos consultados pertencem ao cadastro e o lado é informado. Não foi avaliado um fluxo de pessoas desconhecidas, cadastramento incremental ou detecção de ataques de apresentação. A normalização entre os 16 candidatos torna o escore dependente da galeria. O limiar e as taxas não devem ser transportados diretamente para outra quantidade de pessoas, para consulta sem lateralidade ou para fotografias de celular obtidas sem protocolo compatível.

O suporte considerado foi a íris visível definida pela anotação original. Parte da superfície anatômica pode estar naturalmente encoberta antes da intervenção. Uma máscara predita pode omitir textura da íris ou incluir pixels de outras estruturas. A identificação pode explorar informação de cor, geometria e aparência do suporte disponível, não apenas uma textura iridiana isolada e anatomicamente perfeita. O limite encontrado descreve o sistema completo, sem provar que todos os pixels preservados sejam necessários ou igualmente informativos.

A relação com anomalias oculares permanece exploratória, apesar da extensão com casos rotulados. O número de olhos repetidos e as falhas de cadastro impedem uma estimativa clínica geral. Uma doença pode alterar geometria, transparência, textura, reflexão ou condições de aquisição. O cinza artificial remove a aparência de pixels selecionados, mas não reproduz todas essas mudanças. A evidência permite afirmar que perdas localizadas podem interferir de maneira distinta no processamento estudado; não permite estimar a extensão clínica de uma doença a partir das porcentagens da tabela, atribuir causalidade de diagnóstico ou recomendar decisões assistenciais.

Também não é possível concluir que o desempenho de toda tecnologia de reconhecimento de íris esteja limitado a 91,36%. Esse número pertence à configuração, à amostra e às condições declaradas. Os mínimos elevados observados podem refletir a pequena margem do reconhecedor sobre o critério, além da qualidade dos dados e da instabilidade de extração. Um estudo de invariância da textura exigiria outro desenho, enquanto uma alegação clínica demandaria medidas anatômicas e diagnósticas independentes e controle das condições de aquisição.

## 4 CONSIDERAÇÕES FINAIS

O trabalho investigou a relação entre área preservada e identificação ocular por meio de intervenções controladas em dados públicos, mantendo modelo, cadastro e limiar congelados. A condição original apresentou 91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR, atendendo ao critério pontual definido. Na grade irregular executada, o menor aproveitamento nominal aprovado foi 99,5% para oclusão superior e 99% para inferior. As próximas áreas testadas, 99% na superior e 98,5% na inferior, reprovaram.

A pergunta de pesquisa foi respondida dentro desse protocolo, sem estabelecer um mínimo universal de íris anatômica. A aprovação dependeu da região afetada e apresentou incerteza amostral ampla. Com perda nominal de 10%, a oclusão inferior teve Rank-1 24,07 pontos percentuais abaixo da superior. O processamento inclui os efeitos da intervenção sobre segmentação e normalização, o que impede atribuir toda a queda exclusivamente à quantidade de textura removida.

Entre as frações avaliadas nas duas orientações, o prefixo comum continuou em 100%; não se avaliou perda inferior de 0,5%. As porcentagens por orientação não podem ser convertidas automaticamente em um limite comum ou em extensão de doença ocular. A manutenção das falhas e das referências vazias, a preservação dos escores e a verificação do processamento tornam explícitas essas condições de interpretação.

A extensão clínica mostrou um cadastro recuperado por controle de escala e outro prejudicado, sem aprovação de uma variante geral. Assim, a máscara predita não pode servir como denominador de tecido preservado antes de sua validação clínica. Como continuidade, recomenda-se avaliar participantes e capturas novos, com referência anatômica independente, e separar a perda de informação da instabilidade geométrica. Estudos clínicos precisariam documentar a condição ocular e os fatores de aquisição, sem pressupor equivalência com a oclusão digital. A contribuição atual consiste em uma fronteira observada e auditável, acompanhada de seus limites e de evidência quantitativa da influência da posição da perda.

## REFERÊNCIAS

BOYD, Aidan et al. Human Saliency-Driven Patch-Based Matching for Interpretable Post-Mortem Iris Recognition. In: IEEE/CVF Winter Conference on Applications of Computer Vision Workshops, 2023. p. 701–710. Disponível em: https://openaccess.thecvf.com/content/WACV2023W/XAI4B/html/Boyd_Human_Saliency-Driven_Patch-Based_Matching_for_Interpretable_Post-Mortem_Iris_Recognition_WACVW_2023_paper.html. Acesso em: 27 out. 2026.

CRUZ-VEGA, Israel; MORALES, Hans Israel. Nuclear Cataract Database for Biomedical and Machine Learning Applications. Mendeley Data, versão 2, 2023. Conjunto de dados. DOI: 10.17632/6wv33nbcvv.2. Disponível em: https://data.mendeley.com/datasets/6wv33nbcvv/2. Acesso em: 27 out. 2026.

CVRL. Notre Dame Open-Source Iris Recognition. University of Notre Dame, 2026. Disponível em: https://github.com/CVRL/OpenSourceIrisRecognition. Acesso em: 23 out. 2026.

DAUGMAN, John. How iris recognition works. IEEE Transactions on Circuits and Systems for Video Technology, v. 14, n. 1, p. 21–30, 2004. DOI: 10.1109/TCSVT.2003.818350. Disponível em: https://www.robots.ox.ac.uk/~az/lectures/est/iris.pdf. Acesso em: 23 out. 2026.

DENG, Jiankang; GUO, Jia; XUE, Niannan; ZAFEIRIOU, Stefanos. ArcFace: Additive Angular Margin Loss for Deep Face Recognition. In: IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2019. p. 4690–4699. Disponível em: https://arxiv.org/abs/1801.07698v1. Acesso em: 23 out. 2026.

FARMANIFARD, Parisa; ROSS, Arun. Iris-SAM: Iris Segmentation Using a Foundation Model. arXiv:2402.06497, 2024. Código e pesos dos autores. Disponível em: https://arxiv.org/abs/2402.06497. Repositório: https://github.com/ParisaFarmanifard/Iris-SAM. Acesso em: 27 out. 2026.

HE, Kaiming; ZHANG, Xiangyu; REN, Shaoqing; SUN, Jian. Deep Residual Learning for Image Recognition. In: IEEE Conference on Computer Vision and Pattern Recognition, 2016. Disponível em: https://arxiv.org/abs/1512.03385. Acesso em: 23 out. 2026.

IGNATOWICZ, Alicja Anna; MARCINIAK, Tomasz; MARCINIAK, E. AI-Powered Mobile App for Nuclear Cataract Detection. Sensors, v. 25, n. 13, artigo 3954, 2025. DOI: 10.3390/s25133954. Disponível em: https://doi.org/10.3390/s25133954. Acesso em: 27 out. 2026.

KHURSHID, Mahapara et al. CatScreen: A Large MultiModal Benchmark Dataset for Cataract Screening. Transactions on Machine Learning Research, 2026. Página e amostra dos autores. Disponível em: https://www.iab-rubric.org/resources/healthcare-datasets/catscreen. Acesso em: 27 out. 2026.

KIRILLOV, Alexander et al. Segment Anything. In: IEEE/CVF International Conference on Computer Vision, 2023. Disponível em: https://arxiv.org/abs/2304.02643. Código: https://github.com/facebookresearch/segment-anything. Acesso em: 27 out. 2026.

KOZLOVA, J. Masks for MMU Iris dataset. Repositório de máscaras, [s.d.]. Disponível em: https://github.com/jkozlova/Masks-for-MMU-Iris-dataset. Acesso em: 27 out. 2026.

LIU, Zhuang et al. A ConvNet for the 2020s. In: IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2022. Disponível em: https://arxiv.org/abs/2201.03545. Acesso em: 23 out. 2026.

META AI. SAM 2. Repositório oficial de código e modelos, [s.d.a]. Disponível em: https://github.com/facebookresearch/sam2. Acesso em: 27 out. 2026.

META AI. SAM 3. Repositório oficial de código e modelos, [s.d.b]. Revisão local registrada: 7f473cfd983d5eb43040ff608f66bff0d7bdcb53. Disponível em: https://github.com/facebookresearch/sam3. Acesso em: 27 out. 2026.

MOHAMMAD, Naureen. MMU Iris Dataset. Kaggle, [s.d.]. Cópia de aquisição utilizada no projeto. Disponível em: https://www.kaggle.com/datasets/naureenmohammad/mmu-iris-dataset. Acesso em: 20 out. 2026.

PADOLE, Chandrashekhar; PROENÇA, Hugo. Periocular Recognition: Analysis of Performance Degradation Factors. In: Fifth IAPR/IEEE International Conference on Biometrics, New Delhi, 2012. Base UBIPr disponível em: https://iris.di.ubi.pt/ubipr.html. Acesso em: 23 out. 2026.

QIAN, Hulei. SLP-VLD: An Anonymized Slit-Lamp Image Dataset with Expert Clinical Reports for Vision-Language Modeling of Anterior Segment Diseases. Figshare, versão 3, 2026. Conjunto de dados. DOI: 10.6084/m9.figshare.32576697.v3. Disponível em: https://doi.org/10.6084/m9.figshare.32576697.v3. Acesso em: 20 out. 2026.

RONNEBERGER, Olaf; FISCHER, Philipp; BROX, Thomas. U-Net: Convolutional Networks for Biomedical Image Segmentation. In: Medical Image Computing and Computer-Assisted Intervention, 2015. Disponível em: https://arxiv.org/abs/1505.04597. Acesso em: 23 out. 2026.

SIMÉONI, Oriane et al. DINOv3. arXiv:2508.10104, 2025. Disponível em: https://arxiv.org/abs/2508.10104. Acesso em: 23 out. 2026.

TEJANI, Ali S. et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 Update. Radiology: Artificial Intelligence, v. 6, n. 4, artigo e240300, 2024. DOI: 10.1148/ryai.240300. Disponível em: https://doi.org/10.1148/ryai.240300. Acesso em: 27 out. 2026.

TROKIELEWICZ, Mateusz; CZAJKA, Adam; MACIEJEWICZ, Piotr. Assessment of iris recognition reliability for eyes affected by ocular pathologies. In: IEEE Seventh International Conference on Biometrics Theory, Applications and Systems, Arlington, 2015. p. 1–6. DOI: 10.1109/BTAS.2015.7358747. Disponível em: https://arxiv.org/abs/1809.00206. Acesso em: 23 out. 2026.

WORLDCOIN. Open Iris Recognition Inference System. Repositório oficial OpenIRIS, [s.d.]. Disponível em: https://github.com/worldcoin/open-iris. Acesso em: 27 out. 2026.

XU, Mingyu et al. SLID: a slit-lamp image dataset for deep learning-based anterior eye anatomical segmentation and multi-lesion detection. Frontiers in Digital Health, v. 7, artigo 1716501, 2026. DOI: 10.3389/fdgth.2025.1716501. Disponível em: https://doi.org/10.3389/fdgth.2025.1716501. Dados: https://github.com/xumingyu-hub/SLID. Acesso em: 27 out. 2026.
