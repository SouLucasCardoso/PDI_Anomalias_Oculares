
> Atualização posterior de 21/10: teste com configuração congelada =91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR. A busca de área em passos nominais de 1% foi concluída:99% aprovados na oclusão inferior; na superior, apenas a condição original passou. Consulte [os resultados e limitações](RESULTADOS_CONGELADOS_E_OCLUSAO_2026-10-21.md).



## Atualização de desenvolvimento — 21/10/2026

O candidato congelado atingiu **Rank-1 de 90,04% e TAR de 90,66%, com FMR de 0,98%**, na validação UBIPr de 482 consultas, com uma foto original e lado do olho informado (16 candidatos). São 434 identificações corretas e 437 aceitações genuínas; o resultado conjunto de identificação correta e aceitação é88,38%. A validação foi reutilizada para seleção de estratégias e o componente externo ArcIris tem população de pré-treinamento desconhecida: estes números são exploratórios, sem confirmação independente. O mínimo de área permanece não determinado, com e sem oclusão. Consulte [o relatório atualizado](AVANCO_RECONHECIMENTO_2026-10-21.md) e `outputs/candidato_congelado_2026-10-21/CONGELADO.json`.

# Instalação local — 20/10/2026

## Estado atual das execuções

Rodada complementar concluída: encoder polar denso com 29 épocas, seleção na
21, e métrica linear ajustada só no treino. A fusão densa chegou a 78,84% de
Rank-1 e 68,26% de TAR, sem ganho consistente sobre a referência. O checkpoint
recarregado reproduziu os escores exatamente; 39 testes passaram. As saídas
foram copiadas para `outputs/encoder_polar_denso_2026-10-20`,
`outputs/fusao_densa_val_2026-10-20` e `outputs/metrica_intra_val_2026-10-20`,
com hashes conferidos. Não é preciso usar a cópia temporária para consultá-las.
Use `carregar_encoder_polar.load` para reconstruir a arquitetura densa ao carregar
os pesos. [Relatório](outputs/fusao_densa_val_2026-10-20/RELATORIO_CONTINUACAO.md).

Concluídos o treinamento polar (28 épocas, seleção na 20), o controle de fase,
a correspondência espacial e as fusões fixas de duas/três vias. O melhor
resultado pontual desta validação foi 79,88% de Rank-1, 68,05% de TAR e 0,99%
de FMR. Não é resultado de teste independente nem mínimo de área aprovado.
Os 37 testes passaram. Ver [relatório da rodada](outputs/fusao_espacial_val_2026-10-20/RELATORIO_AVANCO_POLAR_FUSAO.md).

O TripletIris público foi instalado com seus dois pesos oficiais e fontes
verificadas. Terminaram nove variantes circulares e seis elípticas na validação.
Não houve substituição do encoder atual, novo treinamento nessa etapa, novo
teste independente ou curva de oclusão. Os 32 testes passaram. Ver
[relatório do reconhecedor polar](outputs/tripletiris_elipse_validacao_2026-10-20/RELATORIO_RECONHECEDOR_POLAR.md)
e [protocolo de reprodução](PROTOCOLO_RECONHECEDOR_POLAR_2026-10-20.md).

As adaptações de treinamento em máscaras automáticas também terminaram: seis
épocas de ajuste angular simples e seis com triplet balanceado. Nenhuma superou
a TAR da época zero, e os parâmetros anteriores foram mantidos. A referência
pareada desta execução foi 66,80% de Rank-1 e 59,34% de TAR na validação.
Os 29 testes passaram. Ver
[relatório dos treinamentos](outputs/identidade_metrica_automatica_2026-10-20/RELATORIO_TREINAMENTOS.md).

Concluídas também as onze variantes de cadastro multicaptura e recorte automático,
mais seis controles exploratórios de suporte polar. O encoder automático top-3
obteve Rank-1 de 67,01%, TAR de 59,34% e FMR de 0,99%, somente na validação.
Os 24 testes passaram. Não foi executado novo treinamento, teste independente ou
curva de oclusão nesta atualização. Ver
[relatório multicaptura](outputs/cadastro_multicaptura_val_v2_2026-10-20/RELATORIO_CADASTRO.md).

Também terminaram quatro controles novos, somente na validação: HDBIF com imagem
inteira e com recorte prévio, mais encoder congelado em 128 e 256 pixels. O recorte
melhorou o HDBIF; a ampliação simples piorou o encoder. Vinte testes automatizados
passaram. Ver [relatório de melhoria](outputs/melhoria_normalizacao_val_gpu_2026-10-20/RELATORIO_MELHORIA.md).
Não há novo teste independente, nova curva de oclusão ou mínimo aprovado nessa rodada.

As execuções desta rodada terminaram: U-Net de segmentação, 19 condições DINOv3,
teste clínico HDBIF, treinamento de identidade e 19 condições com o novo encoder.
O encoder treinado alcançou Rank-1 de 67,90%, TAR de 55,14% e FMR de 0,96% no
benchmark exploratório UBIPr. O mínimo global de área continua não determinado
pelo critério registrado. A tentativa Nuclear foi interrompida na inspeção de
qualidade, antes de escores de reconhecimento; não retomar com os mesmos recortes.

- Síntese inicial: `outputs/consolidacao_biometria_2026-10-20/RESULTADOS_CONCLUIDOS.md`.
- Rodada exploratória: `outputs/consolidacao_biometria_2026-10-20/SEGUNDA_RODADA.md`.
- Texto do artigo: `artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md`.
- Pesos e fontes necessários foram preservados em `backups/`.

As indicações de execução em andamento nas seções históricas abaixo
descrevem etapas já encerradas. Não iniciar cópias duplicadas para acompanhá-las.
Use `executar.ps1 status_producao.py` para consultar os marcadores atuais.

> **Fase de produção:** o novo retreinamento UBIPr está em
> `outputs/cnn/ubipr_retreino_2026-10-20`. Consulte
> [PLANO_ARTIGO_2026-11-09.md](PLANO_ARTIGO_2026-11-09.md) e
> [PESQUISA_BASES_PUBLICAS_2026-10-20.md](PESQUISA_BASES_PUBLICAS_2026-10-20.md)
> para a estratégia com bases públicas. `executar.ps1 status_producao.py` mostra
> o progresso salvo; checkpoint parcial não equivale a treinamento concluído.
> A base clínica principal atual é SLP-VLD v3, com protocolo em
> `outputs/clinico_slpvld_2026-10-20/`. CatScreen permanece como domínio externo.

O ambiente foi instalado e verificado neste computador com Python 3.12.10,
PyTorch 2.14.1+cu126 e a RTX 3050 Laptop de 6 GB. As versões completas estão em
`requirements-windows.lock.txt`. O Python base está em `../.runtime/python312`.

O ambiente virtual fica em `C:/Users/lucaz/pfc-tcc-venv`, e o cache Hugging Face
em `C:/Users/lucaz/pfc-hf-cache`. Os caminhos curtos resolvem falhas de instalação
e download causadas pelo limite de caminhos do Windows. Os arquivos locais
`data/python-path.txt` e `data/hf-home.txt` registram esses destinos.

## Executar

Abra PowerShell em `pfc1-segmentacao-mmu`. O lançador configura Python, cache de
modelos e Matplotlib; não é necessário ativar o ambiente nem modificar o PATH.

```powershell
.\executar.ps1 preparar_dados.py --no-download
.\executar.ps1 auditar_catscreen.py
.\executar.ps1 diagnosticar_ambiente.py
.\executar.ps1 -Script '-m' -Argumentos @('unittest', 'discover', '-p', 'test_*.py', '-v')
```

Os relatórios locais ficam em `data/auditoria_instalacao.json`,
`data/catscreen/auditoria.json` e `data/diagnostico_ambiente.json`.

## Dados obtidos

| Base | Cópia disponível | Finalidade |
|---|---|---|
| MMU + máscaras | 450 pares, 45 pessoas | Segmentação; sem rótulos clínicos |
| UBIPr Single Eyes Segmented | 11.018 pares, 261 pessoas | Segmentação e reconhecimento entre sessões |
| CatScreen, amostra Data2025-main | 400 imagens e quatro planilhas | Inspeção e preparação de estudos clínicos |
| SLP-VLD v3 | 2.228 registros pareados, uma duplicata removida | Base clínica principal; 1.520/304/304 imagens internas e 99 externas |
| SLID | 2.617 imagens e anotações | Alternativa clínica auditada, fora do caminho crítico |
| Nuclear Cataract v2 | 1.320 imagens de 115 pacientes; seleção rotulada de 335 imagens | Alternativa para graduação de catarata |

O arquivo UBIPr tem o mesmo SHA-256 do registro histórico. O CatScreen contém
200 imagens Clean (140/20/40), 100 Noisy e 100 Unlabelled. A auditoria encontrou
todos os arquivos referenciados nas planilhas, imagens válidas e nenhum ID
compartilhado entre treino, validação e teste Clean. Não há máscaras de íris
nessa amostra; não assumir que o identificador e as imagens repetidas bastam
para um estudo longitudinal de reconhecimento. As classes brutas foram
preservadas sem reinterpretar diagnóstico ou gravidade.

Fontes e condições: [UBIPr, CC BY-NC-SA 4.0](https://iris.di.ubi.pt/ubipr.html),
[CatScreen, uso acadêmico e educacional](https://www.iab-rubric.org/resources/healthcare-datasets/catscreen).
O CatScreen baixado é somente a amostra pública, não a base completa.

## Modelos e validação

- SAM 2.1 Tiny e OpenIRIS: pesos públicos baixados nas revisões dos scripts.
  SAM 2.1 executou em CUDA; OpenIRIS fez inferência ONNX em uma imagem real.
- SAM 3: código oficial instalado na revisão
  `7f473cfd983d5eb43040ff608f66bff0d7bdcb53`. Checkpoint SAM 3.1 completo
  baixado (3.502.755.717 bytes), com segmentação offline de duas imagens UBIPr
  concluída em CUDA e prancha visual conferida. O carregador informou quatro
  pesos ausentes em `backbone.vision_backbone.convs.3`, como na execução
  histórica. Essa limitação impede afirmar compatibilidade integral do
  checkpoint multiplex com o detector de imagem, embora a inferência funcione.
- DINOv3: autenticação validada, pesos completos baixados (1.212.559.808 bytes)
  e inferência offline em CUDA concluída em duas imagens. Embeddings de 1.024
  dimensões, finitos e com norma 1. Revisão fixada no script de validação.
- U-Net: os checkpoints científicos anteriores não estão nesta cópia. O teste
  de instalação criou um checkpoint novo de uma época em oito amostras por
  partição; ele não substitui o modelo dos relatórios.

Os testes de instalação ficam em `outputs/instalacao_2026-10-20/`. Não utilizar
suas métricas no TCC: validam execução e têm amostragem reduzida. Os resultados
históricos foram preservados. SAM 2 emitiu aviso de configuração `sam2_video`
ao carregar o detector de imagem, mas concluiu a inferência; reter esse aviso
na análise de reprodutibilidade com a versão nova de Transformers.

Para baixar/verificar os pesos completos dos quatro modelos e registrar seus
tamanhos e hashes SHA-256 (downloads existentes são reutilizados):

```powershell
.\executar.ps1 baixar_modelos.py
```

Para repetir os testes offline de DINOv3 e SAM 3.1:

```powershell
.\executar.ps1 validar_dinov3.py
.\executar.ps1 avaliar_sam3_1_ubipr.py --model-dir outputs/instalacao_2026-10-20/ubipr_smoke --local-files-only --limit 2 --output-dir outputs/instalacao_2026-10-20/sam3_smoke
```

Evidências: `outputs/instalacao_2026-10-20/dinov3_smoke/validacao.json` e
`outputs/instalacao_2026-10-20/sam3_smoke/metricas.json`, além da prancha
`amostras_visuais.png` no mesmo diretório SAM. Esses comandos não dependem dos
checkpoints U-Net históricos; o SAM usa somente o manifesto do teste local.

O código de saída 1 indica modelos pendentes; `data/modelos/status.json`
distingue downloads concluídos de restrições de acesso.

Para recriar o ambiente, tendo o Python base instalado:

```powershell
.\instalar.ps1 -Sam3
```

O arquivo `requirements-sam3.txt` inclui os limites NumPy/ContourPy necessários
ao SAM. Para repetir exatamente as versões desta instalação, use o Python do
ambiente com `-m pip install -r requirements-windows.lock.txt --extra-index-url
https://download.pytorch.org/whl/cu126`. O arquivo é específico deste Windows.

## Pendências externas

| Base/recurso | O que falta |
|---|---|
| MOBIUS/SBVPI | Formulário assinado e liberação dos autores |
| Warsaw Disease Iris | Obter acesso/versão e termos com o mantenedor; não foi encontrado download direto utilizável |
| CMPD | Acordo institucional e senha; instruções na página oficial |
| MCIS | Licença assinada e senha |
| CatScreen completo | Acordo assinado por representante institucional e liberação |
| SLID | Download por Git LFS concluído; faltam vínculo por paciente e licença de dados separada explícita para uso principal |
| Checkpoints U-Net históricos | Recuperar cópia original ou executar novo treinamento, com novo registro |

As bases opcionais NIR, como OpenEDS/CASIA/Notre Dame, não são dependências
dos scripts atuais e não foram baixadas. As minutas existentes em
`EMAILS_SOLICITACAO_DATASETS.md` podem ser utilizadas nos pedidos institucionais.

Para um novo treinamento completo, grave em outra pasta:

```powershell
.\executar.ps1 treinar_segmentacao_ubipr.py --no-download --epochs 30 --batch-size 32 --base-channels 8 --seed 42 --output-dir outputs/cnn/ubipr_reproducao_2026-10-20
```

Isso cria novos pesos, não recupera os pesos históricos nem garante métricas
idênticas em versões diferentes. Os avaliadores que recebem `--cnn-dir`,
`--cnn-output-dir` ou `--model-dir` devem apontar para esse novo diretório.
O ensaio `avaliar_robustez_reconhecimento.py` agora aceita `--cnn-dir` e verifica
a existência das métricas finais antes de usar os pesos da U-Net. O protocolo
ativo está em `PROTOCOLO_AREA_IRIS_2026-10-20.md`. O piloto técnico concluiu 19
condições; a execução completa aguarda o retreinamento automaticamente pelo
processo `iniciar_biometria_area.py` já iniciado. Não abrir outra cópia em paralelo.

Para acompanhar:

```powershell
.\executar.ps1 status_producao.py
Get-Content outputs/biometria_area_completa_2026-10-20.log -Tail 8
```

A triagem clínica está em
`outputs/biometria_clinica_triagem_2026-10-20/protocolo_triagem.json` e ainda
não corresponde a resultados biométricos clínicos. O rascunho ativo do artigo é
`artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md`.

## Reconhecedor específico de íris — HDBIF

Fontes e três arquivos de pesos públicos foram obtidos dos autores e verificados
em `data/modelos/cvrl_hdbif`. Foi instalado OpenCV headless 4.11.0.86; `pip check`
passou e o ambiente está registrado em `requirements-windows.lock.txt`.

Os pilotos UBIPr e SLP-VLD estão concluídos e preservados em
`outputs/hdbif_validacao_piloto_2026-10-20` e
`outputs/hdbif_slpvld_validacao_piloto_2026-10-20`. Não reexecutar nessas pastas.
São testes de quatro consultas, sem resultados finais nem mínimo de área.
Consulte `AVALIACAO_RECONHECEDORES_2026-10-20.md` para limitações e diferença
entre o checkpoint circular disponibilizado e o citado na configuração original.

O relatório do experimento completo de área está aguardando automaticamente a
conclusão da inferência. Seu log é
`outputs/biometria_area_completa_2026-10-20_relatorio.log`.

## Validação clínica ampliada e teste congelado

A validação HDBIF em 171 imagens terminou: Rank-1 de 45,95% e TAR de 43,24%,
com FMR empírica de 0,98%. O resultado do piloto pequeno não deve ser
generalizado. Os intervalos por pessoa e as falhas estão em
`outputs/hdbif_slpvld_validacao_completa_2026-10-20/RELATORIO_VALIDACAO.md`.

Após comparar quatro variantes apenas na validação, a configuração padrão
permaneceu selecionada. O teste clínico independente foi iniciado com esse
reconhecedor e o limiar congelado, sem ajustes no teste:

```powershell
Get-Content outputs/hdbif_slpvld_teste_congelado_2026-10-20.log -Tail 8
.\executar.ps1 status_producao.py
```

O teste contém 495 imagens, 176 olhos e 319 consultas. O relatório com
intervalos será gerado automaticamente após `CONCLUIDO.json`. A execução é
em CPU e preserva a GPU para o retreinamento e o experimento UBIPr.
Esta rodada usa imagens originais e não estabelece mínimo de área clínica.

## Rodada inicial concluída; treinamento de identidade em andamento

O retreinamento de segmentação terminou (30 épocas; melhor checkpoint na 26ª;
Dice de teste da íris 0,9342). As 19 condições DINOv3 e o teste clínico HDBIF
também terminaram. Os números consolidados e as figuras estão em
`outputs/consolidacao_biometria_2026-10-20/RESULTADOS_CONCLUIDOS.md`.
O mínimo não foi determinado pelo critério registrado nesta rodada.

Uma nova rodada exploratória treina um extrator para identidade ocular,
com ResNet18 e margem angular. O teste técnico passou e o treinamento completo
foi iniciado, com até 30 épocas e seleção apenas pela validação UBIPr:

```powershell
Get-Content outputs/identidade_arcface_ubipr_2026-10-20.log -Tail 8
.\executar.ps1 status_producao.py
```

Não executar outra cópia simultânea. Um processo já aguarda `CONCLUIDO.json`
para criar o backup dos pesos finais. A avaliação Nuclear Cataract foi
registrada em `outputs/nuclear_biometria_protocolo_2026-10-20/protocolo.json`,
com pacientes separados entre calibração e teste, antes de examinar escores.
Ainda não foi executada a avaliação de reconhecimento nessa base.


### Desenvolvimento posterior: segmentação sob oclusão

O diagnóstico e o novo ajuste foram concluídos. O novo segmentador melhorou Dice e identificação sob oclusão inferior, mas regrediu em outras condições; não substituiu o candidato aprovado. [Resultados e máscaras reais](DIAGNOSTICO_E_SEGMENTACAO_ROBUSTA_2026-10-21.md).
