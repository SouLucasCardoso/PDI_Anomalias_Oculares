# Datasets recomendados para o PFC I

Levantamento verificado em 31 de agosto de 2026. Neste documento, “público”
significa disponível à comunidade acadêmica, mas não necessariamente livre para
redistribuição: várias bases exigem formulário, assinatura ou uso exclusivamente
não comercial.

## Recomendação executiva

Não foi encontrada uma única base que reúna, ao mesmo tempo, muitas máscaras de
íris de boa qualidade e rótulos clínicos completos. O desenho mais defensável é:

1. formar e validar o segmentador em **MOBIUS + UBIPr**;
2. usar **MCIS** ou **OpenEDS** apenas como validação externa complementar;
3. executar a pergunta clínica do PFC na **Warsaw-BioBase-Disease-Iris**;
4. congelar o segmentador antes de treinar os classificadores com e sem recorte.

As duas solicitações prioritárias são, portanto, o subconjunto de segmentação do
MOBIUS e a versão mais recente disponível da Warsaw-BioBase-Disease-Iris.

## Matriz de decisão

| Base | Conteúdo relevante | Acesso e licença | Uso recomendado | Prioridade |
|---|---|---|---|---:|
| [MOBIUS](https://sclera.fri.uni-lj.si/datasets.html) | 16.717 imagens RGB de 100 pessoas, três celulares, três iluminações e quatro direções do olhar. O subconjunto de segmentação tem 3.559 imagens e máscaras multiclasse de esclera, íris, pupila e região periocular. | Formulário assinado e envio por e-mail; subconjunto de aproximadamente 700 MB. Confirmar no termo recebido as permissões de derivados e publicação. | Principal base de treinamento para segmentação em luz visível e condições móveis. | 1 |
| [UBIPr segmentado](https://iris.di.ubi.pt/) | Máscaras para todas as amostras UBIPr, distinguindo pele, sobrancelha, esclera e íris. É derivada do UBIRIS.v2, com imagens RGB menos controladas e região periocular ampla. | Download gratuito sob **CC BY-NC-SA 4.0**, conforme a página oficial. | Base de início imediato e pré-treinamento; será necessário confirmar como o fundo pupilar é codificado, pois não há uma classe de pupila separada. | 1 |
| [Warsaw-BioBase-Disease-Iris](https://arxiv.org/abs/1809.01040) | 2.996 imagens de 230 íris, 184 delas afetadas, com mais de 20 condições oculares. Há NIR para todas as classes e RGB para parte delas, além de metadados clínicos. | Uso público para pesquisa e fins não comerciais é declarado no [artigo da base](https://arxiv.org/abs/1809.00212); a obtenção exige solicitação ao grupo responsável. Confirmar a versão liberada e o termo atual. | Base clínica principal para comparar classificação com imagem original e com íris segmentada. | 1 |
| [MCIS](https://dasec.h-da.de/research/biometrics/mcis/) | Rótulos de segmentação semântica multiclasse para 500 imagens da NICE.I, em comprimento de onda visível. | Download protegido por senha; requer acordo de licença assinado e envio aos responsáveis indicados na página. | Teste externo compacto do segmentador em RGB; não possui rótulos clínicos. | 2 |
| [OpenEDS](https://arxiv.org/abs/1905.03702) | 12.759 imagens com máscaras de íris, pupila e esclera de 152 participantes, além de 252.690 imagens sem rótulo e sequências. | Download mediante solicitação. Verificar se o canal de solicitação original ainda está ativo e arquivar o termo concedido. | Pré-treinamento ou teste de generalização multiclasse. Há forte mudança de domínio: NIR, iluminação controlada e câmera interna de headset VR. | 2 |
| [SBVPI](https://sclera.fri.uni-lj.si/datasets.html) | 1.858 imagens RGB de alta resolução de 55 pessoas. Todas têm marcação de esclera/periocular, mas apenas cerca de 100–130 têm íris e pupila anotadas. | Mesmo processo por formulário assinado do MOBIUS. | Pequeno teste complementar; o MOBIUS é mais vantajoso para segmentação de íris. | 3 |

## Bases grandes que não resolvem o objetivo principal

- [CASIA-IrisV4](https://tsapps.nist.gov/BDbC/Search/Details/224) tem 54.607
  imagens NIR ou sintéticas e acesso público, mas não fornece as máscaras e os
  rótulos clínicos necessários. Pode ser útil apenas para pré-treinamento não
  supervisionado ou reconhecimento biométrico.
- [ND-Iris-0405](https://cvrl-web.crc.nd.edu/projects/data/) tem 64.980 imagens
  NIR de 356 pessoas e exige licença institucional. Também não resolve, por si
  só, segmentação supervisionada nem classificação de alterações.
- UBIRIS.v2 possui mais de 11 mil imagens RGB, mas a edição UBIPr segmentada é a
  opção com licença e máscaras mais claras para começar.

## Baseline externo recomendado

O projeto [Notre Dame Open-Source Iris Recognition](https://github.com/CVRL/OpenSourceIrisRecognition)
oferece em 2026 código e modelos de segmentação baseados em U-Net++, treinados
com uma composição de BioSec, BATH, ND-Iris-0405, CASIA, UBIRIS.v2 e bases
Warsaw, inclusive olhos doentes e pós-morte. Ele deve ser avaliado como
**baseline externo congelado**, não misturado silenciosamente ao modelo autoral.
Os pesos precisam ser obtidos no link indicado pelo próprio repositório e os
termos de uso acadêmico devem ser preservados.

Essa comparação é particularmente útil para o PFC: mostra se as conclusões sobre
classificação dependem de um segmentador pequeno treinado localmente ou continuam
válidas com um método externo treinado em múltiplos domínios.

## Protocolo experimental proposto

1. Converter as máscaras das bases de segmentação para uma convenção única:
   `0=fundo`, `1=íris visível`, sempre excluindo pupila, pálpebras, cílios e
   reflexos quando a anotação permitir.
2. Dividir cada base por pessoa, nunca por imagem. Manter um arquivo de manifesto
   com identificador, olho, sessão, dispositivo e condição de captura.
3. Pré-treinar em UBIPr/MOBIUS e ajustar somente com o conjunto de treino da base
   alvo. Limiar, arquitetura e pós-processamento são escolhidos na validação.
4. Congelar o segmentador antes de abrir o teste clínico.
5. Na Warsaw, executar com as mesmas partições e o mesmo classificador:
   imagem ocular original versus imagem com máscara de íris aplicada.
6. Usar validação cruzada por pessoa/íris se o número de indivíduos liberado for
   pequeno. Relatar média, desvio-padrão e intervalo de confiança, além de AUC,
   sensibilidade, especificidade e matriz de confusão.
7. Fazer uma análise pareada: para cada repetição, calcular a diferença entre os
   resultados com e sem segmentação. Isso responde diretamente à pergunta do PFC.
8. Manter um teste de generalização separado, preferencialmente MCIS ou uma parte
   do MOBIUS nunca usada no ajuste.

## Cuidados de governança

- Não enviar imagens, máscaras, formulários ou pesos com restrição ao GitHub.
- Registrar nome e versão da base, data de obtenção, URL, termo aceito e hash dos
  arquivos recebidos.
- Confirmar se máscaras previstas e modelos treinados são considerados derivados
  redistribuíveis em cada licença.
- Não interpretar rótulo biométrico, metadado de “condição ocular” ou qualidade de
  captura como diagnóstico clínico.
- Solicitar ao orientador aprovação formal do conjunto clínico e da definição da
  tarefa: binária (saudável/alterado), por grupo de impacto ou multirrótulo por
  patologia.

## Ordem prática de aquisição

1. Enviar o formulário do **MOBIUS**, pedindo explicitamente o *Segmentation
   subset*.
2. Solicitar a **Warsaw-BioBase-Disease-Iris v2.1** ou a versão mais recente
   liberável, incluindo metadados e máscaras caso estejam disponíveis.
3. Baixar o **UBIPr segmentado** após registrar a licença CC BY-NC-SA 4.0.
4. Solicitar **MCIS** se houver tempo para um benchmark externo RGB.
5. Usar OpenEDS, CASIA e Notre Dame apenas se o experimento precisar de maior
   diversidade NIR ou de um baseline externo adicional.
