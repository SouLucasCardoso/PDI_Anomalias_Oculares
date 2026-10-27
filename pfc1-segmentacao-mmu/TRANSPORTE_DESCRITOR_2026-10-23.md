# Compatibilidade do descritor polar com a nova geometria — 23/10/2026

## Resultado

Uma correção residual de descritores foi ajustada exclusivamente no treino original, sem alterar o reconhecedor. O piloto falhou no controle interno previamente registrado: embora recuperasse um acerto de identificação, piorou a aceitação de genuínos e a aproximação aos descritores de referência. **Não houve execução de identidade na validação principal ou no teste, nem promoção de modelo.**

## Hipótese e método

O ResNet18 polar congelado foi treinado com a geometria original. A representação circular/elíptica aprendida modifica os recortes de alguns casos sem modificar esse encoder. Foi investigado se um transporte residual simples poderia aproximar os novos descritores dos descritores originais da mesma foto, isolando a compatibilidade de domínio da mudança de pesos do encoder.

Foram conferidas as 7.716 entradas de treino na ordem do manifesto. Das 259 imagens que utilizavam a alternativa geométrica concêntrica, 255 produziram recortes diferentes sob a geometria aprendida. As demais imagens reutilizaram exatamente os descritores originais. Nas 259 imagens recompostas, os recortes polares originais coincidiram pixel a pixel com o cache anterior. Nenhuma máscara de referência foi usada para produzir os recortes dessa inferência; foram usadas as máscaras preditas pelo segmentador congelado.

O ajuste da regressão usou somente as 200 imagens alteradas dos 167 participantes de ajuste. Outras 55 imagens alteradas pertenciam aos 16 participantes do monitor. O monitor completo contém 960 fotos, incluindo 480 consultas S2, todas mantidas, com uma falha de extração. As 55 fotos alteradas incluem cadastro e consulta; não são 55 consultas.

A regressão recebe o descritor novo normalizado de 256 dimensões e estima o resíduo entre o descritor original e o novo da mesma foto. Foram usados padronização, ridge com regularização fixa 1, pesos uniformes e intercepto não penalizado. A saída é normalizada em L2 e convertida ao mesmo tipo float32. A correção só se aplica quando houve mudança efetiva do recorte. Não houve busca de hiperparâmetros, ajuste do backbone, seleção nas consultas de validação ou nova oclusão artificial.

O critério registrado antes da execução exigia melhora da similaridade média com o professor nas fotos alteradas do monitor, além de Rank-1 e TAR pelo menos iguais aos das duas referências internas, original e elíptica. Essa barreira impedia avaliar a adaptação na validação principal se os controles internos piorassem.

## Alinhamento de descritores

| Papel | Fotos alteradas | Cosseno médio antes | Cosseno médio depois |
|---|---:|---:|---:|
| Ajuste | 200 | 0,684239 | 0,850565 |
| Monitor | 55 | 0,740051 | 0,661303 |

Os valores são similaridades entre descritores da mesma foto sob duas geometrias, não taxas de identificação. A melhora no ajuste acompanhada de piora no monitor é compatível com sobreajuste deste transporte. Não permite concluir que toda adaptação de descritores falhará, nem atribuir causalmente a ela todos os erros anteriores.

## Reconhecimento interno — não é validação independente

| Descritor | Rank-1 | TAR | FMR empírico |
|---|---:|---:|---:|
| Geometria original | 479/480 = 99,7917% | 479/480 = 99,7917% | 71/7.200 = 0,9861% |
| Nova geometria, sem transporte | 478/480 = 99,5833% | 478/480 = 99,5833% | 71/7.200 = 0,9861% |
| Nova geometria, com transporte | 479/480 = 99,7917% | 477/480 = 99,3750% | 71/7.200 = 0,9861% |

Essa tabela avalia **somente o componente ResNet18 polar**, com 16 candidatos do mesmo lado e um limiar interno por método, calibrado no monitor limpo. Os limiares foram 0,28573266665140795 para o original e o transporte, e 0,28674998879432684 para a nova geometria sem transporte. Os escores não são os da fusão final.

As pessoas do monitor estão separadas das 167 pessoas que ajustaram este transporte, mas **já foram vistas pelo encoder original e pelo segmentador em seu treinamento**; o monitor também participou da seleção dos localizadores geométricos. Os 99% não são um novo resultado de generalização, não podem substituir os 91,36% do teste anterior e não demonstram progresso de área mínima. A retenção da falha de extração é responsável por pelo menos um erro em cada método.

O transporte recuperou o Rank-1 perdido pela nova geometria, mas o TAR ficou abaixo das duas referências, e o alinhamento médio também piorou. Portanto, a barreira falhou e a etapa foi encerrada sem passar à validação principal.

## Conferências

A regressão foi refeita a partir dos vetores preservados, usando apenas os índices de ajuste. A correção, os limiares, as três matrizes de escores, as decisões e a barreira foram reproduzidos. A diferença máxima de escore foi zero; as linhas sem mudança geométrica mantiveram seus descritores exatamente. Os pesos do encoder permaneceram inalterados. A suíte completa passou em **97 testes**.

Foi criada uma evidência compacta com 1.160 imagens distintas: todas as 255 fotos alteradas e todas as 960 do monitor, descontadas as 55 comuns aos dois grupos. Ela preserva os vetores usados no ajuste e todos os necessários para reproduzir a avaliação interna, sem duplicar as fotos ordinárias de ajuste. A verificação também foi executada usando essa evidência compacta. O cache completo derivado pode ser refeito, mas não é necessário para esse replay.

- [Protocolo](outputs/transporte_descritor_polar_2026-10-23/protocolo.json).
- [Conclusão e medidas](outputs/transporte_descritor_polar_2026-10-23/CONCLUIDO.json).
- [Diagnóstico de ajuste e monitor](outputs/transporte_descritor_polar_2026-10-23/DIAGNOSTICO_AJUSTE.json).
- [Auditoria com evidência compacta](outputs/transporte_descritor_polar_2026-10-23/VERIFICACAO_RELOAD.json).
- [Similaridades por imagem](outputs/transporte_descritor_polar_2026-10-23/alinhamento_por_imagem.csv).
- [Código de reprodução](verificar_transporte_descritor.py).

## Preservação e estado do estudo

A execução gravou somente em pasta temporária; os arquivos legíveis foram preservados no projeto pelo mecanismo de edição, sem alterar o Defender ou pedir exceções. O pacote recuperável preserva os bytes originais dos parâmetros, evidência compacta, escores, protocolos, auditorias e fontes em partes Base64 fora do Git. As cópias legíveis normalizam quebras de linha. Não foram duplicados os dados brutos ou os pesos dos modelos antigos; o upload na nuvem não foi confirmado.

Foi testada a restauração a partir das 31 partes preservadas no projeto: 17 arquivos recuperados, todos com SHA-256 conferido. A regressão, os escores e a rejeição foram reproduzidos novamente a partir da evidência compacta restaurada, sem acesso ao cache completo original de embeddings. O pacote tem 2.016.510 bytes e SHA-256 `1ebd423300dba0c20485a92394717cfe6e811d12f1db5f874e2ba89a8715d792`. Foram também conferidas as sete cópias textuais legíveis. Ver [registro da restauração](backups/transporte_descritor_2026-10-23/VERIFICACAO_PRESERVACAO.json).

O resultado de teste anteriormente examinado continua em 91,36% de Rank-1, 92,39% de TAR e 0,88% de FMR. As menores áreas nominais aprovadas na grade continuam em 100% para oclusão superior e 99% para inferior, sem interpretação de mínimo anatômico ou clínico universal. O piloto mostrou uma limitação de uma adaptação específica; não justificou mudar o reconhecedor de referência ou anunciar novo mínimo.
