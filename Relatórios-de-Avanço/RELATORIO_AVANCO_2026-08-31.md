# Relatório de avanço — correção e reavaliação do recorte da íris

| Identificação | Informação |
|---|---|
| Projeto | Influência da segmentação da íris no desempenho de redes neurais convolucionais para a classificação de alterações oculares |
| Disciplina | Projeto Final de Curso I — PFC I |
| Curso | Engenharia de Computação |
| Instituição | UniSatc |
| Acadêmico | Lucas Cardoso Rodrigues |
| Orientador | Rodrigo Ramos Silva |
| Data | 31 de agosto de 2026 |
| Etapa | Auditoria e melhoria da segmentação da íris |

## 1. Síntese

Foi realizada uma auditoria da prova de conceito construída com 450 imagens do
MMU Iris Database e 450 máscaras manuais. A inspeção revelou que a igualdade do
índice do arquivo não garantia que imagem e máscara representassem a mesma pose
ocular. Essa falha era mais importante que o tamanho da rede ou a função de
perda, pois introduzia ruído diretamente na referência supervisionada.

O pareamento foi corrigido por meio de uma atribuição de custo mínimo entre os
centros estimados nas cinco imagens e nas cinco máscaras de cada pessoa e lado.
Foram reordenadas 350 das 450 correspondências. A pipeline foi ampliada com
auditoria de qualidade, escolha do limiar exclusivamente na validação, parada
antecipada, métricas por imagem e pessoa, análise do preenchimento pupilar,
figuras de casos ordenados e testes automatizados.

## 2. Protocolo

Os 45 indivíduos foram separados com a semente 42: 32 no treinamento, 6 na
validação e 7 no teste, sem pessoas compartilhadas. A configuração escolhida foi
uma U-Net de 121.033 parâmetros, entrada em tons de cinza com 160 × 120 pixels,
oito canais iniciais, otimizador AdamW, perda BCE + Dice e aumento leve de dados.

Arquitetura, perda, resolução e filtros foram comparados usando a validação. O
teste foi preservado durante a seleção por meio da opção `--no-test`. Depois da
escolha, o modelo da melhor época foi avaliado uma vez nas 70 imagens de teste.
O limiar 0,46 também foi determinado apenas nas 60 imagens de validação.

## 3. Resultado principal

| Indicador | Valor |
|---|---:|
| Melhor época | 35 |
| Dice de validação | 0,6549 |
| Dice de teste | 0,5247 |
| IoU de teste | 0,3739 |
| Precisão | 0,4533 |
| Revocação | 0,6372 |
| Especificidade | 0,9387 |
| Razão entre área prevista e real | 1,4364 |
| Fração média da pupila preenchida | 0,6066 |

O Dice por imagem apresentou média 0,5247, desvio-padrão 0,1714, mediana 0,5140
e intervalo de 0,2093 a 0,8130. Das 70 imagens, 12 alcançaram Dice maior ou igual
a 0,70, enquanto 32 ficaram abaixo de 0,50. A dispersão impede classificar o
segmentador como robusto.

## 4. Auditoria de qualidade

A distância média de pareamento foi 22,8 pixels na resolução original, com
máximo de 88,4 pixels. Os sujeitos 10, 13 e 32 têm as maiores médias; o sujeito
10 pertence ao teste e obteve Dice médio 0,3448. A inspeção mostrou referências
incompatíveis em parte de suas imagens.

Por transparência, nenhuma imagem foi removida do resultado principal. Uma
análise de sensibilidade com limiar pré-declarado de 45 pixels exclui apenas o
sujeito 10 do teste e resulta em Dice 0,5547 e IoU 0,4004 nas 60 imagens
restantes. Esse resultado é secundário e não substitui a avaliação completa.

## 5. Efeito sobre o recorte

O Dice antigo e o atual não são diretamente comparáveis, porque a correção mudou
a referência associada a várias imagens. Indicadores geométricos e a inspeção
visual, porém, mostram melhora no comportamento desejado:

| Indicador de erro | Pipeline anterior | Pipeline corrigida |
|---|---:|---:|
| Área prevista / área real | 1,848 | 1,436 |
| Fração da pupila preenchida | 0,893 | 0,607 |
| Precisão | 0,415 | 0,453 |

A rede deixou de produzir apenas uma massa central sólida em muitos casos e
passou a manter a abertura da pupila. Persistem extensões para a esclera, perda
de trechos encobertos por pálpebras e cílios e baixa generalização em algumas
pessoas.

## 6. Experimentos de melhoria

| Configuração | Dice de validação | Resultado |
|---|---:|---|
| U-Net compacta, 160 × 120, BCE + Dice | **0,6549** | Selecionada |
| Tversky focal com ponderação de borda | 0,6454 | Não selecionada |
| Exclusão rígida de sujeitos com distância > 45 px | 0,6425 | Não selecionada |
| U-Net maior, 320 × 240 | 0,6353 | Não selecionada |

Também foi avaliada uma restrição circular após a rede. O ganho de Dice na
validação foi apenas 0,0006, insuficiente para justificar a imposição de uma
geometria rígida. Esse pós-processamento não foi incorporado.

## 7. Grau de satisfação

O resultado é **satisfatório como prova de conceito metodológica**: os dados são
auditados, a divisão impede vazamento entre pessoas, a seleção não consulta o
teste e as falhas ficam rastreáveis por imagem e sujeito.

O resultado é **parcialmente satisfatório como segmentador**. Ele localiza a
íris e já produz bons recortes em parte das imagens, mas o Dice médio de 0,525 e
a alta dispersão indicam desempenho moderado, não robusto.

O resultado é **insatisfatório como evidência final do PFC**. O MMU não contém
rótulos de alterações oculares, as licenças da cópia e das máscaras são pouco
claras, e o experimento ainda não mede se a segmentação melhora a classificação.

## 8. Novos dados recomendados

O levantamento identificou:

- MOBIUS: 3.559 imagens RGB com máscaras multiclasse de íris, pupila, esclera e
  região periocular, dentro de uma base de 16.717 imagens de 100 pessoas;
- UBIPr segmentado: máscaras para todas as amostras e licença CC BY-NC-SA 4.0;
- Warsaw-BioBase-Disease-Iris: 2.996 imagens de 230 íris, 184 afetadas e mais de
  20 condições, adequada para a etapa clínica;
- MCIS: 500 imagens visíveis com rótulos de segmentação multiclasse;
- OpenEDS: 12.759 imagens NIR com máscaras de íris, pupila e esclera;
- Notre Dame Open-Source Iris Recognition: baseline de segmentação treinado em
  múltiplas bases, inclusive imagens de olhos doentes e pós-morte.

A recomendação é solicitar MOBIUS e Warsaw imediatamente, usar UBIPr como base
de início e manter Notre Dame como comparação externa congelada.

## 9. Próximas etapas

1. Registrar e obter os termos de MOBIUS, UBIPr e Warsaw.
2. Implementar um carregador multibase com convenção única de máscara.
3. Pré-treinar a segmentação em RGB e validar em pessoas não vistas.
4. Congelar o segmentador antes do experimento clínico.
5. Comparar o mesmo classificador, nas mesmas partições, com imagem original e
   recorte de íris.
6. Aplicar análise estatística pareada e relatar incerteza entre partições.

## 10. Evidências

- Código: `pfc1-segmentacao-mmu/treinar_segmentacao_mmu.py`;
- testes: `pfc1-segmentacao-mmu/test_treinar_segmentacao_mmu.py`;
- execução: `pfc1-segmentacao-mmu/outputs/pareamento_corrigido_50ep/`;
- levantamento: `pfc1-segmentacao-mmu/DATASETS_RECOMENDADOS.md`.

## Referências principais

- VITEK, Matej et al. MOBIUS e SBVPI. Disponível em:
  <https://sclera.fri.uni-lj.si/datasets.html>. Acesso em: 31 ago. 2026.
- PROENÇA, Hugo et al. UBIRIS e UBIPr. Disponível em:
  <https://iris.di.ubi.pt/>. Acesso em: 31 ago. 2026.
- TROKIELEWICZ, Mateusz; CZAJKA, Adam; MACIEJEWICZ, Piotr. *Iris recognition in
  cases of eye pathology*. Disponível em: <https://arxiv.org/abs/1809.01040>.
- GARBIN, Stephan J. et al. *OpenEDS: Open Eye Dataset*. Disponível em:
  <https://arxiv.org/abs/1905.03702>.
- COMPUTER VISION RESEARCH LABORATORY. *Notre Dame Open-Source Iris
  Recognition*. Disponível em:
  <https://github.com/CVRL/OpenSourceIrisRecognition>. Acesso em: 31 ago. 2026.
