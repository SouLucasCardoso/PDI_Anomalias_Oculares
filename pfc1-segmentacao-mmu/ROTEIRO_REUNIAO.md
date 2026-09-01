# Roteiro para a reunião com o orientador

## Resumo em 50 segundos

> A auditoria visual mostrou que a numeração interna das imagens e máscaras do
> MMU não representa a mesma pose. Corrigi os pares por atribuição geométrica,
> e 350 das 450 correspondências mudaram. Com divisão por pessoa e seleção só
> pela validação, a U-Net obteve Dice 0,655 na validação e 0,525 no teste
> completo. O valor é moderado, mas o recorte passou a preservar melhor a pupila
> e reduziu a área excedente. Um sujeito do teste ainda possui referências
> incompatíveis; por transparência, ele permanece na métrica principal. Pesquisei
> bases melhores: recomendo MOBIUS e UBIPr para segmentação, Warsaw
> Disease-Iris para a etapa clínica e um modelo aberto da Notre Dame como
> baseline externo. A infraestrutura está satisfatória; o segmentador ainda não
> é resultado final.

## O que foi corrigido

- Pareamento em dois níveis: pastas de pessoas e, dentro de cada lado, atribuição
  das cinco máscaras pelos centros estimados da íris.
- Auditoria salva no manifesto: 350 pares reordenados, distância média de 22,8
  pixels na resolução original e sujeitos suspeitos identificados.
- Divisão sem vazamento: 32 pessoas no treino, 6 na validação e 7 no teste.
- Limiar escolhido só na validação; opção `--no-test` para comparar configurações
  sem consultar o teste.
- Métricas por imagem e pessoa, análise da pupila, razão de área e exemplos do
  pior ao melhor resultado.
- Testes automatizados para pareamento, cavidade pupilar e função de perda.

## Resultado atual

| Item | Resultado |
|---|---:|
| Imagens / pessoas | 450 / 45 |
| Treino / validação / teste | 320 / 60 / 70 |
| Parâmetros treináveis | 121.033 |
| Resolução | 160 × 120 |
| Melhor época | 35 |
| Limiar escolhido na validação | 0,46 |
| Dice de validação | 0,6549 |
| Dice / IoU de teste | 0,5247 / 0,3739 |
| Precisão / revocação | 0,4533 / 0,6372 |
| Área prevista / real | 1,436 |
| Pupila preenchida | 0,607 |

O sujeito 10 tem a pior qualidade de referência entre as pessoas de teste. Sem
ele, apenas como análise de sensibilidade, o Dice é 0,5547 em 60 imagens. O valor
oficial continua sendo 0,5247 nas 70 imagens.

## Interpretação honesta

- **Satisfatório:** rastreabilidade, divisão por pessoa, ausência de ajuste pelo
  teste, diagnóstico do erro de rótulo e geração de evidências.
- **Parcialmente satisfatório:** localização e formato geral da íris; há bons
  casos, com 12 imagens acima de Dice 0,70.
- **Insatisfatório para conclusão final:** dispersão alta, 32 imagens abaixo de
  Dice 0,50, dificuldade com oclusões e ausência de avaliação clínica.

A pequena diferença em relação ao Dice do pipeline antigo não representa piora
direta, pois a referência foi corrigida. Os sinais qualitativos mais úteis foram
a redução da razão de área de aproximadamente 1,85 para 1,44 e da fração pupilar
preenchida de aproximadamente 0,89 para 0,61.

## Experimentos rejeitados pela validação

| Alteração | Dice de validação | Decisão |
|---|---:|---|
| Configuração compacta, BCE + Dice | **0,6549** | Manter |
| Focal Tversky com peso de borda | 0,6454 | Rejeitar |
| Exclusão rígida de sujeitos suspeitos | 0,6425 | Rejeitar como treino padrão |
| Resolução 320 × 240 e rede maior | 0,6353 | Rejeitar nesta amostra |

Uma restrição circular pós-processada melhorou a validação em apenas 0,0006 e
também foi rejeitada por impor uma geometria rígida sem benefício material.

## Bases recomendadas

1. **MOBIUS:** 3.559 imagens RGB com máscaras de íris, pupila, esclera e região
   periocular. Melhor opção para formar o segmentador visível.
2. **UBIPr segmentado:** máscaras para todas as amostras e licença
   CC BY-NC-SA 4.0. Melhor opção para começar imediatamente.
3. **Warsaw-BioBase-Disease-Iris:** 2.996 imagens de 230 íris e mais de 20
   condições; base prioritária para responder à pergunta clínica.
4. **MCIS/OpenEDS:** validação externa complementar; OpenEDS tem 12.759 máscaras,
   mas domínio NIR de headset VR.
5. **Notre Dame Open-Source Iris Recognition:** segmentador externo treinado em
   várias bases, incluindo Warsaw, para comparação independente.

## Decisões para o orientador

1. Aprovar o MMU apenas como prova de conceito, sem usá-lo como evidência clínica.
2. Autorizar a solicitação do MOBIUS e da Warsaw Disease-Iris em nome do projeto.
3. Definir a tarefa clínica: binária, por grupos de impacto ou multirrótulo por
   patologia.
4. Aprovar o protocolo pareado: mesmo classificador e mesmas partições, mudando
   apenas a entrada original versus a entrada segmentada.
5. Decidir se o modelo da Notre Dame deve ser um terceiro braço experimental.
6. Confirmar como documentar bases clássicas quando as referências metodológicas
   principais precisam estar na janela 2022–2026.

## Próxima execução recomendada

1. Solicitar MOBIUS e Warsaw; registrar licenças e versões.
2. Preparar o carregador multibase e a conversão de rótulos para íris visível.
3. Pré-treinar em UBIPr/MOBIUS e medir generalização por pessoa.
4. Congelar o segmentador e abrir somente então a partição clínica de teste.
5. Comparar estatisticamente a classificação com e sem recorte.

Detalhes e links estão em `DATASETS_RECOMENDADOS.md`; os resultados completos
estão em `outputs/pareamento_corrigido_50ep/`.
