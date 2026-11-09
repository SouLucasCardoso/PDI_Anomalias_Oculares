# Resultados e respostas para a defesa do PFC

O estudo demonstra sensibilidade da cadeia à quantidade e à posição da oclusão. O percentual observado depende do protocolo; não foi estabelecido mínimo anatômico universal nem efeito causal de doenças.

## Resultado central

“Na população e na cadeia avaliadas, retirar parte do suporte de íris alterou a identificação e as falsas correspondências. Com a mesma perda de 31%, o Rank-1 foi 69,34% na orientação superior e 32,51% na inferior. A posição da informação preservada e a estabilidade do processamento importaram, além da quantidade restante.”

## Estimativa pontual e incerteza

| Medida do controle | Contagem | Estimativa | Intervalo descritivo de 95% | Alvo pontual |
|---|---:|---:|---:|---:|
| Rank-1 | 443/486 | 91,15% | 84,79% a 95,83% | ≥90% |
| TAR | 449/486 | 92,39% | 86,25% a 96,75% | ≥90% |
| FMR | 63/7290 | 0,864% | 0,514% a 1,278% | ≤1% |
| Correto e aceito | 435/486 | 89,51% | 82,92% a 94,44% | ≥90% na regra posterior |

![Incerteza do controle e alvos pontuais](controle_incerteza.png)

O controle passou pelos três alvos marginais nas estimativas pontuais. Os intervalos ultrapassam seus limites; essa incerteza impede apresentar o resultado como garantia populacional. Os intervalos são ponto a ponto, condicionados à galeria fixa, e não corrigem a seleção ou exposição prévia ao teste. Não formam uma certificação simultânea de 95%.

## Qual é o percentual mínimo observado?

| Interpretação da grade atual | Superior | Inferior |
|---|---:|---:|
| Menor suporte nominal no prefixo com os três alvos marginais pontuais | 100% | 99% |
| Exigindo também correto e aceito de pelo menos 90% | Nenhum nível aprovado | Nenhum nível aprovado |
| Intervalos descritivos inteiramente dentro dos três alvos | Nenhum nível | Nenhum nível |

Essas linhas respondem a perguntas diferentes. Na perda superior de 1%, o controle teve 437 acertos; seriam necessários 438 para chegar a 90% em 486 consultas. O refinamento histórico de outra execução encontrou 99,5% no alto e 99% embaixo, em grade e ambiente próprios. Não se misturam esses valores com os da rodada atual nem se interpolam pontos ausentes.

## Como responder às perguntas mais prováveis

**Isso comprova a regra de 70%?** A perda de 30% deixou 70% do suporte originalmente anotado; a perda de 31% deixou 69%. Esse denominador não é uma medição normativa do anel completo. A mudança entre os dois níveis não demonstrou ruptura em 70%; os intervalos pareados das perdas de Rank-1 incluíram zero.

**Foi isolada a influência da área?** A quantidade nominal retirada foi controlada, com cadastro e limiar fixos. A máscara e a geometria foram recalculadas após a intervenção; o efeito observado reúne textura removida e instabilidade de processamento. O diagnóstico assistido por geometria limpa ajuda a investigar esse mecanismo, mas depende da fotografia original disponível.

**Por que não adotar o candidato com mais acertos?** O candidato polar ganhou seis acertos líquidos com 1% de perda superior, mas piorou em condições severas e aumentou falsas correspondências em partes da grade. A regra completa foi preservada; uma melhora localizada não autorizou a troca geral.

**E o SAM3.1?** Foi avaliado em segmentação e geometria. Houve ganho localizado de validação, mas o controle limpo piorou. Os treinos e ablações não cumpriram a seleção registrada. A curva principal preserva a referência histórica de identidade; resultados de aparência ou Dice não foram tratados como prova de reconhecimento.

**Posso concluir o efeito de patologias?** A extensão clínica tem quatro consultas de apenas dois olhos, sem pares saudáveis equivalentes dos mesmos olhos. Ela documenta falhas de transferência e a necessidade de referências revisadas; não estima causalmente o efeito de uma doença ou seu percentual anatômico mínimo.

**O resultado vale para o celular?** A curva usa UBIPr entre sessões, lateralidade informada e dezesseis candidatos do mesmo lado. O aplicativo do S23 é um demonstrador separado, sem limiar clínico ou acurácia móvel validados por esta curva.

## Conferência dos dados

Foram conferidas as contagens e os hashes dos escores das 13 condições, mantendo 486 consultas e 7.290 pares impostores por condição. As seis referências de área vazia permanecem no denominador primário; a análise secundária fixa usa as mesmas 480 referências definidas. Não houve novo treinamento, inferência, ajuste de limiar ou seleção de modelo nesta consolidação.

[Artigo atualizado](../../artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx). [Auditoria desta consolidação](AUDITORIA_DEFESA.json). [Curva completa e fontes](../ensaio_oclusoes_2026-11-08/analise_final/RESULTADO_PARA_DEFESA.md).
