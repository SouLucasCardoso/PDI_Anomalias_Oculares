# Análise do projeto e preparação do ambiente

**Data:** 20/10/2026. **Escopo:** código, documentação, seis relatórios de avanço
de agosto a outubro e artefatos experimentais disponíveis nesta cópia.
Não foi localizada uma monografia completa em PDF/DOCX para revisão textual.

**Atualização posterior no mesmo dia:** autenticação DINOv3/SAM 3.1 validada,
checkpoints completos baixados e inferência offline de ambos concluída em CUDA.
As pendências de acesso aos modelos descritas no registro inicial abaixo foram
resolvidas. DINOv3 produziu embeddings finitos de 1.024 dimensões em duas imagens;
SAM 3.1 segmentou duas imagens e gerou prancha visual. O carregador SAM mantém
o aviso histórico de quatro pesos ausentes na camada convolucional adicional.
As evidências ficam em `outputs/instalacao_2026-10-20/dinov3_smoke` e `sam3_smoke`.
Os checkpoints científicos U-Net continuam ausentes; esses testes não os
substituem nem constituem novo benchmark científico.

**Fase de produção para 09/11:** novo treinamento UBIPr iniciado e ainda não
concluído neste registro. Bases públicas SLP-VLD, SLID e Nuclear Cataract foram
adquiridas e auditadas. SLP-VLD selecionado como principal antes de escores
clínicos: 2.128 imagens internas após deduplicação, com divisão 1.520/304/304,
e 99 imagens externas. CatScreen passa a domínio externo complementar.
O protocolo ativo está em `outputs/clinico_slpvld_2026-10-20/`. Os registros
iniciais abaixo são históricos; as pendências institucionais não integram
mais o caminho crítico. Pesquisa e cronograma estão nos novos documentos
`PESQUISA_BASES_PUBLICAS_2026-10-20.md` e `PLANO_ARTIGO_2026-11-09.md`.

## Avaliação do TCC

O trabalho apresenta evolução experimental consistente: a prova de conceito
MMU identificou e corrigiu erros de pareamento; o UBIPr ampliou a avaliação
para 11.018 pares; os benchmarks distinguiram segmentação de representação
visual; o ensaio de outubro corrigiu a identidade para pessoa + lado do olho
e passou a estimar perdas pareadas e incerteza por pessoa.

Os controles mais relevantes são separação por pessoa, seleção na validação,
preservação do teste, contabilização de referências vazias e distinção entre
perturbação sintética e patologia real. Os relatórios registram as limitações
em vez de transformar falhas artificiais em conclusões clínicas.

O problema central continua aberto: o título trata de **classificar alterações
oculares**, mas os experimentos recentes medem **reconhecer identidades**.
Dice, Rank-1 e diagnóstico respondem a perguntas diferentes. Para preservar o
título, a próxima etapa precisa comparar o mesmo classificador clínico com
imagem original e íris segmentada, nas mesmas pessoas e partições. O estudo
biométrico pode permanecer como objetivo complementar. Caso a intenção seja
tornar biometria o objetivo principal, título e objetivos precisam ser
alinhados com o orientador.

Os 74,28% antigos do DINOv3 agrupam identidade por pessoa e não são comparáveis
diretamente aos 46,50% do ensaio ocular de outubro. Também não se deve comparar
o Dice global UBIPr de 0,9332 com o Dice médio por imagem de 0,9171 como se
fossem a mesma agregação. O resultado de imagem inteira é compatível com uso
de contexto periocular; não valida reconhecimento exclusivo da textura da íris.

Um risco técnico é a reprodução incompleta: Git preservou métricas e código,
mas excluiu datasets, pesos e manifestos locais. Isso é coerente com a política
de dados do projeto, porém exige inventário de artefatos fora do Git, hashes,
versões e instruções de recuperação. O checkpoint U-Net anterior, cujo hash
consta no registro experimental, não está disponível nesta cópia.

## Trabalho realizado nesta preparação

- Instalação do Python 3.12.10 oficial, assinatura digital verificada.
- Ambiente virtual de caminho curto em `C:/Users/lucaz/pfc-tcc-venv` e cache
  Hugging Face em `C:/Users/lucaz/pfc-hf-cache`, evitando o limite de caminhos
  do Windows/OneDrive encontrado nas tentativas iniciais.
- PyTorch CUDA, torchvision, Transformers, ONNX Runtime, bibliotecas científicas,
  código SAM 3 oficial, Triton para Windows e dependências instalados.
- Ajuste das versões NumPy/ContourPy/SciPy para compatibilidade com SAM 3;
  verificação final de dependências sem conflitos.
- MMU: imagens e máscaras baixadas, ZIPs íntegros, 450 pares/45 pessoas.
- UBIPr: 11.018 pares/261 pessoas; divisão reproduzida em 7.716/1.652/1.650.
  SHA-256 do TAR igual ao histórico:
  `b71a593dc03e04808a6ff11a1e12698cbc9151deb04575dcf8e648dabaf3de34`.
- CatScreen: amostra oficial pública baixada e extraída, com 400 imagens válidas
  e quatro planilhas. SHA-256 do ZIP:
  `f0f9e21a47f3969601c902e24448c1b951be62990ec57451f2addf71ca46f44f`.
- SAM 2.1 e OpenIRIS baixados nas revisões já fixadas pelo projeto.
- Scripts de instalação, execução, aquisição, auditoria e diagnóstico adicionados;
  versões instaladas registradas em `requirements-windows.lock.txt`.

Dados, manifestos e imagens clínicas continuam fora do Git. Os artefatos
científicos anteriores não foram substituídos por resultados novos.

## O que a amostra clínica acrescenta

A amostra CatScreen contém 200 imagens Clean, 100 Noisy e 100 Unlabelled.
No Clean, as planilhas fornecem 140/20/40 imagens para treino/validação/teste,
sem sobreposição dos IDs de metadados entre essas partições. Há 102 rótulos
`Cataract`, 58 `Normal` e 40 `Other` no Clean. Todos os nomes das planilhas
correspondem a imagens presentes; as 400 imagens passaram na verificação PIL.

Existem campos de ID, lado, diagnóstico, gravidade, qualidade e iluminação.
Não foram encontrados campos explícitos de sessão ou pré/pós-cirurgia nas
planilhas. Existem poucas repetições por ID + lado, mas isso não comprova
capturas longitudinais independentes. A amostra não contém máscaras de íris.
Ela é útil para preparar a etapa clínica exploratória, não substitui
automaticamente Warsaw/CMPD/CaSD no protocolo biométrico longitudinal.

Origem e restrições foram conferidas na [página oficial CatScreen](https://www.iab-rubric.org/resources/healthcare-datasets/catscreen).
O conjunto completo depende de acordo institucional. O [UBIPr oficial](https://iris.di.ubi.pt/ubipr.html)
declara CC BY-NC-SA 4.0 e exige atribuição ao trabalho dos autores.

## Validação de execução

- Operação matricial CUDA executada com resultado correto na RTX 3050.
- Treinamento U-Net UBIPr de uma época, oito imagens por partição, concluído
  em CUDA; gravação e recarga do checkpoint funcionaram.
- SAM 2.1 executado offline em CUDA, com quatro imagens de validação e duas
  de teste, em diretório separado. Houve aviso `sam2_video` ao instanciar
  `Sam2Model`; a execução concluiu, mas o aviso deve ser mantido na reprodução.
- OpenIRIS realizou inferência CPU em imagem real; saída de quatro canais,
  dimensões corretas e somente valores finitos.
- Construtor e processador SAM 3 importados; inferência não realizada, pois
  o checkpoint SAM 3.1 exige acesso na conta Hugging Face.
- Suíte de 28 testes automatizados aprovada; `pip check` sem conflitos.

Esses ensaios validam instalação e execução, **não são novos resultados
científicos**. Não usar as métricas das subamostras nas tabelas do TCC.

## Pendências que não se resolvem instalando bibliotecas

1. **Pesos U-Net históricos:** recuperar a cópia anterior ou executar novo
   treinamento com novo diretório e novo registro. O peso criado no teste
   reduzido não é o modelo que gerou Dice 0,9171.
2. **DINOv3/SAM 3.1:** os repositórios retornaram restrição de acesso no ambiente
   atual. É necessário autenticar a conta que aceitou as licenças. Nenhum token
   foi solicitado em texto, gravado no código ou exposto no relatório.
3. **MOBIUS/SBVPI:** o [mantenedor](https://sclera.fri.uni-lj.si/datasets.html)
   exige formulário assinado e envio para liberação.
4. **CMPD:** a [página oficial](https://www.iab-rubric.org/resources/biometric-datasets/iris)
   exige acordo assinado por representante institucional e senha.
5. **MCIS:** o [mantenedor](https://dasec.h-da.de/research/biometrics/mcis/)
   exige licença assinada e senha.
6. **Warsaw:** continua sem cópia local; o acesso/versão deve ser obtido com o
   mantenedor. A rota institucional consultada não forneceu download utilizável.
7. **SLID:** a [origem indicada no artigo](https://github.com/xumingyu-hub/SLID)
   foi localizada, mas imagens e CSV retornaram HTTP 503 nas duas rotas de
   conteúdo tentadas. Não foram marcados como adquiridos.

## Prioridade recomendada

Recuperar primeiro o checkpoint U-Net e autenticar o Hugging Face. Em seguida,
usar a amostra CatScreen para inspecionar a mudança de domínio e definir a
tarefa clínica, mantendo os rótulos Noisy separados. Antes de treinar, confirmar
o significado dos IDs e rótulos com a documentação dos autores e manter divisão
por pessoa. Para responder ao título atual, planejar a comparação pareada de
classificação original/segmentada; para biometria longitudinal, manter o pedido
CMPD/Warsaw e exigir sessões e identidades oculares verificáveis.

As instruções operacionais estão em
[INSTALACAO_LOCAL.md](../pfc1-segmentacao-mmu/INSTALACAO_LOCAL.md).
