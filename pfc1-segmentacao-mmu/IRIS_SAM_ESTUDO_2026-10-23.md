# Estudo do Iris-SAM — 23/10/2026

## Escopo

O usuário solicitou verificar a cópia local `Segmentadores de Terceiros/Iris-SAM-main`, sua utilização real, comparação com nossa U-Net e possibilidades de reaproveitamento. O repositório externo permanece sem alterações. A comparação foi registrada em `outputs/irissam_viabilidade_val_2026-10-23` antes da inferência e utiliza somente uma amostra de validação, sem treino, teste ou identificação biométrica.

Fontes primárias: [repositório dos autores](https://github.com/ParisaFarmanifard/Iris-SAM), [artigo, versão 3](https://arxiv.org/html/2402.06497v3) e [implementação original SAM](https://github.com/facebookresearch/segment-anything). Autores: Parisa Farmanifard e Arun Ross, ICPRAI 2024, arXiv:2402.06497.

## Relevância científica

O trabalho ajusta SAM para segmentação binária da íris, com destaque para Focal Loss. Avalia ND-IRIS-0405, CASIA-Iris-Interval-v3 e IIT-Delhi-Iris; o artigo não apresenta avaliação no nosso UBIPr. Os 99,58% reportados para ND são **IoU médio de segmentação**, conforme a Tabela 2, não taxa de identificação de pessoas. Não são diretamente comparáveis aos nossos 91,36% de identificação ou ao Dice da U-Net em outra população e protocolo.

O README declara disponibilização do modelo para pesquisa e outros projetos com citação dos autores. Não foi encontrado um arquivo LICENSE padrão na cópia examinada. Isso deve ser registrado como descrição da autorização declarada, sem presumir uma licença comercial ampla para todos os componentes. A implementação SAM original informa Apache-2.0.

## O que funciona e o que precisa de adaptação

1. **Há um checkpoint público acessível.** O link do README responde sem conta e identifica `IrisSAM_model.pt`, com 2.564.545.909 bytes. Ele não veio na cópia local, cuja pasta `weights` contém apenas orientação textual.
2. **A arquitetura é compatível.** A inspeção de metadados encontrou 594 tensores com formas compatíveis com SAM ViT-H, de 641.090.608 parâmetros e entrada de lado máximo 1024. Essa verificação não alocou os pesos completos.
3. **O checkpoint não é simplesmente idêntico ao SAM genérico.** Uma comparação dos metadados/CRCs dos arquivos ZIP encontrou diferenças em 89 dos 120 tensores do decoder e em um tensor do encoder (`pos_embed`), sem diferença nos 17 tensores do prompt encoder. É evidência de conteúdo modificado; CRC não é autenticação criptográfica nem informa em qual base o modelo foi treinado. O README/arquivo único não identifica inequivocamente essa base.
4. **Os exemplos de dados não são uma base utilizável.** Os arquivos `img.jpg` examinados nas pastas de exemplos têm um byte. É necessário fornecer imagens e máscaras válidas.
5. **A inferência automática não está pronta no código publicado.** `sam_infer.py` pede cliques. `sam_infer_auto.py` também chama a interface de cliques; seu esboço de detector está comentado. O artigo descreve localização automática, mas essa parte não está implementada de forma executável nesses scripts examinados.
6. **O teste usa informação privilegiada.** `dataset.py` obtém `input_boxes` da máscara de referência, via `get_bounding_box`, e os scripts de teste passam essas caixas ao SAM. Isso avalia segmentação com localização fornecida pela anotação; não equivale ao nosso pipeline automático. A nossa comparação separa esse modo como diagnóstico oracle.
7. **Os rótulos precisam ser convertidos.** O loader externo pressupõe máscaras binárias e usa limiar 117 em uma transformação. No UBIPr, íris é valor nativo 85, esclera 170 e sobrancelha 255; aplicar essa transformação diretamente produziria o alvo errado. Nosso adaptador decodifica explicitamente a classe da íris.
8. **Há ajustes operacionais e de treinamento.** Alguns scripts fixam `cuda:2`; nossa máquina tem uma GPU. O treino reinicia o iterador com `next(iter(train_dataloader))` dentro do laço, mudando a amostragem em relação a percorrer cada lote uma vez. A variante Dice recebe logits sem conversão explícita para probabilidades, enquanto Focal usa BCE com logits. O bloco de execução/plotagem ao final do arquivo de treino também exige revisão antes de importá-lo como biblioteca.

Não foram executados os scripts de treino/GUI externos. A inferência é feita por um adaptador do nosso projeto, com o pacote SAM 1.0 instalado apenas em pasta temporária, sem alterar versões do ambiente principal nem exceções do Defender. Os pesos são carregados com `weights_only=True`, mapeamento em CPU e correspondência estrita de chaves; a inferência CUDA usa FP16 e o controle U-Net usa FP32, com verificação FP32 predefinida quando couber na VRAM.

## Protocolo da comparação local

- 32 pessoas distintas escolhidas da validação, uma imagem por pessoa, semente 63, sem filtrar pela máscara ou qualidade. As pessoas não pertencem ao treino ou ao teste do manifesto; a validação já foi usada no desenvolvimento, portanto não é confirmação cega.
- Cada imagem é avaliada limpa e com perda superior/inferior exata de 10% dos pixels anotados da íris: 96 casos pareados.
- Controle: U-Net atual, com extração automática original.
- Candidato primário: Iris-SAM com caixa calculada somente na máscara predita pela U-Net, com margem fixa de 5%. Trata-se de refinamento em duas etapas, não de localização autônoma do Iris-SAM.
- Diagnóstico secundário: Iris-SAM sem prompt. Não será escolhido depois como novo candidato primário apenas pelo melhor escore.
- Diagnóstico oracle: caixa apertada da referência, claramente separado e sem possibilidade de promoção como método automático.
- Dice/IoU são calculados por imagem contra a referência completa e contra a área ainda visível, sem confundir os dois alvos. Todas as imagens e máscaras vazias/falhas são contabilizadas. Há intervalo bootstrap pareado por pessoa.
- Critério de viabilidade registrado: preservar o Dice limpo da U-Net e melhorar o Dice visível em pelo menos 0,01 em cada oclusão. Isso não autoriza substituir o reconhecedor ou declarar um novo mínimo de íris.

## Situação dos resultados locais

A inferência foi concluída e auditada: 32 pessoas, 32 fotos, três condições, quatro métodos e 384 registros. São médias por imagem nesta amostra exploratória de validação, não os resultados de todo o teste de segmentação nem de identificação. A seleção sem filtro inclui casos difíceis; por isso o Dice limpo da U-Net nesta amostra não deve ser confundido com seus 93,42% no teste completo anterior.

| Método | Dice limpo | Dice visível, perda superior 10% | Dice visível, perda inferior 10% |
|---|---:|---:|---:|
| U-Net atual | 84,40% | 81,29% | 78,67% |
| Iris-SAM + caixa automática da U-Net, primário | 78,80% | 80,29% | 77,49% |
| Iris-SAM sem prompt, diagnóstico | 0,19% | 0,13% | 0,04% |
| Iris-SAM + caixa da referência, oracle | 85,10% | 85,46% | 81,69% |

O IoU limpo da U-Net foi 79,23%, contra 70,25% do candidato primário. O ganho de Dice do oracle não implica superioridade em todas as métricas: seu IoU limpo foi 76,75%. O modo sem prompt foi avaliado com o decoder padrão de máscara única, sem busca de prompts ou seleção de máscaras pela referência; estes números não cobrem todas as variantes possíveis da arquitetura SAM.

O candidato primário perdeu **5,61 pontos percentuais** de Dice limpo; IC95% bootstrap pareado de **−6,69 a −4,60 pp**. Nas perdas superior/inferior, as diferenças de Dice visível foram **−1,00 pp** (IC95% −2,30 a +0,52) e **−1,19 pp** (−3,78 a +2,00). Os intervalos das oclusões incluem zero: esta amostra não permite afirmar uma diferença populacional nessas duas condições. O critério de viabilidade predefinido falhou, inclusive pela perda limpa. Não houve máscara vazia no controle ou candidato primário; todas as falhas/saídas permaneceram no denominador.

O processamento das 96 entradas levou aproximadamente 80 segundos, excluindo carga e conferência dos pesos, com pico de memória CUDA alocada de 2.993.655.808 bytes, aproximadamente 2,79 GiB. Esse tempo inclui U-Net e os três modos SAM, portanto não é uma comparação isolada de latência. Não foi treinado nenhum modelo. O controle FP32 em duas imagens limpas concluiu com diferença máxima de Dice de 0,0000537, ou 0,00537 pp, frente ao FP16; não houve diferença material pelo critério de 0,005. Esse controle pequeno não prova equivalência de precisão em todas as imagens.

**Decisão: utilizável com adaptações, mas não recomendado para substituir a U-Net neste momento.** O refinamento automático avaliado foi pior em média e não passou o critério registrado. A caixa oracle é informação privilegiada e não pode ser usada para justificar uma troca. Não foi executado reconhecimento biométrico nem novo teste final; os 91,36% de identificação e a fronteira de área anteriores permanecem inalterados. Não se conclui que SAM seja universalmente inferior ou que um ajuste específico no UBIPr não possa funcionar.

Checkpoint público: 2.564.545.909 bytes; SHA-256 `388a1b4ca72a455b3710fa434118c390b1e7cd1614960aaef29e5f319961fffe`. Ficou em `%TEMP%/pfc-irissam/IrisSAM_model.pt`, fora do Git. A transferência teve interrupção de conexão e foi retomada por blocos. Os registros UTC documentam a conclusão; o nome do experimento conserva a data do registro, 23/10.

Artefatos legíveis em [outputs/irissam_viabilidade_val_2026-10-23](outputs/irissam_viabilidade_val_2026-10-23), incluindo protocolo anterior à inferência, métricas individuais, caixas, proveniência e auditoria. A auditoria recalculou exatamente Dice/IoU a partir das máscaras, reproduziu caixas automáticas e bootstrap, e confirmou separação de pessoas entre treino/validação/teste. Passaram três testes do adaptador.

O pacote preservado em `backups/irissam_viabilidade_val_2026-10-23` contém 22 arquivos em 83 partes base64, ZIP de 3.945.803 bytes, sem o checkpoint público. Inclui máscaras compactadas, cópia do código registrado e figura real das primeiras duas pessoas sorteadas, sem seleção por desempenho. A restauração em TEMP conferiu hashes e a auditoria das máscaras passou novamente. Isso comprova recuperação local; não verifica envio à nuvem do OneDrive.

Para recuperar a figura e demais artefatos:

```powershell
.\executar.ps1 preservar_irissam_viabilidade.py
# Figura: $env:TEMP\pfc-irissam-restaurado-20261023\irissam_viabilidade_val_2026-10-23\comparacao_recortes_irissam.png
```

## Possibilidades de reaproveitamento

A contribuição é pertinente como referência bibliográfica de segmentação de íris e como hipótese de uso de Focal Loss para desequilíbrio de classes. Podemos aproveitar essa hipótese em um piloto controlado da nossa rede, ou estudar ajuste do decoder no UBIPr com protocolo próprio. O checkpoint e o adaptador já disponíveis permitem esse estudo futuro, mas os resultados atuais não justificam investir imediatamente em retreinar o ViT-H de 641 milhões de parâmetros, diante do prazo. Focal Loss já foi explorada em partes do projeto; citar o artigo não constitui evidência de um novo ganho local. O repositório não fornece um reconhecedor de identidade nem resolve diretamente o mínimo de área necessário.
