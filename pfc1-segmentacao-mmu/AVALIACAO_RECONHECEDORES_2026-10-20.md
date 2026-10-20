# Avaliação inicial dos reconhecedores

Os números abaixo descrevem pilotos técnicos. Não devem ser incorporados ao artigo como estimativas finais, nem comparados diretamente entre bases para concluir superioridade ou efeito de doença.

| Piloto | Dados usados | Consultas | Rank-1 | Interpretação |
|---|---|---:|---:|---|
| DINOv3, íris de referência | Quatro olhos do teste UBIPr, uma captura por sessão | 4 | 50% | Execução das 19 condições verificada; mínimo não determinado porque a condição original não atende ao critério. |
| HDBIF, máscara de referência e círculos previstos | Quatro olhos da validação UBIPr | 4 | 25% | Compatibilidade confirmada; normalização, resolução e interferência dos óculos exigem investigação. |
| HDBIF, máscara e círculos previstos | Quatro olhos da validação SLP-VLD, datas mais antiga e recente | 4 | 100% | Compatibilidade em imagens clínicas confirmada; quatro consultas de duas pessoas não sustentam uma conclusão de desempenho. |

As populações dos pilotos diferem; não usar suas porcentagens para selecionar um vencedor. Nenhuma avaliação de reconhecimento foi feita no teste clínico reservado. O piloto clínico não calibrou limiar, não calculou mínimo de área e não realizou busca de hiperparâmetros. Máscaras previstas não são referência de área clínica.

## Origem e configuração HDBIF

Fontes: [repositório acadêmico CVRL](https://github.com/CVRL/OpenSourceIrisRecognition), revisão `4a535e4a9a0728e4428c25f743f6d59098ae397f`. Foram baixados somente fontes necessários e os pesos indicados pelo [README dos autores](https://github.com/CVRL/OpenSourceIrisRecognition/blob/main/methods/HDBIF/Python/readme.md). Os hashes Git das fontes foram verificados contra a árvore do repositório; fontes e pesos têm SHA-256 local em `data/modelos/cvrl_hdbif/fontes.json` e `pesos.json`.

Usam-se imagens em cinza, normalização polar 64 × 512, cinco filtros 17 × 17, busca exaustiva de deslocamento angular de ±16 colunas e distância de Hamming, sem normalização do escore. Os parâmetros seguem a configuração padrão e não foram ajustados aos pilotos.

A pasta pública dos autores disponibilizou o regressor circular `resnet18-027-0.008222-maskIoU-0.967159.pth`, enquanto o `cfg.yaml` cita um checkpoint `1543` ausente no catálogo. A substituição está explícita no protocolo, sem modificar as fontes dos autores. Não se trata de reprodução exata desse cfg. Sobreposição entre populações de pré-treinamento e avaliação não está estabelecida.

OpenCV headless 4.11.0.86 foi instalado sem alterar NumPy 1.26.4. `pip check` passou. Dependências específicas em `requirements-hdbif.txt`; ambiente completo atualizado em `requirements-windows.lock.txt`.

## Análise de área

`relatar_area_preservada.py` verifica se o experimento terminou, se cada combinação registrada possui exatamente um resultado e se a grade está completa. Aplica o critério já registrado: Rank-1 e TAR de pelo menos 90% no original e em todas as frações maiores. Uma recuperação isolada depois de uma falha não define o mínimo. O limiar é o da validação original; a FMR de teste é apresentada separadamente e pode exceder 1%.

No piloto DINOv3, a FMR de teste original foi 50%, reforçando que a calibração de uma amostra tão pequena não estabelece segurança operacional. Não usar esse piloto para estabelecer um percentual de aproveitamento da íris.

O relatório do experimento completo será gerado automaticamente pelo processo de espera já iniciado, após `CONCLUIDO.json`. Log: `outputs/biometria_area_completa_2026-10-20_relatorio.log`. Saídas: `RELATORIO_AREA.md` e `area_minima.json` na pasta da execução. A regra foi verificada com casos de condição original insuficiente, curva não monotônica e falha de uma das métricas.

## Próximas decisões científicas

Concluir o retreinamento e a curva completa UBIPr. Inspecionar a normalização clínica e a estabilidade das máscaras antes de congelar uma avaliação clínica maior. A adaptação ou o treinamento de outro reconhecedor deve usar somente treino/validação e registrar nova rodada; o teste clínico continua reservado. Um mínimo não determinado é um resultado admissível, sem atribuir a falha automaticamente à presença de doença.

A prancha dos oito exemplos clínicos do piloto foi inspecionada em `data/qa_biometria/hdbif_slpvld_normalizacao_validacao.jpg`. Os círculos acompanham aproximadamente as regiões pupilar e externa da íris, mas há pálpebras, cílios e reflexos a mascarar. Essa inspeção limitada confirma a execução da normalização, não a precisão clínica dos limites nem uma referência verdadeira de área útil. Os resultados favorecem continuar a validação, sem dispensar a auditoria da população completa.

## Validação ampliada e início do teste independente

A validação completa, com 60 olhos de 36 pessoas e 111 consultas, obteve Rank-1 de 45,95%, TAR de 43,24% e FMR empírica de 0,98%. Houve duas falhas de extração, mantidas no denominador. IC 95% condicional por pessoa: Rank-1 31,82–60,95%; TAR 29,08–57,84%. Os números do piloto de quatro consultas não se sustentaram como estimativa da amostra ampliada. Relatório em `outputs/hdbif_slpvld_validacao_completa_2026-10-20/RELATORIO_VALIDACAO.md`.

As 171 imagens foram inspecionadas em nove pranchas. Há casos de localização incorreta ou imagem muito oblíqua; nenhuma exclusão posterior a escores foi feita. A revisão está em `REVISAO_QUALIDADE.md` na mesma pasta.

Uma ablação registrada antes de calcular as variantes comparou ±16 colunas e busca circular completa, com e sem normalização do escore. Pela regra de maximizar TAR de validação com desempate predefinido, `default_raw` permaneceu selecionado. A busca completa sem normalização reduziu a TAR para 30,63%; com normalização, para 38,74%. A configuração padrão obteve 43,24%. A hipótese de que bastaria ampliar a rotação não foi confirmada.

O comparador FFT foi verificado contra o comparador oficial em todas as comparações da validação, com tolerância absoluta de 10⁻¹². O teste clínico foi iniciado somente após essa validação, seleção e registro de protocolo, mantendo configuração e limiar de 0,6546885168313318. São 495 imagens, 176 olhos, 107 pessoas e 319 consultas. Log em `outputs/hdbif_slpvld_teste_congelado_2026-10-20.log`. Esse experimento avalia reconhecimento original, sem estimar mínimo de área. Não será recalibrado no teste.
