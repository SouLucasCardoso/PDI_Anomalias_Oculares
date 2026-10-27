# Viabilidade do segmentador compartilhado pelo orientador — 23/10/2026

## Decisão

Não integrar a aplicação `segmentadorduffatto-main` ao projeto de íris neste momento. Sua lógica principal atende à separação de mudas de Pinus, com âncoras físicas, conectividade, disputa entre instâncias e medição de caules. A ideia genérica de orientar o SAM por pontos e caixas é reaproveitável, mas o piloto automático descrito abaixo não preservou a qualidade limpa da nossa U-Net. Isso não prova que SAM seja inadequado para íris; não justifica, porém, investir na adaptação integral dessa aplicação no prazo atual.

## O que foi examinado

Foram lidos README, configuração, dependências, implementação dos fornecedores SAM2/DINOv3, evidência de primeiro plano, métodos de separação e refinamento visual. Os hashes dos arquivos examinados constam do protocolo do piloto.

- O primeiro plano clássico usa excesso de verde, canais de cor e operações direcionadas a estruturas verticais. Esses pressupostos não correspondem à íris.
- A geodésica resolve conflitos entre mudas ancoradas. Nosso problema é distinguir íris, pupila e oclusores de uma fotografia de olho; não é a mesma tarefa.
- O fornecedor SAM2 recebe pontos positivos/negativos e caixa e seleciona a máscara com maior confiança prevista. Essa interface é genérica e motivou o teste.
- O DINOv3 é opcional e atua no desempate entre instâncias; não é um segmentador de íris treinado no repositório.
- Não foram encontrados pesos treinados para íris no material examinado. O pacote também não fornece um reconhecedor biométrico.

Não foi instalado nem executado o aplicativo de plantas, e seus arquivos não foram modificados. O teste ocorreu apenas no nosso projeto, com os pesos SAM2.1 Tiny já disponíveis, sem download. O repositório externo configura SAM2 Tiny; portanto, o piloto é uma adaptação da ideia, não uma reprodução exata do pipeline externo. A comparação histórica com SAM2.1 no UBIPr já existia; este piloto usa uma orientação automática diferente, derivada da U-Net atual.

## Piloto curto registrado antes da inferência

Foram escolhidas 32 fotografias da segunda sessão do treino original: uma por olho de 16 pessoas do monitor interno, pela primeira ocorrência em ordem de nome, antes de observar os escores. Cada foto foi avaliada limpa e com perda superior/inferior de 10% da área anotada, totalizando 96 casos pareados. O monitor é reutilizado e já foi visto pela U-Net: este é um teste de viabilidade, não confirmação independente.

A U-Net congelada fornece automaticamente caixa com margem de 5%, até quatro pontos positivos de maior distância à borda por quadrante e negativos condicionados ao fundo predito. A anotação não entra nos prompts; serve apenas para definir a oclusão experimental e calcular as métricas. O SAM seleciona a máscara com maior confiança prevista, sem seleção pela referência, ajuste manual ou busca de prompts. Falha na geração de prompt produziria máscara vazia e seria contabilizada; não houve falhas nesta amostra.

O critério exigia preservar o Dice limpo, melhorar o Dice visível de cada oclusão em pelo menos 0,01 e não reduzir o Dice médio da referência completa. Nenhuma condição de validação/teste ou identidade foi inferida.

## Resultado de segmentação — Dice médio

| Condição / alvo | U-Net | SAM guiado |
|---|---:|---:|
| Limpa / referência completa | 95,15% | 91,45% |
| Perda superior de 10% / referência completa | 89,74% | 88,39% |
| Perda inferior de 10% / referência completa | 84,73% | 87,38% |
| Perda superior de 10% / área ainda visível | 91,70% | 92,65% |
| Perda inferior de 10% / área ainda visível | 89,07% | 90,75% |

O alvo visível exclui exatamente os pixels da intervenção, inclusive aqueles que já tinham valor cinza 128. A referência completa mantém os pixels anotados originalmente. A diferença entre os alvos impede confundir boa segmentação do que resta visível com recuperação de tecido oculto.

Houve melhora localizada inferior, mas perda limpa de 3,70 pontos percentuais e ganho superior visível de aproximadamente 0,95 ponto, abaixo do requisito de um ponto. O piloto **reprovou**. Os percentuais da tabela são Dice de segmentação, não acurácia de identificação nem percentual mínimo de íris necessário.

## Verificação e continuidade

Dois testes direcionados passaram. A auditoria reproduziu os prompts a partir das máscaras automáticas, os 192 registros de Dice/IoU e a reprovação do critério. O pacote de 11 arquivos em quatro partes inclui máscaras comprimidas, prompts e escores; foi restaurado com hashes conferidos. As verificações usam as referências UBIPr locais, sem nova inferência dos modelos. Não foram alteradas exceções do Defender; o envio pelo OneDrive não foi verificado.

```powershell
.\executar.ps1 preservar_triagem_sam.py
.\executar.ps1 verificar_triagem_sam.py --root "$env:TEMP/pfc-sam-triagem-restaurado-20261023"
```

Os registros ficam em `outputs/triagem_sam_guiado_treino_2026-10-23`, e a preservação em `backups/triagem_sam_guiado_treino_2026-10-23`. O carregador Transformers emitiu aviso sobre a configuração `sam2_video` usada pela classe de imagem `Sam2Model`; o carregamento e as 96 inferências terminaram, utilizando o mesmo tipo de adaptador de imagem empregado no benchmark anterior. Essa observação integra o alcance técnico do piloto; não foi comparada outra implementação do carregador.

A prioridade volta ao descritor de identidade e à tolerância à oclusão com a normalização original. Não será feita integração dos métodos botânicos nem busca adicional de prompts nesta rodada. A U-Net e o reconhecedor principal permanecem preservados; o teste principal continua com 444/486 (91,36%) sem oclusão, e nenhum novo mínimo de área foi estabelecido.
