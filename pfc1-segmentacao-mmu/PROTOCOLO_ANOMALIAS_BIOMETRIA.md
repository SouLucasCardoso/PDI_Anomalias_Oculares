# Impacto de alterações oculares no reconhecimento biométrico

Decisão experimental proposta em 01/10/2026, diante da indisponibilidade da Warsaw.

**Atualização experimental no mesmo dia:** o ensaio de robustez no UBIPr foi
executado integralmente, com análise das capturas originais e perturbações
pareadas. Consulte o [relatório de resultados](outputs/robustez_reconhecimento_2026-10-01/RELATORIO_RESULTADOS.md).
As pendências abaixo relativas a dados clínicos continuam válidas.

## O que já é possível afirmar

O relatório local de 24/09 registra Top-1 de 74,28% com DINOv3 e imagem inteira no UBIPr, em 16 pessoas e 486 consultas de teste. Esse resultado inclui contexto periocular e não mede impacto clínico. O experimento de faixas pretas mede segmentação sob oclusão artificial, não reconhecimento nem doença.

Na literatura, Nigam et al. (2019) relatam desempenho de autenticação de 93,42 ± 1,76% no cenário pré/pré-operatório e 74,69 ± 9,77% no pré/pós-operatório: diferença de 18,73 pontos percentuais entre as médias, aproximadamente 20,05% de redução relativa. É efeito associado à cirurgia de catarata naquele protocolo, não uma estimativa universal de catarata, nem resultado deste projeto. Não interpretar os termos ± como intervalos de confiança sem consultar sua definição no artigo.

Fonte: https://www.nature.com/articles/s41598-019-47222-4

## Escolha de dados

1. **CMPD — alternativa principal para o pipeline RGB/periocular existente.** A página oficial informa 2.380 imagens, 145 pessoas no pré-operatório e 99 no pós, com 56 presentes em ambos. Tem download de 5,23 GB, porém protegido por senha e condicionado a acordo institucional. Permite estudar mudança pré/pós-cirurgia, não isolar doença de cirurgia. Fonte e formulário: https://iab-rubric.org/resources/biometric-datasets/iris
2. **IIITD CaSD — alternativa para reconhecimento da íris em sensores dedicados.** O artigo descreve 132 pacientes e três sensores. A disponibilidade imediata dos arquivos não foi confirmada nesta consulta; o artigo não equivale a acesso concedido. Fonte: https://www.nature.com/articles/s41598-019-47222-4
3. **CatScreen — candidato para começar a inspeção de olhos clinicamente alterados.** Há amostra pública anunciada e conjunto completo mediante licença. É uma base de triagem clínica; antes de qualquer reconhecimento, verificar identificador pseudonimizado, lateralidade, capturas distintas por olho, sessões e permissões de uso. Sem esses elementos, serve para inspeção/segmentação, não para medir identificação. Fonte: https://www.iab-rubric.org/resources/healthcare-datasets/catscreen

Nenhuma dessas bases foi baixada ou testada nesta etapa. Não substituir fotos externas do olho por retinografias para testar o pipeline atual de íris.

## Pergunta e medida principal

Pergunta operacional: quanto cai a identificação correta de uma mesma identidade ocular quando a condição da consulta muda, mantendo a galeria, o reconhecedor e a regra de decisão fixos?

Medida principal: queda absoluta de Rank-1, em pontos percentuais, entre cenário de referência e cenário alterado. Reportar também redução relativa, EER descritivo, TAR/FNMR no limiar fixado em validação, FAR efetivamente observado no teste e falhas de cadastro/extração. Não confundir similaridade do embedding com probabilidade de identificação correta.

## Protocolo mínimo para dados reais

- Criar manifesto com caminho, pessoa, lado do olho, sessão, condição, dispositivo e origem do rótulo clínico. Usar pessoa + lado como identidade ocular; separar pessoas entre treino, validação e teste. Auditar o carregador atual, cujo reconhecimento agrupa por `sample.subject`, antes de reutilizá-lo para íris.
- Exigir pelo menos duas capturas distintas por olho para pares genuínos. Não usar a própria imagem, cópia ou transformação da imagem da galeria como consulta real independente.
- Na CMPD/CaSD, comparar pré/pré e pré/pós nos mesmos indivíduos elegíveis, mantendo sensor e condições de aquisição tão comparáveis quanto possível. Separar fotos da galeria das consultas pré-operatórias. Pós/pós é um terceiro cenário para investigar recadastro.
- Fixar modelo e limiares usando somente treino/validação. Para FAR-alvo de 1%, registrar a FAR empírica e tratar empates de escores explicitamente. Não anunciar FAR de 0,1% como estimativa estável com poucos indivíduos/comparações independentes.
- Avaliar imagem inteira e íris isolada separadamente. DINOv3 inteiro é baseline periocular; para uma conclusão sobre textura da íris, incluir normalização e reconhecedor específico validado no domínio.
- Contabilizar as falhas de segmentação/extração: resultado entre casos processados e resultado operacional incluindo falhas. Revisar máscaras em amostra anotada, pois uma queda pode vir da segmentação.
- Calcular intervalo de confiança de 95% para a diferença com bootstrap por pessoa, preservando todas as capturas e os dois olhos no mesmo bloco. Informar tamanho da galeria e número de pessoas, olhos e consultas.
- Comparação de grupos saudáveis e alterados de bases/sensores diferentes não isola efeito da doença. Sem comparação longitudinal adequada ou controles de aquisição, apresentar associação, não causalidade.

## Caminho executável enquanto o acesso clínico não chega

No UBIPr, é possível preparar um estudo de robustez do reconhecimento com perda controlada de informação: manter galeria da sessão 1, perturbar somente consultas da sessão 2 em níveis predefinidos e comparar cada consulta à sua versão original. Medir níveis sobre a área anotada de íris e registrar cobertura efetiva. Congelar escolhas em validação antes de avaliar teste.

Esse experimento produz uma curva de perda de reconhecimento sob perturbação sintética. Não produz percentual de impacto de catarata, ceratite ou outra doença e não deve receber rótulos clínicos. O teste antigo de segmentação não substitui essa curva.

## Entrega e limite da conclusão de hoje

Há evidência publicada de interferência relevante e um protocolo definido para medi-la localmente. Ainda não há resultado clínico próprio. Para iniciar testes reais de reconhecimento, a pendência concreta é obter imagens com identidade ocular e capturas repetidas; apenas ter rótulos de doença não resolve essa exigência.
