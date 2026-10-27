# Fechamento do estudo e artigo — prazo de 09/11/2026

## Prioridade

Responder qual é a menor fração nominal aprovada no protocolo UBIPr de oclusão simulada, apresentar a incerteza e explicar a influência da região afetada. Uma consulta original, lado informado e 16 candidatos do mesmo lado continuam sendo as condições do resultado. O alcance clínico precisa ficar delimitado: perda artificial de suporte não mede todas as alterações causadas por anomalias reais.

## Trabalho restante e limite de escopo

| Período planejado | Entrega prioritária |
|---|---|
| 23–25/10 | Consolidar a incerteza da fronteira. No máximo uma rodada nova com dois pontos, superior 0,5% e inferior 1,5%, sem mudar o reconhecedor ou recalibrar. Registrar perdas efetivas em pixels, falhas e referências vazias. |
| 26–29/10 | Fechar tabelas, figuras reais, protocolo, limitações e conclusões quantitativas. Conferir reprodução a partir dos artefatos preservados. |
| 30/10–03/11 | Consolidar o texto no modelo de artigo do PFC I, conferir referências, método e correspondência entre tabelas e arquivos. |
| 04–06/11 | Reservar para revisão com o orientador e ajustes de redação/alcance. Reuniões não foram agendadas pelo agente. |
| 07–08/11 | Conferência final de números, formatação, exportação e cópias verificadas. |
| 09/11 | Prazo de entrega informado pelo usuário. |

As datas intermediárias são uma proposta de organização, não compromissos já agendados. A rodada fracionária foi concluída em 23/10, exatamente nos dois pontos previstos: superior 0,5% aprovada; inferior 1,5% reprovada. A fronteira nominal passou a 99,5% na superior e permaneceu em 99% na inferior, na grade irregular estudada. Não foi avaliado o nível inferior de 0,5%; o prefixo comum às orientações continua em 100% entre os níveis coincidentes. Não serão acrescentados novos pontos nesta rodada. A prioridade seguinte é consolidar as evidências no artigo. Ver [resultado e alcance](FRONTEIRA_REFINADA_2026-10-23.md).

## Uso econômico das interações

- Reaproveitar escores, contagens e fontes; cálculos numéricos executados localmente com roteiros reproduzíveis.
- Fechar uma pergunta por rodada e preservar os resultados antes de avançar; resumos curtos no chat, detalhes nos arquivos.
- Usar no máximo os dois novos níveis definidos para refinar os intervalos já conhecidos; não abrir novas bases, modelos ou varreduras de hiperparâmetros durante o fechamento.
- Manter limiar, cadastro e modelo congelados; não repetir execuções concluídas para procurar um resultado melhor.
- Executar verificações direcionadas quando só a análise muda, e ampliar testes quando uma mudança ou falha justificar.
- Preservar dados e modelos por artefatos verificáveis, mantendo o Defender sem exceções amplas.

Esse limite controla o volume de trabalho e interações, sem prometer um consumo exato de tokens ou cotas. A análise de incerteza de 23/10 já foi concluída reaproveitando seis condições, sem novo treino ou inferência.

## Critério de encerramento científico

O artigo deve distinguir mínimo pontual da grade, incerteza de amostragem e impossibilidade de inferir um mínimo clínico universal com os dados atuais. Resultados negativos das adaptações podem ser resumidos como desenvolvimento, sem transformar a quantidade de tentativas no argumento central. Não é necessário reduzir artificialmente o mínimo ou superar todos os modelos para responder à pergunta delimitada.

Os resultados de teste já foram examinados: o refinamento é exploratório, não uma nova confirmação cega. Uma alegação clínica ou populacional mais ampla exigiria evidência adicional que não está sendo presumida neste cronograma.

## Reabertura do desenvolvimento solicitada em 23 de outubro

Após a consolidação inicial do artigo, o usuário solicitou continuar as melhorias. Foram concluídos os pilotos de segmentação multivista/consenso e de correção externa. Nenhum substituiu a referência; a correção externa trouxe ganho localizado na oclusão inferior. Os resultados estão em [retomada](RETOMADA_ROBUSTEZ_2026-10-23.md) e [contorno externo](CONTORNO_EXTERNO_2026-10-23.md). A segunda formulação geométrica reaproveitou as características da primeira, evitando repetir a preparação dos dados. A [adaptação polar](ADAPTACAO_POLAR_2026-10-23.md) foi rejeitada no monitor por perda frente ao controle limpo original. O [complemento geométrico fixo](COMPLEMENTO_GEOMETRICO_2026-10-23.md) preservou esse controle, mas reprovou os critérios sob oclusão. Ambos foram barrados antes da validação, sem nova inferência no teste. A referência, o prazo de 09/11 e os limites de interpretação clínica permanecem. A [adaptação mantendo a normalização original](ADAPTACAO_POLAR_ORIGINAL_2026-10-23.md) foi concluída em 12 épocas: preservou o controle limpo e melhorou ambas as oclusões, mas a FMR de 1,5139%/1,4861% barrou o avanço antes da validação. A [perda de identidade](ADAPTACAO_IDENTIDADE_POLAR_2026-10-23.md) também foi concluída em 12 épocas, com pequeno ganho de identificação, porém FMR de 1,6111%/1,5000%, sem avanço à validação. O [piloto com cadastro múltiplo e negativos difíceis](ADAPTACAO_TOP3_POLAR_2026-10-23.md) concluiu 12 épocas; a época 11 reduziu a FMR para 1,4861%/1,2917%, ainda acima de 1%, sem avanço à validação. O [piloto de penalização absoluta](ADAPTACAO_FMR_POLAR_2026-10-23.md) parou na época 8, selecionou a época 4 e reduziu a FMR para 1,4167%/1,2778%, com perda de identificação/TAR e sem avanço à validação. O diagnóstico encontrou erros distribuídos entre dezenas de consultas. O [piloto de correções espaciais de rank8 no último bloco](ENCODER_ESPACIAL_2026-10-23.md) concluiu oito épocas e selecionou a sexta, preservando o limpo e elevando o TAR superior/inferior para 80,63%/60,21% frente ao encoder sem adaptação. As FMR de 1,5833%/1,3056% mantiveram o bloqueio antes da validação. Os kernels originais não foram liberados, portanto não é teste de ajuste completo do bloco. O cache FP32 foi preservado para reutilização. O próximo trabalho deve examinar calibração, comparação e fusão nas pessoas de treino antes de ampliar novamente o treinamento. Não será recalibrado o limiar nas oclusões do monitor. Não será feita varredura de pesos ou ajuste de limiar nas oclusões para promover os candidatos rejeitados.
