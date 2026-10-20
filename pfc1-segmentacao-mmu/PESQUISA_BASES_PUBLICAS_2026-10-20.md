# Bases clínicas públicas e decisão experimental

Consulta de 20/10/2026. Prazo do artigo: 09/11/2026, daqui a 20 dias.
Este levantamento é exploratório e direcionado à viabilidade de execução,
não uma revisão sistemática. Foram pesquisados títulos, modalidades, termos
de acesso e estudos relacionados, priorizando páginas dos autores, periódicos,
Mendeley Data, Figshare e Harvard Dataverse. A busca indexada no domínio Google
Scholar não trouxe resultados úteis nesta sessão; não se declara uma busca
completa no Google Acadêmico. As decisões abaixo se baseiam nas fontes primárias
vinculadas e nas auditorias dos arquivos efetivamente obtidos.
Foram consultados textos HTML, metadados e trechos indexados. Não se declara
leitura integral de todos os artigos localizados; os registros de acesso e de
conteúdo devem ser completados na conferência bibliográfica da versão final.

## Decisão para não depender de assinatura

Manter a pergunta do pré-projeto: comparar classificação de imagens oculares
com e sem segmentação prévia da íris. Usar somente bases do segmento anterior
com rótulos clínicos, sem construir artificialmente a classe saudável a partir
de uma base biométrica adquirida por outro sensor. Reconhecimento de identidade
permanece complementar; não é o desfecho principal do artigo.

A auditoria permitiu selecionar **SLP-VLD v3 como base principal**, com o
segmentador U-Net treinado separadamente no UBIPr. Foram pareadas 2.228 imagens;
após remover uma duplicata, ficam 2.128 imagens de desenvolvimento e 99 de outra
instituição para teste externo. A divisão registrada é 1.520/304/304, com 911
grupos conservadores sem sobreposição. CatScreen Clean fica como avaliação
externa complementar com rótulos próprios. SLID não integra o caminho crítico,
pois falta vínculo público por paciente e licença de dados separada explícita.
Não há resultado de classificação clínica nesta data. A decisão foi registrada
antes de qualquer escore clínico de teste; o protocolo inicial CatScreen não
foi executado.

## Comparação de alternativas

| Base | Evidência de acesso e conteúdo | Auditoria e decisão |
|---|---|---|
| [CatScreen](https://www.iab-rubric.org/resources/healthcare-datasets/catscreen) | Amostra pública; uso acadêmico/educacional. O conjunto completo exige acordo institucional. | Obtidas 400 imagens: Clean 200, Noisy 100, Unlabelled 100. Clean 140/20/40, IDs distintos e sem duplicatas exatas. É a alternativa imediata; teste com apenas oito imagens Normal exige conclusão exploratória e ICs amplos. |
| [SLID](https://github.com/xumingyu-hub/SLID), [artigo de 2026](https://doi.org/10.3389/fdgth.2025.1716501) | Repositório público com imagens e anotações. Artigo CC BY; repositório não apresenta licença separada para os dados. | Recuperados ZIP e CSV por Git LFS, sem assinatura. 2.617 imagens válidas, 245 sem lesão anotada e 2.372 com lesões. Sem vínculo explícito por paciente no CSV. Reservar para teste externo; não redistribuir os dados. |
| [Nuclear Cataract v2](https://doi.org/10.17632/6wv33nbcvv.2) | Mendeley, CC BY 4.0, sem assinatura. Publicação associada de 2023. | Obtidas 1.320 imagens de 115 pacientes, não 1.437 imagens rotuladas como sugere a descrição. O XLSX do depósito é somente arquivo temporário de 165 bytes. Recuperadas 335 imagens rotuladas, de 69 pacientes, pela seleção dos autores de 2025. Útil para graduação, não para criar controle saudável. |
| [SLP-VLD v3](https://doi.org/10.6084/m9.figshare.32576697.v3) | Figshare, CC BY 4.0; relatórios e diagnósticos estruturados; tabela nome–ID excluída. | ZIP de 3,52 GB adquirido, MD5 igual ao oficial. 2.228 registros pareados com imagens válidas e rótulos XLSX. Uma duplicata removida. Selecionada como principal, com agrupamento conservador descrito abaixo. É depósito de dados, não artigo revisado por pares confirmado. |
| [Infectious Keratitis](https://doi.org/10.6084/m9.figshare.28578860.v1) | Figshare, CC BY 4.0; dois ZIPs públicos, total aproximado de 4,02 GB. Há duas instituições e três iluminações. | Metadados oficiais obtidos. O grupo Other contém outras alterações corneanas, não controles saudáveis. Adequado para etiologia de ceratite ou teste complementar, não substituição direta da pergunta binária original. Imagens não baixadas nesta etapa. |
| [SLIT-Net](https://doi.org/10.7910/DVN/BWJJRP) | Harvard Dataverse, CC BY-NC 4.0; arquivos sem restrição no registro consultado. Código dos autores em [GitHub](https://github.com/jessicaloohw/SLIT-Net). | Confirmados ZIPs de luz branca/azul e annotations.mat. Adequado à segmentação de biomarcadores de ceratite; não fornece diretamente a tarefa saudável/alterado. Evitar baixar mais de 5 GB sem necessidade experimental. |
| [SDCTrans](https://doi.org/10.1016/j.media.2025.103533) | Artigo de 2025 informa ampliação dos dados de ceratite e disponibilização de código/dados. | Alternativa bibliográfica para segmentação patológica; não confundir anúncio com aquisição. Não depende desta base o cronograma principal. |
| [EyeHealer](https://pmc.ncbi.nlm.nih.gov/articles/PMC8982547/) | Artigo descreve base extensa, mas a seção de disponibilidade condiciona dados à análise de comitê de acesso. | Não é solução de acesso imediato, apesar do termo public no texto. Não colocar no caminho crítico do prazo. |
| [ASOCT-MSDC](https://doi.org/10.1038/s41597-026-08315-8) | Publicação de 2026, com estruturas e rótulos em OCT do segmento anterior. | Modalidade diferente de fotografia RGB externa; exige reformulação do pipeline. Não priorizar em 20 dias. |

ODIR, RFMiD e coleções de retinografia não substituem fotografias externas da
íris. Cataract-101/CaDIS são vídeos cirúrgicos; presença de catarata em todos os
procedimentos e instrumentos introduz outra tarefa. Não misturar essas fontes
para fabricar classes saudáveis/doentes.

## Descobertas que mudam o desenho

**SLP-VLD.** Os 2.129 registros de desenvolvimento incluem 190 imagens com rótulo
exato Normal eye e 1.939 com outras condições. O teste institucional externo
tem 99 imagens, sete Normal eye. A única duplicata exata aparece sob OD e OS
no mesmo pseudocódigo, com o mesmo rótulo, e foi reduzida a um registro. Não
foram usados os textos das respostas VLM para gerar alvos de classificação;
os rótulos vêm da coluna Diagnosis das planilhas.

Prefixos P#### do nome de arquivo e IDs de metadados não se relacionam
perfeitamente: cinco IDs vinculam múltiplos prefixos, e seis prefixos têm
múltiplos IDs. Todos os registros conectados por identificador compartilhado
foram unidos antes da divisão, reduzindo 916 prefixos a 911 grupos. São grupos
conservadores a partir dos identificadores distribuídos; a independência além
desses identificadores não pode ser confirmada sem o mapa original excluído.
Treino/validação/teste ficaram com 1.520/304/304 imagens e 651/131/129 grupos.
O teste interno contém 27 imagens Normal e 277 da classe agrupada; há forte
desequilíbrio, portanto acurácia isolada é inadequada.

**Recuperação SLID.** O download direto falhou anteriormente, mas Git LFS
funcionou. A auditoria encontrou zero imagens corrompidas e zero duplicatas
exatas. Contagens únicas de lesões batem com várias categorias do artigo,
incluindo 225 cataratas e 222 ceratites; a classe Corneal scarring apresentou
67 imagens no CSV, enquanto o artigo declara 69. Preservar essa discrepância
no registro e não modificar os rótulos para forçar concordância.

O próprio estudo SLID reporta diferença entre divisão por imagem e por paciente.
Isso reforça que proximidade visual, arquivos consecutivos ou capturas do mesmo
olho não podem ser tratados como indivíduos independentes. Para teste externo
congelado, as imagens repetidas ainda afetam a incerteza: sem IDs, não calcular
IC por paciente nem apresentar 2.617 observações como 2.617 pessoas.

**Rótulos Nuclear Cataract.** A seleção publicada por
[Ignatowicz et al. em 2025](https://doi.org/10.3390/s25133954), disponível no
[repositório do estudo](https://github.com/ignatowicz-alicja/AI-Powered-Mobile-App-for-Nuclear-Cataract-Detection),
permitiu parear 335 arquivos por voluntário, olho e nome, distribuídos nos graus
NC 1–6. Não foram recuperados rótulos para todas as 1.320 imagens. A fonte de
2025 afirma que a coleção utilizada não contém controles saudáveis, embora o
artigo original descreva também uma proposta de classificação binária.
O que foi adquirido não sustenta rotular NC 1 como saudável. Os rótulos de 2025
são uma seleção secundária especializada e devem ser citados separadamente.

**Íris não é cristalino.** O estudo de 2025 extrai a região pupilar para avaliar
catarata. No SLID, catarata e lente intraocular são anotadas na região pupilar;
outras lesões aparecem na córnea ou conjuntiva. Assim, infere-se que remover
pupila e contexto pode apagar sinais úteis à classificação. Isso é uma hipótese
a testar, não um defeito a esconder nem evidência de iridologia. Uma conclusão
de piora com íris isolada também responde ao problema original.

## Protocolo mínimo executável

1. Retreinar a U-Net multiclasse no UBIPr com a configuração previamente
   selecionada, mantendo pessoas separadas. Escolher checkpoint exclusivamente
   na validação UBIPr e congelar antes de gerar imagens clínicas.
2. No SLP-VLD, usar Normal eye exato como classe 0 e as demais condições
   anotadas como classe 1, preservando os grupos conservadores. No CatScreen
   externo, Normal é 0 e Cataract/Other são 1. Não combinar métricas de fontes
   distintas sem identificação nem incluir Noisy/Unlabelled.
3. Comparar mesma CNN e mesmo orçamento de treino em três entradas: original;
   caixa ao redor da íris com contexto preservado; máscara de íris na mesma
   caixa. A segunda entrada controla o efeito de recortar/ampliar a região.
4. Priorizar ResNet18 com pesos ImageNet e cabeça binária treinada, com três
   sementes predefinidas. Evitar fine-tuning completo de DINOv3/SAM e busca ampla
   de modelos. Definir hiperparâmetros na validação antes do primeiro teste.
5. Manter todas as amostras, inclusive máscaras vazias. Registrar falhas, área
   preservada e exemplos favoráveis e desfavoráveis. Sem referência clínica de
   íris, não anunciar Dice clínico usando máscaras previstas como verdade.
6. Desfecho principal: diferença pareada de AUROC no teste interno, máscara
   menos original. Complementar com acurácia balanceada, sensibilidade,
   especificidade, macro-F1 e matriz de confusão, com limiar predefinido 0,5.
7. IC de 95% por bootstrap de pessoas, mantendo os dois olhos juntos. Sementes
   são repetições computacionais, não novos pacientes. O tamanho do teste é
   desequilibrado; relatar contagem de pessoas/grupos e incerteza com transparência.
8. Bijie e CatScreen como avaliações externas congeladas e separadas. SLID
   fica como extensão opcional, após revisão de termos e de independência.
   Relatar mudança de instituição, captura e distribuição de alterações;
   não atribuir a diferença só à doença.

O manifesto e o protocolo ativo estão em `outputs/clinico_slpvld_2026-10-20/`.
O protocolo inicial em `outputs/clinico_publico_2026-10-20/` foi preservado como
alternativa não executada. O estado é `prepared_not_executed`; nenhum resultado
clínico foi inventado.

## Referências centrais para a redação

- KHURSHID, M. et al. CatScreen: A Large MultiModal Benchmark Dataset for Cataract
  Screening. TMLR, 2026. [Página dos autores](https://www.iab-rubric.org/resources/healthcare-datasets/catscreen)
  e [publicação](https://openreview.net/pdf?id=cF7tSNAVQ6).
- XU, M. et al. SLID: a slit-lamp image dataset for deep learning-based anterior
  eye anatomical segmentation and multi-lesion detection. Frontiers in Digital
  Health, 7, 1716501, 2026. [DOI](https://doi.org/10.3389/fdgth.2025.1716501).
- CRUZ-VEGA, I. et al. Nuclear Cataract Database for Biomedical and Machine
  Learning Applications. IEEE Access, 11, 107754–107766, 2023.
  [DOI](https://doi.org/10.1109/ACCESS.2023.3312616).
- IGNATOWICZ, A. A.; MARCINIAK, T.; MARCINIAK, E. AI-Powered Mobile App for
  Nuclear Cataract Detection. Sensors, 25(13), 3954, 2025.
  [DOI](https://doi.org/10.3390/s25133954).
- YANG, Z. et al. Self-knowledge distillation-empowered directional connectivity
  transformer for microbial keratitis biomarkers segmentation on slit-lamp
  photography. Medical Image Analysis, 102, 103533, 2025.
  [DOI](https://doi.org/10.1016/j.media.2025.103533).
- TEJANI, A. S. et al. Checklist for Artificial Intelligence in Medical Imaging
  (CLAIM): 2024 Update. Radiology: Artificial Intelligence, 6(4), e240300, 2024.
  [DOI](https://doi.org/10.1148/ryai.240300). Usar como referência de transparência
  e descrição do estudo, não como pontuação de qualidade ou certificação clínica.

Os registros de dados de Qian (SLP-VLD, 2026) e Li (Infectious Keratitis, 2025)
têm DOIs e licenças nos catálogos preservados. Não apresentá-los como artigos
revisados por pares sem localizar e conferir uma publicação associada.
