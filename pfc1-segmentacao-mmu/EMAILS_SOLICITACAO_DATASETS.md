# E-mails para solicitação de bases de dados

Modelos preparados em 11 de setembro de 2026 para o PFC I de Lucas Cardoso
Rodrigues, Engenharia de Computação, UniSatc, sob orientação do professor
Rodrigo Ramos Silva.

Antes do envio, usar preferencialmente o e-mail institucional da UniSatc,
colocar o orientador em cópia e substituir os campos entre colchetes. Não anexar
documentos pessoais além dos exigidos pelo termo de cada base.

## 1. MOBIUS — solicitação prioritária

**Para:** matej.vitek@fri.uni-lj.si  
**Cc:** [e-mail institucional do orientador]  
**Assunto:** Request for access to the MOBIUS Segmentation Subset — undergraduate research at UniSatc, Brazil

```text
Dear Dr. Vitek,

My name is Lucas Cardoso Rodrigues, and I am an undergraduate Computer Engineering student at UniSatc, Brazil. I am conducting my Final Course Project under the supervision of Prof. Rodrigo Ramos Silva.

The project investigates iris segmentation in ocular images and evaluates how preserving the visible iris region affects a subsequent ocular-abnormality classification pipeline. The work is strictly academic and non-commercial.

I would like to request access to the MOBIUS Segmentation Subset (approximately 700 MB), including the 3,559 RGB images and the corresponding multiclass annotations for the sclera, iris, pupil, and periocular regions. We intend to use the dataset to train and evaluate semantic segmentation models, with subject-disjoint training, validation, and test partitions.

The completed and hand-signed access form is attached to this message. We agree to follow the dataset's license and usage conditions, preserve its confidentiality where required, not redistribute the data, and cite the relevant publications in any resulting academic work.

Could you also please confirm whether trained model weights and aggregate results may be published, provided that the original images and annotations cannot be reconstructed or redistributed?

Thank you for considering this request. Please let me know if any additional information or signature from my supervisor or institution is required.

Kind regards,

Lucas Cardoso Rodrigues
Undergraduate student — Computer Engineering
UniSatc, Brazil
Institutional e-mail: [seu e-mail institucional]

Supervisor: Prof. Rodrigo Ramos Silva
Supervisor's institutional e-mail: [e-mail institucional do orientador]
```

**Anexo obrigatório:** formulário oficial preenchido e assinado à mão, disponível
na página oficial do MOBIUS. No formulário e no e-mail, marcar explicitamente
`Segmentation subset`.

## 2. Warsaw-BioBase-Disease-Iris — solicitação prioritária

**Para:** [responsável atual indicado pelo Warsaw Biometrics Group/autor da base]  
**Cc:** [e-mail institucional do orientador]  
**Assunto:** Academic access request — Warsaw-BioBase-Disease-Iris v2.1 or latest available version

```text
Dear Warsaw-BioBase team,

My name is Lucas Cardoso Rodrigues, and I am an undergraduate Computer Engineering student at UniSatc, Brazil. I am conducting my Final Course Project under the supervision of Prof. Rodrigo Ramos Silva.

I am writing to request academic access to the Warsaw-BioBase-Disease-Iris v2.1 dataset, or to the most recent version currently available to external researchers. The project studies whether iris segmentation and preservation of the visible iris texture affect the performance of ocular-abnormality classification models.

We plan to conduct a strictly academic and non-commercial experiment using subject-disjoint partitions. The same classifier and partitions will be used in a paired comparison between original ocular images and images with an iris mask applied. Results will be reported only in aggregate form.

If available, we would like to request:

- NIR and RGB ocular images;
- subject/iris identifiers suitable for subject-disjoint partitioning;
- ocular-condition labels and their definitions;
- acquisition-device and session metadata;
- iris, pupil, or occlusion masks, if distributed with the current release;
- the recommended citation, license agreement, and data-use conditions.

We will not redistribute images, metadata, annotations, or any restricted material. Access will be limited to the student and supervisor, stored in a controlled project environment, and used only for the approved research purpose. We will comply with all attribution, security, publication, and deletion requirements specified by the data-use agreement.

Could you please provide the current application procedure and confirm whether trained model weights, predicted masks, and aggregate evaluation results may be published when they do not permit reconstruction of the source data?

Thank you for considering our request. I can provide a project summary, institutional confirmation, or a signed agreement if required.

Kind regards,

Lucas Cardoso Rodrigues
Undergraduate student — Computer Engineering
UniSatc, Brazil
Institutional e-mail: [seu e-mail institucional]

Supervisor: Prof. Rodrigo Ramos Silva
Supervisor's institutional e-mail: [e-mail institucional do orientador]
```

**Observação:** confirmar o destinatário na página ou formulário vigente antes do
envio. O canal histórico do grupo de Varsóvia encontrado em publicações antigas
não deve ser presumido como atual. Se a instituição exigir que o pesquisador
responsável faça o pedido, o orientador deve enviar este texto em nome do projeto.

## 3. MCIS — benchmark externo opcional

**Para:** dosorioroig@gmail.com  
**Cc:** christian.rathgeb@h-da.de; [e-mail institucional do orientador]  
**Assunto:** Signed license agreement and access request for the MCIS database

```text
Dear Dr. Osorio-Roig,

My name is Lucas Cardoso Rodrigues, and I am an undergraduate Computer Engineering student at UniSatc, Brazil, working under the supervision of Prof. Rodrigo Ramos Silva.

I would like to request academic access to the MCIS (Multi-Class Iris Segmentation) database for my Final Course Project. The project evaluates iris segmentation methods and the preservation of visible iris texture in ocular images. MCIS would be used as an external RGB benchmark for semantic segmentation, independently from model training whenever the experimental protocol permits.

The research is strictly academic and non-commercial. We will not redistribute the dataset, and we will cite the required MCIS publication in every resulting work.

The completed and signed license agreement is attached. Could you please provide the password or access instructions for the database? Please let us know if any additional institutional information or supervisor signature is required.

Kind regards,

Lucas Cardoso Rodrigues
Undergraduate student — Computer Engineering
UniSatc, Brazil
Institutional e-mail: [seu e-mail institucional]

Supervisor: Prof. Rodrigo Ramos Silva
Supervisor's institutional e-mail: [e-mail institucional do orientador]
```

**Anexo obrigatório:** acordo de licença oficial do MCIS preenchido e assinado.

## 4. UBIPr segmentado — esclarecimento opcional

O UBIPr segmentado possui download direto e licença CC BY-NC-SA 4.0; portanto,
não é necessário pedir acesso por e-mail. A mensagem abaixo só deve ser enviada
se a documentação baixada não esclarecer a codificação das máscaras ou o status
dos artefatos derivados.

**Para:** hugomcp@di.ubi.pt  
**Cc:** lfbaa@di.ubi.pt; [e-mail institucional do orientador]  
**Assunto:** Clarification on UBIPr segmented labels and derived research artifacts

```text
Dear Prof. Proença and SOCIA Lab team,

My name is Lucas Cardoso Rodrigues, and I am an undergraduate Computer Engineering student at UniSatc, Brazil. I am using the UBIPr Single Eyes Segmented Version in a strictly academic and non-commercial Final Course Project under the supervision of Prof. Rodrigo Ramos Silva.

The project investigates semantic iris segmentation and the preservation of visible iris texture for a subsequent ocular-abnormality classification experiment. We will comply with the CC BY-NC-SA 4.0 license and include the requested dataset citation.

Could you please clarify the following points about the segmented release?

1. Which label values or colors represent skin/background, eyebrow, sclera, iris, and pupil?
2. Is the pupil encoded as a separate class or as background inside the iris region?
3. Under the dataset terms, may we publish trained model weights, predicted masks, and aggregate metrics if they do not contain or allow reconstruction of the original images?

We will not redistribute the original dataset. Thank you for your guidance.

Kind regards,

Lucas Cardoso Rodrigues
Undergraduate student — Computer Engineering
UniSatc, Brazil
Institutional e-mail: [seu e-mail institucional]

Supervisor: Prof. Rodrigo Ramos Silva
Supervisor's institutional e-mail: [e-mail institucional do orientador]
```

## Ordem recomendada de envio

1. Pedir ao orientador a aprovação do texto e seu e-mail institucional para cópia.
2. Preencher, imprimir, assinar e digitalizar o formulário do MOBIUS; enviar o
   primeiro e-mail imediatamente.
3. Confirmar o canal atual da Warsaw e enviar a solicitação; se exigido, fazer o
   pedido diretamente pelo e-mail do orientador.
4. Baixar o UBIPr segmentado e enviar a consulta somente se a documentação não
   responder às três perguntas.
5. Solicitar o MCIS apenas se o cronograma comportar um benchmark externo adicional.

## Registro após cada envio

Guardar fora do repositório Git os formulários assinados e as respostas recebidas.
Registrar no projeto apenas: nome e versão da base, data do pedido e da liberação,
URL oficial, hash dos arquivos, licença aplicável e limitações de publicação. Não
versionar imagens biométricas, credenciais, senhas de download ou termos assinados.
