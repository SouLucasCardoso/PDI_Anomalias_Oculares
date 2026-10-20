# INFLUÊNCIA DA SEGMENTAÇÃO DA ÍRIS NO DESEMPENHO DE REDES NEURAIS CONVOLUCIONAIS PARA CLASSIFICAÇÃO DE ALTERAÇÕES OCULARES

Lucas Cardoso Rodrigues

Orientação: Rodrigo Ramos Silva

Registro de produção de 20/10/2026. Introdução e desenho metodológico em redação;
os resultados clínicos ainda não foram produzidos. Este arquivo não é a versão
final para submissão. A formatação Word seguirá o modelo institucional localizado
na pasta do PFC I. Titulação, e-mails e composição final de autoria serão
conferidos antes da exportação.

**Resumo:** redigir após a conclusão do experimento, informando objetivo,
quantidade de pessoas/imagens, três entradas comparadas, resultado pareado com
intervalo de confiança e conclusão proporcional à amostra. Não reutilizar
como resultado clínico o Dice de segmentação nem o Rank-1 biométrico histórico.

**Palavras-chave:** Visão computacional. Segmentação da íris. Redes neurais
convolucionais. Transferência de aprendizado. Alterações oculares.

## 1 INTRODUÇÃO

Fotografias do segmento anterior registram estruturas e alterações visuais que
podem subsidiar o estudo computacional de condições oculares. Entretanto, essas
imagens também contêm variações de iluminação, reflexos, posição do olhar,
ampliação e enquadramento. Na classificação por aprendizado profundo, o
resultado depende tanto da informação clínica disponível quanto da forma como
essa informação é apresentada ao modelo. A escolha da região de interesse é,
portanto, uma decisão experimental que precisa ser avaliada em vez de assumida
como benefício automático.

A disponibilidade de dados públicos influencia essa avaliação. O CatScreen
reúne imagens de lâmpada de fenda e atributos clínicos, incluindo categorias
diagnósticas e características de aquisição. Seus autores disponibilizam uma
amostra pública e mantêm um procedimento de acesso ao conjunto completo
(Khurshid et al., 2026). O SLID, por sua vez, fornece anotações anatômicas e
lesões em fotografias do segmento anterior, possibilitando estudar a relação
entre localização das alterações e análise automatizada (Xu et al., 2026).
Essas fontes são mais adequadas à classificação de condições oculares em
fotografias externas que bases biométricas sem rótulos clínicos.

A segmentação da íris permite isolar parte da região ocular, mas não garante
preservação de toda a informação relevante à tarefa clínica. O estudo de
Ignatowicz, Marciniak e Marciniak (2025), por exemplo, utiliza extração da região
pupilar na graduação de catarata nuclear. No SLID, as regiões de referência
incluem pupila, córnea e conjuntiva, e diferentes alterações são associadas a
estruturas distintas (Xu et al., 2026). Assim, infere-se que um procedimento que
remove a pupila ou a região externa à íris pode descartar sinais úteis ao
classificador. Essa possibilidade justifica a comparação controlada entre
imagem original e imagem segmentada, incluindo a hipótese de redução do
desempenho após o isolamento da íris.

Também é necessário distinguir classificação clínica, segmentação e
reconhecimento biométrico. A segmentação estima regiões da imagem; a
classificação atribui categorias definidas pelos rótulos do conjunto de dados;
o reconhecimento de identidade compara indivíduos ou olhos. Melhoria na
sobreposição de uma máscara não implica melhoria de classificação, assim como
uma taxa de identificação não corresponde a desempenho diagnóstico. Neste
trabalho, a comparação clínica constitui o objetivo principal. Experimentos
biométricos anteriores servem apenas como contexto metodológico e não como
evidência de classificação de doenças.

A pergunta que orienta o estudo é: em que medida a segmentação da região da
íris influencia o desempenho de uma rede neural convolucional na diferenciação
entre imagens rotuladas como normais e imagens com condições oculares anotadas?
O objetivo geral consiste em desenvolver e comparar pipelines com e sem
segmentação prévia, mantendo o classificador, as partições e os critérios de
avaliação comparáveis. Como objetivos específicos, estabelecem-se a auditoria
dos dados públicos, o treinamento independente do segmentador, a construção
das entradas clínicas pareadas e a análise de desempenho e falhas operacionais.

O estudo é de natureza experimental e abordagem quantitativa. A contribuição
pretendida é delimitar os efeitos da seleção espacial de informação em um
cenário reproduzível de dados públicos. Não se propõe um sistema para uso
diagnóstico autônomo nem se presume que o isolamento da íris seja suficiente
para caracterizar condições de outras estruturas oculares. A descrição dos
dados, das partições e das limitações será orientada pelos princípios de
transparência do CLAIM 2024 (Tejani et al., 2024).

## 2 PROCEDIMENTO EXPERIMENTAL

Esta seção descreve o desenho preparado antes da avaliação clínica. Sua redação
deverá ser atualizada para o procedimento efetivamente executado, preservando
eventuais desvios documentados. A possibilidade de substituição por SLP-VLD
será decidida na auditoria de dados, antes do cálculo dos escores clínicos de
teste. Não se realizará seleção de base a partir do resultado de teste.

### 2.1 MATERIAIS

O desenvolvimento utiliza Python, PyTorch, torchvision, bibliotecas de
processamento de imagens e ferramentas de avaliação estatística. O equipamento
disponível possui GPU NVIDIA GeForce RTX 3050 Laptop com 6 GB de memória.
Versões dos pacotes, configuração, sementes e hashes dos artefatos são
registrados junto às execuções. A instalação foi verificada por testes de
execução, mas esses testes reduzidos não constituem resultados científicos.

O segmentador utiliza o UBIPr Single Eyes Segmented, obtido da fonte oficial
sob CC BY-NC-SA 4.0. A auditoria local identificou 11.018 pares de imagem e
máscara, pertencentes a 261 pessoas. As máscaras distinguem fundo/pupila,
íris, esclera e sobrancelha. Como pupila e fundo compartilham o mesmo valor,
esse conjunto não oferece uma classe pupilar independente. A separação por
pessoa utiliza 7.716 imagens para treinamento, 1.652 para validação e 1.650
para teste, sem compartilhamento de pessoas.

O conjunto clínico principal é o SLP-VLD v3, disponibilizado sob CC BY 4.0
em depósito público de dados (Qian, 2026). A auditoria pareou 2.228 registros
JSON com imagens válidas e diagnósticos das planilhas. Uma duplicata exata,
registrada sob lados diferentes do mesmo pseudocódigo e com o mesmo rótulo,
foi removida. A análise principal utiliza 2.128 imagens de desenvolvimento;
99 imagens da instituição Bijie permanecem como teste externo.

O prefixo anônimo P#### dos arquivos e o campo ID dos metadados apresentam
algumas inconsistências de correspondência. Para reduzir vazamento, todos os
registros conectados por qualquer identificador compartilhado foram unidos
antes da divisão. Os 916 prefixos resultaram em 911 grupos conservadores,
separados em 651 de treino, 131 de validação e 129 de teste. As partições
contêm 1.520, 304 e 304 imagens, respectivamente. Como o mapa original foi
excluído da versão pública, a independência além dos identificadores
distribuídos não pode ser confirmada.

O rótulo exato Normal eye é classe 0; as demais condições anotadas são classe
1. O teste interno contém 27 imagens Normal e 277 da classe agrupada. Esse
desequilíbrio exige métricas que não sejam dominadas pela classe majoritária
e limita a precisão da especificidade. Os alvos vêm da coluna Diagnosis,
sem utilizar respostas VLM ou descrições textuais como entrada preditiva.
O depósito de dados não é apresentado como artigo revisado por pares.

A amostra pública Clean do CatScreen, com 200 imagens e rótulos Normal,
Cataract e Other, constitui domínio externo complementar. Nenhuma dessas
imagens será utilizada para ajustar o classificador principal. Os resultados
serão apresentados separadamente dos obtidos em Bijie, e as parcelas Noisy e
Unlabelled não integrarão o experimento supervisionado principal.

Como extensão, será considerada a avaliação externa no SLID, adquirido do
repositório dos autores. A auditoria local verificou 2.617 imagens válidas,
245 sem lesão anotada e 2.372 com ao menos uma lesão. O CSV distribuído não
contém vínculo explícito entre imagem e paciente. Por essa razão, não se
propõe uma divisão interna aleatória dessa coleção nem se interpreta a
quantidade de imagens como quantidade de indivíduos independentes. As
condições de uso e a compatibilidade de rótulos devem ser confirmadas antes
da inclusão dessa extensão nos resultados finais.

### 2.2 MÉTODOS

#### 2.2.1 Auditoria e rastreabilidade

A auditoria verifica correspondência entre arquivos e rótulos, integridade de
imagens, duplicatas exatas por SHA-256 e sobreposição de pessoas entre
partições. Os arquivos originais são preservados. Manifestos registram origem,
identificador disponível, lado do olho, partição, rótulo bruto e hash. A
ausência de duplicatas exatas não será apresentada como garantia de ausência
de capturas semelhantes; identificação por pessoa continua necessária.

Os dados clínicos e biométricos não são combinados para construir a classe
Normal. Essa combinação confundiria condição ocular com sensor, população,
iluminação e enquadramento. Da mesma forma, graus leves de catarata não serão
renomeados como olhos saudáveis. Bases de retinografia e OCT não substituirão
fotografias externas sem reformulação explícita da pergunta e do método.

#### 2.2.2 Segmentação independente

A U-Net multiclasse é treinada no UBIPr com a configuração previamente
selecionada: entrada 320 × 240, oito canais iniciais, lote 32, semente 42 e
até 30 épocas, com parada antecipada após dez épocas sem melhora. O
checkpoint é selecionado pelo desempenho de validação UBIPr e posteriormente
congelado. O retreinamento gera novos pesos e não é apresentado como
recuperação dos checkpoints históricos perdidos.

A segmentação é avaliada no seu próprio domínio por métricas de sobreposição,
mantidas separadas das métricas clínicas. Como não existe referência de íris
na amostra CatScreen utilizada, não se calculará Dice clínico tomando a
própria previsão como anotação verdadeira. A qualidade em imagens clínicas
será discutida por falhas, área preservada e inspeção visual documentada,
sem atribuir a essa inspeção o valor de anotação especializada.

#### 2.2.3 Entradas pareadas e classificação

Para cada imagem clínica serão geradas três entradas: imagem original;
recorte pela caixa estimada da íris com contexto preservado; e máscara da
íris aplicada dentro da mesma caixa. As duas últimas entradas compartilharão
a geometria de recorte para controlar o efeito de ampliação e enquadramento.
Todas as entradas serão redimensionadas para 224 × 224 para a CNN.

O classificador principal previsto é ResNet18 pré-treinada no ImageNet, com
extrator convolucional congelado e cabeça binária treinada. O mesmo
procedimento será aplicado às três entradas com sementes 42, 123 e 2026.
O protocolo fixa AdamW, taxa de aprendizado 0,001, regularização 0,0001,
até 100 épocas e paciência de 15 épocas na cabeça linear. A perda binária
pondera as classes pela razão Normal/Alterado do treino; a maior AUROC de
validação seleciona a época, preservando a primeira em empates. As sementes constituem
repetições computacionais e não novas observações clínicas independentes.

Máscaras vazias permanecerão no resultado operacional. Nesses casos, a
entrada mascarada será preta e o controle de caixa usará o enquadramento
completo. A regra será aplicada sem consultar a classe clínica. Não serão
excluídas amostras por falha induzida pelo próprio pipeline; a taxa de falha
será apresentada junto ao desempenho agregado.

#### 2.2.4 Avaliação e análise estatística

O desfecho principal previsto é a diferença pareada de área sob a curva ROC
entre entrada mascarada e original no teste interno. Acurácia balanceada,
sensibilidade, especificidade, macro-F1 e matriz de confusão serão
apresentadas como medidas complementares, com limiar binário predefinido
de 0,5. As mesmas consultas serão utilizadas nas entradas comparadas.

Os intervalos de confiança serão estimados por 5.000 reamostragens pareadas
dos grupos conservadores, mantendo capturas e lados do olho no mesmo bloco. O procedimento
preserva parte da dependência entre imagens, mas não elimina a limitação de
tamanho da amostra. A predição principal será a média das probabilidades das
três sementes; resultados de cada semente também serão apresentados. O
bootstrap usa predições fixas e não representa toda a incerteza do treinamento
ou da população clínica.

No teste externo, se incluído, modelo, limiar e pré-processamento permanecerão
congelados. As diferenças de distribuição entre instituições e aquisições
serão explicitadas. Sem identificadores disponíveis, não se anunciará
bootstrap por paciente no SLID nem se interpretará a generalização externa
como efeito isolado de uma patologia.

## 3 RESULTADOS E DISCUSSÕES

Seção reservada aos resultados efetivamente produzidos. Inserir somente após
a conclusão das execuções e conferência dos arquivos:

1. Fluxo de inclusão de imagens e pessoas; características dos dados.
2. Resultado do novo segmentador UBIPr e distinção entre Dice global e por imagem.
3. Falhas e exemplos clínicos de segmentação, incluindo casos desfavoráveis.
4. Tabela pareada das três entradas, por semente e com regra de agregação explícita.
5. Diferença de AUROC com IC por pessoa, matriz de confusão e métricas operacionais.
6. Teste externo, se elegível, com mudança de domínio e limites de independência.
7. Discussão da eventual perda de informação pupilar/periocular e da incerteza
   decorrente do pequeno conjunto clínico.

## 4 CONSIDERAÇÕES FINAIS

Redigir a resposta à pergunta-problema após os resultados. Não antecipar ganho
de classificação, adequação clínica ou robustez biométrica. Apresentar o que
foi demonstrado, o domínio em que foi demonstrado e o que permanece limitado
pela amostra, pelos rótulos e pela ausência de referência clínica de íris.

## REFERÊNCIAS EM CONFERÊNCIA

QIAN, H. SLP-VLD: An Anonymized Slit-Lamp Image Dataset with Expert Clinical
Reports for Vision-Language Modeling of Anterior Segment Diseases. Figshare,
v. 3, 2026. Conjunto de dados. https://doi.org/10.6084/m9.figshare.32576697.v3.

CRUZ-VEGA, I. et al. Nuclear Cataract Database for Biomedical and Machine
Learning Applications. IEEE Access, v. 11, p. 107754–107766, 2023.
https://doi.org/10.1109/ACCESS.2023.3312616.

IGNATOWICZ, A. A.; MARCINIAK, T.; MARCINIAK, E. AI-Powered Mobile App for Nuclear
Cataract Detection. Sensors, v. 25, n. 13, 3954, 2025.
https://doi.org/10.3390/s25133954.

KHURSHID, M. et al. CatScreen: A Large MultiModal Benchmark Dataset for Cataract
Screening. Transactions on Machine Learning Research, 2026.
https://openreview.net/pdf?id=cF7tSNAVQ6.

TEJANI, A. S. et al. Checklist for Artificial Intelligence in Medical Imaging
(CLAIM): 2024 Update. Radiology: Artificial Intelligence, v. 6, n. 4, e240300,
2024. https://doi.org/10.1148/ryai.240300.

XU, M. et al. SLID: a slit-lamp image dataset for deep learning-based anterior eye
anatomical segmentation and multi-lesion detection. Frontiers in Digital Health,
v. 7, 1716501, 2026. https://doi.org/10.3389/fdgth.2025.1716501.

Completar nesta seção as referências originais de UBIPr, U-Net, ResNet e das
versões efetivamente utilizadas, conferindo metadados e normalização. Não
copiar referências apenas localizadas em trabalhos secundários sem conferir
a fonte primária.
