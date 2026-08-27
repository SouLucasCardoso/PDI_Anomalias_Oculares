# Roteiro para a reunião com o orientador

## Resumo em 40 segundos

> Eu separei o projeto em duas etapas. Enquanto aguardo uma base clínica com
> rótulos de alterações oculares, implementei e executei uma prova de conceito
> da segmentação usando o MMU e 450 máscaras manuais associadas a um trabalho de
> 2022. A divisão foi feita por pessoa, para evitar vazamento entre treino e
> teste. Uma U-Net pequena já localiza a região da íris, mas o Dice de teste foi
> 0,527, mostrando que ainda erra principalmente o recorte da pupila e oclusões.
> Portanto, não estou tratando isso como resultado clínico final, e sim como um
> baseline reproduzível que define os próximos experimentos.

## O que foi realizado

- Download e auditoria das 450 imagens do MMU e das 450 máscaras manuais.
- Identificação de uma inconsistência de numeração: as imagens usam 45 pastas
  entre 1 e 46, pulando o número 4; as máscaras usam 1 a 45. O código corrige o
  pareamento pela ordem numérica e valida todas as correspondências.
- Separação sem pessoas repetidas: 32 pessoas no treino, 6 na validação e 7 no
  teste.
- Implementação de uma U-Net pequena, aumento de dados leve, perda BCE + Dice e
  métricas Dice e IoU.
- Duas execuções exploratórias: uma curta de 10 épocas e uma de 30 épocas.
- Geração automática de pesos, manifesto da divisão, histórico, curvas e
  exemplos visuais.

## Resultado medido da execução de 30 épocas

| Item | Resultado |
|---|---:|
| Imagens / pessoas | 450 / 45 |
| Treino / validação / teste | 320 / 60 / 70 imagens |
| Parâmetros treináveis | 121.033 |
| Resolução de entrada | 160 × 120 pixels |
| Melhor época pela validação | 21 |
| Dice de validação | 0,588 |
| Dice de teste | 0,527 |
| IoU de teste | 0,369 |

O resultado indica que a rede aprendeu a localizar aproximadamente a íris, mas
ainda tende a preencher parte da pupila e perde regiões ocluídas por pálpebras e
cílios. Esse comportamento aparece nos exemplos salvos e justifica novos testes
com maior resolução, mais capacidade e funções de perda voltadas ao contorno.

## O que este resultado não demonstra

- Não classifica olhos saudáveis versus olhos com alterações.
- Não permite concluir ainda se a segmentação melhora a classificação.
- Não valida desempenho em imagens clínicas ou olhos doentes.
- Não deve ser apresentado como resultado final do artigo.

O MMU é biométrico e não possui rótulos de doenças. Ele foi usado somente para
validar a infraestrutura e estudar a primeira etapa do pipeline.

## Próximos experimentos propostos

1. Repetir o treino em 320 × 240 pixels com U-Net de maior capacidade.
2. Comparar BCE + Dice com Focal/Tversky, mantendo exatamente a mesma divisão.
3. Medir média, dispersão e exemplos de sucesso/falha; depois selecionar uma
   configuração de segmentação sem usar o conjunto de teste para ajustes.
4. Continuar a solicitação da Warsaw-BioBase-Disease-Iris para o experimento
   clínico com e sem segmentação.
5. Iniciar Materiais e Métodos com o protocolo já definido, deixando a base
   clínica como item pendente de autorização.

## Decisões para pedir ao orientador

1. O orientador aprova o MMU apenas como base provisória de desenvolvimento da
   segmentação?
2. A regra de referências dos últimos cinco anos permite uma base clássica como
   material, desde que o método e as discussões sejam sustentados por artigos de
   2022–2026?
3. Caso a Warsaw não seja liberada, qual alternativa ele aprova: outra base
   clínica, anotação de uma amostra ou ajuste do escopo?
4. Devemos solicitar por escrito autorização para as máscaras, já que o
   repositório não possui licença explícita e o Kaggle informa licença
   `Unknown`?

## Referências recentes para citar na conversa

- Ganeeva e Myasnikov (2022) descrevem CNNs nas etapas de segmentação e extração
  de características no MMU e informam o compartilhamento das máscaras manuais.
- Sumi et al. (2024) apresentam uma avaliação abrangente de métodos de
  segmentação em diferentes bases e reforçam a necessidade de avaliação em
  composições variadas de dados.
