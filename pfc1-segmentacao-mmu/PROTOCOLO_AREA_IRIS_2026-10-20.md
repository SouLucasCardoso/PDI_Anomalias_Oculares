# Objetivo atualizado pelo autor em 20/10/2026

Investigar a relação entre área preservada da íris e reconhecimento de identidade ocular. O título e o escopo podem mudar com anuência já informada do orientador. Os protocolos de classificação clínica previamente preparados ficam como alternativas não executadas; não são o objetivo principal.

Título provisório: Influência da área preservada da íris no reconhecimento de identidade sob oclusões controladas e alterações oculares.

## Experimento em execução

1. Retreinamento U-Net UBIPr, até 30 épocas, semente 42, sem recuperar resultados históricos como se fossem novos.
2. Piloto técnico em CPU, quatro olhos por partição, uma captura por sessão e olho, exclusivamente com máscaras de referência. Seus resultados não serão estimativas finais para o artigo.
3. Execução completa em GPU automaticamente após conclusão do treino e do piloto. Partições originais por pessoa; identidade pessoa + lado; galeria da sessão 1 e consultas da sessão 2; galeria fixa. Ramos: imagem inteira, íris com referência e íris com U-Net.

Oclusões superior e inferior de 10% a 90%, em passos de 10 pontos percentuais, substituem somente pixels da íris anotada. A condição original preserva 100%. Registrar a cobertura efetivamente alterada, pois há arredondamento por pixel. Este ensaio mede perda controlada de área; não reproduz um diagnóstico nem prova causalidade de doenças.

Métricas: Rank-1, TAR e FMR; limiar definido somente na validação para FMR empírica de até 1%; intervalos pareados com reamostragem por pessoa. O mínimo operacional exploratório exige Rank-1 e TAR de pelo menos 90%, inclusive em todas as frações maiores, separadamente por orientação e ramo. Se a condição original não atingir o critério, o mínimo não é determinado neste reconhecedor. O critério é uma escolha experimental, não uma norma clínica. A grade oferece resolução de 10 pontos, não um percentual universal exato.

DINOv3 é inicialmente uma referência de características genéricas. Um desempenho baixo da íris original exige investigar normalização e reconhecedor específico antes de atribuir as perdas exclusivamente à área disponível. Evitar usar informação periocular como evidência de reconhecimento pela íris.

## Condições clínicas reais

Auditar Nuclear Cataract e SLP-VLD para múltiplas imagens por olho, datas distintas, duplicatas e consistência de identidade e lateralidade. Mais de uma imagem não comprova sessões independentes. SLP-VLD possui inconsistências entre identificadores de metadados e prefixos e uma duplicata entre lados: resolver antes da avaliação. Não há máscaras de referência da íris nessas bases; as previsões exigem inspeção. Área visível, qualidade útil e extensão da doença não são equivalentes.

## Acompanhamento

Logs: `outputs/retreino_2026-10-20.log`, `outputs/biometria_area_piloto_2026-10-20.log` e `outputs/biometria_area_completa_2026-10-20.log`. Conclusão do reconhecimento: arquivo `CONCLUIDO.json` na respectiva pasta. Máquina deve permanecer ligada. O agendador aguarda no máximo seis horas pelas dependências e registra falhas; não utiliza checkpoint parcial.

Este protocolo substitui o objetivo de classificação nos documentos de planejamento e no rascunho anterior. O artigo será reescrito com o objetivo atualizado e resultados novos, sem reutilizar números históricos como novos experimentos.

## Continuação da execução

O piloto concluiu 19 condições sem falhas de extração; é uma amostra técnica e não determina o percentual mínimo. O lançador PowerShell foi corrigido para não interromper Python devido a mensagens normais em stderr. A primeira tentativa interrompida foi preservada na pasta com sufixo `falha_lancador`.

O processo de espera do experimento completo foi reiniciado com o lançador corrigido; seu log ativo é `outputs/biometria_area_completa_2026-10-20_reinicio.log`. O treinamento não foi reiniciado.

A triagem clínica selecionou preliminarmente 666 imagens, 236 olhos e 143 pessoas. Foram excluídos 12 prefixos com metadados ambíguos. A validação tem 60 olhos e 111 consultas; o teste, 176 olhos e 319 consultas. A auditoria perceptual e a revisão visual inicial estão em `outputs/biometria_clinica_triagem_2026-10-20/REVISAO_VISUAL.md`. Nenhum resultado biométrico clínico foi produzido.

O rascunho ativo é `artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md`. A eventual avaliação complementar de um reconhecedor específico deverá usar nova pasta, protocolo e registro de origem dos pesos. O repositório acadêmico [CVRL/OpenSourceIrisRecognition](https://github.com/CVRL/OpenSourceIrisRecognition) disponibiliza alternativas que incluem normalização polar e codificação específica de íris; compatibilidade e adequação à luz visível ainda não foram verificadas localmente.
