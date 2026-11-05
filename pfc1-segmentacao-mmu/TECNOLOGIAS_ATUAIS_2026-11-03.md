# SAM 3 e versões atuais — 03/11/2026

O usuário determinou usar SAM 3 e as tecnologias mais atuais possíveis. A preferência foi persistida em [AGENTS.md](../AGENTS.md). Novos ensaios SAM usam a família SAM 3, na revisão oficial mais recente verificada antes de registrar cada rodada. Resultados antigos permanecem identificados com suas versões originais.

## Versão oficial e ambiente adotado

A [página oficial da Meta](https://github.com/facebookresearch/sam3) e as [notas do SAM 3.1](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md) apontam SAM 3.1 como atualização mais recente anunciada da família. A consulta à API oficial do GitHub encontrou a revisão `f1647e8d0c1d280991f4d1b7d974c2704537fe66`, de 23/10/2026. Ela foi instalada no ambiente novo. O pacote continua numerado `0.1.0`; por isso a adoção foi verificada pelo commit/URL de origem e pelos arquivos instalados, além do número de versão.

O [checkpoint oficial SAM3.1](https://huggingface.co/facebook/sam3.1) permanece no snapshot `daa63191845a41281374e725f4c9e51c7a824460`. O hash local de `sam3.1_multiplex.pt` coincide com o LFS oficial: `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`. Não foi necessário baixar novamente os 3,50 GB.

| Componente | Ambiente dos novos ensaios | Evidência/limitação |
|---|---|---|
| SAM 3 | SAM3.1, código `f1647e8…` | Código oficial e pesos atuais conferidos separadamente. |
| PyTorch | 2.14.1 + CUDA13.0 | Maior build GPU Windows/CPython3.12 localizado nos índices oficiais cu126, cu128 e cu130 consultados. PyPI já lista2.15.0; não foi adotado sem build GPU verificado nessa consulta. O índice cu131 retornou HTTP403. |
| torchvision | 0.29.1 + CUDA13.0 | Par GPU instalado do mesmo índice oficial; NMS CUDA passou. PyPI lista0.29.2, sem build correspondente identificado nesses índices. |
| Transformers | 5.22.1 | Versão mais recente retornada pelo PyPI na consulta. |
| Hugging Face Hub | 2.4.0 | Versão mais recente retornada pelo PyPI na consulta. |
| Pillow | 13.0.0 | Versão mais recente retornada pelo PyPI na consulta. |
| NumPy | 1.26.4 | O próprio SAM3 exige `numpy>=1.26,<2`. PyPI lista2.5.4, incompatível com essa restrição. |
| OpenCV headless | 4.11.0.86 | Mantido compatível com NumPy1.26; a versão5.0.0.93 consultada exige NumPy≥2 neste Python. |

O Python do ambiente novo é3.12.10, derivado da instalação já validada e compatível com os pacotes nativos utilizados. A atualização não troca globalmente o Python, o driver ou o ambiente da rodada em curso. Os índices, as respostas do PyPI, as restrições do pacote SAM3 e as versões resolvidas estão em [outputs/tecnologias_atuais_2026-11-03](outputs/tecnologias_atuais_2026-11-03/).

O ambiente curto é `C:\Users\lucaz\pfc-sam3-20261103`. A primeira tentativa dentro do caminho longo do projeto encontrou o limite de caminhos do Windows ao instalar Transformers; foi substituída por esse prefixo curto. Os pacotes atualizados são carregados do novo prefixo. As demais dependências validadas são lidas do ambiente de base, sem alterá-lo; o inventário resolvido foi preservado.

Para preparar/reproduzir o ambiente e executar os novos scripts:

```powershell
./preparar_ambiente_sam3_atual.ps1
./executar_sam3_atual.ps1 diagnosticar_sam3_prompts_clinicos.py --registrar
./executar_sam3_atual.ps1 diagnosticar_sam3_prompts_clinicos.py
```

O ensaio acima já está concluído; seu diretório é preservado e recusa sobrescrita. Para uma nova rodada, deve-se abrir outro diretório/protocolo. O preparador instala somente no ambiente separado; `data/python-sam3-atual.txt` aponta para ele. A entrada histórica `data/python-path.txt` conserva o ambiente do experimento já registrado.

## Verificação executada

`pip check` passou. Multiplicação BF16 na RTX3050 e NMS de torchvision em CUDA passaram. Foi conferido que SAM3, PyTorch, torchvision e Transformers vieram do prefixo novo. Os dois testes de coordenadas das caixas passaram. Evidência: [AMBIENTE_VALIDADO.json](outputs/tecnologias_atuais_2026-11-03/AMBIENTE_VALIDADO.json).

A comparação das 30 fontes Python alteradas entre as revisões instalada anteriormente e atual encontrou ASTs idênticas: a atualização revisou comentários/anotações de análise estática, sem mudança identificada no código executável desses arquivos. Não atribuir ganho de segmentação a essa atualização de revisão. A comparação está em `comparacao_codigo_ast.json`.

Houve aviso do Triton herdado sobre descoberta de um toolkit CUDA para compilação. A execução avaliada usa os kernels de inferência que efetivamente passaram no novo ambiente; não foi validado `torch.compile`, treinamento SAM3 ou compilação de kernels Triton nesse ambiente. Não foram alteradas proteções do Windows ou instalações globais para suprimir o aviso.

## Novo ensaio SAM3.1 concluído

Foram processados os mesmos quatro casos clínicos fixos, com três métodos registrados antes da inferência: texto `iris of the eye`, texto mais caixa automática da U-Net antiga e texto mais caixa automática da U-Net diversa. O terceiro usa apenas as máscaras U-Net da época15 já preservadas; nenhum modelo SAM2 foi importado ou executado neste ensaio. O caminho semântico de imagem foi carregado estritamente: todos os1.130 tensores, sem ausentes ou inesperados, excluindo as ramificações de vídeo que não entram nesse caminho. Não foi avaliado rastreamento multiplex completo.

O [resultado](outputs/sam31_atual_prompts_2026-11-03/CONCLUIDO.json), a [prancha](outputs/sam31_atual_prompts_2026-11-03/comparacao_sam31_atual.png), o [protocolo](outputs/sam31_atual_prompts_2026-11-03/protocolo.json) e a [auditoria](outputs/sam31_atual_prompts_2026-11-03/AUDITORIA.json) foram preservados. A auditoria reproduziu as12 máscaras e as8 caixas a partir das evidências gravadas, conferiu imagens/fontes/hashes e confirmou que as dez fontes da rodada ativa continuam iguais.

O texto isolado ainda inclui a pupila em P0005 e seleciona a pupila em P0007/P0803. Com caixa diversa, P0005/P0007 passam a apresentar fragmentos periféricos inadequados; P0803 também falha. P0114 produz uma região central ampla, sem referência manual para aferir seu significado anatômico. Todos os casos foram preservados. Essa configuração de prompts continua experimental: não houve promoção para reconhecimento, cálculo de Dice clínico, identificação ou mínimo de área.

A preferência por versões atuais orienta os próximos ensaios. A adoção no reconhecedor depende da avaliação científica correspondente; a comparação de segmentação/identidade já em curso conserva suas versões e parâmetros registrados.

## Compatibilidade dos reconhecedores após a atualização

Enquanto o SAM3.1 calculava os mapas na GPU, foi executada uma verificação independente em CPU nos nove componentes congelados: RGB, polar, espacial, ResNet50, ConvNeXt, nativo224, Transformer polar e duas vistas ArcIris. Os seis checkpoints internos, os pesos e o código externo ArcIris e a configuração congelada foram conferidos por SHA256 antes da inferência. O ensaio usa o controle U-Net original para preparar as entradas; não avalia o decodificador SAM3 ainda em treinamento.

A escolha foi fixada sem consultar qualidade ou escores: primeiro olho elegível em ordem lexical e primeira fotografia de cada uma das duas sessões na validação. As duas fotografias foram processadas no ambiente novo e no ambiente de referência, usando o mesmo script e os mesmos pesos. Não houve leitura de pixels do teste, acesso à rede, ajuste de limiar, seleção de modelo ou filtragem de falhas.

Os quatro tipos de entrada preparados foram **idênticos pixel a pixel**. As saídas dos **nove componentes foram finitas e exatamente iguais** entre os ambientes nessas duas fotografias em CPU. Isso inclui o Transformer com Transformers 5.20.2 na referência e 5.22.1 no ambiente novo, e Pillow 12.3.0 versus 13.0.0. Ambos usam PyTorch 2.14.1/torchvision 0.29.1; as distribuições CUDA são cu126 e cu130, respectivamente. Os processos de verificação ocultaram a GPU e confirmaram que CUDA não foi inicializado.

Os resultados são uma checagem de compatibilidade FP32 com duas entradas, **não uma nova taxa de reconhecimento, equivalência CUDA ou confirmação da validação completa**. A comparação pareada de 482 consultas no novo ambiente permanece necessária e será feita pelo fluxo registrado após a seleção do candidato SAM3.

- [Protocolo e saídas no ambiente novo](outputs/tecnologias_atuais_2026-11-03/identidade_smoke_cpu/CONCLUIDO.json).
- [Protocolo e saídas no ambiente de referência](outputs/tecnologias_atuais_2026-11-03/identidade_smoke_cpu_referencia/CONCLUIDO.json).
- [Comparação dos ambientes](outputs/tecnologias_atuais_2026-11-03/COMPARACAO_CPU_IDENTIDADE.json).
- [Script reproduzível](verificar_identidade_ambiente_sam3.py), que preserva resultados existentes e exige novas pastas para uma repetição.
