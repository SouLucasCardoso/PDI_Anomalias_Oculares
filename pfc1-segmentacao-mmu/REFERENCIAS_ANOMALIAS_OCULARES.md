# Registro de pesquisa — alterações oculares e biometria

**Data de consulta:** 01/10/2026. **Finalidade:** preservar as fontes encontradas nesta pesquisa para futura redação do artigo. Complementa [REFERENCIAS_RECENTES.md](REFERENCIAS_RECENTES.md) e [DATASETS_RECOMENDADOS.md](DATASETS_RECOMENDADOS.md), sem substituir o levantamento anterior.

Este é um levantamento exploratório, não uma revisão sistemática. Foram pesquisadas combinações de iris recognition, ocular pathology, diseased eyes dataset, cataract surgery, mobile periocular, slit-lamp e dataset access. Foram priorizados artigos originais, páginas dos autores e mantenedores. Resultados comerciais, fóruns e resultados sem relação direta foram descartados. A presença de um artigo aqui não significa leitura integral nem reprodução de seus resultados.

## 1. Referências prioritárias com metadados conferidos

### R01 — Cirurgia de catarata e autenticação pela íris

NIGAM, Ishan; KESHARI, Rohit; VATSA, Mayank; SINGH, Richa; BOWYER, Kevin. **Phacoemulsification Cataract Surgery Affects the Discriminative Capacity of Iris Pattern Recognition**. *Scientific Reports*, v. 9, art. 11139, 2019. [DOI: 10.1038/s41598-019-47222-4](https://doi.org/10.1038/s41598-019-47222-4).

- Consulta: resumo e página editorial; [registro PubMed](https://pubmed.ncbi.nlm.nih.gov/31366988/).
- Contribuição: experimento com a IIITD CaSD, 132 pacientes e três sensores; oferece referência quantitativa de mudança pré/pós-cirurgia.
- Resultado de interesse: 93,42 ± 1,76% no pré/pré e 74,69 ± 9,77% no pré/pós; diferença calculada entre médias de 18,73 pontos percentuais, ou 20,05% de redução relativa. Com recadastro, o estudo relata 86,67 ± 5,64%.
- Uso: introdução, trabalhos relacionados e discussão. O resultado é de autenticação no protocolo dos autores, não Rank-1 do nosso projeto. A cirurgia não equivale ao efeito isolado da catarata. Conferir no texto integral o significado dos termos ± antes de reproduzi-los como medida de incerteza.

### R02 — Reconhecimento periocular móvel pré/pós-catarata

KESHARI, Rohit; GHOSH, Soumyadeep; AGARWAL, Akshay; SINGH, Richa; VATSA, Mayank. **Mobile Periocular Matching with Pre-Post Cataract Surgery**. In: *IEEE International Conference on Image Processing (ICIP)*, 2016. [Manuscrito disponibilizado pelo laboratório](https://iab-rubric.org/old1/papers/ICIP16_cataract.pdf).

- Consulta: resumo, descrição da base e protocolo no PDF; DOI e paginação não conferidos.
- Contribuição: CMPD com 2.380 imagens, 145 participantes no pré, 99 no pós e 56 comuns às sessões. O texto registra intervalo de 7–10 dias e aquisição móvel sem controle rigoroso.
- Uso: justificar a avaliação periocular e a alternativa RGB à Warsaw. Não atribuir toda diferença à cirurgia, pois também há variação de captura. A condição pós-operatória não deve ser rotulada automaticamente como saudável.

### R03 — Confiabilidade biométrica em olhos com patologias

TROKIELEWICZ, Mateusz; CZAJKA, Adam; MACIEJEWICZ, Piotr. **Assessment of iris recognition reliability for eyes affected by ocular pathologies**. In: *IEEE 7th International Conference on Biometrics Theory, Applications and Systems (BTAS)*, 2015. p. 1–6. [DOI: 10.1109/BTAS.2015.7358747](https://doi.org/10.1109/BTAS.2015.7358747). [Manuscrito](https://arxiv.org/abs/1809.00206).

- Consulta: resumo e metadados do arXiv.
- Contribuição: 2.996 imagens, 230 olhos, incluindo 184 afetados; destaca obstrução, distorção e erros de segmentação.
- Uso: fundamentar por que avaliar segmentação e reconhecimento separadamente. Publicação de 2015, depósito de 2018. Há sobreposição declarada com R04; não tratar como uma replicação independente.

### R04 — Efeitos das patologias sobre comparações biométricas

TROKIELEWICZ, Mateusz; CZAJKA, Adam; MACIEJEWICZ, Piotr. **Implications of Ocular Pathologies for Iris Recognition Reliability**. *Image and Vision Computing*, 2016. [DOI: 10.1016/j.imavis.2016.08.001](https://doi.org/10.1016/j.imavis.2016.08.001). [Manuscrito](https://arxiv.org/abs/1809.00168).

- Consulta: resumo e metadados; volume e páginas não conferidos.
- Contribuição: compara quatro reconhecedores e descreve mudanças de escores genuínos/impostores e problemas de segmentação.
- Uso: principal referência da família Warsaw para discutir mecanismos de falha. Os resultados dependem dos algoritmos e das condições avaliadas; não fornecem um percentual universal de perda.

### R05 — Primeira descrição da base de olhos com patologias

TROKIELEWICZ, Mateusz; CZAJKA, Adam; MACIEJEWICZ, Piotr. **Database of iris images acquired in the presence of ocular pathologies and assessment of iris recognition reliability for disease-affected eyes**. In: *IEEE 2nd International Conference on Cybernetics (CYBCONF)*, 2015. p. 495–500. [DOI: 10.1109/CYBConf.2015.7175984](https://doi.org/10.1109/CYBConf.2015.7175984). [Manuscrito](https://arxiv.org/abs/1809.00212).

- Consulta: resumo e metadados.
- Contribuição: descrição de uma coleção de 91 olhos, organizada por tipos esperados de impacto ocular.
- Uso: histórico da base e desenho de grupos. Não associar silenciosamente a este artigo a contagem de 230 olhos de R03/R04; são descrições de coleções/etapas distintas.

### R06 — Síntese sobre reconhecimento em presença de patologias

TROKIELEWICZ, Mateusz; CZAJKA, Adam; MACIEJEWICZ, Piotr. **Iris recognition in cases of eye pathology**. In: NAIT-ALI, A. (ed.). *Biometrics under Biomedical Considerations*. Springer, 2019. [Manuscrito depositado em 2018](https://arxiv.org/abs/1809.01040).

- Consulta: resumo e nota bibliográfica; DOI do capítulo e páginas pendentes.
- Contribuição: síntese sobre catarata, alterações geométricas, obstrução e segmentação.
- Uso: organizar a fundamentação. Relacionado a R03–R05; não contar como nova população independente.

### R07 — Estudo anterior sobre doenças oculares e reconhecimento

ASLAM, Tariq Mehmood; TAN, Shi Zhuan; DHILLON, Baljean. **Iris recognition in the presence of ocular disease**. *Journal of the Royal Society Interface*, v. 6, p. 489–493, 2009. [DOI: 10.1098/rsif.2008.0530](https://doi.org/10.1098/rsif.2008.0530). [PDF institucional](https://www.pure.ed.ac.uk/ws/portalfiles/portal/12418040/Iris_recognition_in_the_presence_of_ocular_disease.pdf).

- Consulta: identificação bibliográfica e trecho inicial indexado; resultados não extraídos nesta etapa.
- Uso: histórico do problema. Exige leitura integral antes de sustentar afirmações específicas sobre patologias ou taxas de erro.

### R08 — CatScreen

KHURSHID, Mahapara et al. **CatScreen: A Large MultiModal Benchmark Dataset for Cataract Screening**. *Transactions on Machine Learning Research*, 2026. [Página oficial e referência dos autores](https://www.iab-rubric.org/resources/healthcare-datasets/catscreen). [Artigo indicado pela página](https://openreview.net/pdf/84990354b4a5360864522f7c9c6039e0108ac771.pdf).

- Consulta: página oficial, referência e descrição da base; sem auditoria dos arquivos.
- Contribuição: imagens de lâmpada de fenda para triagem clínica; há amostra anunciada publicamente e acesso condicionado ao conjunto completo.
- Uso: alternativa para inspeção de alterações e tarefas clínicas. A elegibilidade para biometria depende de IDs, lateralidade e capturas repetidas, ainda não verificados.

### R09 — SLID

XU, Mingyu et al. **SLID: a slit-lamp image dataset for deep learning-based anterior eye anatomical segmentation and multi-lesion detection**. *Frontiers in Digital Health*, v. 7, art. 1716501, 2026. [DOI: 10.3389/fdgth.2025.1716501](https://doi.org/10.3389/fdgth.2025.1716501). [Repositório indicado no artigo](https://github.com/xumingyu-hub/SLID).

- Consulta: identificação editorial e descrição indexada do artigo, sem avaliação dos arquivos.
- Contribuição: segmentação anatômica e detecção de lesões no segmento anterior.
- Uso: candidato recente para discussão de segmentação clínica. A publicação informa 12/01/2026, embora o DOI contenha 2025. A disponibilidade de dados não demonstra, por si só, adequação à identificação biométrica.

## 2. Trabalhos localizados para leitura posterior

Os registros abaixo preservam pistas relevantes da busca. Não são referências bibliográficas finais: completar autores, ano editorial, DOI e leitura antes de incorporá-los ao artigo.

| ID | Trabalho e localização | Interesse e estado da consulta |
|---|---|---|
| R10 | [Self-Knowledge Distillation-Empowered Directional Connectivity Transformer for Microbial Keratitis Biomarkers Segmentation on Slit-Lamp Photography](https://pubmed.ncbi.nlm.nih.gov/40117989/) — registro de 2025; [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12004389/) | Segmentação de biomarcadores de ceratite. Descrição indexada consultada; acesso direto encontrou bloqueio de navegador. Metadados completos e adequação biométrica pendentes. |
| R11 | [MTCD: Cataract detection via near-infrared eye images](https://iab-rubric.org/old1/papers/2021_CVIU_MTCD.pdf) — *Computer Vision and Image Understanding*, 214, 103303, 2022, conforme cabeçalho indexado | Detecção de catarata em NIR; tarefa distinta de reconhecimento de identidade. Localizado em busca, sem leitura integral. |
| R12 | [Iris Recognition under Biologically Troublesome Conditions](https://www.scitepress.org/papers/2017/62517/62517.pdf), 2017 | Discussão de grupos de impacto ocular. Localizado em busca; verificar relação com a família Warsaw antes de tratar como evidência independente. |
| R13 | [Dense anatomical annotation of slit-lamp images improves the performance of deep learning for the diagnosis of ophthalmic disorders](https://doi.org/10.1038/s41551-020-0577-y), 2020 | Segmentação/anotação anatômica e diagnóstico. Página indexada informa restrições ao compartilhamento dos dados; não é solução confirmada de acesso imediato. |
| R14 | I-SOCIAL-DB — artigo associado ao [DOI 10.1016/j.imavis.2020.104058](https://doi.org/10.1016/j.imavis.2020.104058) | Localizado por descrição de base ocular com máscaras. Título completo, metadados, acesso e rótulos clínicos não conferidos. |
| R15 | A survey of iris datasets — [manuscrito institucional localizado](https://imec-publications.be/server/api/core/bitstreams/5a53ccdd-6fe6-4e71-8b78-34ce929e14cd/content) | Mapeamento de bases. Usar para descobrir fontes primárias, não substituir sua verificação. |

## 3. Páginas técnicas, catálogos e bases consultadas/localizadas

| Fonte | Papel no levantamento e limite |
|---|---|
| [IAB — bases de íris e CMPD](https://iab-rubric.org/resources/biometric-datasets/iris) | Página consultada: acesso, tamanho e termo institucional da CMPD. Download protegido por senha; não obtido. Também lista bases de lentes de contato, que não equivalem a doença. |
| [IAB — recursos](https://iab-rubric.org/resources) | Portal consultado para localizar o mantenedor e as páginas atuais. |
| [IEEE Biometrics — bases oculares](https://ieee-biometrics.org/resources/biometric-databases/ocular-iris-periocular/) | Catálogo localizado; pista de busca, não evidência experimental. |
| [IAPR TC4 — Iris Datasets](https://iapr-tc4.org/iris-datasets/) | Catálogo localizado; confirmar cada base na fonte original. |
| [NIST — ND-Iris-0405](https://tsapps.nist.gov/BDbC/Search/Details/371) | Registro localizado: base biométrica e acesso institucional; não resolve rótulos de doença. |
| [IRISSEG](https://github.com/HalmstadUniversityBiometrics/Iris-Segmentation-Groundtruth-Database) | Repositório localizado de anotações; não fornece necessariamente as imagens originais nem rótulos clínicos. |
| [Reconhecimento com BSIF para olhos doentes/pós-morte](https://github.com/aczajka/iris-recognition---pm-diseased-human-driven-bsif) | Implementação candidata localizada; não instalada nem avaliada nesta etapa. |
| [CVRL/PBM](https://github.com/CVRL/PBM) | Repositório localizado de reconhecimento forense; pós-morte é outro domínio, não substituto de doença em pessoas vivas. |
| [SLP-VLD — registro Figshare](https://doi.org/10.6084/m9.figshare.32576697.v3) | Pista encontrada via catálogo secundário; conteúdo, licença e identidade ocular não verificados. |

Fontes já registradas anteriormente — MMU, UBIPr, MOBIUS, MCIS, OpenEDS, SBVPI, CASIA, Notre Dame Open-Source Iris Recognition e artigos recentes de segmentação — permanecem nos dois documentos vinculados no início. Não foram revalidadas integralmente neste levantamento.

## 4. Regras para aproveitar as referências no artigo

1. Priorizar R01–R06 para a pergunta biométrica; R08–R10 tratam principalmente de dados/tarefas clínicas e exigem essa distinção.
2. Usar o ano da publicação, não a data de depósito ou de indexação. A regra de cinco anos registrada no projeto exige avaliar com o orientador o uso de trabalhos históricos de 2009–2019; sua inclusão neste inventário não declara atendimento à regra.
3. Separar resultados de literatura dos experimentos próprios. Não comparar diretamente autenticação, Rank-1, Dice e diagnóstico como se fossem a mesma métrica.
4. Não afirmar que uma base foi obtida porque há artigo ou link de download. Registrar versão, licença e manifesto quando os arquivos forem recebidos.
5. Não somar R03–R06 como quatro confirmações independentes. Conferir populações e sobreposição de experimentos na leitura integral.
6. Completar os campos pendentes antes da formatação bibliográfica final e citar a publicação editorial quando confirmada, conservando o manuscrito aberto como rota de acesso.
