# Relatório de avanço — segmentação, oclusão e reconhecimento no UBIPr

**Data:** 24 de setembro de 2026  
**Projeto:** Influência da segmentação da íris no desempenho de redes neurais convolucionais para a classificação de alterações oculares  
**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Base principal desta etapa:** UBIPr Single Eyes Segmented Version

## 1. Objetivos da etapa

Nesta etapa foram atendidas as orientações de expressar em percentual o comprometimento da segmentação sob oclusão, investigar o limite operacional de detecção, testar tecnologias recentes — SAM 3.1 e DINOv3 ViT-L/16 — e produzir resultados quantitativos e imagens com recortes reais.

O trabalho não realizou diagnóstico de alterações oculares. O UBIPr é útil para segmentação e identidade, mas não possui os rótulos clínicos necessários para classificar doenças.

## 2. Base e protocolo comum

O UBIPr contém 11.018 pares de imagem e máscara, de 261 pessoas. Foi mantida a divisão sem sobreposição de pessoas, com semente 42:

| Partição | Quantidade |
|---|---:|
| Treino | 7.716 |
| Validação | 1.652 |
| Teste congelado | 1.650 |

No teste, 1.642 referências de íris são não vazias e oito são vazias. Foram separadas duas tarefas: **segmentação**, que produz máscara pixel a pixel e usa Dice, IoU, recall e precision; e **reconhecimento**, que compara embeddings e usa Top-1, EER, TAR e FAR.

## 3. Acesso e preparação dos modelos

O acesso aos pesos oficiais, inicialmente pendente, foi aprovado e validado por `verificar_acesso_meta.py`, com retorno `ACESSO OK`. Também foi criado `ACESSO_MODELOS_META.md`.

O SAM 3.1 foi instalado no ambiente `C:\Users\Lucas\pfc-sam3-venv`, fora da pasta longa do OneDrive. Foram resolvidos:

- `WinError 206`, causado pelo comprimento do caminho;
- incompatibilidade BF16/FP32, usando autocast coerente em `bfloat16`;
- erro do backend Tk do Matplotlib, usando `Agg`;
- valores `NaN` do DINOv3 em FP16, usando BF16 e verificação de valores finitos.

## 4. Linha de base: Small U-Net

A Small U-Net multiclasse treinada no UBIPr obteve, no teste congelado:

| Dice | IoU | Aproveitamento | Pureza |
|---:|---:|---:|---:|
| **0,9171** | **0,8676** | 92,10% | **92,24%** |

O Dice global registrado no treinamento foi 0,9332, mas não deve ser comparado diretamente ao Dice médio por imagem da tabela. A U-Net continua sendo o melhor método de segmentação geral neste conjunto.

## 5. Oclusão artificial

Foi criado `avaliar_oclusao_ubipr.py`. Nas 1.642 imagens com referência não vazia, faixas pretas horizontais foram inseridas pelas margens superior e inferior. A cobertura foi medida como percentual dos pixels anotados. A U-Net permaneceu congelada e foi comparada com a porção ainda visível.

O sucesso foi predefinido como Dice visível ≥ 0,70. O limite seria o maior percentual em que pelo menos 95% dos casos-direções fossem aprovados. Foram executadas avaliações de 0% a 90% e uma faixa fina de 0% a 10%.

| Alvo | Oclusão real média | Dice visível | Sucesso |
|---:|---:|---:|---:|
| 0% | 0,00% | 0,9171 | 96,22% |
| 1% | 1,92% | 0,7091 | 58,25% |
| 5% | 6,39% | 0,6921 | 56,85% |
| 10% | 11,60% | 0,6650 | 52,89% |
| 20% | 21,79% | 0,6061 | 46,86% |
| 30% | 31,80% | 0,4885 | 33,50% |
| 40% | 41,83% | 0,2757 | 10,87% |
| 50% | 51,80% | 0,1002 | 1,31% |

Pelo critério adotado, o limite operacional foi **0% de oclusão artificial adicional**. A primeira perturbação causou queda de 37,97 pontos percentuais na aprovação.

Esse resultado demonstra baixa robustez a faixas pretas fora da distribuição de treino. Ele **não** prova que 1,92% de oclusão natural inviabiliza uma íris e não estabelece o limite biométrico de reconhecimento. A faixa altera também o contexto e não reproduz pálpebras, cílios ou reflexos. O valor deve ser apresentado como limite do protocolo artificial.

## 6. SAM 3.1 zero-shot

O SAM 3.1 foi executado em CUDA nas 1.650 imagens, com o prompt `iris of the eye` e confiança 0,5, sem treinamento no UBIPr.

| Método | Dice | IoU | Aproveitamento | Pureza |
|---|---:|---:|---:|---:|
| Small U-Net | **0,9171** | **0,8676** | 92,10% | **92,24%** |
| SAM 3.1 | 0,8834 | 0,8095 | **95,90%** | 82,51% |
| SAM 2.1 Tiny | 0,7026 | 0,6278 | 77,22% | 65,33% |

O SAM 3.1 superou o SAM 2.1 em 0,1808 de Dice e ficou 0,0337 abaixo da U-Net. Seu maior recall indica que preserva mais pixels da referência; a pureza inferior revela mais inclusão de região externa. Houve falso positivo nas oito referências vazias.

A prancha `outputs/modelos_modernos/sam3_1_ubipr/amostras_visuais.png` mostra pior, mediano e melhor caso com recortes reais. O pior revela possível anomalia de anotação: a referência contém poucos pixels sobre a esclera, enquanto o SAM recorta visualmente a íris. Esses casos exigem auditoria manual.

O carregador oficial informou quatro pesos convolucionais ausentes ao extrair o detector de imagem do checkpoint multiplex. A inferência terminou, mas a advertência foi registrada como limitação de reprodutibilidade.

## 7. DINOv3 ViT-L/16 para reconhecimento

O modelo oficial `facebook/dinov3-vitl16-pretrain-lvd1689m`, com cerca de 300 milhões de parâmetros, foi usado congelado como extrator de embeddings. Ele não foi usado para máscaras porque o checkpoint é um backbone de representação visual, sem uma cabeça de segmentação pixel a pixel.

Foram mantidas 16 pessoas presentes nas duas sessões na validação e 16 no teste. A sessão 1 formou a galeria por centróide; a sessão 2 forneceu 482 consultas de validação e 486 de teste. Os limiares de FAR foram definidos somente na validação.

| Entrada | Top-1 | EER | TAR @ FAR 1% | TAR @ FAR 0,1% |
|---|---:|---:|---:|---:|
| Imagem inteira | **74,28%** | **14,41%** | **47,33%** | **10,08%** |
| Referência manual | 26,54% | 41,36% | 7,82% | 2,67% |
| Máscara da U-Net | 33,33% | 38,72% | 10,29% | 3,29% |

Na imagem inteira, as similaridades médias foram 0,8802 para pares genuínos e 0,7009 para impostores.

O DINOv3 foi útil como prova de conceito de reconhecimento, não como recortador pronto. O resultado superior com a imagem inteira indica uso de pele, sobrancelha, geometria do olho e contexto periocular. Ao isolar a íris, o Top-1 caiu 47,74 pontos percentuais mesmo com a máscara manual. Logo, 74,28% não representa reconhecimento puro da textura da íris.

O recorte da U-Net superar o manual provavelmente ocorreu porque preservou contexto externo útil ao DINOv3, e não porque seja anatomicamente superior. Para reconhecimento específico ainda são necessários normalização polar, adaptação ao domínio e aprendizado métrico. Para segmentar com DINOv3, seria preciso acrescentar e treinar uma cabeça densa.

O gráfico foi salvo em `outputs/modelos_modernos/dinov3_vitl16_ubipr/comparacao_reconhecimento.png`.

## 8. Conclusões

Não existe um vencedor único porque as tarefas diferem:

- **Melhor segmentação geral:** Small U-Net, Dice 0,9171.
- **Melhor cobertura da referência:** SAM 3.1, recall 95,90%, porém com mais falso positivo.
- **Melhor modelo zero-shot:** SAM 3.1, muito acima do SAM 2.1.
- **Reconhecimento:** somente o DINOv3 foi avaliado nesta etapa; o Top-1 de 74,28% depende fortemente do contexto periocular.
- **Oclusão:** a U-Net foi sensível ao artefato; o limite de 0% é específico do protocolo, não anatômico ou biométrico.

Assim, DINOv3, U-Net e SAM não podem ser ordenados em uma mesma tabela de “melhor modelo”. U-Net e SAM geram máscaras; DINOv3 gera representações vetoriais. Para recortar hoje, a U-Net é a melhor opção geral e o SAM 3.1 a melhor alternativa zero-shot. Para identidade, o DINOv3 é uma linha de base promissora, mas ainda precisa ser adaptado à íris.

## 9. Artefatos e verificação

- `ACESSO_MODELOS_META.md` e `verificar_acesso_meta.py`;
- `avaliar_oclusao_ubipr.py` e seu teste;
- `outputs/robustez_oclusao_ubipr/` e `outputs/robustez_oclusao_ubipr_fino/`;
- `avaliar_sam3_1_ubipr.py`, seu teste, métricas e `amostras_visuais.png`;
- `avaliar_dinov3_ubipr.py`, seu teste, métricas e `comparacao_reconhecimento.png`;
- `comparar_modelos_ubipr.py`, `outputs/comparacao_ubipr.json` e `README.md` atualizados.

Ao final, **23 testes automatizados foram aprovados**.

## 10. Próximos passos

1. Auditar referências vazias e casos visualmente inconsistentes.
2. Calibrar prompt e confiança do SAM 3.1 apenas na validação.
3. Comparar no reconhecimento os recortes da referência, U-Net e SAM 3.1.
4. Normalizar o anel da íris para coordenadas polares.
5. Adaptar o DINOv3 com fine-tuning e aprendizado métrico, sem misturar identidades entre partições.
6. Repetir a oclusão com um reconhecedor adaptado e artefatos mais realistas.
7. Obter uma base clínica com rótulos de alterações oculares.

## 11. Síntese para apresentação

A U-Net treinada no UBIPr ainda fornece o melhor recorte geral. O SAM 3.1 chegou perto sem treinamento local e cobriu mais a referência, embora inclua regiões extras. O DINOv3 não é um segmentador pronto: ele transforma imagens em embeddings e, nesta avaliação, reconheceu melhor com o contexto periocular. Isso mostra potencial para reconhecimento, mas exige adaptação antes de sustentar conclusões sobre a textura da íris ou o percentual necessário para identificação.
