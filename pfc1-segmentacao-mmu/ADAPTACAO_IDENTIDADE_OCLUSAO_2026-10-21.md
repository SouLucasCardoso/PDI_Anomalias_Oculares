# Adaptação do reconhecedor a oclusões — 21/10/2026

## Situação e decisão

Foram executadas duas estratégias usando somente treino e validação: adaptação por gradiente com professor limpo e correção residual linear com o extrator congelado. Nenhuma foi promovida ao lugar do candidato aprovado. O teste não foi inferido nesta rodada, não houve nova estimativa de área mínima e o benchmark anterior continua associado ao modelo original.

São 7.716 imagens de 183 pessoas de treino e 482 consultas de 16 pessoas na validação, com 16 candidatos do lado informado por consulta. Todas as falhas de consulta foram mantidas. Na formação dos pares de treino, 7.640 imagens tinham recortes válidos tanto para o aluno quanto para o professor; as exclusões ocorreram somente no treino.

## 1. Adaptação por gradiente

O aluno recebeu recortes nativos do novo segmentador, reduzidos a 128 × 128, com oclusão cinza aleatória em 50% dos exemplos, perda de 1–40% no suporte previsto do recorte, rotação e pequenas variações de contraste/brilho. O professor congelado forneceu embeddings dos recortes automáticos limpos anteriores da mesma imagem de treino. O professor não participa da inferência e não restaura textura.

Foram reutilizados o ResNet18 e o classificador angular de 366 olhos de treino. A perda combinou classificação angular, contraste supervisionado e retenção do embedding do professor. As estatísticas de BatchNorm permaneceram congeladas. Cada checkpoint calibrou um limiar na validação limpa, aplicado sem mudança às oclusões.

A seleção exigiu melhorar a pior TAR sem perder mais de dois pontos percentuais nas métricas limpas do reconhecedor inicial. Essa trava é de desenvolvimento e não substitui o critério final de 90%.

| Época | Rank-1 limpo | TAR limpa | Rank-1 superior 10% | TAR superior 10% | Rank-1 inferior 10% | TAR inferior 10% | Trava limpa |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 |74,48%|60,58%|59,54%|41,29%|63,90%|45,23%|Passou|
| 1 |69,29%|51,04%|68,67%|46,06%|65,56%|41,08%|Reprovou|
| 2 |69,71%|53,11%|72,61%|48,34%|68,26%|46,68%|Reprovou|
| 3 |70,12%|52,28%|72,41%|47,93%|67,84%|46,89%|Reprovou|

O treino terminou após três épocas por paciência, dentro do limite registrado de seis. A seleção permaneceu na **época 0**: nenhuma época treinada passou na trava limpa. A verificação confirmou zero tensores diferentes no encoder selecionado em relação ao original. O hash do arquivo mudou por conter outro protocolo; isso não representa alteração dos pesos selecionados.

As métricas acima são do componente ResNet18 isolado; não são os 90% da fusão completa.

## 2. Correção residual sem alterar o extrator

A segunda estratégia fixou integralmente o CNN e aprendeu uma correção 512 → 256 para aproximar embeddings de recortes novos/ocluídos dos embeddings limpos do professor. A regressão ridge usou regularização 1 e estatísticas calculadas somente no treino, sem busca de hiperparâmetros ou seleção de época pela validação. Cada par de treino gerou uma vista limpa com peso 2 e duas ocluídas com peso 1 cada, com perdas amostradas de 1% a 40%. A correção atua em embeddings, não em pixels.

| Componente isolado | Condição | Rank-1 | TAR | FMR |
|---|---|---:|---:|---:|
| Inicial |Limpa|74,48%|60,58%|0,98%|
| Residual |Limpa|75,10%|58,71%|0,98%|
| Inicial |Superior 10%|59,54%|41,29%|1,04%|
| Residual |Superior 10%|65,98%|39,42%|0,66%|
| Inicial |Inferior 10%|63,90%|45,23%|1,04%|
| Residual |Inferior 10%|63,28%|42,32%|0,94%|

Houve recuperação de Rank-1 em parte das condições, mas não melhora conjunta de TAR e Rank-1. Os escores das três condições foram reproduzidos exatamente após recarregar checkpoint e parâmetros: diferença máxima **0**. O extrator permaneceu idêntico ao original.

## 3. Comparação na fusão completa

Foram registradas previamente cinco combinações fixas de controles/candidatos. As principais abaixo usam o pipeline original, o híbrido com apenas o componente RGB novo, ou todos os componentes com a segmentação ajustada. A calibração de cada combinação usou somente a validação limpa: médias/desvios por componente e um limiar para FMR ≤1%, aplicados sem recalibração às oclusões. Não houve busca dos pesos da fusão. O híbrido calcula duas segmentações da mesma foto, sem exigir outra captura.

| Configuração | Condição | Rank-1 | TAR | FMR |
|---|---|---:|---:|---:|
| Original |Limpa|90,04%|90,66%|0,98%|
| Híbrido residual |Limpa|89,83%|90,25%|0,98%|
| Segmentação ajustada + residual |Limpa|88,59%|89,21%|0,98%|
| Original |Superior 10%|80,71%|78,01%|1,30%|
| Híbrido residual |Superior 10%|79,46%|77,18%|1,18%|
| Segmentação ajustada + residual |Superior 10%|79,67%|73,44%|1,16%|
| Original |Inferior 10%|59,96%|57,88%|2,41%|
| Híbrido residual |Inferior 10%|64,32%|61,41%|2,07%|
| Segmentação ajustada + residual |Inferior 10%|81,33%|79,67%|1,12%|

No híbrido residual, a condição limpa teve **433/482** identificações corretas: uma a menos que o mínimo de 434. A condição inferior melhorou em relação ao controle, mas a superior piorou. Não se alterou o limiar para obter aprovação.

Como a adaptação por gradiente selecionou a época 0, seus resultados finais coincidem com o respectivo controle sem adaptação; não se pode atribuí-los ao treinamento. Os controles permitem separar mudanças de segmentação/calibração do efeito da correção residual. Todos os controles e parâmetros estão nos arquivos de evidência.

## 4. Conclusão desta rodada

A adaptação por gradiente não preservou suficientemente o desempenho limpo. A correção linear evitou alterar os pesos originais, mas os ganhos parciais não bastaram para aprovar uma nova fusão. Esses resultados não justificam substituir o modelo que obteve **91,36% de Rank-1 no teste anterior**. A referência e as fronteiras de área anteriormente relatadas ficam inalteradas.

A próxima estratégia deve priorizar descritores locais e comparação das regiões válidas da íris, em vez de depender apenas de um vetor global alterado pela oclusão. Aprendizagem, seleção e calibração novas devem permanecer no treino/validação. Não há novo resultado de teste ou mínimo clínico nesta rodada.

Foram aprovados **67 testes automatizados**. Protocolos, históricos, modelos, controles, escores e verificação de recarregamento foram preservados. As limitações de reutilização da validação e de pré-treinamento externo desconhecido continuam válidas.

## Evidências

- [Treino com professor](outputs/identidade_oclusao_segmentacao_2026-10-21/CONCLUIDO.json).
- [Correção residual](outputs/identidade_residual_oclusao_2026-10-21/CONCLUIDO.json).
- [Recarregamento verificado](outputs/identidade_residual_oclusao_2026-10-21/VERIFICACAO_RELOAD.json).
- [Fusão completa e controles](outputs/fusao_identidade_residual_val_2026-10-21/CONCLUIDO.json).
