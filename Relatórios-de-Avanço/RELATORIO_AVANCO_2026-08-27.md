# Relatório de avanço — prova de conceito de segmentação da íris

| Identificação | Informação |
|---|---|
| Projeto | Influência da segmentação da íris no desempenho de redes neurais convolucionais para a classificação de alterações oculares |
| Disciplina | Projeto Final de Curso I — PFC I |
| Curso | Engenharia de Computação |
| Instituição | UniSatc |
| Acadêmico | Lucas Cardoso Rodrigues |
| Orientador | Rodrigo Ramos Silva |
| Data do registro | 26 de agosto de 2026 |
| Etapa | Prova de conceito da segmentação da íris |
| Situação | Pipeline executada de ponta a ponta; experimento clínico ainda não iniciado |

## 1. Síntese do avanço

No dia 26 de agosto de 2026, foi concluída a primeira prova de conceito computacional do projeto. O avanço consistiu na configuração do ambiente de desenvolvimento, aquisição e auditoria dos dados, pareamento entre imagens e máscaras, separação das amostras por indivíduo, treinamento de uma rede U-Net de pequeno porte e geração de métricas, curvas de aprendizagem e exemplos visuais das segmentações produzidas.

O experimento foi executado localmente por meio do Visual Studio Code, utilizando Python e PyTorch. Foram empregadas 450 imagens do MMU Iris Database e 450 máscaras binárias associadas. O código implementado automatiza o fluxo desde a obtenção dos arquivos até a avaliação do melhor modelo no conjunto de teste.

Esta etapa não realiza diagnóstico nem classificação de alterações oculares. O MMU é uma base biométrica sem rótulos clínicos e, neste momento, foi utilizado exclusivamente para verificar a viabilidade técnica da etapa de segmentação que antecederá o experimento principal.

## 2. Objetivo da atividade

O objetivo da atividade foi validar uma pipeline supervisionada capaz de receber uma imagem ocular e produzir uma máscara binária para a região da íris. Pretendeu-se verificar se:

1. as imagens e as máscaras poderiam ser obtidas, auditadas e pareadas de forma consistente;
2. a divisão dos dados poderia ser realizada sem compartilhamento de indivíduos entre treinamento, validação e teste;
3. uma U-Net compacta conseguiria aprender uma localização inicial da íris;
4. o processo produziria artefatos suficientes para análise e reprodução posterior.

O resultado desta atividade deve ser entendido como um *baseline* metodológico. Ele valida a infraestrutura experimental, mas ainda não responde à pergunta central do PFC, que exigirá uma base clínica e a comparação da classificação com e sem segmentação prévia.

## 3. Materiais e ambiente computacional

Foram utilizadas 450 imagens em tons de cinza de 45 indivíduos, com cinco imagens de cada olho por indivíduo. As máscaras binárias indicam, em nível de pixel, a região considerada pertencente à íris e funcionam como referência para o treinamento supervisionado.

**Tabela 1 — Materiais e ferramentas utilizados**

| Item | Emprego no experimento |
|---|---|
| MMU Iris Database | Fornecimento das 450 imagens oculares |
| Máscaras manuais do MMU | Referência correta para cada imagem durante o treinamento |
| Python | Implementação da pipeline |
| PyTorch | Definição, treinamento e avaliação da rede neural |
| NumPy e Pillow | Leitura, transformação e normalização das imagens |
| Matplotlib | Geração das curvas e comparações visuais |
| Visual Studio Code | Execução e acompanhamento local do experimento |
| Git e GitHub privado | Versionamento do código, documentação e resultados permitidos |

*Fonte: Elaborado pelo autor (2026).*

O programa seleciona automaticamente uma GPU compatível com CUDA quando disponível; caso contrário, utiliza a CPU. O dispositivo efetivamente usado, o tempo de execução e as versões instaladas devem ser preservados junto aos resultados locais para garantir rastreabilidade.

## 4. Procedimentos realizados

### 4.1 Configuração do ambiente

Foi criado um ambiente virtual Python para isolar as dependências do projeto. Em seguida, foram instaladas as bibliotecas descritas em `requirements.txt`, incluindo PyTorch, NumPy, Pillow e Matplotlib. A disponibilidade da GPU foi verificada antes da execução do treinamento.

### 4.2 Aquisição e extração dos dados

O script `treinar_segmentacao_mmu.py` foi configurado para obter automaticamente dois arquivos: as imagens oculares disponibilizadas por uma cópia pública do MMU e as máscaras manuais mantidas em um repositório público. Após o download, os arquivos foram extraídos para uma pasta local ignorada pelo controle de versão.

As imagens brutas não devem ser enviadas ao GitHub, ainda que o repositório seja privado. A ausência de licença explícita para as máscaras e a indicação de licença desconhecida na cópia das imagens exigem cautela. O repositório deve conter o código de obtenção e processamento, não uma redistribuição dos dados.

### 4.3 Auditoria e pareamento

Foi verificada a existência de 45 indivíduos, 450 imagens e 450 máscaras. Durante essa etapa, foi identificada uma inconsistência entre as duas fontes:

- as pastas das imagens são numeradas de 1 a 46, com ausência da pasta 4;
- as pastas das máscaras são numeradas continuamente de 1 a 45.

Consequentemente, a associação direta por igualdade do número da pasta produziria pareamentos incorretos para a maior parte da base. O código corrige a diferença ao ordenar numericamente os 45 indivíduos de cada fonte e associá-los pela posição correspondente. Também são verificadas a lateralidade do olho, a quantidade esperada de cinco imagens por lado e a igualdade do índice de cada arquivo.

Esse controle de integridade constitui um resultado técnico relevante, pois um treinamento com imagens e máscaras de indivíduos diferentes produziria métricas sem validade.

### 4.4 Divisão sem vazamento de dados

Os dados foram separados por indivíduo, e não aleatoriamente por imagem. Com a semente aleatória 42, a divisão resultou em:

**Tabela 2 — Divisão do conjunto de dados**

| Partição | Indivíduos | Imagens | Finalidade |
|---|---:|---:|---|
| Treinamento | 32 | 320 | Atualização dos pesos da rede |
| Validação | 6 | 60 | Seleção da melhor época |
| Teste | 7 | 70 | Avaliação final do modelo selecionado |
| **Total** | **45** | **450** | — |

*Fonte: Elaborado pelo autor (2026).*

Nenhum indivíduo aparece em mais de uma partição. Essa decisão reduz o risco de o modelo ser avaliado em imagens de pessoas já vistas durante o treinamento.

### 4.5 Pré-processamento e aumento de dados

As imagens foram convertidas para tons de cinza, redimensionadas para 160 × 120 pixels e normalizadas para o intervalo de 0 a 1. As máscaras foram redimensionadas pelo método do vizinho mais próximo e convertidas para valores binários, nos quais 0 representa o fundo e 1 representa a região anotada como íris.

Somente no conjunto de treinamento foram aplicadas transformações aleatórias moderadas: espelhamento horizontal, alteração de brilho entre 90% e 110% e alteração de contraste no mesmo intervalo. As partições de validação e teste não receberam aumento de dados.

### 4.6 Arquitetura e treinamento

Foi utilizada uma U-Net compacta com três níveis de codificação e decodificação, conexões de atalho entre níveis correspondentes e saída binária por pixel. Na configuração com oito canais iniciais, a rede possui 121.033 parâmetros treináveis.

**Tabela 3 — Configuração do baseline de 30 épocas**

| Hiperparâmetro | Valor |
|---|---:|
| Épocas | 30 |
| Tamanho do lote | 16 |
| Resolução de entrada | 160 × 120 pixels |
| Canais iniciais | 8 |
| Taxa de aprendizagem | 0,001 |
| Otimizador | AdamW |
| Função de perda | Entropia cruzada binária + Dice Loss |
| Limiar da máscara prevista | 0,5 |
| Semente aleatória | 42 |
| Critério de seleção | Maior Dice de validação |

*Fonte: Elaborado pelo autor (2026).*

A cada época, foram calculadas a perda, o coeficiente Dice e a interseção sobre união (IoU) nos conjuntos de treinamento e validação. Sempre que o Dice de validação aumentou, os pesos foram gravados em `melhor_modelo.pt`. Após as 30 épocas, o melhor estado foi recarregado e avaliado uma única vez nas 70 imagens de teste.

## 5. Resultados preliminares

O pacote de referência utilizado na preparação da prova de conceito apresentou o melhor Dice de validação na época 21. No teste, foram obtidos Dice médio de 0,5267 e IoU média de 0,3694.

**Tabela 4 — Resultados da execução de referência**

| Indicador | Resultado |
|---|---:|
| Melhor época | 21 |
| Melhor Dice de validação | 0,5883 |
| Perda no teste | 0,8626 |
| Dice médio no teste | 0,5267 |
| IoU média no teste | 0,3694 |

*Fonte: Elaborado pelo autor com base nos arquivos gerados pelo experimento (2026).*

> **Controle de rastreabilidade:** os valores da Tabela 4 correspondem à execução de referência que acompanha o projeto. Antes de usar este relatório como evidência da reprodução local, esses números devem ser comparados com `outputs/minha_reproducao_30ep/metricas.json` e substituídos caso a execução realizada no VS Code tenha produzido valores diferentes.

**Figura 1 — Curvas de perda e coeficiente Dice ao longo de 30 épocas**

![Curvas de treinamento](outputs/baseline_30ep/curvas_treinamento.png)

*Fonte: Elaborado pelo autor com base nos resultados do experimento (2026).*

As curvas mostram redução contínua da perda de treinamento e validação. O Dice cresce rapidamente nas primeiras épocas e passa a oscilar em uma faixa próxima de 0,55 a 0,59 na validação. O comportamento indica que a pipeline está aprendendo, mas que o baseline atinge um patamar limitado com a resolução e a capacidade utilizadas.

**Figura 2 — Exemplos do conjunto de teste: imagem, referência, probabilidade e máscara prevista**

![Exemplos de segmentação](outputs/baseline_30ep/exemplos_teste.png)

*Fonte: Elaborado pelo autor com base nos resultados do experimento (2026).*

A inspeção visual demonstra que a rede localiza aproximadamente a região central da íris. Entretanto, as máscaras previstas frequentemente preenchem também a pupila e não reproduzem adequadamente o formato anular da referência, além de apresentarem dificuldade nas áreas ocluídas por pálpebras e cílios. Assim, o modelo realiza uma localização grosseira da região ocular de interesse, mas ainda não uma segmentação precisa da íris.

## 6. Artefatos produzidos

**Tabela 5 — Evidências geradas pela execução**

| Arquivo | Conteúdo e finalidade |
|---|---|
| `metricas.json` | Configuração, partições, melhor época, Dice, IoU, perda, dispositivo e tempo |
| `historico.csv` | Métricas de treinamento e validação de cada época |
| `curvas_treinamento.png` | Evolução visual da perda e do Dice |
| `exemplos_teste.png` | Comparação entre imagem, máscara real, probabilidade e previsão |
| `manifesto.json` | Relação completa entre arquivos, indivíduos e partições |
| `melhor_modelo.pt` | Pesos correspondentes ao maior Dice de validação |

*Fonte: Elaborado pelo autor (2026).*

O comando empregado para reproduzir a configuração de 30 épocas é:

```powershell
python treinar_segmentacao_mmu.py --epochs 30 --base-channels 8 --batch-size 16 --height 120 --width 160 --learning-rate 0.001 --seed 42 --output-dir outputs/minha_reproducao_30ep
```

## 7. Limitações e cuidados científicos

As seguintes limitações foram identificadas:

1. o MMU não contém rótulos de condições oculares e, portanto, não permite avaliar a classificação clínica prevista no objetivo final;
2. a licença de redistribuição das imagens e máscaras ainda não está suficientemente esclarecida;
3. o conjunto possui apenas 45 indivíduos, o que limita a generalização;
4. foi avaliada somente uma arquitetura, uma divisão e uma semente aleatória;
5. a resolução reduzida favorece uma execução rápida, mas elimina detalhes de borda importantes;
6. as previsões ainda confundem a pupila com a região da íris;
7. Dice e IoU médios não mostram a dispersão dos erros entre indivíduos e condições de captura.

Esses limites impedem que os resultados sejam tratados como evidência de desempenho clínico. O valor científico da etapa está na criação de uma baseline reproduzível, na prevenção de vazamento entre indivíduos e na identificação dos principais pontos que precisam ser melhorados.

## 8. Próximas etapas propostas

Recomenda-se executar as próximas atividades de forma controlada, alterando um fator por vez:

1. registrar as métricas e versões exatas da execução local;
2. repetir o treinamento em maior resolução, preferencialmente 320 × 240 pixels;
3. aumentar a capacidade inicial da U-Net de 8 para 16 canais e comparar com o baseline;
4. avaliar uma função de perda mais sensível ao formato anular e ao desequilíbrio entre pixels, como Tversky ou Focal Tversky;
5. calcular a distribuição das métricas por imagem e inspecionar os piores casos;
6. repetir a avaliação com divisões por indivíduo ou validação cruzada por grupos;
7. obter autorização ou definir uma base com licença compatível para os experimentos publicáveis;
8. adquirir uma base com rótulos clínicos para iniciar a comparação entre classificação com imagem original e classificação com íris segmentada.

O próximo experimento não deve modificar simultaneamente resolução, arquitetura e função de perda. Se todas as variáveis forem alteradas de uma vez, não será possível identificar qual mudança causou eventual melhora.

## 9. Conclusão do avanço

Foi implementada e executada uma pipeline completa de segmentação supervisionada da íris. A atividade comprovou a viabilidade do carregamento, pareamento, particionamento, treinamento, seleção e teste do modelo, além de gerar evidências numéricas e visuais para acompanhamento do projeto.

O principal avanço acadêmico não é apenas o Dice obtido, mas a consolidação de um procedimento reproduzível e a identificação de um problema de numeração que poderia invalidar o treinamento. Os resultados indicam aprendizagem inicial da localização da íris, porém ainda com erros sistemáticos na exclusão da pupila e no tratamento de oclusões.

Portanto, a etapa de segmentação encontra-se tecnicamente iniciada e apta a receber experimentos de melhoria. A pergunta central da pesquisa permanece em aberto e somente poderá ser respondida após a utilização de uma base clínica e a comparação controlada entre as pipelines com e sem segmentação.

## 10. Registro recomendado no GitHub

Devem ser versionados:

- código-fonte;
- `requirements.txt`;
- documentação e este relatório;
- `metricas.json`, `historico.csv`, `manifesto.json` e figuras geradas;
- arquivo `.gitignore`.

Não devem ser versionados:

- pasta `data/`;
- arquivos compactados das bases;
- imagens e máscaras extraídas;
- ambiente `.venv/`;
- pastas `__pycache__/`;
- pesos `melhor_modelo.pt` enquanto a possibilidade de distribuir artefatos derivados não estiver esclarecida.

Um repositório privado reduz a exposição, mas não substitui a autorização de uso e redistribuição dos dados.

## Referências

GANEEVA, Yulia; MYASNIKOV, Evgeny. Development of a method for iris-based person recognition using convolutional neural networks. In: BURNAEV, Evgeny et al. (ed.). *Analysis of Images, Social Networks and Texts*. Cham: Springer International Publishing, 2022. p. 175–189. DOI: [10.1007/978-3-031-16500-9_15](https://doi.org/10.1007/978-3-031-16500-9_15).

SUMI, Mst Rumana et al. A comprehensive evaluation of iris segmentation on benchmarking datasets. *Sensors*, v. 24, n. 21, art. 7079, 2024. DOI: [10.3390/s24217079](https://doi.org/10.3390/s24217079).

KOZLOVA, Julia. *Masks for MMU Iris dataset*. Repositório de máscaras manuais. Disponível em: <https://github.com/jkozlova/Masks-for-MMU-Iris-dataset>. Acesso em: 27 ago. 2026.

MOHAMMAD, Naureen. *MMU Iris Dataset*. Kaggle. Disponível em: <https://www.kaggle.com/datasets/naureenmohammad/mmu-iris-dataset>. Acesso em: 27 ago. 2026.
